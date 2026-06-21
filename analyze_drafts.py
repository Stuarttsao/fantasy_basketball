#!/usr/bin/env python3
"""Retrospective draft and roster-construction analysis for the SAS league."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, time, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"
RAW_WEEKLY_ROSTERS = (
    ROOT / "data" / "raw" / "yahoo-2025-26" / "weekly_rosters"
)
OUT = ROOT / "analysis"
WEEKS = 23


def read_csv(name: str) -> list[dict]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def number(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def numeric_items(mapping: dict):
    for key in sorted(
        (key for key in mapping if str(key).isdigit()),
        key=lambda value: int(value),
    ):
        yield mapping[key]


def merge_fragments(value) -> dict:
    merged = {}
    if isinstance(value, dict):
        merged.update(value)
    elif isinstance(value, list):
        for item in value:
            merged.update(merge_fragments(item))
    return merged


def main() -> None:
    teams = read_csv("teams.csv")
    draft = read_csv("draft_analysis.csv")
    actions = read_csv("transaction_actions.csv")
    bbm = read_csv("bbm_players.csv")
    coverage = read_csv("league_player_coverage.csv")
    weekly_stats = read_csv("weekly_team_stats.csv")
    weekly_strength = read_csv("weekly_team_strength.csv")
    standings = read_csv("standings.csv")

    team_names = {row["team_key"]: row["team_name"] for row in teams}
    bbm_by_name = {row["player_name"]: row for row in bbm}
    coverage_by_key = {row["player_key"]: row for row in coverage}
    draft_by_player = {row["player_key"]: row for row in draft}

    injury_rows = []
    injury_by_team_week_player = {}
    if RAW_WEEKLY_ROSTERS.exists():
        for path in sorted(RAW_WEEKLY_ROSTERS.glob("team_*_week_*.json")):
            payload = json.loads(path.read_text())
            team = payload["fantasy_content"]["team"]
            team_meta = merge_fragments(team[0])
            roster = team[1]["roster"]
            week = int(path.stem.rsplit("_", 1)[-1])
            players = roster.get("0", {}).get("players", {})
            if not players:
                continue
            for wrapper in numeric_items(players):
                player_parts = wrapper["player"]
                base = merge_fragments(player_parts[0])
                details = merge_fragments(player_parts[1:])
                selected = merge_fragments(details.get("selected_position", []))
                selected_position = selected.get("position", "")
                # Yahoo returns today's player injury label even when an old
                # roster week is requested. The historical selected roster
                # position is reliable, so only treat IL/IL+ placement as
                # week-specific injury evidence.
                if not selected_position.startswith("IL"):
                    continue
                player_key = base.get("player_key", "")
                bbm_rank = number(
                    coverage_by_key.get(player_key, {}).get("bbm_rank")
                )
                draft_pick = number(
                    draft_by_player.get(player_key, {}).get("pick")
                )
                is_major = bool(
                    (bbm_rank is not None and bbm_rank <= 100)
                    or (draft_pick is not None and draft_pick <= 72)
                )
                row = {
                    "week": week,
                    "team_key": team_meta.get("team_key", ""),
                    "team_name": team_names.get(team_meta.get("team_key", ""), ""),
                    "player_key": player_key,
                    "player_name": base.get("name", {}).get("full", ""),
                    "status": selected_position,
                    "status_full": "Injury-list slot",
                    "injury_note": "",
                    "selected_position": selected_position,
                    "bbm_rank": int(bbm_rank) if bbm_rank is not None else "",
                    "draft_pick": int(draft_pick) if draft_pick is not None else "",
                    "is_major": int(is_major),
                }
                injury_rows.append(row)
                injury_by_team_week_player[
                    (row["team_key"], week, player_key)
                ] = row

    # Initial ownership is the drafted roster.
    owner = {row["player_key"]: row["team_key"] for row in draft}
    actions.sort(key=lambda row: (row["timestamp_utc"], row["transaction_key"], row["action"]))

    week_ends = {}
    week_starts = {}
    active_weeks = defaultdict(set)
    for row in weekly_stats:
        week = int(row["week"])
        active_weeks[row["team_key"]].add(week)
        week_starts[week] = datetime.combine(
            datetime.fromisoformat(row["week_start"]).date(),
            time.min,
            tzinfo=timezone.utc,
        )
        week_ends[week] = datetime.combine(
            datetime.fromisoformat(row["week_end"]).date(),
            time.max,
            tzinfo=timezone.utc,
        )

    action_index = 0
    snapshots: dict[int, dict[str, set[str]]] = {}
    anomalies = defaultdict(int)

    for week in sorted(week_ends):
        cutoff = week_ends[week]
        while action_index < len(actions):
            action = actions[action_index]
            timestamp = datetime.fromisoformat(action["timestamp_utc"])
            if timestamp > cutoff:
                break

            player_key = action["player_key"]
            source = action["source_team_key"]
            destination = action["destination_team_key"]
            action_type = action["action"]

            if action_type in {"drop", "trade"} and source:
                if owner.get(player_key) == source:
                    owner.pop(player_key, None)
                elif owner.get(player_key):
                    anomalies["source_owner_mismatch"] += 1
                else:
                    anomalies["remove_unowned"] += 1

            if action_type in {"add", "trade"} and destination:
                previous = owner.get(player_key)
                if previous and previous != destination:
                    anomalies["add_owned_player"] += 1
                owner[player_key] = destination

            action_index += 1

        rosters = {team_key: set() for team_key in team_names}
        for player_key, team_key in owner.items():
            if team_key in rosters:
                rosters[team_key].add(player_key)
        snapshots[week] = rosters

    def week_for_timestamp(timestamp: datetime) -> int:
        for week in sorted(week_ends):
            if timestamp <= week_ends[week]:
                return week
        return max(week_ends)

    # There were 156 drafted roster spots (12 teams × 13 picks). Because only
    # final-season BBM values are available, use the next ranked player as the
    # retrospective replacement baseline. A time-varying baseline would create
    # look-ahead bias by treating future breakout players as elite in October.
    all_bbm = [
        row for row in bbm if number(row["bbm_value"]) is not None and number(row["games"], 0) > 0
    ]
    replacement = next(row for row in all_bbm if int(row["bbm_rank"]) == 157)
    replacement_rank = int(replacement["bbm_rank"])
    replacement_level = number(replacement["bbm_value"], 0)
    replacement_band = [
        number(row["bbm_value"])
        for row in all_bbm
        if 145 <= int(row["bbm_rank"]) <= 168
    ]
    replacement_rows = [
        {
            "method": "first player beyond 156 draft slots",
            "replacement_player": replacement["player_name"],
            "replacement_rank": replacement["bbm_rank"],
            "replacement_value": round(replacement_level, 6),
            "rank_145_to_168_average": round(
                sum(replacement_band) / len(replacement_band), 6
            ),
        }
    ]

    team_final_dates = {
        team_key: week_ends[max(weeks)] for team_key, weeks in active_weeks.items()
    }
    season_start = min(week_starts.values())
    season_end = max(week_ends.values())
    season_days = max((season_end.date() - season_start.date()).days + 1, 1)

    # Build free-agent/waiver pickup stints. Trades are not pickups. A stint
    # closes on the player's next drop/trade from that team or the team's last
    # active matchup, whichever comes first.
    open_pickups = {}
    pickup_rows = []

    def close_pickup(player_key: str, team_key: str, end_at: datetime, reason: str) -> None:
        key = (player_key, team_key)
        stint = open_pickups.pop(key, None)
        if not stint:
            return
        team_end = team_final_dates.get(team_key, season_end)
        end_at = min(end_at, team_end)
        if end_at < stint["pickup_at"]:
            return
        held_days = max((end_at.date() - stint["pickup_at"].date()).days + 1, 1)
        credited_start = max(stint["pickup_at"], season_start)
        credited_end = min(end_at, season_end)
        credited_days = max(
            (credited_end.date() - credited_start.date()).days + 1, 0
        )
        coverage_row = coverage_by_key.get(player_key, {})
        player_value = number(coverage_row.get("bbm_value"))
        value_above_replacement = (
            max(player_value - replacement_level, 0) if player_value is not None else 0
        )
        pickup_rows.append(
            {
                "team_key": team_key,
                "team_name": team_names.get(team_key, ""),
                "player_key": player_key,
                "player_name": stint["player_name"],
                "pickup_date": stint["pickup_at"].date().isoformat(),
                "end_date": end_at.date().isoformat(),
                "held_days": held_days,
                "credited_season_days": credited_days,
                "end_reason": reason,
                "source_type": stint["source_type"],
                "bbm_rank": coverage_row.get("bbm_rank", ""),
                "bbm_value": coverage_row.get("bbm_value", ""),
                "value_above_replacement": round(value_above_replacement, 6),
                "pickup_score": round(
                    value_above_replacement * credited_days / season_days, 6
                ),
                "originally_drafted": coverage_row.get("was_drafted", "0"),
                "original_draft_team": coverage_row.get("draft_team", ""),
            }
        )

    for action in actions:
        timestamp = datetime.fromisoformat(action["timestamp_utc"])
        player_key = action["player_key"]
        source_team = action["source_team_key"]
        destination_team = action["destination_team_key"]
        if action["action"] in {"drop", "trade"} and source_team:
            close_pickup(player_key, source_team, timestamp, action["action"])
        if (
            action["action"] == "add"
            and destination_team
            and action["source_type"] in {"freeagents", "waivers"}
            and timestamp <= team_final_dates.get(destination_team, season_end)
        ):
            close_pickup(player_key, destination_team, timestamp, "re-added")
            open_pickups[(player_key, destination_team)] = {
                "pickup_at": timestamp,
                "player_name": action["player_name"],
                "source_type": action["source_type"],
            }

    for player_key, team_key in list(open_pickups):
        close_pickup(
            player_key,
            team_key,
            team_final_dates.get(team_key, season_end),
            "season end",
        )
    pickup_rows.sort(
        key=lambda row: (row["pickup_score"], row["held_days"]), reverse=True
    )
    for rank, row in enumerate(pickup_rows, 1):
        row["pickup_rank"] = rank

    streamer_rows = []
    for row in pickup_rows:
        if (
            int(row["held_days"]) <= 14
            and int(row["credited_season_days"]) > 0
            and row["end_reason"] != "season end"
        ):
            streamer = dict(row)
            streamer["streamer_score"] = round(
                number(row["value_above_replacement"], 0)
                * int(row["credited_season_days"])
                / 14,
                6,
            )
            streamer_rows.append(streamer)
    streamer_rows.sort(
        key=lambda row: (row["streamer_score"], row["held_days"]), reverse=True
    )
    for rank, row in enumerate(streamer_rows, 1):
        row["streamer_rank"] = rank

    streamer_intervals = defaultdict(list)
    for row in streamer_rows:
        streamer_intervals[(row["player_key"], row["team_key"])].append(
            (
                datetime.fromisoformat(row["pickup_date"]).date(),
                datetime.fromisoformat(row["end_date"]).date(),
            )
        )

    weekly_roster_rows = []
    for week, rosters in snapshots.items():
        for team_key, roster in rosters.items():
            drafted_set = {
                row["player_key"] for row in draft if row["team_key"] == team_key
            }
            for player_key in sorted(
                roster,
                key=lambda key: coverage_by_key.get(key, {}).get("player_name", ""),
            ):
                player = coverage_by_key.get(player_key, {})
                week_date = week_ends[week].date()
                is_streamer = any(
                    start <= week_date <= end
                    for start, end in streamer_intervals.get(
                        (player_key, team_key), []
                    )
                )
                injury = injury_by_team_week_player.get(
                    (team_key, week, player_key), {}
                )
                weekly_roster_rows.append(
                    {
                        "week": week,
                        "team_key": team_key,
                        "team_name": team_names[team_key],
                        "player_key": player_key,
                        "player_name": player.get("player_name", ""),
                        "nba_team": player.get("yahoo_nba_team", ""),
                        "bbm_rank": player.get("bbm_rank", ""),
                        "bbm_value": player.get("bbm_value", ""),
                        "original_draft_pick": draft_by_player.get(player_key, {}).get(
                            "pick", ""
                        ),
                        "is_original_draft_pick": int(player_key in drafted_set),
                        "is_streamer": int(is_streamer),
                        "is_injured": int(bool(injury)),
                        "injury_status": injury.get("status", ""),
                        "injury_status_full": injury.get("status_full", ""),
                        "injury_note": injury.get("injury_note", ""),
                        "is_major_injury": injury.get("is_major", 0),
                    }
                )

    actions_by_transaction = defaultdict(list)
    for action in actions:
        actions_by_transaction[action["transaction_key"]].append(action)

    weekly_event_rows = []
    trade_rows = []
    for transaction_key, transaction_actions in actions_by_transaction.items():
        transaction_actions.sort(
            key=lambda row: (row["action"], row["player_name"])
        )
        timestamp = datetime.fromisoformat(transaction_actions[0]["timestamp_utc"])
        week = week_for_timestamp(timestamp)
        transaction_type = transaction_actions[0]["transaction_type"]

        if transaction_type == "trade":
            involved_teams = sorted(
                {
                    team_key
                    for action in transaction_actions
                    for team_key in (
                        action["source_team_key"],
                        action["destination_team_key"],
                    )
                    if team_key
                }
            )
            summaries = []
            for team_key in involved_teams:
                incoming = [
                    action
                    for action in transaction_actions
                    if action["destination_team_key"] == team_key
                ]
                outgoing = [
                    action
                    for action in transaction_actions
                    if action["source_team_key"] == team_key
                ]
                incoming_value = sum(
                    max(
                        number(
                            coverage_by_key.get(action["player_key"], {}).get(
                                "bbm_value"
                            ),
                            replacement_level,
                        )
                        - replacement_level,
                        0,
                    )
                    for action in incoming
                )
                outgoing_value = sum(
                    max(
                        number(
                            coverage_by_key.get(action["player_key"], {}).get(
                                "bbm_value"
                            ),
                            replacement_level,
                        )
                        - replacement_level,
                        0,
                    )
                    for action in outgoing
                )
                incoming_names = ", ".join(
                    action["player_name"] for action in incoming
                )
                outgoing_names = ", ".join(
                    action["player_name"] for action in outgoing
                )
                trade_rows.append(
                    {
                        "transaction_key": transaction_key,
                        "trade_date": timestamp.date().isoformat(),
                        "week": week,
                        "team_key": team_key,
                        "team_name": team_names.get(team_key, ""),
                        "players_received": incoming_names,
                        "players_sent": outgoing_names,
                        "received_final_value": round(incoming_value, 6),
                        "sent_final_value": round(outgoing_value, 6),
                        "preliminary_value_delta": round(
                            incoming_value - outgoing_value, 6
                        ),
                        "method_status": "preliminary_full_season_value",
                    }
                )
                summaries.append(
                    f"{team_names.get(team_key, '')} received {incoming_names or 'nothing'}"
                )

            detail = "; ".join(summaries)
            for team_key in involved_teams:
                weekly_event_rows.append(
                    {
                        "week": week,
                        "event_date": timestamp.date().isoformat(),
                        "team_key": team_key,
                        "team_name": team_names.get(team_key, ""),
                        "event_type": "trade",
                        "transaction_key": transaction_key,
                        "detail": detail,
                    }
                )
            continue

        for team_key in sorted(
            {
                key
                for action in transaction_actions
                for key in (
                    action["source_team_key"],
                    action["destination_team_key"],
                )
                if key
            }
        ):
            adds = [
                action["player_name"]
                for action in transaction_actions
                if action["action"] == "add"
                and action["destination_team_key"] == team_key
            ]
            drops = [
                action["player_name"]
                for action in transaction_actions
                if action["action"] == "drop"
                and action["source_team_key"] == team_key
            ]
            details = []
            if adds:
                details.append("Added " + ", ".join(adds))
            if drops:
                details.append("Dropped " + ", ".join(drops))
            weekly_event_rows.append(
                {
                    "week": week,
                    "event_date": timestamp.date().isoformat(),
                    "team_key": team_key,
                    "team_name": team_names.get(team_key, ""),
                    "event_type": "add/drop",
                    "transaction_key": transaction_key,
                    "detail": "; ".join(details),
                }
            )

    trade_rows.sort(
        key=lambda row: row["preliminary_value_delta"], reverse=True
    )
    for rank, row in enumerate(trade_rows, 1):
        row["preliminary_side_rank"] = rank

    for injury in injury_rows:
        if injury["is_major"]:
            weekly_event_rows.append(
                {
                    "week": injury["week"],
                    "event_date": "",
                    "team_key": injury["team_key"],
                    "team_name": injury["team_name"],
                    "event_type": "injury",
                    "transaction_key": "",
                    "detail": (
                        f"{injury['player_name']}: {injury['status_full']}"
                        + (
                            f" ({injury['injury_note']})"
                            if injury["injury_note"]
                            else ""
                        )
                    ),
                }
            )

    draft_player_rows = []
    draft_team_players = defaultdict(list)
    for row in draft:
        value = number(row["bbm_value"])
        final_rank = int(row["bbm_rank"]) if row["bbm_rank"] else None
        effective_final_rank = (
            min(final_rank, replacement_rank)
            if final_rank is not None
            else replacement_rank
        )
        replacement_adjusted_gain = int(row["pick"]) - effective_final_rank
        value_above_replacement = (
            max(value - replacement_level, 0) if value is not None else 0
        )
        result = {
            "team_key": row["team_key"],
            "team_name": row["team_name"],
            "pick": int(row["pick"]),
            "round": int(row["round"]),
            "player_key": row["player_key"],
            "player_name": row["player_name"],
            "bbm_rank": row["bbm_rank"],
            "effective_final_rank": effective_final_rank,
            "bbm_value": row["bbm_value"],
            "replacement_level": round(replacement_level, 6),
            "value_above_replacement": round(value_above_replacement, 6),
            "draft_position_gain": replacement_adjusted_gain,
            "raw_draft_position_gain": row["draft_value_vs_rank"],
            "games": row["games"],
            "data_status": row["match_status"],
        }
        draft_player_rows.append(result)
        draft_team_players[row["team_key"]].append(result)

    draft_team_rows = []
    for team_key, players in draft_team_players.items():
        ranked = sorted(players, key=lambda row: row["value_above_replacement"], reverse=True)
        matched = [row for row in players if row["bbm_rank"]]
        positive = [row for row in players if row["value_above_replacement"] > 0]
        ranked_by_gain = sorted(
            matched, key=lambda row: int(row["draft_position_gain"]), reverse=True
        )
        ranked_by_loss = sorted(
            matched, key=lambda row: int(row["draft_position_gain"])
        )
        missing = [row["player_name"] for row in players if not row["bbm_rank"]]
        steal = ranked_by_gain[0]
        miss = ranked_by_loss[0]
        draft_team_rows.append(
            {
                "team_key": team_key,
                "team_name": team_names[team_key],
                "draft_score": round(
                    sum(row["value_above_replacement"] for row in players), 4
                ),
                "top_5_draft_score": round(
                    sum(row["value_above_replacement"] for row in ranked[:5]), 4
                ),
                "players_above_replacement": len(positive),
                "matched_players": len(matched),
                "average_final_rank": round(
                    sum(int(row["bbm_rank"]) for row in matched) / len(matched), 1
                ),
                "best_pick": ranked[0]["player_name"],
                "best_pick_value": ranked[0]["value_above_replacement"],
                "best_steal": steal["player_name"],
                "best_steal_pick": steal["pick"],
                "best_steal_final_rank": steal["bbm_rank"],
                "best_steal_rank_gain": steal["draft_position_gain"],
                "largest_miss": miss["player_name"],
                "largest_miss_pick": miss["pick"],
                "largest_miss_final_rank": miss["bbm_rank"],
                "largest_miss_rank_loss": miss["draft_position_gain"],
                "players_without_bbm_data": ", ".join(missing),
            }
        )
    draft_team_rows.sort(key=lambda row: row["draft_score"], reverse=True)
    for rank, row in enumerate(draft_team_rows, 1):
        row["draft_rank"] = rank

    # Measure roster composition only in weeks where the team still had a
    # matchup. This avoids post-elimination drops distorting the final roster.
    construction_rows = []
    for team_key, team_name in team_names.items():
        weeks = sorted(active_weeks[team_key])
        draft_set = {
            row["player_key"] for row in draft if row["team_key"] == team_key
        }
        roster_slot_weeks = 0
        original_draft_slot_weeks = 0
        draft_value_weeks = 0.0
        acquired_value_weeks = 0.0

        for week in weeks:
            roster = snapshots[week][team_key]
            for player_key in roster:
                roster_slot_weeks += 1
                coverage_row = coverage_by_key.get(player_key, {})
                value = number(coverage_row.get("bbm_value"))
                vor = max(value - replacement_level, 0) if value is not None else 0
                if player_key in draft_set:
                    original_draft_slot_weeks += 1
                    draft_value_weeks += vor
                else:
                    acquired_value_weeks += vor

        last_week = max(weeks)
        final_roster = snapshots[last_week][team_key]
        retained = final_roster & draft_set
        acquired = final_roster - draft_set
        union = final_roster | draft_set
        total_value_weeks = draft_value_weeks + acquired_value_weeks
        construction_rows.append(
            {
                "team_key": team_key,
                "team_name": team_name,
                "last_active_week": last_week,
                "final_roster_size": len(final_roster),
                "drafted_players_retained": len(retained),
                "new_players_on_final_roster": len(acquired),
                "draft_roster_retention": round(len(retained) / len(draft_set), 4),
                "final_roster_similarity": round(len(retained) / len(union), 4)
                if union
                else 0,
                "roster_turnover": round(1 - len(retained) / len(union), 4)
                if union
                else 0,
                "drafted_roster_slot_share": round(
                    original_draft_slot_weeks / roster_slot_weeks, 4
                )
                if roster_slot_weeks
                else 0,
                "drafted_value_share": round(draft_value_weeks / total_value_weeks, 4)
                if total_value_weeks
                else 0,
                "acquired_value_share": round(acquired_value_weeks / total_value_weeks, 4)
                if total_value_weeks
                else 0,
                "draft_value_weeks": round(draft_value_weeks, 4),
                "acquired_value_weeks": round(acquired_value_weeks, 4),
            }
        )

    reliance = sorted(
        construction_rows, key=lambda row: row["drafted_value_share"], reverse=True
    )
    turnover = sorted(
        construction_rows, key=lambda row: row["roster_turnover"], reverse=True
    )

    write_csv("replacement_level.csv", replacement_rows)
    write_csv(
        "final_standings.csv",
        sorted(standings, key=lambda row: int(row["rank"])),
    )
    write_csv("draft_player_value.csv", draft_player_rows)
    write_csv("draft_team_rankings.csv", draft_team_rows)
    write_csv("roster_construction.csv", construction_rows)
    write_csv("pickup_analysis.csv", pickup_rows)
    write_csv("streamer_analysis.csv", streamer_rows)
    write_csv("weekly_injuries.csv", injury_rows)
    write_csv("weekly_rosters.csv", weekly_roster_rows)
    write_csv("weekly_events.csv", weekly_event_rows)
    write_csv("team_week_power.csv", weekly_strength)
    write_csv("trade_ledger.csv", trade_rows)

    report = [
        "# Draft and Roster Construction Analysis",
        "",
        "## Method",
        "",
        f"- Replacement level is BBM rank 157, the first player beyond the league's 156 draft slots.",
        f"- Replacement player: **{replacement['player_name']}**, value **{replacement_level:.3f}**.",
        f"- Sensitivity check: the average value from ranks 145–168 is **{sum(replacement_band) / len(replacement_band):.3f}**.",
        "- Player draft value is `max(final BBM value - replacement value, 0)`.",
        f"- Draft-position losses are capped at replacement rank {replacement_rank}; worse final ranks do not create extra penalties.",
        "- Team draft score is the sum of that value across all 13 draft picks.",
        "- Draft reliance weights player value by weeks spent on that team's roster.",
        "- Final roster means the roster at each team's last active matchup, avoiding post-elimination cleanup moves.",
        "",
        "## Best Drafts",
        "",
    ]
    for row in draft_team_rows:
        report.append(
            f"{row['draft_rank']}. **{row['team_name']}** — score {row['draft_score']:.3f}; "
            f"{row['players_above_replacement']} above-replacement picks; "
            f"best pick: {row['best_pick']}."
        )

    report.extend(["", "## Best Pickups", ""])
    for row in pickup_rows[:12]:
        report.append(
            f"{row['pickup_rank']}. **{row['player_name']}** — {row['team_name']}; "
            f"picked up {row['pickup_date']}; held {row['held_days']} days; "
            f"final BBM rank {row['bbm_rank'] or 'N/A'}; score {row['pickup_score']:.3f}."
        )

    report.extend(["", "## Team-by-Team Draft Notes", ""])
    for row in draft_team_rows:
        missing_note = (
            f" No BBM season row: {row['players_without_bbm_data']}."
            if row["players_without_bbm_data"]
            else ""
        )
        report.append(
            f"- **{row['team_name']}**: top contributor **{row['best_pick']}**; "
            f"best rank value **{row['best_steal']}** at pick {row['best_steal_pick']} "
            f"(finished {row['best_steal_final_rank']}); largest rank miss "
            f"**{row['largest_miss']}** at pick {row['largest_miss_pick']} "
            f"(finished {row['largest_miss_final_rank']}).{missing_note}"
        )

    report.extend(["", "## Most Reliant on Their Draft", ""])
    for rank, row in enumerate(reliance, 1):
        report.append(
            f"{rank}. **{row['team_name']}** — {percent(row['drafted_value_share'])} "
            f"of rostered positive value from original draft picks; "
            f"{percent(row['drafted_roster_slot_share'])} of roster slots."
        )

    report.extend(["", "## Final Roster Changed Most From Draft", ""])
    for rank, row in enumerate(turnover, 1):
        report.append(
            f"{rank}. **{row['team_name']}** — turnover {percent(row['roster_turnover'])}; "
            f"retained {row['drafted_players_retained']} of 13 picks; "
            f"{row['new_players_on_final_roster']} final-roster additions."
        )

    report.extend(
        [
            "",
            "## Data Quality",
            "",
            f"- Ownership reconstruction anomalies: {sum(anomalies.values())}.",
            f"- Details: {dict(anomalies)}.",
            "- The team draft ranking is unchanged when replacement value uses the ranks 145–168 average instead of rank 157.",
            "- Kyrie Irving and Fred VanVleet have no BBM row because they recorded no qualifying season data; they receive zero above-replacement value.",
            "- This is retrospective: BBM final value measures season outcome, not what managers knew on draft day.",
            "- Rostered-value share uses final player value weighted by roster duration; it is not exact production accrued while owned.",
        ]
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "DRAFT_ANALYSIS.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print("\n".join(report))


if __name__ == "__main__":
    main()
