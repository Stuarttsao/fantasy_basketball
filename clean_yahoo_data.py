#!/usr/bin/env python3
"""Turn the raw Yahoo league responses into small analysis-ready CSV files."""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "yahoo-2025-26"
BBM_RAW = ROOT / "data" / "raw" / "player-rankings-2025-26"
OUT = ROOT / "data" / "processed"

STAT_COLUMNS = {
    "9004003": "fgm_fga",
    "5": "fg_pct",
    "9007006": "ftm_fta",
    "8": "ft_pct",
    "10": "three_pt_made",
    "12": "points",
    "15": "rebounds",
    "16": "assists",
    "17": "steals",
    "18": "blocks",
    "19": "turnovers",
}
SCORING_STATS = {
    "5": "fg_pct",
    "8": "ft_pct",
    "10": "three_pt_made",
    "12": "points",
    "15": "rebounds",
    "16": "assists",
    "17": "steals",
    "18": "blocks",
    "19": "turnovers",
}
PLAYER_NAME_ALIASES = {
    "cameronjohnson": ("camjohnson", "Cameron ↔ Cam; same DEN player"),
    "nicclaxton": ("nicolasclaxton", "Nic ↔ Nicolas; same BKN player"),
    "alexsarr": ("alexandresarr", "Alex ↔ Alexandre; same WAS player"),
    "herbertjones": ("herbjones", "Herbert ↔ Herb; same NOP/NOR player"),
    "cameronpayne": ("campayne", "Cameron ↔ Cam; same player"),
    "elijahharkless": ("ejharkless", "Elijah J. ↔ EJ; same UTA player"),
    "ronaldholland": ("ronholland", "Ronald Holland II ↔ Ron Holland; same DET player"),
}


def load(name: str) -> dict:
    return json.loads((RAW / name).read_text())["fantasy_content"]


def numeric_items(mapping: dict):
    for key in sorted((key for key in mapping if str(key).isdigit()), key=lambda value: int(value)):
        yield mapping[key]


def merge_fragments(value) -> dict:
    """Merge Yahoo's list-of-single-key-dictionaries representation."""
    merged = {}
    if isinstance(value, dict):
        merged.update(value)
    elif isinstance(value, list):
        for item in value:
            merged.update(merge_fragments(item))
    return merged


def parse_team(team) -> tuple[dict, dict]:
    parts = team if isinstance(team, list) else [team]
    base = merge_fragments(parts[0]) if parts else {}
    details = merge_fragments(parts[1:]) if len(parts) > 1 else {}
    return base, details


def manager_name(base: dict) -> str:
    managers = base.get("managers", [])
    if not managers:
        return ""
    return managers[0].get("manager", {}).get("nickname", "")


def team_logo(base: dict) -> str:
    logos = base.get("team_logos", [])
    if not logos:
        return ""
    return logos[0].get("team_logo", {}).get("url", "")


def stat_values(details: dict) -> dict:
    values = {column: "" for column in STAT_COLUMNS.values()}
    stats = details.get("team_stats", {}).get("stats", [])
    for wrapper in stats:
        stat = wrapper.get("stat", {})
        column = STAT_COLUMNS.get(str(stat.get("stat_id")))
        if column:
            values[column] = stat.get("value", "")
    return values


def write_csv(name: str, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    with (OUT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote data/processed/{name}: {len(rows)} rows")


def clean_teams() -> tuple[list[dict], dict[str, str]]:
    teams = load("03_teams.json")["league"][1]["teams"]
    rows = []
    names = {}
    for wrapper in numeric_items(teams):
        base, _ = parse_team(wrapper["team"])
        team_key = base["team_key"]
        names[team_key] = base["name"]
        rows.append(
            {
                "team_key": team_key,
                "team_id": base.get("team_id", ""),
                "team_name": base.get("name", ""),
                "manager_name": manager_name(base),
                "logo_url": team_logo(base),
                "number_of_moves": base.get("number_of_moves", ""),
                "number_of_trades": base.get("number_of_trades", ""),
                "clinched_playoffs": base.get("clinched_playoffs", 0),
                "previous_season_rank": base.get("previous_season_team_rank", ""),
            }
        )
    return rows, names


def clean_standings() -> list[dict]:
    teams = load("04_standings.json")["league"][1]["standings"][0]["teams"]
    rows = []
    for wrapper in numeric_items(teams):
        base, details = parse_team(wrapper["team"])
        standings = details.get("team_standings", {})
        outcomes = standings.get("outcome_totals", {})
        row = {
            "rank": standings.get("rank", ""),
            "playoff_seed": standings.get("playoff_seed", ""),
            "team_key": base.get("team_key", ""),
            "team_name": base.get("name", ""),
            "manager_name": manager_name(base),
            "wins": outcomes.get("wins", ""),
            "losses": outcomes.get("losses", ""),
            "ties": outcomes.get("ties", ""),
            "win_pct": outcomes.get("percentage", ""),
            "games_back": standings.get("games_back", ""),
        }
        row.update(stat_values(details))
        rows.append(row)
    return rows


def clean_draft(team_names: dict[str, str]) -> list[dict]:
    results = load("05_draft_results.json")["league"][1]["draft_results"]
    rows = []
    for wrapper in numeric_items(results):
        result = wrapper["draft_result"]
        rows.append(
            {
                "pick": result.get("pick", ""),
                "round": result.get("round", ""),
                "team_key": result.get("team_key", ""),
                "team_name": team_names.get(result.get("team_key", ""), ""),
                "player_key": result.get("player_key", ""),
            }
        )
    return rows


def normalize_name(name: str) -> str:
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    value = value.lower().replace("’", "'")
    value = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", value)
    return re.sub(r"[^a-z0-9]", "", value)


def clean_bbm_players() -> list[dict]:
    path = BBM_RAW / "BBM_AllPlayers.csv"
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for source in csv.DictReader(handle):
            row = {
                "bbm_rank": source["Rank"],
                "bbm_round": source["Round"],
                "bbm_value": source["Value"],
                "player_name": source["Name"].strip(),
                "normalized_name": normalize_name(source["Name"]),
                "nba_team": source["Team"],
                "position": source["Pos"],
                "injury_note": source["Inj"],
                "games": source["g"],
                "minutes_per_game": source["m/g"],
                "points_per_game": source["p/g"],
                "threes_per_game": source["3/g"],
                "rebounds_per_game": source["r/g"],
                "assists_per_game": source["a/g"],
                "steals_per_game": source["s/g"],
                "blocks_per_game": source["b/g"],
                "fg_pct": source["fg%"],
                "fga_per_game": source["fga/g"],
                "ft_pct": source["ft%"],
                "fta_per_game": source["fta/g"],
                "turnovers_per_game": source["to/g"],
                "usage": source["USG"],
                "points_value": source["pV"],
                "threes_value": source["3V"],
                "rebounds_value": source["rV"],
                "assists_value": source["aV"],
                "steals_value": source["sV"],
                "blocks_value": source["bV"],
                "fg_pct_value": source["fg%V"],
                "ft_pct_value": source["ft%V"],
                "turnovers_value": source["toV"],
            }
            rows.append(row)
    return rows


def clean_yahoo_draft_players() -> list[dict]:
    players = {}
    for path in sorted(RAW.glob("draft_players_*.json")):
        collection = json.loads(path.read_text())["fantasy_content"]["league"][1]["players"]
        for wrapper in numeric_items(collection):
            base, _ = parse_team(wrapper["player"])
            key = base.get("player_key", "")
            if not key:
                continue
            players[key] = {
                "player_key": key,
                "player_id": base.get("player_id", ""),
                "player_name": base.get("name", {}).get("full", ""),
                "normalized_name": normalize_name(base.get("name", {}).get("full", "")),
                "nba_team": base.get("editorial_team_abbr", ""),
                "positions": base.get("display_position", ""),
                "headshot_url": base.get("headshot", {}).get("url", ""),
            }
    return list(players.values())


def match_bbm_player(yahoo_name: str, bbm_by_name: dict[str, dict]):
    normalized = normalize_name(yahoo_name)
    bbm = bbm_by_name.get(normalized)
    if bbm:
        return bbm, "exact", ""
    if normalized in PLAYER_NAME_ALIASES:
        alias_name, note = PLAYER_NAME_ALIASES[normalized]
        bbm = bbm_by_name.get(alias_name)
        if bbm:
            return bbm, "alias", note
    return None, "missing_from_bbm", "No corresponding player row in the BBM all-player export"


def join_draft_to_bbm(
    draft: list[dict], yahoo_players: list[dict], bbm_players: list[dict]
) -> list[dict]:
    yahoo_by_key = {row["player_key"]: row for row in yahoo_players}
    bbm_by_name = {row["normalized_name"]: row for row in bbm_players}
    rows = []
    for pick in draft:
        yahoo = yahoo_by_key.get(pick["player_key"], {})
        bbm, match_status, match_note = match_bbm_player(
            yahoo.get("player_name", ""), bbm_by_name
        )
        bbm_rank = int(bbm["bbm_rank"]) if bbm else None
        draft_pick = int(pick["pick"])
        rows.append(
            {
                **pick,
                "player_name": yahoo.get("player_name", ""),
                "bbm_player_name": bbm.get("player_name", "") if bbm else "",
                "nba_team": yahoo.get("nba_team", ""),
                "bbm_nba_team": bbm.get("nba_team", "") if bbm else "",
                "positions": yahoo.get("positions", ""),
                "headshot_url": yahoo.get("headshot_url", ""),
                "bbm_rank": bbm_rank if bbm_rank is not None else "",
                "bbm_value": bbm.get("bbm_value", "") if bbm else "",
                "games": bbm.get("games", "") if bbm else "",
                "injury_note": bbm.get("injury_note", "") if bbm else "",
                "draft_value_vs_rank": (
                    draft_pick - bbm_rank if bbm_rank is not None else ""
                ),
                "match_status": match_status,
                "match_note": match_note,
            }
        )
    return rows


def build_player_coverage(
    draft_analysis: list[dict],
    actions: list[dict],
    bbm_players: list[dict],
) -> tuple[list[dict], list[dict]]:
    players = {}
    for row in draft_analysis:
        players[row["player_key"]] = {
            "player_key": row["player_key"],
            "player_name": row["player_name"],
            "yahoo_nba_team": row["nba_team"],
            "was_drafted": 1,
            "had_transaction": 0,
            "draft_pick": row["pick"],
            "draft_team": row["team_name"],
        }
    for action in actions:
        player = players.setdefault(
            action["player_key"],
            {
                "player_key": action["player_key"],
                "player_name": action["player_name"],
                "yahoo_nba_team": action["nba_team"],
                "was_drafted": 0,
                "had_transaction": 0,
                "draft_pick": "",
                "draft_team": "",
            },
        )
        player["had_transaction"] = 1

    bbm_by_name = {row["normalized_name"]: row for row in bbm_players}
    coverage = []
    for player in players.values():
        bbm, status, note = match_bbm_player(player["player_name"], bbm_by_name)
        coverage.append(
            {
                **player,
                "bbm_player_name": bbm.get("player_name", "") if bbm else "",
                "bbm_nba_team": bbm.get("nba_team", "") if bbm else "",
                "bbm_rank": bbm.get("bbm_rank", "") if bbm else "",
                "bbm_value": bbm.get("bbm_value", "") if bbm else "",
                "games": bbm.get("games", "") if bbm else "",
                "match_status": status,
                "match_note": note,
            }
        )
    coverage.sort(key=lambda row: row["player_name"])
    discrepancies = [row for row in coverage if row["match_status"] != "exact"]
    return coverage, discrepancies


def unwrap_matchup(matchup: dict) -> dict:
    if "0" in matchup and isinstance(matchup["0"], dict):
        merged = dict(matchup["0"])
        merged.update({key: value for key, value in matchup.items() if key != "0"})
        return merged
    return matchup


def clean_scoreboards() -> tuple[list[dict], list[dict]]:
    matchup_rows = []
    team_week_rows = []
    for week in range(1, 24):
        scoreboard = load(f"scoreboard_week_{week:02d}.json")["league"][1]["scoreboard"]["0"]
        for wrapper in numeric_items(scoreboard["matchups"]):
            matchup = unwrap_matchup(wrapper["matchup"])
            team_records = []
            for team_wrapper in numeric_items(matchup["teams"]):
                base, details = parse_team(team_wrapper["team"])
                stats = stat_values(details)
                row = {
                    "week": week,
                    "week_start": matchup.get("week_start", ""),
                    "week_end": matchup.get("week_end", ""),
                    "team_key": base.get("team_key", ""),
                    "team_name": base.get("name", ""),
                    "category_wins": details.get("team_points", {}).get("total", ""),
                    "completed_player_games": details.get("team_remaining_games", {})
                    .get("total", {})
                    .get("completed_games", ""),
                }
                row.update(stats)
                team_week_rows.append(row)
                team_records.append(row)

            if len(team_records) != 2:
                continue
            winners = {
                str(item["stat_winner"].get("stat_id")): (
                    "TIE"
                    if item["stat_winner"].get("is_tied")
                    else item["stat_winner"].get("winner_team_key", "")
                )
                for item in matchup.get("stat_winners", [])
            }
            row = {
                "week": week,
                "week_start": matchup.get("week_start", ""),
                "week_end": matchup.get("week_end", ""),
                "team_1_key": team_records[0]["team_key"],
                "team_1_name": team_records[0]["team_name"],
                "team_1_category_wins": team_records[0]["category_wins"],
                "team_2_key": team_records[1]["team_key"],
                "team_2_name": team_records[1]["team_name"],
                "team_2_category_wins": team_records[1]["category_wins"],
                "is_tied": matchup.get("is_tied", 0),
                "is_playoffs": matchup.get("is_playoffs", "0"),
                "is_consolation": matchup.get("is_consolation", "0"),
            }
            for stat_id, column in SCORING_STATS.items():
                row[f"{column}_winner"] = winners.get(stat_id, "")
            matchup_rows.append(row)
    return matchup_rows, team_week_rows


def clean_transactions(team_names: dict[str, str]) -> tuple[list[dict], list[dict]]:
    transactions = {}
    actions = []
    for path in sorted(RAW.glob("transactions_*.json")):
        collection = json.loads(path.read_text())["fantasy_content"]["league"][1]["transactions"]
        for wrapper in numeric_items(collection):
            transaction = merge_fragments(wrapper["transaction"])
            key = transaction.get("transaction_key", "")
            if not key or key in transactions:
                continue
            timestamp = int(transaction.get("timestamp", 0))
            transactions[key] = {
                "transaction_key": key,
                "transaction_id": transaction.get("transaction_id", ""),
                "transaction_type": transaction.get("type", ""),
                "status": transaction.get("status", ""),
                "timestamp_utc": datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
            }
            players = transaction.get("players", {})
            for player_wrapper in numeric_items(players):
                base, details = parse_team(player_wrapper["player"])
                transaction_data = details.get("transaction_data", [])
                if isinstance(transaction_data, dict):
                    transaction_data = [transaction_data]
                for action_wrapper in transaction_data:
                    action = merge_fragments(action_wrapper)
                    source_key = action.get("source_team_key", "")
                    destination_key = action.get("destination_team_key", "")
                    actions.append(
                        {
                            "transaction_key": key,
                            "timestamp_utc": transactions[key]["timestamp_utc"],
                            "transaction_type": transaction.get("type", ""),
                            "player_key": base.get("player_key", ""),
                            "player_id": base.get("player_id", ""),
                            "player_name": base.get("name", {}).get("full", ""),
                            "nba_team": base.get("editorial_team_abbr", ""),
                            "positions": base.get("display_position", ""),
                            "action": action.get("type", ""),
                            "source_type": action.get("source_type", ""),
                            "source_team_key": source_key,
                            "source_team_name": team_names.get(
                                source_key, action.get("source_team_name", "")
                            ),
                            "destination_type": action.get("destination_type", ""),
                            "destination_team_key": destination_key,
                            "destination_team_name": team_names.get(
                                destination_key, action.get("destination_team_name", "")
                            ),
                        }
                    )
    return list(transactions.values()), actions


def numeric(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def percentile(values: list[float], target: float, lower_is_better: bool = False) -> float:
    if len(values) <= 1:
        return 0.5
    lower = sum(value < target for value in values)
    equal = sum(value == target for value in values)
    rank = lower + (equal - 1) / 2
    score = rank / (len(values) - 1)
    return 1 - score if lower_is_better else score


def calculate_strength(weekly: list[dict]) -> tuple[list[dict], list[dict]]:
    by_week = defaultdict(list)
    for row in weekly:
        by_week[row["week"]].append(row)

    strength_rows = []
    for week, rows in sorted(by_week.items(), key=lambda item: int(item[0])):
        category_values = {
            column: [
                value
                for value in (numeric(row[column]) for row in rows)
                if value is not None
            ]
            for column in SCORING_STATS.values()
        }
        for row in rows:
            result = {
                "week": week,
                "team_key": row["team_key"],
                "team_name": row["team_name"],
            }
            scores = []
            for column in SCORING_STATS.values():
                value = numeric(row[column])
                score = (
                    percentile(
                        category_values[column],
                        value,
                        lower_is_better=column == "turnovers",
                    )
                    if value is not None
                    else None
                )
                result[f"{column}_strength"] = (
                    round(score * 100, 2) if score is not None else ""
                )
                if score is not None:
                    scores.append(score)
            result["overall_strength"] = (
                round(sum(scores) / len(scores) * 100, 2) if scores else ""
            )
            strength_rows.append(result)

    by_team = defaultdict(list)
    for row in strength_rows:
        if row["overall_strength"] != "":
            by_team[(row["team_key"], row["team_name"])].append(row)

    season_rows = []
    for (team_key, team_name), rows in by_team.items():
        result = {
            "team_key": team_key,
            "team_name": team_name,
            "weeks_played": len(rows),
            "average_strength": round(
                sum(row["overall_strength"] for row in rows) / len(rows), 2
            ),
            "peak_strength": max(row["overall_strength"] for row in rows),
            "peak_week": max(rows, key=lambda row: row["overall_strength"])["week"],
        }
        for column in SCORING_STATS.values():
            values = [
                numeric(row[f"{column}_strength"])
                for row in rows
                if numeric(row[f"{column}_strength"]) is not None
            ]
            result[f"average_{column}_strength"] = (
                round(sum(values) / len(values), 2) if values else ""
            )
        season_rows.append(result)
    season_rows.sort(key=lambda row: row["average_strength"], reverse=True)
    for rank, row in enumerate(season_rows, 1):
        row["strength_rank"] = rank
    return strength_rows, season_rows


def write_summary(
    teams: list[dict],
    standings: list[dict],
    drafts: list[dict],
    matchups: list[dict],
    weekly: list[dict],
    transactions: list[dict],
    actions: list[dict],
    season_strength: list[dict],
    draft_analysis: list[dict],
    player_coverage: list[dict],
) -> None:
    adds = Counter()
    drops = Counter()
    for action in actions:
        if action["action"] == "add" and action["destination_team_name"]:
            adds[action["destination_team_name"]] += 1
        if action["action"] == "drop" and action["source_team_name"]:
            drops[action["source_team_name"]] += 1

    average_wins = defaultdict(list)
    for row in weekly:
        try:
            average_wins[row["team_name"]].append(float(row["category_wins"]))
        except (TypeError, ValueError):
            pass
    average_wins = sorted(
        (
            (team, sum(values) / len(values))
            for team, values in average_wins.items()
            if values
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    lines = [
        "# Initial Data Exploration",
        "",
        "## Coverage",
        "",
        f"- Teams: {len(teams)}",
        f"- Final standings rows: {len(standings)}",
        f"- Draft picks: {len(drafts)}",
        f"- Weekly matchups: {len(matchups)}",
        f"- Team-week stat rows: {len(weekly)}",
        f"- Transactions: {len(transactions)}",
        f"- Player transaction actions: {len(actions)}",
        f"- Draft players matched to BBM: "
        f"{sum(row['match_status'] in {'exact', 'alias'} for row in draft_analysis)}"
        f"/{len(draft_analysis)}",
        f"- All drafted/rostered players matched to BBM: "
        f"{sum(row['match_status'] in {'exact', 'alias'} for row in player_coverage)}"
        f"/{len(player_coverage)}",
        "",
        "## Final Standings",
        "",
    ]
    for row in sorted(standings, key=lambda item: int(item["rank"])):
        lines.append(
            f"{row['rank']}. **{row['team_name']}** — "
            f"{row['wins']}-{row['losses']}-{row['ties']}"
        )

    lines.extend(["", "## Early Leads to Explore", ""])
    if average_wins:
        team, value = average_wins[0]
        lines.append(f"- Highest average weekly category wins: **{team}** ({value:.2f}).")
    if season_strength:
        leader = season_strength[0]
        lines.append(
            f"- Highest average nine-category strength: **{leader['team_name']}** "
            f"({leader['average_strength']}/100)."
        )
        peak = max(season_strength, key=lambda row: row["peak_strength"])
        lines.append(
            f"- Strongest single team-week: **{peak['team_name']}**, Week "
            f"{peak['peak_week']} ({peak['peak_strength']}/100)."
        )
    if adds:
        team, count = adds.most_common(1)[0]
        lines.append(f"- Most recorded player adds: **{team}** ({count}).")
    if drops:
        team, count = drops.most_common(1)[0]
        lines.append(f"- Most recorded player drops: **{team}** ({count}).")
    matched_drafts = [
        row for row in draft_analysis if row["match_status"] in {"exact", "alias"}
    ]
    if matched_drafts:
        steal = max(matched_drafts, key=lambda row: row["draft_value_vs_rank"])
        reach = min(matched_drafts, key=lambda row: row["draft_value_vs_rank"])
        lines.append(
            f"- Largest draft value gain by final BBM rank: **{steal['player_name']}** "
            f"to {steal['team_name']} at pick {steal['pick']} "
            f"(BBM rank {steal['bbm_rank']})."
        )
        lines.append(
            f"- Largest draft value loss by final BBM rank: **{reach['player_name']}** "
            f"to {reach['team_name']} at pick {reach['pick']} "
            f"(BBM rank {reach['bbm_rank']})."
        )
    missing_players = [
        row["player_name"]
        for row in draft_analysis
        if row["match_status"] == "missing_from_bbm"
    ]
    if missing_players:
        lines.append(
            "- Drafted players absent from the BBM export: "
            + ", ".join(f"**{name}**" for name in missing_players)
            + "."
        )
    lines.extend(
        [
            "- Join draft picks to the BBM player rankings to investigate draft steals and misses.",
            "- Compare weekly category profiles to find team identities and turning points.",
            "- Rank matchup closeness using category margins rather than only the final category score.",
            "",
            "## Source Notes",
            "",
            "- Yahoo raw JSON remains unchanged in `data/raw/yahoo-2025-26/`.",
            "- Manager emails and Yahoo account identifiers are intentionally excluded.",
            "- BBM source workbooks are preserved in `data/raw/player-rankings-2025-26/`.",
        ]
    )
    (OUT / "INITIAL_EXPLORATION.md").write_text("\n".join(lines) + "\n")
    print("Wrote data/processed/INITIAL_EXPLORATION.md")


def main() -> None:
    teams, team_names = clean_teams()
    standings = clean_standings()
    drafts = clean_draft(team_names)
    bbm_players = clean_bbm_players()
    yahoo_draft_players = clean_yahoo_draft_players()
    draft_analysis = join_draft_to_bbm(drafts, yahoo_draft_players, bbm_players)
    matchups, weekly = clean_scoreboards()
    transactions, actions = clean_transactions(team_names)
    player_coverage, discrepancies = build_player_coverage(
        draft_analysis, actions, bbm_players
    )
    weekly_strength, season_strength = calculate_strength(weekly)

    write_csv("teams.csv", teams)
    write_csv("standings.csv", standings)
    write_csv("draft_results.csv", drafts)
    write_csv("bbm_players.csv", bbm_players)
    write_csv("yahoo_draft_players.csv", yahoo_draft_players)
    write_csv("draft_analysis.csv", draft_analysis)
    write_csv("matchups.csv", matchups)
    write_csv("weekly_team_stats.csv", weekly)
    write_csv("transactions.csv", transactions)
    write_csv("transaction_actions.csv", actions)
    write_csv("league_player_coverage.csv", player_coverage)
    write_csv("player_data_discrepancies.csv", discrepancies)
    write_csv("weekly_team_strength.csv", weekly_strength)
    write_csv("season_team_strength.csv", season_strength)
    write_summary(
        teams,
        standings,
        drafts,
        matchups,
        weekly,
        transactions,
        actions,
        season_strength,
        draft_analysis,
        player_coverage,
    )


if __name__ == "__main__":
    main()
