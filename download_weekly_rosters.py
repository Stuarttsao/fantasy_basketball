#!/usr/bin/env python3
"""Download Yahoo's historical weekly roster snapshots with injury status."""

from __future__ import annotations

import json
from pathlib import Path

import download_yahoo_data as yahoo


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "data" / "raw" / "yahoo-2025-26" / "weekly_rosters"
LEAGUE_KEY = "466.l.95762"


def main() -> None:
    token = yahoo.access_token()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for team_id in range(1, 13):
        team_key = f"{LEAGUE_KEY}.t.{team_id}"
        for week in range(1, 24):
            path = OUTPUT / f"team_{team_id:02d}_week_{week:02d}.json"
            if path.exists():
                continue
            payload = yahoo.api_get(f"team/{team_key}/roster;week={week}", token)
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            print(f"Saved team {team_id}, week {week}")


if __name__ == "__main__":
    main()
