# src/Snapshots.py
"""Snapshots - Discovery and validated loading of daily scrape output.

Handles every layout generation that exists in Data/:
  1. Oldest local days:  Data/<date>/steamspy_data.jsonl (files at date root)
  2. Current layout:     Data/<date>/<ScraperName>/<prefix>_<file>
  3. ReleaseSync output: same as (2) — sync normalizes release asset names

Loading a day returns cleaned records plus a DayReport describing everything
that was repaired or rejected, so ingest can fail loudly instead of letting
bad data through silently.

Known quirks handled here (see DATA.md):
  - retry/resume runs append duplicate appids within a day → dedupe, keep last
  - `owners` is a bucket string like "20,000 .. 50,000" → parsed to low/high
  - price/initialprice/discount are strings, occasionally missing/None
  - `tags` is a dict tag→votes, but an empty *list* when the game has no tags
  - HTML-fallback days (~200 apps, mode=html_fallback) have None for
    appdetails-only fields and must be flagged partial
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# A full SteamSpy API run covers ~10k games; fallback days are far smaller.
STEAMSPY_FULL_DAY_MIN_ROWS = 5000
IGDB_FULL_DAY_MIN_ROWS = 15000
# Steam covers the same ~10k catalog; a run with < 5000 apps is partial.
STEAM_FULL_DAY_MIN_ROWS = 5000
# IGDB has far more Steam links than this; fewer means a truncated pull.
IGDB_LINKS_FULL_DAY_MIN_ROWS = 1000

# Search order per source: (subdir, data file, metadata candidates)
_LAYOUTS = {
    "steamspy": [
        ("SteamSpyScraper", "steamspy_data.jsonl",
         ["steamspy_metadata.json", "metadata.json"]),
        ("", "steamspy_data.jsonl",
         ["steamspy_metadata.json", "metadata.json", "daily_metadata.json"]),
    ],
    "igdb": [
        ("IGDBScraper", "igdb_data.jsonl", ["igdb_metadata.json", "metadata.json"]),
        ("", "igdb_data.jsonl", ["igdb_metadata.json", "metadata.json"]),
    ],
    # Steam is a new source (2026-07): current-layout subdir only, no legacy
    # root layout ever existed.
    "steam": [
        ("SteamScraper", "steam_data.jsonl", ["steam_metadata.json", "metadata.json"]),
    ],
    # IGDB <-> Steam appid links (2026-11+), written by the IGDB scraper.
    "igdb_links": [
        ("IGDBScraper", "igdb_steam_links.jsonl", ["igdb_metadata.json"]),
    ],
}


@dataclass
class DayFiles:
    date: str
    source: str
    data_path: Path
    metadata_path: Optional[Path]


@dataclass
class DayReport:
    date: str
    source: str
    rows: int = 0
    dups_removed: int = 0
    bad_lines: int = 0
    rejected_records: int = 0
    unparseable_owners: int = 0
    partial: bool = False
    mode: Optional[str] = None  # from metadata, e.g. "html_fallback"
    issues: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.rows > 0 and not self.issues


def discover(data_dir: str = "Data") -> Dict[str, Dict[str, DayFiles]]:
    """Find all snapshot days on disk.

    Returns {source: {date: DayFiles}} for every source in _LAYOUTS.
    """
    root = Path(data_dir)
    found: Dict[str, Dict[str, DayFiles]] = {source: {} for source in _LAYOUTS}
    if not root.exists():
        return found

    for day_dir in sorted(root.iterdir()):
        if not day_dir.is_dir() or not DATE_RE.match(day_dir.name):
            continue
        for source, layouts in _LAYOUTS.items():
            for subdir, data_name, meta_names in layouts:
                base = day_dir / subdir if subdir else day_dir
                data_path = base / data_name
                if data_path.exists():
                    meta = next((base / m for m in meta_names if (base / m).exists()), None)
                    found[source][day_dir.name] = DayFiles(day_dir.name, source, data_path, meta)
                    break
    return found


def _parse_owners(owners: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """'20,000 .. 50,000' -> (20000, 50000)."""
    if not owners:
        return None, None
    parts = owners.replace(",", "").split("..")
    if len(parts) != 2:
        return None, None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None, None


def _to_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _read_mode(files: DayFiles) -> Optional[str]:
    if files.metadata_path is None:
        return None
    try:
        return json.loads(files.metadata_path.read_text(encoding="utf-8")).get("mode")
    except (OSError, json.JSONDecodeError):
        return None


def _iter_jsonl(path: Path, report: DayReport) -> Iterator[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                report.bad_lines += 1


def load_steamspy_day(files: DayFiles) -> Tuple[List[Dict[str, Any]], DayReport]:
    """Load, clean, and validate one SteamSpy day.

    Returns (records, report). Records are keyed for the warehouse schema;
    duplicates within the day keep the last occurrence (most recent write).
    """
    report = DayReport(files.date, "steamspy", mode=_read_mode(files))
    by_appid: Dict[int, Dict[str, Any]] = {}

    for raw in _iter_jsonl(files.data_path, report):
        appid = _to_int(raw.get("appid"))
        name = raw.get("name")
        if appid is None or not name or appid == 999999:
            report.rejected_records += 1
            continue

        owners_low, owners_high = _parse_owners(raw.get("owners"))
        if raw.get("owners") and owners_low is None:
            report.unparseable_owners += 1

        tags = raw.get("tags")
        tags_list = ([{"tag": str(t), "votes": _to_int(v)} for t, v in tags.items()]
                     if isinstance(tags, dict) else [])

        if appid in by_appid:
            report.dups_removed += 1
        by_appid[appid] = {
            "appid": appid,
            "name": str(name),
            "developer": raw.get("developer"),
            "publisher": raw.get("publisher"),
            "positive": _to_int(raw.get("positive")),
            "negative": _to_int(raw.get("negative")),
            "userscore": _to_int(raw.get("userscore")),
            "owners": raw.get("owners"),
            "owners_low": owners_low,
            "owners_high": owners_high,
            "average_forever": _to_int(raw.get("average_forever")),
            "average_2weeks": _to_int(raw.get("average_2weeks")),
            "median_forever": _to_int(raw.get("median_forever")),
            "median_2weeks": _to_int(raw.get("median_2weeks")),
            "price_cents": _to_int(raw.get("price")),
            "initialprice_cents": _to_int(raw.get("initialprice")),
            "discount_pct": _to_int(raw.get("discount")),
            "ccu": _to_int(raw.get("ccu")),
            "languages": raw.get("languages"),
            "genre": raw.get("genre"),
            "score_rank": str(raw["score_rank"]) if raw.get("score_rank") not in (None, "") else None,
            "tags": tags_list,
        }

    records = list(by_appid.values())
    report.rows = len(records)
    report.partial = (report.mode == "html_fallback"
                      or report.rows < STEAMSPY_FULL_DAY_MIN_ROWS)
    _finalize_issues(report)
    return records, report


def load_steam_day(files: DayFiles) -> Tuple[List[Dict[str, Any]], DayReport]:
    """Load, clean, and validate one Steam official-data day.

    Records carry live review summaries (GetItems) and concurrent-player
    counts. Duplicates within a day keep the last occurrence.
    """
    report = DayReport(files.date, "steam", mode=_read_mode(files))
    by_appid: Dict[int, Dict[str, Any]] = {}

    for raw in _iter_jsonl(files.data_path, report):
        appid = _to_int(raw.get("appid"))
        if appid is None or appid == 999999:
            report.rejected_records += 1
            continue

        if appid in by_appid:
            report.dups_removed += 1
        by_appid[appid] = {
            "appid": appid,
            "name": raw.get("name") or None,
            "visible": raw["visible"] if isinstance(raw.get("visible"), bool) else None,
            "parent_appid": _to_int(raw.get("parent_appid")),
            "review_count": _to_int(raw.get("review_count")),
            "percent_positive": _to_int(raw.get("percent_positive")),
            "review_score": _to_int(raw.get("review_score")),
            "review_score_label": raw.get("review_score_label"),
            "player_count": _to_int(raw.get("player_count")),
        }

    records = list(by_appid.values())
    report.rows = len(records)
    report.partial = report.rows < STEAM_FULL_DAY_MIN_ROWS
    _finalize_issues(report)
    return records, report


def _names(items: Optional[List[Dict[str, Any]]]) -> List[str]:
    return [i["name"] for i in items or [] if isinstance(i, dict) and i.get("name")]


def load_igdb_day(files: DayFiles) -> Tuple[List[Dict[str, Any]], DayReport]:
    """Load, clean, and validate one IGDB day."""
    report = DayReport(files.date, "igdb")
    by_id: Dict[int, Dict[str, Any]] = {}

    for raw in _iter_jsonl(files.data_path, report):
        game_id = _to_int(raw.get("id"))
        name = raw.get("name")
        if game_id is None or not name:
            report.rejected_records += 1
            continue

        if game_id in by_id:
            report.dups_removed += 1
        by_id[game_id] = {
            "igdb_id": game_id,
            "name": str(name),
            "rating": raw.get("rating"),
            "rating_count": _to_int(raw.get("rating_count")),
            "aggregated_rating": raw.get("aggregated_rating"),
            "aggregated_rating_count": _to_int(raw.get("aggregated_rating_count")),
            "first_release_date": _to_int(raw.get("first_release_date")),  # epoch seconds
            "genres": _names(raw.get("genres")),
            "platforms": _names(raw.get("platforms")),
            "companies": _names([c.get("company") for c in raw.get("involved_companies") or []
                                 if isinstance(c, dict)]),
        }

    records = list(by_id.values())
    report.rows = len(records)
    report.partial = report.rows < IGDB_FULL_DAY_MIN_ROWS
    _finalize_issues(report)
    return records, report


def load_igdb_links_day(files: DayFiles) -> Tuple[List[Dict[str, Any]], DayReport]:
    """Load one day's IGDB <-> Steam links; duplicate pairs are dropped."""
    report = DayReport(files.date, "igdb_links")
    pairs = {}
    for raw in _iter_jsonl(files.data_path, report):
        igdb_id, appid = _to_int(raw.get("igdb_id")), _to_int(raw.get("steam_appid"))
        if igdb_id is None or appid is None:
            report.rejected_records += 1
            continue
        if (igdb_id, appid) in pairs:
            report.dups_removed += 1
        pairs[(igdb_id, appid)] = {"igdb_id": igdb_id, "steam_appid": appid}

    records = list(pairs.values())
    report.rows = len(records)
    report.partial = report.rows < IGDB_LINKS_FULL_DAY_MIN_ROWS
    _finalize_issues(report)
    return records, report


def _finalize_issues(report: DayReport) -> None:
    """Promote serious problems to issues (issues => day fails ingest)."""
    if report.rows == 0:
        report.issues.append("no valid records")
    total = report.rows + report.rejected_records
    if report.bad_lines > max(1, total // 100):
        report.issues.append(f"{report.bad_lines} unparseable lines")
    if report.rejected_records > max(1, total // 100):
        report.issues.append(f"{report.rejected_records} rejected records")
