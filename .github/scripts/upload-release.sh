#!/usr/bin/env bash
# Usage: upload-release.sh DATE DIR DATA_FILE
# Uploads DIR/* to release DATE, unless the release already holds a DATA_FILE
set -euo pipefail

DATE="$1"; DIR="$2"; DATA="$3"

if [ ! -s "$DIR/$DATA" ]; then
  echo "✗ No $DATA produced; leaving release $DATE untouched"
  exit 1
fi

count_records() {
  python3 -I - "$1" <<'EOF'
import json, sys
ids, n = set(), 0
with open(sys.argv[1], encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        key = row.get("appid", row.get("id")) if isinstance(row, dict) else None
        if key is None:
            n += 1
        else:
            ids.add(key)
print(len(ids) + n)
EOF
}

if ! gh release view "$DATE" &>/dev/null; then
  echo "Creating release for $DATE"
  gh release create "$DATE" --title "Data for $DATE" --notes "Automated game data scraping for $DATE" \
    || gh release view "$DATE" &>/dev/null \
    || { echo "✗ Could not create or find release $DATE"; exit 1; }
fi

NEW=$(count_records "$DIR/$DATA")
OLD_DIR=$(mktemp -d)
if gh release download "$DATE" --pattern "$DATA" --dir "$OLD_DIR" 2>/dev/null; then
  OLD=$(count_records "$OLD_DIR/$DATA")
  echo "Existing $DATA: $OLD records; this run: $NEW"
  if [ "$NEW" -lt "$OLD" ]; then
    echo "::warning::Kept existing $DATA for $DATE ($OLD records > $NEW); nothing uploaded"
    exit 0
  fi
else
  echo "No existing $DATA in $DATE; this run: $NEW records"
fi

for try in 1 2 3; do
  gh release upload "$DATE" "$DIR"/* --clobber && { echo "✓ Uploaded $DIR to $DATE"; exit 0; }
  echo "Upload attempt $try failed; retrying in 30s"; sleep 30
done
echo "✗ Upload failed 3 times"
exit 1
