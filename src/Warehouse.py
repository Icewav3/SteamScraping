# src/Warehouse.py
"""Warehouse - Columnar store over the daily snapshots, queryable with DuckDB.

Ingests raw Data/<date>/ jsonl (via Snapshots cleaning/validation) into
hive-partitioned Parquet under Warehouse/, tracks per-day status in a
manifest, and derives a day-over-day change table:

    Warehouse/
      manifest.json                       per-day ingest status & stats
      steamspy/date=YYYY-MM-DD/data.parquet
      igdb/date=YYYY-MM-DD/data.parquet
      steam/date=YYYY-MM-DD/data.parquet
      igdb_links/date=YYYY-MM-DD/data.parquet   IGDB <-> Steam appid links
      steamspy_changes/date=YYYY-MM-DD/data.parquet

Changes are computed between consecutive FULL steamspy days (partial
html-fallback days are bridged over, `gap_days` records the distance) so a
200-app fallback day never floods the deltas with fake disappearances.

Usage:
    uv run python -m src.Warehouse build     # incremental; safe to re-run
    uv run python -m src.Warehouse status    # coverage, gaps, failures

    from src.Warehouse import Warehouse
    con = Warehouse().connect()              # DuckDB with views:
    con.sql("SELECT ... FROM steamspy ...")  # steamspy, igdb, steam,
                                             # igdb_links, igdb_steam_map,
                                             # steamspy_changes, snapshot_days
"""
import json
from dataclasses import asdict
from datetime import date as date_type, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from .Snapshots import (DayFiles, DayReport, discover, load_igdb_day,
                        load_igdb_links_day, load_steam_day, load_steamspy_day)

STEAMSPY_SCHEMA = pa.schema([
    ("appid", pa.int64()),
    ("name", pa.string()),
    ("developer", pa.string()),
    ("publisher", pa.string()),
    ("positive", pa.int64()),
    ("negative", pa.int64()),
    ("userscore", pa.int64()),
    ("owners", pa.string()),
    ("owners_low", pa.int64()),
    ("owners_high", pa.int64()),
    ("average_forever", pa.int64()),
    ("average_2weeks", pa.int64()),
    ("median_forever", pa.int64()),
    ("median_2weeks", pa.int64()),
    ("price_cents", pa.int64()),
    ("initialprice_cents", pa.int64()),
    ("discount_pct", pa.int64()),
    ("ccu", pa.int64()),
    ("languages", pa.string()),
    ("genre", pa.string()),
    ("score_rank", pa.string()),
    ("tags", pa.list_(pa.struct([("tag", pa.string()), ("votes", pa.int64())]))),
])

IGDB_SCHEMA = pa.schema([
    ("igdb_id", pa.int64()),
    ("name", pa.string()),
    ("rating", pa.float64()),
    ("rating_count", pa.int64()),
    ("aggregated_rating", pa.float64()),
    ("aggregated_rating_count", pa.int64()),
    ("first_release_date", pa.int64()),  # epoch seconds; view exposes release_date
    ("genres", pa.list_(pa.string())),
    ("platforms", pa.list_(pa.string())),
    ("companies", pa.list_(pa.string())),
])

STEAM_SCHEMA = pa.schema([
    ("appid", pa.int64()),
    ("name", pa.string()),
    ("visible", pa.bool_()),
    ("parent_appid", pa.int64()),
    ("review_count", pa.int64()),
    ("percent_positive", pa.int64()),
    ("review_score", pa.int64()),
    ("review_score_label", pa.string()),
    ("player_count", pa.int64()),
])

IGDB_LINKS_SCHEMA = pa.schema([
    ("igdb_id", pa.int64()),
    ("steam_appid", pa.int64()),
])

_LOADERS = {"steamspy": (load_steamspy_day, STEAMSPY_SCHEMA),
            "igdb": (load_igdb_day, IGDB_SCHEMA),
            "steam": (load_steam_day, STEAM_SCHEMA),
            "igdb_links": (load_igdb_links_day, IGDB_LINKS_SCHEMA)}


class Warehouse:
    def __init__(self, warehouse_dir: str = "Warehouse", data_dir: str = "Data"):
        self.root = Path(warehouse_dir)
        self.data_dir = data_dir
        self.manifest_path = self.root / "manifest.json"
        self.manifest: Dict[str, Dict[str, Any]] = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Dict[str, Any]]:
        if self.manifest_path.exists():
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return {}

    def _save_manifest(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.manifest_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.manifest, indent=2, sort_keys=True),
                       encoding="utf-8")
        tmp.replace(self.manifest_path)

    def _partition_path(self, table: str, date: str) -> Path:
        return self.root / table / f"date={date}" / "data.parquet"

    # ------------------------------------------------------------- ingest

    def _needs_ingest(self, source: str, files: DayFiles) -> bool:
        entry = self.manifest.get(source, {}).get(files.date)
        if entry is None or entry.get("input_size") != files.data_path.stat().st_size:
            return True
        return entry["status"] != "fail" and not self._partition_path(source, files.date).exists()

    def _ingest_day(self, source: str, files: DayFiles) -> DayReport:
        loader, schema = _LOADERS[source]
        records, report = loader(files)

        if report.ok:
            table = pa.Table.from_pylist(records, schema=schema)
            dest = self._partition_path(source, files.date)
            dest.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(table, dest, compression="zstd")

        entry = asdict(report)
        entry["status"] = ("fail" if not report.ok
                           else "partial" if report.partial else "ok")
        entry["input_size"] = files.data_path.stat().st_size
        self.manifest.setdefault(source, {})[files.date] = entry
        return report

    def build(self, rebuild: bool = False, progress_callback=None) -> Dict[str, List[str]]:
        """Incrementally ingest all days and derive changes.

        Returns {"ingested": [...], "failed": [...], "changes": [...]}.
        """
        found = discover(self.data_dir)
        result: Dict[str, List[str]] = {"ingested": [], "failed": [], "changes": []}

        for source in _LOADERS:
            days = found[source]
            todo = [f for d, f in sorted(days.items())
                    if rebuild or self._needs_ingest(source, f)]
            for i, files in enumerate(todo):
                if progress_callback:
                    progress_callback(i, len(todo), f"{source} {files.date}")
                report = self._ingest_day(source, files)
                key = f"{source}/{files.date}"
                (result["ingested"] if report.ok else result["failed"]).append(key)
            self._save_manifest()

        result["changes"] = self._build_changes(rebuild)
        self._save_manifest()
        return result

    # ------------------------------------------------------------ changes

    def _full_steamspy_days(self) -> List[str]:
        return sorted(d for d, e in self.manifest.get("steamspy", {}).items()
                      if e["status"] == "ok")

    def _build_changes(self, rebuild: bool = False) -> List[str]:
        days = self._full_steamspy_days()
        built = []
        changes_manifest = self.manifest.setdefault("steamspy_changes", {})

        con = duckdb.connect()
        for prev, cur in zip(days, days[1:]):
            entry = changes_manifest.get(cur)
            dest = self._partition_path("steamspy_changes", cur)
            if not rebuild and entry and entry.get("prev") == prev and dest.exists():
                continue

            gap = (date_type.fromisoformat(cur) - date_type.fromisoformat(prev)).days
            dest.parent.mkdir(parents=True, exist_ok=True)
            prev_pq = self._partition_path("steamspy", prev).as_posix()
            cur_pq = self._partition_path("steamspy", cur).as_posix()
            con.execute(f"""
                COPY (
                    SELECT
                        coalesce(c.appid, p.appid)      AS appid,
                        coalesce(c.name, p.name)        AS name,
                        p.appid IS NULL                 AS appeared,
                        c.appid IS NULL                 AS disappeared,
                        {gap}                           AS gap_days,
                        c.positive - p.positive         AS d_positive,
                        c.negative - p.negative         AS d_negative,
                        c.ccu - p.ccu                   AS d_ccu,
                        c.average_2weeks - p.average_2weeks AS d_average_2weeks,
                        c.price_cents - p.price_cents   AS d_price_cents,
                        p.owners_low                    AS prev_owners_low,
                        c.owners_low                    AS owners_low,
                        (c.owners_low IS NOT NULL AND p.owners_low IS NOT NULL
                         AND c.owners_low != p.owners_low) AS owners_changed
                    FROM read_parquet('{cur_pq}') c
                    FULL OUTER JOIN read_parquet('{prev_pq}') p USING (appid)
                ) TO '{dest.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)
            """)
            changes_manifest[cur] = {"prev": prev, "gap_days": gap}
            built.append(cur)
        con.close()
        return built

    # -------------------------------------------------------------- query

    def connect(self) -> duckdb.DuckDBPyConnection:
        """DuckDB connection with views over the full history.

        Views: one per source plus steamspy_changes (`date` typed DATE),
        igdb_steam_map (newest day's links; NOT one-to-one) and
        snapshot_days (per-day ingest status).
        """
        con = duckdb.connect()
        for table in (*_LOADERS, "steamspy_changes"):
            glob = (self.root / table / "*" / "*.parquet").as_posix()
            if not any((self.root / table).glob("date=*/data.parquet")):
                continue
            extra = (", (TIMESTAMP '1970-01-01' + first_release_date * INTERVAL 1 SECOND)::DATE"
                     " AS release_date" if table == "igdb" else "")
            con.execute(f"""
                CREATE VIEW {table} AS
                SELECT * REPLACE (CAST(date AS DATE) AS date){extra}
                FROM read_parquet('{glob}', hive_partitioning = true,
                                  union_by_name = true)
            """)

        # igdb_id is stable, so the newest good link day joins every igdb day.
        # The date is taken from the manifest and inlined: DuckDB 1.5.4 raises an
        # INTERNAL error filtering hive partitions by (SELECT max(date) ...).
        link_days = sorted(d for d, e in self.manifest.get("igdb_links", {}).items()
                           if e["status"] == "ok"
                           and self._partition_path("igdb_links", d).exists())
        if link_days:
            con.execute(f"""
                CREATE VIEW igdb_steam_map AS
                SELECT DISTINCT igdb_id, steam_appid FROM igdb_links
                WHERE date = DATE '{date_type.fromisoformat(link_days[-1]).isoformat()}'
            """)

        rows = [(s, d, e["status"], e.get("rows"), e.get("mode"))
                for s in _LOADERS
                for d, e in sorted(self.manifest.get(s, {}).items())]
        con.execute("""
            CREATE TABLE snapshot_days (source VARCHAR, date DATE, status VARCHAR,
                                        rows BIGINT, mode VARCHAR)
        """)
        if rows:
            con.executemany("INSERT INTO snapshot_days VALUES (?, ?, ?, ?, ?)", rows)
        return con

    # -------------------------------------------------------------- status

    def status(self) -> str:
        lines = []
        for source in _LOADERS:
            entries = self.manifest.get(source, {})
            if not entries:
                lines.append(f"{source}: no days ingested")
                continue
            days = sorted(entries)
            by_status: Dict[str, int] = {}
            for e in entries.values():
                by_status[e["status"]] = by_status.get(e["status"], 0) + 1
            first, last = days[0], days[-1]
            span = (date_type.fromisoformat(last) - date_type.fromisoformat(first)).days + 1
            missing = span - len(days)
            lines.append(f"{source}: {len(days)} days ({first} → {last}), "
                         f"{missing} missing in span, status counts {by_status}")
            for d in days:
                e = entries[d]
                if e["status"] != "ok":
                    detail = e.get("mode") or ",".join(e.get("issues") or []) or f"rows={e.get('rows')}"
                    lines.append(f"  {e['status']:>7}  {d}  ({detail})")
        changes = self.manifest.get("steamspy_changes", {})
        lines.append(f"steamspy_changes: {len(changes)} day-pairs")
        return "\n".join(lines)

    def missing_dates(self, source: str = "steamspy") -> List[str]:
        """Dates with no snapshot between the first and last ingested day."""
        days = sorted(self.manifest.get(source, {}))
        if not days:
            return []
        cur = date_type.fromisoformat(days[0])
        end = date_type.fromisoformat(days[-1])
        have = set(days)
        out = []
        while cur <= end:
            if cur.isoformat() not in have:
                out.append(cur.isoformat())
            cur += timedelta(days=1)
        return out


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Build/inspect the snapshot warehouse")
    parser.add_argument("command", choices=["build", "status"])
    parser.add_argument("--rebuild", action="store_true",
                        help="re-ingest every day even if unchanged")
    parser.add_argument("--data-dir", default="Data")
    parser.add_argument("--warehouse-dir", default="Warehouse")
    args = parser.parse_args()

    wh = Warehouse(args.warehouse_dir, args.data_dir)
    if args.command == "status":
        print(wh.status())
        sys.exit(0)

    from tqdm import tqdm
    bar = tqdm(desc="Ingesting", unit="day")

    def progress(i, total, label):
        bar.total = total
        bar.n = i
        bar.set_postfix_str(label)
        bar.refresh()

    result = wh.build(rebuild=args.rebuild, progress_callback=progress)
    bar.close()
    print(f"✓ ingested {len(result['ingested'])} days, "
          f"changes for {len(result['changes'])} day-pairs")
    if result["failed"]:
        print(f"✗ FAILED days: {result['failed']}", file=sys.stderr)
        sys.exit(1)
