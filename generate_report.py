#!/usr/bin/env python3
"""Generate a self-contained static HTML draft analysis report."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ANALYSIS = ROOT / "analysis"
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ANALYSIS / "index.html"


def read_csv(name: str) -> list[dict]:
    with (ANALYSIS / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_processed_csv(name: str) -> list[dict]:
    with (PROCESSED / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def json_for_html(value) -> str:
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def main() -> None:
    teams = read_csv("draft_team_rankings.csv")
    players = read_csv("draft_player_value.csv")
    construction = read_csv("roster_construction.csv")
    replacement = read_csv("replacement_level.csv")[0]
    standings = read_csv("final_standings.csv")
    pickups = read_csv("pickup_analysis.csv")
    streamers = read_csv("streamer_analysis.csv")
    weekly_rosters = read_csv("weekly_rosters.csv")
    weekly_events = read_csv("weekly_events.csv")
    team_week_power = read_csv("team_week_power.csv")
    trades = read_csv("trade_ledger.csv")
    team_metadata = read_processed_csv("teams.csv")
    transaction_actions = read_processed_csv("transaction_actions.csv")
    weekly_team_stats = read_processed_csv("weekly_team_stats.csv")

    activity_by_team = {}
    for team in team_metadata:
        activity_by_team[team["team_key"]] = {
            "team_key": team["team_key"],
            "team_name": team["team_name"],
            "manager_name": team["manager_name"],
            "number_of_moves": int(team["number_of_moves"] or 0),
            "number_of_trades": int(team["number_of_trades"] or 0),
            "action_count": 0,
            "add_count": 0,
            "drop_count": 0,
            "trade_action_count": 0,
        }
    for action in transaction_actions:
        team_keys = {
            key
            for key in (
                action["source_team_key"],
                action["destination_team_key"],
            )
            if key in activity_by_team
        }
        for team_key in team_keys:
            activity_by_team[team_key]["action_count"] += 1
            if action["action"] == "add" and action["destination_team_key"] == team_key:
                activity_by_team[team_key]["add_count"] += 1
            if action["action"] == "drop" and action["source_team_key"] == team_key:
                activity_by_team[team_key]["drop_count"] += 1
            if action["action"] == "trade":
                activity_by_team[team_key]["trade_action_count"] += 1

    for team_key, activity in activity_by_team.items():
        team_pickups = [row for row in pickups if row["team_key"] == team_key]
        team_streamers = [row for row in streamers if row["team_key"] == team_key]
        team_trades = [row for row in trades if row["team_key"] == team_key]
        activity["positive_pickup_value"] = round(
            sum(max(float(row["pickup_score"] or 0), 0) for row in team_pickups),
            6,
        )
        activity["streamer_count"] = len(team_streamers)
        activity["positive_streamer_value"] = round(
            sum(max(float(row["streamer_score"] or 0), 0) for row in team_streamers),
            6,
        )
        activity["trade_value_delta"] = round(
            sum(float(row["preliminary_value_delta"] or 0) for row in team_trades),
            6,
        )

    data = {
        "teams": teams,
        "players": players,
        "construction": construction,
        "replacement": replacement,
        "standings": standings,
        "pickups": pickups,
        "streamers": streamers,
        "weeklyRosters": weekly_rosters,
        "weeklyEvents": weekly_events,
        "teamWeekPower": team_week_power,
        "trades": trades,
        "managerActivity": list(activity_by_team.values()),
        "weeklyTeamStats": weekly_team_stats,
    }

    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SAS 2025–26 Draft Analysis</title>
  <style>
    :root {
      --paper: #fbfaf6;
      --white: #ffffff;
      --ink: #22211f;
      --muted: #716e67;
      --line: #dedbd3;
      --soft: #f2efe8;
      --blue: #5d7691;
      --good: #287451;
      --good-soft: #dfece5;
      --bad: #a5413f;
      --bad-soft: #f4e2df;
      --ochre: #b7833f;
    }
    * { box-sizing: border-box; }
    html, body { max-width: 100%; overflow-x: hidden; }
    body {
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font: 15px/1.55 "Avenir Next", Avenir, "Helvetica Neue", Arial, sans-serif;
    }
    main { width: calc(100% - 40px); max-width: 1100px; min-width: 0; margin: 0 auto; padding: 38px 0 84px; }
    h1, h2, h3, .summary-card .value {
      font-family: "Avenir Next", Avenir, "Helvetica Neue", Arial, sans-serif;
      font-weight: 750;
    }
    h1 { font-size: clamp(38px, 7vw, 68px); line-height: .98; letter-spacing: -0.055em; margin: 0; max-width: 820px; }
    h2 { font-size: 30px; line-height: 1.08; letter-spacing: -.035em; margin: 0 0 18px; }
    h3 { margin: 0; font-size: 21px; letter-spacing: -.025em; }
    p { margin: 0; }
    .eyebrow { color: var(--blue); text-transform: uppercase; letter-spacing: .14em; font-weight: 700; margin-bottom: 15px; overflow-wrap: anywhere; }
    .lede { color: var(--muted); max-width: 760px; font-size: 17px; margin-top: 14px; }
    .tabs { position: sticky; top: 0; z-index: 20; display: flex; gap: 6px; margin: 30px 0 0; padding: 9px; background: rgba(251,250,246,.94); border: 1px solid var(--line); backdrop-filter: blur(12px); }
    .tab-button { appearance: none; border: 0; background: transparent; color: var(--muted); padding: 10px 17px; font: inherit; font-weight: 700; cursor: pointer; }
    .tab-button:hover { color: var(--ink); background: var(--soft); }
    .tab-button.active { color: var(--white); background: var(--ink); }
    .tab-panel { display: none; }
    .tab-panel.active { display: block; }
    section { margin-top: 56px; }
    .section-heading { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; }
    .section-heading h2, .section-heading h3 { margin: 0; }
    .chart-caption { margin: -8px 0 20px; color: var(--muted); font-size: 14px; }
    .visual-card { padding: 20px; background: var(--white); border: 1px solid var(--line); }
    .visual-card + .visual-card { margin-top: 16px; }
    .wide-chart-scroll { width: 100%; overflow-x: auto; padding-bottom: 8px; }
    .wide-chart-scroll svg { min-width: 1380px; }
    .wide-chart-scroll.short-series svg { min-width: 900px; }
    .visual-title { display: flex; justify-content: space-between; align-items: baseline; gap: 16px; margin-bottom: 12px; }
    .visual-title h3 { font-size: 21px; }
    .visual-title span { color: var(--muted); font-size: 12px; }
    .visual-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .chart-svg { display: block; width: 100%; height: auto; overflow: visible; }
    .axis-line { stroke: var(--line); stroke-width: 1; }
    .axis-label { fill: var(--muted); font: 11px "Avenir Next", sans-serif; }
    .chart-label-svg { fill: var(--ink); font: 11px "Avenir Next", sans-serif; font-weight: 650; }
    .race-line { fill: none; stroke-width: 3; opacity: .76; stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 1800; animation: draw-line 1.4s ease both; }
    .race-line:hover { opacity: 1; stroke-width: 5; }
    .race-point { stroke: var(--white); stroke-width: 1.5; }
    .race-end-label { font: 700 11px "Avenir Next", sans-serif; }
    @keyframes draw-line { from { stroke-dashoffset: 1200; } to { stroke-dashoffset: 0; } }
    .race-legend { display: flex; flex-wrap: wrap; gap: 7px 13px; margin-top: 14px; }
    .race-key { display: inline-flex; align-items: center; gap: 6px; border: 0; background: transparent; color: var(--muted); padding: 0; font: 12px inherit; cursor: pointer; }
    .race-key::before { content: ""; width: 14px; height: 3px; background: var(--team-color); }
    .race-key:hover, .race-key.active { color: var(--ink); }
    .rank-heatmap-scroll { overflow-x: auto; padding-bottom: 8px; }
    .rank-heatmap { display: grid; min-width: 1380px; border-top: 1px solid var(--line); border-left: 1px solid var(--line); }
    .rank-heatmap.playoffs { min-width: 760px; }
    .heat-cell { min-height: 48px; display: grid; place-items: center; padding: 5px; border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); text-align: center; }
    .heat-cell.header { min-height: 40px; background: var(--ink); color: var(--white); font-size: 11px; font-weight: 700; }
    .heat-cell.team { justify-items: start; padding-left: 10px; background: var(--white); color: var(--ink); font-size: 12px; font-weight: 750; text-align: left; }
    .heat-cell.rank { color: var(--ink); font-weight: 800; font-variant-numeric: tabular-nums; }
    .heat-cell.rank small { display: block; color: rgba(34,33,31,.62); font-size: 9px; font-weight: 600; }
    .heat-cell.missing { background: repeating-linear-gradient(135deg, #f1eee7, #f1eee7 5px, #e7e3da 5px, #e7e3da 10px); color: var(--muted); font-size: 10px; }
    .heatmap-legend { display: flex; align-items: center; gap: 9px; margin-top: 10px; color: var(--muted); font-size: 12px; }
    .rank-gradient { width: 180px; height: 10px; background: linear-gradient(90deg, hsl(145 38% 72%), #f3f0e9, hsl(2 48% 73%)); }
    .scatter-dot { stroke: var(--white); stroke-width: 2; }
    .scatter-label { fill: var(--ink); font: 10px "Avenir Next", sans-serif; }
    .identity-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 10px; color: var(--muted); font-size: 12px; }
    .opportunity-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 18px; }
    .opportunity-card { display: grid; grid-template-columns: 1fr auto 1fr; gap: 10px; align-items: center; padding: 13px; background: var(--white); border: 1px solid var(--line); }
    .opportunity-card .picked { color: var(--bad); }
    .opportunity-card .available { color: var(--good); text-align: right; }
    .opportunity-card .arrow { color: var(--muted); }
    .opportunity-card small { display: block; color: var(--muted); margin-top: 2px; }
    .draft-board-scroll { overflow-x: auto; padding-bottom: 8px; }
    .draft-board { display: grid; grid-template-columns: 52px repeat(12, minmax(112px, 1fr)); min-width: 1450px; border-top: 2px solid var(--ink); border-left: 1px solid var(--line); }
    .draft-cell { min-height: 70px; padding: 8px; border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); }
    .draft-cell.header { min-height: 48px; display: grid; align-items: center; background: var(--ink); color: var(--white); font-size: 11px; font-weight: 700; }
    .draft-cell.round { display: grid; place-items: center; background: var(--soft); color: var(--muted); font-weight: 750; }
    .draft-cell .pick-number { color: rgba(34,33,31,.62); font-size: 10px; }
    .draft-cell .player-name { display: block; margin-top: 4px; font-size: 12px; font-weight: 750; line-height: 1.15; }
    .draft-cell .pick-result { display: block; margin-top: 5px; color: rgba(34,33,31,.67); font-size: 10px; }
    .draft-board-legend { display: flex; align-items: center; gap: 10px; margin-top: 12px; color: var(--muted); font-size: 12px; }
    .draft-gradient { width: 180px; height: 10px; background: linear-gradient(90deg, hsl(2 48% 69%), #f3f0e9, hsl(145 36% 69%)); }
    .formula-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 16px; }
    .formula-card { padding: 15px; background: var(--white); border: 1px solid var(--line); }
    .formula-card strong { display: block; margin-bottom: 5px; }
    .formula-card code { display: block; margin-top: 8px; color: var(--blue); font: 12px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; white-space: normal; }
    details.info { position: relative; display: inline-block; }
    details.info > summary { list-style: none; display: grid; place-items: center; width: 23px; height: 23px; border: 1px solid var(--line); border-radius: 50%; color: var(--muted); background: var(--white); font: 700 13px/1 Georgia, serif; cursor: pointer; }
    details.info > summary::-webkit-details-marker { display: none; }
    details.info[open] > summary { color: var(--white); background: var(--blue); border-color: var(--blue); }
    .info-card { position: absolute; z-index: 30; top: 31px; left: 0; width: min(390px, calc(100vw - 44px)); padding: 15px 17px; background: var(--white); border: 1px solid var(--line); box-shadow: 0 12px 30px rgba(34,33,31,.14); color: var(--muted); font-size: 13px; }
    .info-card strong { color: var(--ink); }
    .header-info { margin-top: 15px; }
    .header-info .info-card { width: min(540px, calc(100vw - 44px)); }
    .summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 28px; }
    .summary-card, .team-card { background: var(--white); border: 1px solid var(--line); }
    .summary-card { padding: 22px; border-top: 4px solid var(--blue); }
    .summary-card.champion { border-top-color: var(--good); }
    .summary-card.third { border-top-color: var(--ochre); }
    .summary-card .label { color: var(--muted); font-size: 13px; text-transform: uppercase; letter-spacing: .08em; }
    .summary-card .value { font-size: 27px; margin-top: 7px; }
    .summary-card .detail { color: var(--muted); margin-top: 4px; }
    .awards-grid {
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: minmax(270px, 31%);
      gap: 16px;
      max-width: 100%;
      padding: 4px 4px 18px;
      overflow-x: auto;
      overscroll-behavior-inline: contain;
      scroll-snap-type: inline mandatory;
      scrollbar-width: thin;
      scrollbar-color: var(--blue) var(--soft);
    }
    .awards-grid::-webkit-scrollbar { height: 8px; }
    .awards-grid::-webkit-scrollbar-track { background: var(--soft); }
    .awards-grid::-webkit-scrollbar-thumb { background: var(--blue); border-radius: 999px; }
    .award-card {
      --award-accent: var(--ochre);
      position: relative;
      aspect-ratio: 4 / 5;
      min-height: 420px;
      overflow: hidden;
      padding: 0;
      color: var(--ink);
      background: #f9f6ee;
      border: 1px solid #cec8bc;
      box-shadow: 0 18px 40px rgba(34,33,31,.12);
      cursor: pointer;
      appearance: none;
      width: 100%;
      text-align: left;
      font: inherit;
      scroll-snap-align: start;
    }
    .award-card::after {
      content: "";
      position: absolute;
      z-index: 4;
      inset: 10px;
      border: 1px solid rgba(29,28,24,.16);
      pointer-events: none;
    }
    .award-card:hover { transform: translateY(-3px); transition: transform .18s ease; }
    .award-visual {
      position: relative;
      display: block;
      height: 48%;
      overflow: hidden;
      background:
        radial-gradient(circle at 78% 28%, color-mix(in srgb, var(--award-accent) 85%, white) 0 11%, transparent 11.5%),
        linear-gradient(145deg, #191816, #302c27);
    }
    .award-art {
      position: absolute;
      inset: 0;
      background-position: center top;
      background-size: cover;
      opacity: 1;
    }
    .award-topline { position: absolute; z-index: 2; top: 20px; left: 20px; right: 20px; display: flex; justify-content: space-between; gap: 12px; color: rgba(255,255,255,.78); font-size: 10px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; text-shadow: 0 1px 6px rgba(0,0,0,.35); }
    .award-number { color: var(--award-accent); }
    .award-content { display: flex; flex-direction: column; height: 52%; padding: 19px 22px 18px; text-align: left; }
    .award-copy { display: block; }
    .award-title { display: block; max-width: 96%; color: var(--muted); font-size: 11px; font-weight: 800; line-height: 1.2; letter-spacing: .1em; text-transform: uppercase; }
    .award-winner { display: block; margin-top: 7px; font-size: clamp(20px, 2.2vw, 27px); font-weight: 800; line-height: 1.05; letter-spacing: -.035em; }
    .award-manager { display: block; margin-top: 4px; color: var(--muted); font-size: 11px; }
    .award-stat { display: block; margin-top: auto; }
    .award-stat strong { display: block; color: var(--award-accent); font: 800 clamp(34px, 5vw, 54px)/.9 "Avenir Next", Avenir, "Helvetica Neue", Arial, sans-serif; letter-spacing: -.055em; }
    .award-stat span { display: block; max-width: 96%; margin-top: 6px; color: var(--muted); font-size: 11px; line-height: 1.3; }
    .award-footer { display: flex; justify-content: space-between; margin-top: 10px; color: #8c877d; font-size: 8px; font-weight: 800; letter-spacing: .11em; text-transform: uppercase; }
    .award-card[data-award="champion"] { --award-accent: #e6bf5b; }
    .award-card[data-award="draft"] { --award-accent: #6fc494; }
    .award-card[data-award="pickup"] { --award-accent: #71a7d3; }
    .award-card[data-award="steal"] { --award-accent: #bc91cf; }
    .award-card[data-award="category"] { --award-accent: #e28a66; }
    .award-card[data-award="activity"] { --award-accent: #d7a75f; }
    .award-card[data-award="photo-finish"] { --award-accent: #ef7d69; }
    .award-card[data-award="last-day"] { --award-accent: #79b8d8; }
    .carousel-hint { display: flex; align-items: center; gap: 8px; margin: 8px 0 12px; color: var(--muted); font-size: 12px; }
    .carousel-hint::after { content: "→"; color: var(--blue); font-size: 18px; }
    .award-share-note { margin-top: 12px; color: var(--muted); font-size: 12px; }
    .award-modal { position: fixed; z-index: 100; inset: 0; display: none; place-items: center; padding: 24px; background: rgba(20,19,17,.88); }
    .award-modal.open { display: grid; }
    .award-modal-inner { position: relative; width: min(540px, calc(100vw - 32px)); }
    .award-modal .award-card { width: 100%; min-height: 0; cursor: default; transform: none; }
    .award-close { position: absolute; z-index: 2; top: -14px; right: -14px; width: 34px; height: 34px; border: 1px solid rgba(255,255,255,.3); border-radius: 50%; color: white; background: #1c1a18; font-size: 20px; cursor: pointer; }
    .section-intro { color: var(--muted); max-width: 820px; margin: -8px 0 20px; }
    .chart-list { display: grid; gap: 10px; }
    .chart-row {
      display: grid; grid-template-columns: minmax(180px, 1.4fr) 4fr 68px;
      gap: 14px; align-items: center; min-height: 28px;
    }
    .chart-label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .track { height: 16px; background: var(--soft); border-radius: 1px; overflow: hidden; }
    .bar { height: 100%; background: var(--blue); }
    .bar.good { background: var(--good); }
    .bar.streamer { background: var(--ochre); }
    .bar.bad, .bar.turnover { background: var(--bad); }
    .number { text-align: right; font-variant-numeric: tabular-nums; color: var(--muted); }
    .table-wrap { width: 100%; max-width: 100%; min-width: 0; overflow-x: auto; border-top: 2px solid var(--ink); border-bottom: 1px solid var(--ink); }
    table { width: 100%; border-collapse: collapse; min-width: 850px; background: transparent; }
    th, td { padding: 13px 12px; border-bottom: 1px solid var(--line); text-align: left; }
    th { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .09em; background: var(--soft); }
    tbody tr:last-child td { border-bottom: 0; }
    tbody tr:hover { background: #f5f2eb; }
    .good-text { color: var(--good); }
    .bad-text { color: var(--bad); }
    .streamer-text { color: var(--ochre); }
    .muted { color: var(--muted); }
    .rank { color: var(--blue); font-weight: 750; }
    .team-grid { display: grid; gap: 20px; }
    .team-picker { display: flex; align-items: center; gap: 12px; margin-top: 24px; padding: 14px 16px; background: var(--white); border: 1px solid var(--line); }
    .team-picker label { color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }
    .team-picker select { flex: 1; min-width: 0; padding: 10px 12px; border: 1px solid var(--line); background: var(--paper); color: var(--ink); font: inherit; }
    .team-card[hidden] { display: none; }
    .team-card { padding: 0; overflow: hidden; }
    .team-hero { display: grid; grid-template-columns: 120px 1fr; gap: 22px; padding: 28px; color: var(--white); background: var(--ink); }
    .finish-badge { display: grid; align-content: center; justify-items: center; min-height: 115px; border: 1px solid rgba(255,255,255,.28); }
    .finish-badge span { font-size: 12px; text-transform: uppercase; letter-spacing: .12em; opacity: .7; }
    .finish-badge strong { font: 800 52px/1 "Avenir Next", Avenir, "Helvetica Neue", Arial, sans-serif; letter-spacing: -.05em; }
    .team-hero h3 { color: var(--white); font-size: 34px; }
    .team-card .meta { color: rgba(255,255,255,.68); margin-top: 5px; }
    .hero-stats { display: flex; flex-wrap: wrap; gap: 9px; margin-top: 17px; }
    .hero-stat { padding: 8px 11px; border: 1px solid rgba(255,255,255,.22); }
    .hero-stat strong { display: block; font-size: 18px; }
    .hero-stat span { color: rgba(255,255,255,.65); font-size: 10px; text-transform: uppercase; letter-spacing: .08em; }
    .team-body { padding: 26px; }
    .spotlight-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .spotlight { min-height: 118px; padding: 16px; background: var(--soft); border-top: 4px solid var(--blue); }
    .spotlight.good { border-color: var(--good); background: var(--good-soft); }
    .spotlight.bad { border-color: var(--bad); background: var(--bad-soft); }
    .spotlight.ochre { border-color: var(--ochre); background: #f7eddc; }
    .spotlight span { display: block; color: var(--muted); font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .09em; }
    .spotlight strong { display: block; margin-top: 7px; font-size: 18px; }
    .spotlight small { display: block; color: var(--muted); margin-top: 5px; }
    .team-card dl { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px 18px; margin: 18px 0 0; }
    .team-card dt { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }
    .team-card dd { margin: 3px 0 0; }
    .team-info { margin-top: 15px; }
    .team-info .info-card { width: min(520px, calc(100vw - 70px)); }
    .pick-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 18px; }
    .pick-list { border: 1px solid var(--line); overflow: hidden; }
    .pick-list h4 { margin: 0; padding: 10px 12px; background: var(--soft); font-size: 13px; }
    .pick-list.good h4 { color: var(--good); }
    .pick-list.bad h4 { color: var(--bad); }
    .pick-list ol { list-style: none; padding: 0; margin: 0; }
    .pick-list li { display: flex; justify-content: space-between; gap: 12px; padding: 9px 12px; border-top: 1px solid var(--line); }
    .pick-list small { color: var(--muted); text-align: right; }
    .missing { color: var(--ochre); margin-top: 14px; font-size: 13px; }
    .subsection { margin-top: 32px; }
    .subsection h3 { font-size: 24px; margin-bottom: 12px; }
    .pickup-chart .chart-row { grid-template-columns: minmax(210px, 1.7fr) 4fr 70px; }
    .team-draft { margin-top: 22px; }
    .team-draft summary { cursor: pointer; color: var(--ink); font-weight: 750; padding: 12px 0; border-top: 1px solid var(--line); }
    .team-draft summary::marker { color: var(--blue); }
    .team-draft table { min-width: 740px; font-size: 14px; }
    .team-draft th, .team-draft td { padding: 9px 10px; }
    .outcome-good { background: var(--good-soft); }
    .outcome-bad { background: var(--bad-soft); }
    .pickup-note { margin-top: 16px; padding: 12px 14px; border-left: 3px solid var(--good); background: var(--good-soft); }
    .pickup-note strong { color: var(--good); }
    .timeline { margin-top: 24px; padding-top: 22px; border-top: 2px dashed var(--line); }
    .timeline-head { display: flex; justify-content: space-between; align-items: baseline; gap: 16px; }
    .timeline-head h4 { margin: 0; font-size: 16px; }
    .week-label { font-family: "Avenir Next", Avenir, "Helvetica Neue", Arial, sans-serif; font-size: 19px; font-weight: 750; letter-spacing: -.025em; color: var(--blue); }
    .week-slider { width: 100%; margin: 14px 0 20px; accent-color: var(--blue); }
    .timeline-grid { display: grid; grid-template-columns: minmax(260px, .9fr) 1.2fr 1fr; gap: 18px; align-items: start; }
    .timeline-panel { border: 1px solid var(--line); background: var(--white); min-height: 250px; padding: 15px; }
    .timeline-panel h5 { margin: 0 0 12px; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
    .radar-wrap { display: grid; place-items: center; }
    .radar-wrap svg { width: 100%; max-width: 340px; height: auto; overflow: visible; }
    .radar-grid { fill: none; stroke: #d8d5cd; stroke-width: 1; }
    .radar-axis { stroke: #dedbd3; stroke-width: 1; }
    .radar-shape { fill: rgba(93,118,145,.22); stroke: var(--blue); stroke-width: 2; }
    .radar-label { font: 10px "Avenir Next", sans-serif; fill: var(--muted); }
    .power-score { text-align: center; font-family: "Avenir Next", Avenir, "Helvetica Neue", Arial, sans-serif; font-size: 21px; font-weight: 750; letter-spacing: -.025em; }
    .roster-list { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 7px; }
    .roster-player { padding: 7px 8px; background: var(--soft); font-size: 13px; display: flex; justify-content: space-between; gap: 8px; }
    .roster-player.entering { animation: roster-enter .34s ease both; }
    .roster-player.leaving { animation: roster-leave .3s ease both; }
    @keyframes roster-enter { from { opacity: 0; transform: translateY(8px) scale(.97); } to { opacity: 1; transform: none; } }
    @keyframes roster-leave { from { opacity: 1; transform: none; } to { opacity: 0; transform: translateY(-8px) scale(.97); } }
    .roster-player.drafted { border-left: 3px solid var(--blue); }
    .roster-player.streamer { border-left: 3px solid var(--ochre); background: #f7eddc; }
    .roster-player.injured { border-left: 3px solid var(--bad); background: var(--bad-soft); }
    .roster-player small { color: var(--muted); white-space: nowrap; }
    .timeline-legend { display: flex; flex-wrap: wrap; gap: 8px 16px; margin: 8px 0 2px; color: var(--muted); font-size: 12px; }
    .roster-change-strip { display: flex; flex-wrap: wrap; gap: 7px; min-height: 28px; margin: 0 0 12px; }
    .change-chip { padding: 4px 8px; font-size: 11px; background: var(--soft); }
    .change-chip.in { color: var(--good); background: var(--good-soft); }
    .change-chip.out { color: var(--bad); background: var(--bad-soft); }
    .legend-key::before { content: ""; display: inline-block; width: 10px; height: 10px; margin-right: 6px; vertical-align: -1px; background: var(--blue); }
    .legend-key.streamer::before { background: var(--ochre); }
    .legend-key.injured::before { background: var(--bad); }
    .event-list { display: grid; gap: 8px; }
    .event { padding: 9px 10px; background: var(--soft); font-size: 13px; }
    .event.trade { background: #eee5f3; border-left: 3px solid #825c91; }
    .event.injury { background: var(--bad-soft); border-left: 3px solid var(--bad); }
    .event-date { color: var(--muted); font-size: 11px; margin-bottom: 3px; }
    .empty-state { color: var(--muted); font-style: italic; font-size: 13px; }
    .trade-table .positive { color: var(--good); font-weight: 700; }
    .trade-table .negative { color: var(--bad); font-weight: 700; }
    .trade-table { margin-top: 18px; }
    .network-edge { stroke: #9e9281; stroke-linecap: round; opacity: .5; }
    .network-node { fill: var(--white); stroke: var(--ink); stroke-width: 2; }
    .network-node-label { fill: var(--ink); font: 10px "Avenir Next", sans-serif; font-weight: 700; }
    .trade-timeline { position: relative; padding: 34px 10px 12px; }
    .trade-timeline-line { height: 2px; background: var(--line); }
    .trade-dot { position: absolute; top: 26px; width: 13px; height: 13px; margin-left: -6px; border: 2px solid var(--white); border-radius: 50%; background: var(--blue); box-shadow: 0 0 0 1px var(--line); cursor: pointer; }
    .trade-dot:hover, .trade-dot.active { transform: scale(1.45); background: var(--ochre); }
    .trade-week-labels { display: flex; justify-content: space-between; color: var(--muted); font-size: 11px; margin-top: 10px; }
    .trade-impact-card { margin-top: 16px; padding: 18px; background: var(--soft); }
    .impact-header { display: flex; justify-content: space-between; gap: 14px; margin-bottom: 12px; }
    .impact-team { display: grid; grid-template-columns: minmax(130px,1fr) 2fr auto; gap: 12px; align-items: center; padding: 9px 0; border-top: 1px solid var(--line); }
    .impact-line { height: 8px; position: relative; background: linear-gradient(90deg, var(--bad-soft), var(--soft), var(--good-soft)); }
    .impact-line::before { content: ""; position: absolute; left: var(--before); top: -3px; width: 3px; height: 14px; background: var(--muted); }
    .impact-line::after { content: ""; position: absolute; left: var(--after); top: -4px; width: 9px; height: 16px; margin-left: -3px; background: var(--blue); }
    @media (max-width: 760px) {
      main { width: calc(100% - 24px); max-width: 1100px; padding-top: 30px; }
      .tabs { overflow-x: auto; }
      .tab-button { white-space: nowrap; padding: 9px 13px; }
      .summary-grid, .team-grid, .pick-grid { grid-template-columns: 1fr; }
      .awards-grid { grid-auto-columns: min(82vw, 330px); }
      .visual-grid, .opportunity-grid, .spotlight-grid, .formula-grid { grid-template-columns: 1fr; }
      .team-picker { align-items: stretch; flex-direction: column; }
      .team-hero { grid-template-columns: 86px 1fr; padding: 20px; }
      .finish-badge { min-height: 88px; }
      .finish-badge strong { font-size: 40px; }
      .team-card dl { grid-template-columns: 1fr 1fr; }
      .chart-row { grid-template-columns: minmax(0, 120px) minmax(0, 1fr) 48px; gap: 8px; font-size: 13px; }
      .pickup-chart .chart-row { grid-template-columns: minmax(0, 140px) minmax(0, 1fr) 48px; }
      .timeline-grid { grid-template-columns: 1fr; }
      .roster-list { grid-template-columns: 1fr 1fr; }
      section { margin-top: 40px; }
    }
  </style>
</head>
<body>
<main>
  <header>
    <div class="eyebrow">SAS · Yahoo Fantasy Basketball · 2025–26</div>
    <h1>Season report</h1>
    <p class="lede">Draft results, roster changes, weekly category comparisons and trades.</p>
    <details class="info header-info">
      <summary aria-label="About this report">i</summary>
      <div class="info-card" id="method"></div>
    </details>
  </header>

  <nav class="tabs" role="tablist" aria-label="Report views">
    <button class="tab-button active" id="tab-league" role="tab" aria-selected="true" aria-controls="view-league" data-tab="league">League</button>
    <button class="tab-button" id="tab-teams" role="tab" aria-selected="false" aria-controls="view-teams" data-tab="teams">Individual teams</button>
    <button class="tab-button" id="tab-trades" role="tab" aria-selected="false" aria-controls="view-trades" data-tab="trades">Trades</button>
  </nav>

  <div class="tab-panel active" id="view-league" role="tabpanel" aria-labelledby="tab-league">
    <div class="summary-grid" id="summary"></div>

    <section>
      <div class="section-heading">
        <h2>Season outcome</h2>
        <details class="info"><summary aria-label="About final standings">i</summary><div class="info-card">The podium reflects the final Yahoo playoff result. The table also preserves each team’s regular-season record and playoff seed.</div></details>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Finish</th><th>Team</th><th>Manager</th><th>Regular-season record</th><th>Playoff seed</th></tr></thead>
          <tbody id="final-standings"></tbody>
        </table>
      </div>
    </section>

    <section hidden aria-hidden="true">
      <div class="section-heading">
        <h2>Awards &amp; season moments</h2>
        <details class="info"><summary aria-label="About league awards and moments">i</summary><div class="info-card">Awards recognize a season-long achievement. Moments capture a specific matchup that came down to one category, one late move or a razor-thin margin. Click a card for a 4:5 share preview.</div></details>
      </div>
      <p class="chart-caption">Season awards first, then the close calls people will actually argue about in the group chat.</p>
      <div class="carousel-hint">Swipe or scroll through the cards</div>
      <div class="awards-grid" id="share-cards-grid"></div>
      <p class="award-share-note">Click any card to preview its future social-share format.</p>
    </section>

    <section>
      <div class="section-heading">
        <h2>How the season evolved</h2>
        <details class="info"><summary aria-label="About weekly category ranking">i</summary><div class="info-card">For each week and category, teams are placed from 0 to 100 relative to the other teams with Yahoo results that week. The best result is 100 and the worst is 0. Turnovers are reversed because fewer is better. The nine category positions are averaged, then teams are ranked by that average. Missing postseason results remain explicitly blank.</div></details>
      </div>
      <div class="visual-card">
        <div class="visual-title"><h3>Regular season</h3><span>Weeks 1–20</span></div>
        <p class="chart-caption">Complete data: 240 of 240 possible team-week results. Each cell shows that week’s rank and the average of the team’s nine category positions.</p>
        <div id="regular-season-race"></div>
      </div>
      <div class="visual-card">
        <div class="visual-title"><h3>Playoffs and consolation bracket</h3><span>Weeks 21–23</span></div>
        <p class="chart-caption">Yahoo records: Week 21 has 8 teams, Week 22 has 12, and Week 23 has 8. Striped cells mean no matchup result; no value is carried forward.</p>
        <div id="playoff-race"></div>
      </div>
    </section>

    <section>
      <div class="section-heading">
        <h2>The draft</h2>
        <details class="info"><summary aria-label="About draft analysis">i</summary><div class="info-card">The draft board shows every selection and final rank. Team draft value adds each pick’s positive BBM value above rank 157. It is a final-results review, not a judgment based on information available on draft night.</div></details>
      </div>
      <div class="draft-board-scroll"><div class="draft-board" id="draft-board"></div></div>
      <div class="draft-board-legend"><span>Worse</span><span class="draft-gradient"></span><span>Better</span></div>
      <div class="visual-grid" style="margin-top:22px">
        <div class="visual-card">
          <div class="visual-title"><h3>Draft value by team</h3><span>Sum above rank 157</span></div>
          <div class="chart-list" id="draft-chart"></div>
        </div>
        <div class="visual-card">
          <div class="visual-title"><h3>Draft value vs. final finish</h3><span>Original draft only</span></div>
          <div id="draft-finish-scatter"></div>
        </div>
      </div>
      <div class="subsection">
        <h3>Draft leaderboard</h3>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Rank</th><th>Team</th><th>Draft value over rank 157</th><th>Picks above rank 157</th><th>Top contributor</th><th>Best steal</th></tr></thead>
            <tbody id="leaderboard"></tbody>
          </table>
        </div>
      </div>
    </section>

    <section>
      <div class="section-heading">
        <h2 class="good-text">Top picks</h2>
        <details class="info"><summary aria-label="How top picks are measured">i</summary><div class="info-card">Value above replacement drives this list. Adjusted rank gain compares draft position with final rank and caps downside at replacement rank 157.</div></details>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Player</th><th>Team</th><th>Pick</th><th>Final BBM rank</th><th>Value above replacement</th><th>Adjusted rank gain</th></tr></thead>
          <tbody id="top-picks"></tbody>
        </table>
      </div>
    </section>

    <section>
      <div class="section-heading">
        <h2 class="bad-text">Worst pick outcomes</h2>
        <details class="info"><summary aria-label="How worst picks are measured">i</summary><div class="info-card">Losses stop at replacement rank 157. Falling from useful to unrosterable matters; falling from rank 300 to 500 does not. Injuries count as outcomes, not proof that a pick was unreasonable.</div></details>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Player</th><th>Team</th><th>Pick</th><th>Final BBM rank</th><th>Adjusted rank loss</th><th>Context</th></tr></thead>
          <tbody id="worst-picks"></tbody>
        </table>
      </div>
      <div class="visual-title" style="margin-top:22px"><h3>Who was still available?</h3><span>Best outcome selected within the next 12 picks</span></div>
      <div class="opportunity-grid" id="opportunity-cost"></div>
    </section>

    <section>
      <div class="section-heading">
        <h2>Roster management</h2>
        <details class="info"><summary aria-label="About roster management">i</summary><div class="info-card">These views compare waiver value, move volume, reliance on original draft picks, and how much each final roster changed from draft night.</div></details>
      </div>
      <div class="visual-card">
        <div class="visual-title"><h3>Moves vs. value added by pickups</h3><span>Labels show player actions</span></div>
        <div id="transaction-scatter"></div>
      </div>
      <div class="visual-grid" style="margin-top:16px">
        <div class="visual-card">
          <div class="visual-title"><h3>Value supplied by original draft picks</h3><span>Higher means more draft-reliant</span></div>
          <div class="chart-list" id="reliance-chart"></div>
        </div>
        <div class="visual-card">
          <div class="visual-title"><h3>Final roster changed from draft night</h3><span>Higher means more turnover</span></div>
          <div class="chart-list" id="turnover-chart"></div>
        </div>
      </div>
    </section>

    <section>
      <div class="section-heading">
        <h2 class="good-text">Best pickups</h2>
        <details class="info"><summary aria-label="How pickup value is calculated">i</summary><div class="info-card">Subtract the BBM value of rank 157 from the player’s final value, then multiply by the fraction of the 167-day fantasy season that the team held him. Trades are excluded.</div></details>
      </div>
      <div class="chart-list pickup-chart" id="pickup-chart"></div>
      <div class="table-wrap" style="margin-top:20px">
        <table>
          <thead><tr><th>Player</th><th>Fantasy team</th><th>Picked up</th><th>Held</th><th>End</th><th>Final BBM rank</th><th>Value × season held</th><th>Context</th></tr></thead>
          <tbody id="best-pickups"></tbody>
        </table>
      </div>
    </section>

    <section>
      <div class="section-heading">
        <h2 class="streamer-text">Best short-term pickups</h2>
        <details class="info"><summary aria-label="How short-term pickups are measured">i</summary><div class="info-card">These are waiver or free-agent pickups held 14 days or fewer and released before season end. Final value over rank 157 is multiplied by days held divided by 14. This does not measure the player’s exact statistics during those days.</div></details>
      </div>
      <div class="chart-list pickup-chart" id="streamer-chart"></div>
      <div class="table-wrap" style="margin-top:20px">
        <table>
          <thead><tr><th>Player</th><th>Fantasy team</th><th>Picked up</th><th>Held</th><th>Final BBM rank</th><th>Value × days held ÷ 14</th></tr></thead>
          <tbody id="best-streamers"></tbody>
        </table>
      </div>
    </section>

    <section>
      <div class="section-heading"><h2>Manager styles</h2><details class="info"><summary aria-label="How to read this chart">i</summary><div class="info-card">Horizontal position is the percentage of positive rostered value supplied by original draft picks. Vertical position is Yahoo’s move count. Circle size is completed trades. Color moves from cool to warm as the number of pickups held 14 days or fewer increases.</div></details></div>
      <div class="visual-card">
        <div id="manager-identity-map"></div>
        <div class="identity-legend"><span>Left: less value from drafted players</span><span>Right: more value from drafted players</span><span>Higher: more moves</span><span>Larger: more trades</span><span>Warmer: more pickups held ≤14 days</span></div>
      </div>
    </section>

    <section>
      <div class="section-heading"><h2>How the numbers are calculated</h2><details class="info"><summary aria-label="About calculations">i</summary><div class="info-card">The report favors explicit calculations over composite mystery scores. These are the four formulas used most often across the page.</div></details></div>
      <div class="formula-grid">
        <div class="formula-card"><strong>Weekly nine-category average</strong>Each category is converted to a 0–100 position among that week’s teams. The nine positions are averaged equally.<code>(FG% position + FT% position + … + turnover position) ÷ 9</code></div>
        <div class="formula-card"><strong>Draft value over replacement</strong>For every pick, subtract the BBM value of rank 157. Negative results become zero, then all 13 picks are added.<code>Σ max(player BBM value − rank-157 value, 0)</code></div>
        <div class="formula-card"><strong>Pickup value while held</strong>A pickup’s value over replacement is multiplied by the fraction of the 167-day fantasy season that the team held him.<code>value over replacement × days held in season ÷ 167</code></div>
        <div class="formula-card"><strong>Trade value difference</strong>For each team in a trade, add the full-season value over replacement received and subtract the value sent.<code>received value over replacement − sent value over replacement</code></div>
      </div>
    </section>
  </div>

  <div class="tab-panel" id="view-teams" role="tabpanel" aria-labelledby="tab-teams" hidden>
    <section>
      <div class="section-heading"><h2>Individual teams</h2><details class="info"><summary aria-label="About team reports">i</summary><div class="info-card">Choose a team to see its complete draft, strongest pickup, weekly roster changes, injury-list placements and its 0–100 position in each scoring category.</div></details></div>
      <div class="team-picker"><label for="team-select">Team</label><select id="team-select"></select></div>
      <div class="team-grid" id="team-cards"></div>
    </section>
  </div>

  <div class="tab-panel" id="view-trades" role="tabpanel" aria-labelledby="tab-trades" hidden>
    <section>
      <div class="section-heading"><h2>Trades</h2><details class="info"><summary aria-label="How trade values are calculated">i</summary><div class="info-card">Each trade appears once. For each team, the table adds the full-season BBM value over rank 157 received, then subtracts the same value sent. It does not yet isolate statistics produced after the trade date.</div></details></div>
      <div class="visual-card">
        <div class="visual-title"><h3>Who traded with whom</h3><span>Thicker line = more completed trades between those managers</span></div>
        <div id="trade-network"></div>
      </div>
      <div class="visual-card">
        <div class="visual-title"><h3>Nine-category rank before and after each trade</h3><span>Select a trade date</span></div>
        <div id="trade-impact-timeline"></div>
        <div id="trade-impact-detail"></div>
      </div>
      <div class="table-wrap trade-table">
        <table>
          <thead><tr><th>Date</th><th>Players received</th><th>Higher received-minus-sent value</th><th>Lower received-minus-sent value</th><th>Difference</th></tr></thead>
          <tbody id="trade-results"></tbody>
        </table>
      </div>
    </section>
  </div>
</main>

<div class="award-modal" id="award-modal" role="dialog" aria-modal="true" aria-label="Award share preview">
  <div class="award-modal-inner">
    <button class="award-close" id="award-close" aria-label="Close award preview">×</button>
    <div id="award-modal-card"></div>
  </div>
</div>

<script>
const data = __DATA__;
const num = value => Number(value || 0);
const pct = value => `${(num(value) * 100).toFixed(1)}%`;
const shortDate = value => new Date(`${value}T12:00:00`).toLocaleDateString("en-US", {month:"short", day:"numeric", year:"numeric"});
const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[char]));
const byTeam = new Map(data.teams.map(team => [team.team_key, team]));
const constructionByTeam = new Map(data.construction.map(team => [team.team_key, team]));
const standingsByTeam = new Map(data.standings.map(team => [team.team_key, team]));
const activityByTeam = new Map(data.managerActivity.map(team => [team.team_key, team]));
const teamPalette = ["#315c46","#8e443d","#526f8d","#b27b34","#745b83","#3f7f7a","#9b5f72","#6e7843","#496b99","#a76b45","#657078","#8b6d4f"];
const teamColorByKey = new Map(
  [...data.standings]
    .sort((a,b) => num(a.rank)-num(b.rank))
    .map((team,index) => [team.team_key, teamPalette[index % teamPalette.length]])
);
const playersByTeam = new Map();
for (const player of data.players) {
  if (!playersByTeam.has(player.team_key)) playersByTeam.set(player.team_key, []);
  playersByTeam.get(player.team_key).push(player);
}
const pickupsByTeam = new Map();
for (const pickup of data.pickups) {
  if (!pickupsByTeam.has(pickup.team_key)) pickupsByTeam.set(pickup.team_key, []);
  pickupsByTeam.get(pickup.team_key).push(pickup);
}
const rosterByTeamWeek = new Map();
for (const player of data.weeklyRosters) {
  const key = `${player.team_key}:${player.week}`;
  if (!rosterByTeamWeek.has(key)) rosterByTeamWeek.set(key, []);
  rosterByTeamWeek.get(key).push(player);
}
const eventsByTeamWeek = new Map();
for (const event of data.weeklyEvents) {
  const key = `${event.team_key}:${event.week}`;
  if (!eventsByTeamWeek.has(key)) eventsByTeamWeek.set(key, []);
  eventsByTeamWeek.get(key).push(event);
}
const powerByTeamWeek = new Map(data.teamWeekPower.map(row => [`${row.team_key}:${row.week}`, row]));
const powerRankByTeamWeek = new Map();
for (let week=1; week<=23; week++) {
  data.teamWeekPower
    .filter(row => num(row.week) === week)
    .sort((a,b) => num(b.overall_strength)-num(a.overall_strength))
    .forEach((row,index) => powerRankByTeamWeek.set(`${row.team_key}:${week}`, index + 1));
}

document.querySelector("#method").innerHTML =
  `Replacement level is <strong>BBM rank ${esc(data.replacement.replacement_rank)}</strong> ` +
  `(${esc(data.replacement.replacement_player)}, value ${num(data.replacement.replacement_value).toFixed(3)}), ` +
  `the first player beyond the league’s 156 draft slots. Draft value is the sum of each pick’s positive BBM value above that threshold. ` +
  `Rank losses are capped there, so every finish below replacement is treated as rank ${esc(data.replacement.replacement_rank)}.`;

const podium = [...data.standings].sort((a,b) => num(a.rank)-num(b.rank)).slice(0,3);
document.querySelector("#summary").innerHTML = podium.map((team, index) => {
  const labels = ["Champion", "Runner-up", "Third place"];
  const classes = ["champion", "runner", "third"];
  return `<article class="summary-card ${classes[index]}"><div class="label">${labels[index]}</div><div class="value">${esc(team.team_name)}</div><div class="detail">${esc(team.wins)}-${esc(team.losses)}-${esc(team.ties)} regular season · seed ${esc(team.playoff_seed)}</div></article>`;
}).join("");

const champion = [...data.standings].sort((a,b) => num(a.rank)-num(b.rank))[0];
const bestDraftTeam = [...data.teams].sort((a,b) => num(a.draft_rank)-num(b.draft_rank))[0];
const bestPickupAward = [...data.pickups].sort((a,b) => num(b.pickup_score)-num(a.pickup_score))[0];
const bestStealAward = [...data.players]
  .filter(player => player.bbm_rank)
  .sort((a,b) => num(b.draft_position_gain)-num(a.draft_position_gain))[0];
const mostActive = [...data.managerActivity].sort((a,b) => num(b.number_of_moves)-num(a.number_of_moves))[0];
const weeklyStealsRecord = [...data.weeklyTeamStats].sort((a,b) => num(b.steals)-num(a.steals))[0];
const weeklyStealsManager = standingsByTeam.get(weeklyStealsRecord.team_key)?.manager_name || "";

const awards = [
  {
    key: "champion",
    title: "League Champion",
    winner: champion.team_name,
    manager: champion.manager_name,
    stat: "#1",
    detail: `${champion.wins}-${champion.losses}-${champion.ties} regular season · playoff seed ${champion.playoff_seed}`
  },
  {
    key: "draft",
    title: "Draft Room Winner",
    winner: bestDraftTeam.team_name,
    manager: standingsByTeam.get(bestDraftTeam.team_key)?.manager_name || "",
    stat: num(bestDraftTeam.draft_score).toFixed(3),
    detail: `total BBM value above rank 157 · ${bestDraftTeam.players_above_replacement} of 13 picks above replacement`
  },
  {
    key: "pickup",
    title: "Waiver Find of the Year",
    winner: bestPickupAward.player_name,
    manager: bestPickupAward.team_name,
    stat: `#${bestPickupAward.bbm_rank || "—"}`,
    detail: `final BBM rank · added ${shortDate(bestPickupAward.pickup_date)} · held ${bestPickupAward.held_days} days`
  },
  {
    key: "steal",
    art: "../design/share-card-art/draft-night-heist.webp",
    title: "Draft Night Heist",
    winner: bestStealAward.player_name,
    manager: bestStealAward.team_name,
    stat: `+${bestStealAward.draft_position_gain}`,
    detail: `drafted ${bestStealAward.pick}th · finished BBM rank ${bestStealAward.bbm_rank}`
  },
  {
    key: "category",
    art: "../design/share-card-art/weekly-steals-record.webp",
    title: "Weekly Steals Record",
    winner: weeklyStealsRecord.team_name,
    manager: weeklyStealsManager,
    stat: `${weeklyStealsRecord.steals} STL`,
    detail: `Week ${weeklyStealsRecord.week} · most steals by any team in a single matchup week`
  },
  {
    key: "activity",
    title: "Transaction Machine",
    winner: mostActive.team_name,
    manager: mostActive.manager_name,
    stat: `${mostActive.number_of_moves}`,
    detail: `Yahoo moves · ${mostActive.action_count} player actions · ${mostActive.number_of_trades} completed trades`
  }
];

const moments = [
  {
    key: "photo-finish",
    art: "../design/share-card-art/weekly-steals-record.webp",
    title: "Playoff Win by One Steal",
    winner: "Nick P's Team",
    manager: "Nicholas",
    stat: "45–44",
    detail: "Week 22 · beat Ronit’s Reasonable Team 5–4 by taking steals by one",
    footer: "Playoff moment"
  },
  {
    key: "photo-finish",
    art: "../design/share-card-art/weekly-steals-record.webp",
    title: "One-Steal Escape",
    winner: "go nembHard or go home",
    manager: "Daniel",
    stat: "36–35",
    detail: "Week 5 · beat Cade and em 5–4 with a one-steal category margin",
    footer: "Matchup moment"
  },
  {
    key: "photo-finish",
    title: "One-Thousandth",
    winner: "go nembHard or go home",
    manager: "Daniel",
    stat: ".460–.459",
    detail: "Week 17 · beat Shanghai Sharks 5–4 with a .001 FG% edge",
    footer: "Matchup moment"
  },
  {
    key: "last-day",
    art: "../design/share-card-art/last-day-gamble.webp",
    title: "Last-Day Gamble",
    winner: "Jet's Fascinating Team",
    manager: "Jet",
    stat: "5–4",
    detail: "Week 20 · added Killian Hayes on Sunday, then beat Stuart by two assists and two fewer turnovers",
    footer: "Transaction timing verified"
  }
];

function awardCard(award, index, preview=false, collection=awards) {
  return `<button class="award-card ${award.art ? "has-art" : ""}" data-award="${esc(award.key)}" data-award-index="${index}" ${preview ? 'tabindex="-1"' : ""} aria-label="${esc(award.title)}: ${esc(award.winner)}">
    <span class="award-visual">
      ${award.art ? `<span class="award-art" style="background-image:url('${esc(award.art)}')"></span>` : ""}
      <span class="award-topline"><span>SAS · 2025–26</span><span class="award-number">${String(index + 1).padStart(2,"0")} / ${String(collection.length).padStart(2,"0")}</span></span>
    </span>
    <span class="award-content">
      <span class="award-copy">
        <span class="award-title">${esc(award.title)}</span>
        <span class="award-winner">${esc(award.winner)}</span>
        <span class="award-manager">${esc(award.manager)}</span>
      </span>
      <span class="award-stat"><strong>${esc(award.stat)}</strong><span>${esc(award.detail)}</span></span>
      <span class="award-footer"><span>${esc(award.footer || "Season award")}</span><span>Fantasy basketball</span></span>
    </span>
  </button>`;
}

const shareCards = [...awards, ...moments];
document.querySelector("#share-cards-grid").innerHTML = shareCards.map((card,index) => awardCard(card,index,false,shareCards)).join("");
const awardModal = document.querySelector("#award-modal");
const closeAwardModal = () => {
  awardModal.classList.remove("open");
  document.body.style.overflow = "";
};
for (const card of document.querySelectorAll("#share-cards-grid .award-card")) {
  card.addEventListener("click", () => {
    const index = num(card.dataset.awardIndex);
    document.querySelector("#award-modal-card").innerHTML = awardCard(shareCards[index], index, true, shareCards);
    awardModal.classList.add("open");
    document.body.style.overflow = "hidden";
  });
}
document.querySelector("#award-close").addEventListener("click", closeAwardModal);
awardModal.addEventListener("click", event => {
  if (event.target === awardModal) closeAwardModal();
});
document.addEventListener("keydown", event => {
  if (event.key === "Escape" && awardModal.classList.contains("open")) closeAwardModal();
});

function barChart(target, rows, valueKey, formatter, className="") {
  const max = Math.max(...rows.map(row => num(row[valueKey])), .0001);
  document.querySelector(target).innerHTML = rows.map(row => `
    <div class="chart-row">
      <div class="chart-label">${esc(row.team_name)}</div>
      <div class="track"><div class="bar ${className}" style="width:${Math.max(num(row[valueKey]) / max * 100, 1)}%"></div></div>
      <div class="number">${formatter(row[valueKey])}</div>
    </div>`).join("");
}

barChart("#draft-chart", data.teams, "draft_score", value => num(value).toFixed(3), "good");
const reliance = [...data.construction].sort((a,b) => num(b.drafted_value_share)-num(a.drafted_value_share));
barChart("#reliance-chart", reliance, "drafted_value_share", pct);
const turnover = [...data.construction].sort((a,b) => num(b.roster_turnover)-num(a.roster_turnover));
barChart("#turnover-chart", turnover, "roster_turnover", pct, "turnover");

function categoryRankHeatmap(target, startWeek, endWeek) {
  const root = document.querySelector(target);
  const weeks = Array.from({length:endWeek-startWeek+1}, (_,index) => startWeek + index);
  const teams = [...data.standings].sort((a,b) => {
    const averageRank = team => {
      const ranks = weeks
        .map(week => powerRankByTeamWeek.get(`${team.team_key}:${week}`))
        .filter(Boolean);
      return ranks.length ? ranks.reduce((sum,rank) => sum+rank,0)/ranks.length : 99;
    };
    return averageRank(a)-averageRank(b);
  });
  const columns = `180px repeat(${weeks.length}, minmax(50px, 1fr))`;
  const headers = `<div class="heat-cell header">Team</div>` +
    weeks.map(week => `<div class="heat-cell header">W${week}</div>`).join("");
  const rows = teams.map(team => {
    const manager = team.manager_name || team.team_name;
    const cells = weeks.map(week => {
      const rank = powerRankByTeamWeek.get(`${team.team_key}:${week}`);
      const result = powerByTeamWeek.get(`${team.team_key}:${week}`);
      if (!rank || !result) {
        return `<div class="heat-cell missing" title="${esc(team.team_name)} · Week ${week}: Yahoo has no matchup result">No result</div>`;
      }
      const positionAverage = num(result.overall_strength);
      const hue = 145 - (rank-1)/11*143;
      const lightness = 91 - Math.abs(6.5-rank)/5.5*16;
      return `<div class="heat-cell rank" style="background:hsl(${hue} 38% ${lightness}%)" title="${esc(team.team_name)} · Week ${week}: rank #${rank}; nine-category average ${positionAverage.toFixed(1)} / 100">#${rank}<small>${positionAverage.toFixed(1)}</small></div>`;
    }).join("");
    return `<div class="heat-cell team">${esc(manager)}<small>${esc(team.team_name)}</small></div>${cells}`;
  }).join("");
  root.innerHTML = `<div class="rank-heatmap-scroll"><div class="rank-heatmap ${endWeek-startWeek <= 3 ? "playoffs" : ""}" style="grid-template-columns:${columns}">${headers}${rows}</div></div><div class="heatmap-legend"><span>Higher weekly rank</span><span class="rank-gradient"></span><span>Lower weekly rank</span><span>Cell: rank · nine-category average</span></div>`;
}

function scatterChart(target, rows, options) {
  const width = 520, height = 390;
  const margin = {top:22, right:24, bottom:48, left:52};
  const xs = rows.map(options.x);
  const ys = rows.map(options.y);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...ys), yMax = Math.max(...ys);
  const pad = (min,max) => Math.max((max-min)*.1, .01);
  const xPad = pad(xMin,xMax), yPad = pad(yMin,yMax);
  const x = value => margin.left + (value-(xMin-xPad))/((xMax+xPad)-(xMin-xPad))*(width-margin.left-margin.right);
  const y = value => options.yReverse
    ? margin.top + (value-(yMin-yPad))/((yMax+yPad)-(yMin-yPad))*(height-margin.top-margin.bottom)
    : height-margin.bottom - (value-(yMin-yPad))/((yMax+yPad)-(yMin-yPad))*(height-margin.top-margin.bottom);
  const grid = [0,.25,.5,.75,1].map(step => {
    const gx = margin.left + step*(width-margin.left-margin.right);
    const gy = margin.top + step*(height-margin.top-margin.bottom);
    return `<line class="axis-line" x1="${gx}" y1="${margin.top}" x2="${gx}" y2="${height-margin.bottom}" opacity=".5"/><line class="axis-line" x1="${margin.left}" y1="${gy}" x2="${width-margin.right}" y2="${gy}" opacity=".5"/>`;
  }).join("");
  const dots = rows.map(row => {
    const cx=x(options.x(row)), cy=y(options.y(row));
    const color=options.color ? options.color(row) : teamColorByKey.get(row.team_key);
    const radius=options.radius ? options.radius(row) : 7;
    return `<g><circle class="scatter-dot" cx="${cx}" cy="${cy}" r="${radius}" fill="${color}"><title>${esc(options.tooltip(row))}</title></circle><text class="scatter-label" x="${cx+radius+3}" y="${cy+3}">${esc(options.label(row))}</text></g>`;
  }).join("");
  const axes = `<line class="axis-line" x1="${margin.left}" y1="${height-margin.bottom}" x2="${width-margin.right}" y2="${height-margin.bottom}"/><line class="axis-line" x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${height-margin.bottom}"/><text class="axis-label" x="${(margin.left+width-margin.right)/2}" y="${height-9}" text-anchor="middle">${esc(options.xLabel)}</text><text class="axis-label" transform="translate(14 ${(margin.top+height-margin.bottom)/2}) rotate(-90)" text-anchor="middle">${esc(options.yLabel)}</text>`;
  document.querySelector(target).innerHTML = `<svg class="chart-svg" viewBox="0 0 ${width} ${height}">${grid}${axes}${dots}</svg>`;
}

categoryRankHeatmap("#regular-season-race", 1, 20);
categoryRankHeatmap("#playoff-race", 21, 23);

const draftFinishRows = data.teams.map(team => ({
  ...team,
  final_rank: num(standingsByTeam.get(team.team_key)?.rank)
}));
scatterChart("#draft-finish-scatter", draftFinishRows, {
  x: row => num(row.draft_score),
  y: row => row.final_rank,
  yReverse: true,
  xLabel: "Sum of draft-pick BBM value over rank 157",
  yLabel: "Final finish (1 is best)",
  label: row => standingsByTeam.get(row.team_key)?.manager_name || row.team_name,
  tooltip: row => `${row.team_name}: draft value over rank 157 = ${num(row.draft_score).toFixed(3)}, finished #${row.final_rank}`
});

scatterChart("#transaction-scatter", data.managerActivity, {
  x: row => num(row.number_of_moves),
  y: row => num(row.positive_pickup_value),
  xLabel: "Yahoo moves",
  yLabel: "Σ(value over rank 157 × share of season held)",
  label: row => `${row.manager_name} · ${row.action_count}a`,
  tooltip: row => `${row.team_name}: ${row.number_of_moves} Yahoo moves, ${row.action_count} player add/drop/trade actions, held-period pickup value ${num(row.positive_pickup_value).toFixed(3)}`,
  radius: row => 6 + Math.min(num(row.number_of_trades), 12) * .35
});

const managerIdentityRows = data.managerActivity.map(activity => ({
  ...activity,
  drafted_value_share: num(constructionByTeam.get(activity.team_key)?.drafted_value_share)
}));
const maxStreamerCount = Math.max(...managerIdentityRows.map(row => num(row.streamer_count)), 1);
scatterChart("#manager-identity-map", managerIdentityRows, {
  x: row => row.drafted_value_share,
  y: row => num(row.number_of_moves),
  xLabel: "Draft reliance",
  yLabel: "Yahoo moves",
  label: row => row.manager_name,
  tooltip: row => `${row.team_name}: ${pct(row.drafted_value_share)} draft reliance, ${row.number_of_moves} moves, ${row.action_count} actions, ${row.number_of_trades} trades, ${row.streamer_count} streamer stints`,
  radius: row => 7 + Math.sqrt(num(row.number_of_trades)) * 2,
  color: row => {
    const heat = num(row.streamer_count) / maxStreamerCount;
    return `hsl(${42 - heat * 35} 48% ${48 + heat * 8}%)`;
  }
});

document.querySelector("#final-standings").innerHTML = [...data.standings]
  .sort((a,b) => num(a.rank)-num(b.rank))
  .map(team => `<tr>
    <td class="rank">${esc(team.rank)}</td>
    <td><strong>${esc(team.team_name)}</strong></td>
    <td>${esc(team.manager_name)}</td>
    <td>${esc(team.wins)}-${esc(team.losses)}-${esc(team.ties)}</td>
    <td>${esc(team.playoff_seed)}</td>
  </tr>`).join("");

document.querySelector("#leaderboard").innerHTML = data.teams.map(team => `
  <tr>
    <td class="rank">${esc(team.draft_rank)}</td>
    <td><strong>${esc(team.team_name)}</strong></td>
    <td>${num(team.draft_score).toFixed(3)}</td>
    <td>${esc(team.players_above_replacement)} / 13</td>
    <td>${esc(team.best_pick)}</td>
    <td>${esc(team.best_steal)} · pick ${esc(team.best_steal_pick)} → rank ${esc(team.best_steal_final_rank)}</td>
  </tr>`).join("");

const draftTeamOrder = [...data.players]
  .filter(player => num(player.round) === 1)
  .sort((a,b) => num(a.pick)-num(b.pick))
  .map(player => player.team_key);
const draftByTeamRound = new Map(data.players.map(player => [`${player.team_key}:${player.round}`, player]));
const draftHeaders = `<div class="draft-cell header">Rd</div>` + draftTeamOrder.map(teamKey => {
  const team = byTeam.get(teamKey);
  const manager = standingsByTeam.get(teamKey)?.manager_name || "";
  return `<div class="draft-cell header" title="${esc(team?.team_name || "")}">${esc(manager)}</div>`;
}).join("");
const draftRounds = Array.from({length:13}, (_,index) => index+1).map(round => {
  const cells = draftTeamOrder.map(teamKey => {
    const player = draftByTeamRound.get(`${teamKey}:${round}`);
    if (!player) return `<div class="draft-cell"></div>`;
    const result = player.bbm_rank
      ? `Final #${esc(player.bbm_rank)} · ${num(player.draft_position_gain)>=0?"+":""}${esc(player.draft_position_gain)}`
      : "No final rank";
    return `<div class="draft-cell" style="${outcomeStyle(player)}" title="${esc(player.team_name)} · pick ${esc(player.pick)} · ${esc(result)}">
      <span class="pick-number">Pick ${esc(player.pick)}</span>
      <span class="player-name">${esc(player.player_name)}</span>
      <span class="pick-result">${result}</span>
    </div>`;
  }).join("");
  return `<div class="draft-cell round">${round}</div>${cells}`;
}).join("");
document.querySelector("#draft-board").innerHTML = draftHeaders + draftRounds;

const rankedPlayers = data.players.filter(player => player.bbm_rank);
const topPicks = [...rankedPlayers]
  .sort((a,b) => num(b.value_above_replacement)-num(a.value_above_replacement))
  .slice(0, 12);
document.querySelector("#top-picks").innerHTML = topPicks.map(player => `
  <tr>
    <td><strong>${esc(player.player_name)}</strong></td>
    <td>${esc(player.team_name)}</td>
    <td>${esc(player.pick)}</td>
    <td>${esc(player.bbm_rank)}</td>
    <td class="good-text">+${num(player.value_above_replacement).toFixed(3)}</td>
    <td>${num(player.draft_position_gain) >= 0 ? "+" : ""}${esc(player.draft_position_gain)}</td>
  </tr>`).join("");

const worstPicks = [...rankedPlayers]
  .sort((a,b) => num(a.draft_position_gain)-num(b.draft_position_gain))
  .slice(0, 12);
document.querySelector("#worst-picks").innerHTML = worstPicks.map(player => `
  <tr>
    <td><strong>${esc(player.player_name)}</strong></td>
    <td>${esc(player.team_name)}</td>
    <td>${esc(player.pick)}</td>
    <td>${esc(player.bbm_rank)}</td>
    <td class="bad-text">${esc(player.draft_position_gain)}</td>
    <td>${num(player.games) ? `${esc(player.games)} games` : "No qualifying BBM season row"}</td>
  </tr>`).join("");

const draftOrder = [...data.players].sort((a,b) => num(a.pick)-num(b.pick));
const opportunityRows = worstPicks.slice(0,8).map(player => {
  const alternatives = draftOrder.filter(candidate =>
    num(candidate.pick) > num(player.pick) &&
    num(candidate.pick) <= num(player.pick) + 12 &&
    candidate.bbm_rank
  );
  const alternative = alternatives.sort((a,b) =>
    num(b.value_above_replacement)-num(a.value_above_replacement)
  )[0];
  return {player, alternative};
}).filter(row => row.alternative);
document.querySelector("#opportunity-cost").innerHTML = opportunityRows.map(({player,alternative}) => `
  <div class="opportunity-card">
    <div class="picked"><strong>${esc(player.player_name)}</strong><small>Pick ${esc(player.pick)} · final #${esc(player.bbm_rank)}</small></div>
    <div class="arrow">→</div>
    <div class="available"><strong>${esc(alternative.player_name)}</strong><small>Still there at ${esc(alternative.pick)} · final #${esc(alternative.bbm_rank)}</small></div>
  </div>`).join("");

const bestPickups = data.pickups
  .filter(pickup => num(pickup.pickup_score) > 0)
  .sort((a,b) => num(b.pickup_score)-num(a.pickup_score))
  .slice(0,15);
const pickupChartRows = bestPickups.slice(0,10).map(pickup => ({
  team_name: `${pickup.player_name} · ${pickup.team_name}`,
  pickup_score: pickup.pickup_score
}));
barChart("#pickup-chart", pickupChartRows, "pickup_score", value => num(value).toFixed(3), "good");
const pickupContext = pickup => {
  if (pickup.originally_drafted !== "1") return "Undrafted";
  if (pickup.original_draft_team === pickup.team_name) return "Re-acquired by original drafter";
  return `Originally drafted by ${pickup.original_draft_team}`;
};
document.querySelector("#best-pickups").innerHTML = bestPickups.map(pickup => `
  <tr>
    <td><strong>${esc(pickup.player_name)}</strong></td>
    <td>${esc(pickup.team_name)}</td>
    <td>${esc(shortDate(pickup.pickup_date))}</td>
    <td>${esc(pickup.held_days)} days</td>
    <td>${esc(shortDate(pickup.end_date))}<br><small>${esc(pickup.end_reason)}</small></td>
    <td>${esc(pickup.bbm_rank || "N/A")}</td>
    <td class="good-text">${num(pickup.pickup_score).toFixed(3)}</td>
    <td>${esc(pickupContext(pickup))}</td>
  </tr>`).join("");

const bestStreamers = [...data.streamers]
  .filter(streamer => num(streamer.streamer_score) > 0)
  .sort((a,b) => num(b.streamer_score)-num(a.streamer_score))
  .slice(0,15);
const streamerChartRows = bestStreamers.slice(0,10).map(streamer => ({
  team_name: `${streamer.player_name} · ${streamer.team_name}`,
  streamer_score: streamer.streamer_score
}));
barChart("#streamer-chart", streamerChartRows, "streamer_score", value => num(value).toFixed(3), "streamer");
document.querySelector("#best-streamers").innerHTML = bestStreamers.map(streamer => `
  <tr>
    <td><strong>${esc(streamer.player_name)}</strong></td>
    <td>${esc(streamer.team_name)}</td>
    <td>${esc(shortDate(streamer.pickup_date))}</td>
    <td>${esc(streamer.held_days)} days</td>
    <td>${esc(streamer.bbm_rank || "N/A")}</td>
    <td class="streamer-text">${num(streamer.streamer_score).toFixed(3)}</td>
  </tr>`).join("");

const tradeGroups = new Map();
for (const side of data.trades) {
  if (!tradeGroups.has(side.transaction_key)) tradeGroups.set(side.transaction_key, []);
  tradeGroups.get(side.transaction_key).push(side);
}
const tradeResults = [...tradeGroups.values()].map(sides => {
  const ordered = [...sides].sort((a,b) => num(b.preliminary_value_delta)-num(a.preliminary_value_delta));
  const better = ordered[0];
  const worse = ordered[ordered.length - 1];
  return {
    trade_date: better.trade_date,
    week: better.week,
    better,
    worse,
    value_gap: num(better.preliminary_value_delta) - num(worse.preliminary_value_delta)
  };
}).sort((a,b) => b.value_gap-a.value_gap);

document.querySelector("#trade-results").innerHTML = tradeResults.map(trade => `
  <tr>
    <td>${esc(shortDate(trade.trade_date))}<br><small>Week ${esc(trade.week)}</small></td>
    <td><strong>${esc(trade.better.team_name)}</strong> received ${esc(trade.better.players_received || "—")}<br><span class="muted"><strong>${esc(trade.worse.team_name)}</strong> received ${esc(trade.worse.players_received || "—")}</span></td>
    <td><strong>${esc(trade.better.team_name)}</strong><br><span class="positive">${num(trade.better.preliminary_value_delta) >= 0 ? "+" : ""}${num(trade.better.preliminary_value_delta).toFixed(3)}</span></td>
    <td><strong>${esc(trade.worse.team_name)}</strong><br><span class="negative">${num(trade.worse.preliminary_value_delta) >= 0 ? "+" : ""}${num(trade.worse.preliminary_value_delta).toFixed(3)}</span></td>
    <td>${trade.value_gap.toFixed(3)}</td>
  </tr>`).join("");

function renderTradeNetwork() {
  const width = 540, height = 480, cx = 270, cy = 235, orbit = 170;
  const teams = [...data.standings].sort((a,b) => num(a.rank)-num(b.rank));
  const positions = new Map(teams.map((team,index) => {
    const angle = -Math.PI/2 + index * Math.PI*2/teams.length;
    return [team.team_key, {x:cx+Math.cos(angle)*orbit, y:cy+Math.sin(angle)*orbit}];
  }));
  const pairs = new Map();
  for (const sides of tradeGroups.values()) {
    const keys = [...new Set(sides.map(side => side.team_key))].sort();
    if (keys.length < 2) continue;
    const key = keys.join("|");
    if (!pairs.has(key)) pairs.set(key, {keys, count:0, players:[]});
    const pair = pairs.get(key);
    pair.count += 1;
    pair.players.push(...sides.flatMap(side => (side.players_received || "").split(", ").filter(Boolean)));
  }
  const totals = new Map(teams.map(team => [team.team_key, 0]));
  for (const pair of pairs.values()) for (const key of pair.keys) totals.set(key, totals.get(key)+pair.count);
  const edges = [...pairs.values()].map(pair => {
    const a=positions.get(pair.keys[0]), b=positions.get(pair.keys[1]);
    const names=pair.keys.map(key => standingsByTeam.get(key)?.manager_name).join(" ↔ ");
    return `<line class="network-edge" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke-width="${1+pair.count*1.5}"><title>${esc(names)}: ${pair.count} trade${pair.count===1?"":"s"} · ${esc([...new Set(pair.players)].slice(0,8).join(", "))}</title></line>`;
  }).join("");
  const nodes = teams.map(team => {
    const point=positions.get(team.team_key);
    const radius=16+Math.sqrt(totals.get(team.team_key))*2.4;
    const initials=team.manager_name.split(/\\s+/).map(part=>part[0]).join("").slice(0,2);
    return `<g><circle class="network-node" cx="${point.x}" cy="${point.y}" r="${radius}" fill="${teamColorByKey.get(team.team_key)}"><title>${esc(team.manager_name)} · ${totals.get(team.team_key)} trades in network</title></circle><text class="network-node-label" x="${point.x}" y="${point.y+4}" text-anchor="middle">${esc(initials)}</text><text class="axis-label" x="${point.x}" y="${point.y+radius+14}" text-anchor="middle">${esc(team.manager_name)}</text></g>`;
  }).join("");
  document.querySelector("#trade-network").innerHTML = `<svg class="chart-svg" viewBox="0 0 ${width} ${height}">${edges}${nodes}</svg>`;
}

function nearbyPower(teamKey, week, direction) {
  const start = Math.max(1, Math.min(23, week));
  for (let candidate=start; candidate>=1 && candidate<=23; candidate+=direction) {
    const row=powerByTeamWeek.get(`${teamKey}:${candidate}`);
    if (row) return {row, week:candidate, rank:powerRankByTeamWeek.get(`${teamKey}:${candidate}`)};
  }
  return null;
}

const tradeTimelineRows = [...tradeGroups.values()].map(sides => ({
  sides,
  transaction_key: sides[0].transaction_key,
  trade_date: sides[0].trade_date,
  week: num(sides[0].week)
})).sort((a,b) => a.trade_date.localeCompare(b.trade_date));

function renderTradeImpact(index) {
  const trade=tradeTimelineRows[index];
  if (!trade) return;
  for (const dot of document.querySelectorAll(".trade-dot")) dot.classList.toggle("active", num(dot.dataset.index)===index);
  const rows=trade.sides.map(side => {
    const before=nearbyPower(side.team_key, trade.week-1, -1) || nearbyPower(side.team_key, trade.week, 1);
    const after=nearbyPower(side.team_key, trade.week+1, 1) || nearbyPower(side.team_key, trade.week, -1);
    const beforeRank=num(before?.rank || 12), afterRank=num(after?.rank || 12);
    const beforeValue=(13-beforeRank)/12*100, afterValue=(13-afterRank)/12*100;
    const delta=beforeRank-afterRank;
    return `<div class="impact-team">
      <div><strong>${esc(side.team_name)}</strong><br><small>Received ${esc(side.players_received || "—")}</small></div>
      <div class="impact-line" style="--before:${Math.max(0,Math.min(100,beforeValue))}%;--after:${Math.max(0,Math.min(100,afterValue))}%"></div>
      <div class="${delta>=0?"positive":"negative"}">#${beforeRank} → #${afterRank}</div>
    </div>`;
  }).join("");
  document.querySelector("#trade-impact-detail").innerHTML = `<div class="trade-impact-card"><div class="impact-header"><strong>${esc(shortDate(trade.trade_date))} · Week ${trade.week}</strong><span class="muted">nine-category rank in prior week → next recorded week</span></div>${rows}</div>`;
}

function renderTradeTimeline() {
  const dots=tradeTimelineRows.map((trade,index) => {
    const left=((trade.week-1)/22*100).toFixed(2);
    const top=22+(index%3)*11;
    return `<button class="trade-dot" data-index="${index}" style="left:${left}%;top:${top}px" aria-label="${esc(shortDate(trade.trade_date))}, Week ${trade.week}"></button>`;
  }).join("");
  document.querySelector("#trade-impact-timeline").innerHTML = `<div class="trade-timeline" style="height:78px"><div class="trade-timeline-line"></div>${dots}<div class="trade-week-labels"><span>Week 1</span><span>Week 12</span><span>Week 23</span></div></div>`;
  for (const dot of document.querySelectorAll(".trade-dot")) {
    dot.addEventListener("click", () => renderTradeImpact(num(dot.dataset.index)));
  }
  renderTradeImpact(0);
}

renderTradeNetwork();
renderTradeTimeline();

const radarCategories = [
  ["FG%", "fg_pct_strength"], ["FT%", "ft_pct_strength"],
  ["3PM", "three_pt_made_strength"], ["PTS", "points_strength"],
  ["REB", "rebounds_strength"], ["AST", "assists_strength"],
  ["STL", "steals_strength"], ["BLK", "blocks_strength"],
  ["TO", "turnovers_strength"]
];

function radarSvg(power) {
  const size = 300, center = 150, radius = 104;
  const point = (index, value=1) => {
    const angle = -Math.PI / 2 + index * Math.PI * 2 / radarCategories.length;
    return [center + Math.cos(angle) * radius * value, center + Math.sin(angle) * radius * value];
  };
  const polygon = scale => radarCategories.map((_, index) => point(index, scale).join(",")).join(" ");
  const values = radarCategories.map(([, key]) => num(power?.[key]) / 100);
  const shape = values.map((value, index) => point(index, value).join(",")).join(" ");
  const grids = [.25,.5,.75,1].map(scale => `<polygon class="radar-grid" points="${polygon(scale)}"/>`).join("");
  const axes = radarCategories.map((_, index) => {
    const [x,y] = point(index,1);
    return `<line class="radar-axis" x1="${center}" y1="${center}" x2="${x}" y2="${y}"/>`;
  }).join("");
  const labels = radarCategories.map(([label], index) => {
    const [x,y] = point(index,1.18);
    const anchor = x < center - 8 ? "end" : x > center + 8 ? "start" : "middle";
    return `<text class="radar-label" x="${x}" y="${y}" text-anchor="${anchor}" dominant-baseline="middle">${label}</text>`;
  }).join("");
  return `<svg viewBox="0 0 ${size} ${size}" role="img" aria-label="Team position from 0 to 100 in each scoring category">${grids}${axes}<polygon class="radar-shape" points="${shape}"/>${labels}</svg>`;
}

function outcomeStyle(player) {
  if (!player.bbm_rank) return "background:#ece9e2";
  const delta = num(player.draft_position_gain);
  const maxMagnitude = delta >= 0 ? 100 : 150;
  const intensity = Math.min(Math.abs(delta) / maxMagnitude, 1);
  const lightness = 96 - intensity * 27;
  return delta >= 0
    ? `background:hsl(145 36% ${lightness}%)`
    : `background:hsl(2 48% ${lightness}%)`;
}

function timelineMarkup(teamKey, maxWeek) {
  return `<div class="timeline" data-team="${esc(teamKey)}">
    <div class="timeline-head"><h4>Weekly roster and nine-category comparison</h4><span class="week-label">Week ${maxWeek}</span></div>
    <div class="timeline-legend"><span class="legend-key">Original draft pick</span><span class="legend-key streamer">Streamer</span><span class="legend-key injured">Yahoo IL / IL+ slot that week</span></div>
    <input class="week-slider" type="range" min="1" max="${maxWeek}" value="${maxWeek}" step="1" aria-label="Select fantasy week">
    <div class="roster-change-strip"></div>
    <div class="timeline-grid">
      <div class="timeline-panel radar-panel"><h5>Position in each category (0–100)</h5><div class="radar-wrap"></div><div class="power-score"></div></div>
      <div class="timeline-panel"><h5>Full roster</h5><div class="roster-list"></div></div>
      <div class="timeline-panel"><h5>Moves, trades & key injuries</h5><div class="event-list"></div></div>
    </div>
  </div>`;
}

function renderTimeline(container, teamKey, week) {
  week = num(week);
  const key = `${teamKey}:${week}`;
  const roster = [...(rosterByTeamWeek.get(key) || [])].sort((a,b) => {
    const rankA = a.bbm_rank ? num(a.bbm_rank) : 9999;
    const rankB = b.bbm_rank ? num(b.bbm_rank) : 9999;
    if (rankA !== rankB) return rankA-rankB;
    return a.player_name.localeCompare(b.player_name);
  });
  const events = [...(eventsByTeamWeek.get(key) || [])].sort((a,b) => a.event_date.localeCompare(b.event_date));
  const power = powerByTeamWeek.get(key);
  const previousRoster = rosterByTeamWeek.get(`${teamKey}:${week-1}`) || [];
  const previousKeys = new Set(previousRoster.map(player => player.player_key));
  const currentKeys = new Set(roster.map(player => player.player_key));
  const added = roster.filter(player => !previousKeys.has(player.player_key));
  const removed = previousRoster.filter(player => !currentKeys.has(player.player_key));
  container.querySelector(".week-label").textContent = `Week ${week}`;
  container.querySelector(".radar-wrap").innerHTML = power ? radarSvg(power) : `<div class="empty-state">No category result for this week.</div>`;
  container.querySelector(".power-score").textContent = power ? `Average of 9 category positions: ${num(power.overall_strength).toFixed(1)} / 100` : "";
  container.querySelector(".roster-change-strip").innerHTML = week === 1
    ? `<span class="change-chip">Opening roster</span>`
    : `${added.map(player => `<span class="change-chip in">+ ${esc(player.player_name)}</span>`).join("")}${removed.map(player => `<span class="change-chip out">− ${esc(player.player_name)}</span>`).join("")}` || `<span class="change-chip">No roster changes</span>`;
  const rosterList = container.querySelector(".roster-list");
  const existing = new Map([...rosterList.querySelectorAll("[data-player-key]")].map(node => [node.dataset.playerKey, node]));
  const fragment = document.createDocumentFragment();
  for (const player of roster) {
    let node = existing.get(player.player_key);
    const className = `roster-player ${player.is_original_draft_pick === "1" ? "drafted" : ""} ${player.is_streamer === "1" ? "streamer" : ""} ${player.is_injured === "1" ? "injured" : ""}`;
    if (!node) {
      node = document.createElement("div");
      node.dataset.playerKey = player.player_key;
      node.className = container.dataset.renderedWeek ? `${className} entering` : className;
    } else {
      node.className = className;
      existing.delete(player.player_key);
    }
    node.title = player.injury_note || player.injury_status_full || "";
    node.innerHTML = `<span>${esc(player.player_name)}</span><small>${player.is_original_draft_pick === "1" ? `Draft ${esc(player.original_draft_pick)}` : player.is_streamer === "1" ? "Streamer" : "Pickup/trade"}${player.bbm_rank ? ` · #${esc(player.bbm_rank)}` : ""}${player.is_injured === "1" ? ` · ${esc(player.injury_status || "INJ")}` : ""}</small>`;
    fragment.appendChild(node);
  }
  for (const node of existing.values()) {
    node.classList.add("leaving");
    fragment.appendChild(node);
    setTimeout(() => node.remove(), 310);
  }
  rosterList.replaceChildren(fragment);
  setTimeout(() => {
    for (const node of rosterList.querySelectorAll(".entering")) node.classList.remove("entering");
  }, 360);
  if (!roster.length) rosterList.innerHTML = `<div class="empty-state">No reconstructed roster.</div>`;
  container.dataset.renderedWeek = week;
  container.querySelector(".event-list").innerHTML = events.length ? events.map(event => `
    <div class="event ${event.event_type === "trade" ? "trade" : event.event_type === "injury" ? "injury" : ""}">
      <div class="event-date">${event.event_date ? `${esc(shortDate(event.event_date))} · ` : ""}${event.event_type === "trade" ? "Trade" : event.event_type === "injury" ? "Injury status" : "Roster move"}</div>
      <div>${esc(event.detail)}</div>
    </div>`).join("") : `<div class="empty-state">No roster moves recorded this week.</div>`;
}

function teamInsight(team, roster, standing) {
  const draftRank = num(team.draft_rank);
  const reliance = num(roster.drafted_value_share);
  const turnover = num(roster.roster_turnover);
  const quality = draftRank <= 4 ? "one of the league’s strongest drafts"
    : draftRank >= 9 ? "a below-average draft by final-season value"
    : "a middle-of-the-pack draft";
  const build = reliance >= .8 ? "The team leaned heavily on its drafted core"
    : reliance <= .4 ? "Most positive value came from post-draft roster work"
    : "Value was split between drafted players and later acquisitions";
  const change = turnover >= .85 ? "and aggressively rebuilt the roster."
    : turnover <= .65 ? "and kept more of its original roster than most teams."
    : "while still making substantial roster changes.";
  return `Finished #${standing.rank} after entering the playoffs as seed ${standing.playoff_seed}. This was ${quality}. ${build} ${change}`;
}

const teamsByFinish = [...data.teams].sort((a,b) =>
  num(standingsByTeam.get(a.team_key)?.rank) - num(standingsByTeam.get(b.team_key)?.rank)
);
document.querySelector("#team-cards").innerHTML = teamsByFinish.map(team => {
  const roster = constructionByTeam.get(team.team_key);
  const standing = standingsByTeam.get(team.team_key);
  const activity = activityByTeam.get(team.team_key);
  const powerRows = data.teamWeekPower.filter(row => row.team_key === team.team_key);
  const averagePower = powerRows.reduce((sum,row) => sum + num(row.overall_strength), 0) / Math.max(powerRows.length, 1);
  const peakPower = Math.max(...powerRows.map(row => num(row.overall_strength)), 0);
  const allTeamPlayers = [...(playersByTeam.get(team.team_key) || [])].sort((a,b) => num(a.pick)-num(b.pick));
  const bestPickup = (pickupsByTeam.get(team.team_key) || [])
    .filter(pickup => num(pickup.pickup_score) > 0)
    .sort((a,b) => num(b.pickup_score)-num(a.pickup_score))[0];
  const missing = team.players_without_bbm_data
    ? `<div class="missing">No BBM season row: ${esc(team.players_without_bbm_data)}</div>` : "";
  const tier = num(team.draft_rank) <= 4 ? "strong" : num(team.draft_rank) >= 9 ? "weak" : "";
  const fullDraft = `<details class="team-draft"><summary>Complete draft · 13 picks</summary><div class="table-wrap"><table>
    <thead><tr><th>Pick</th><th>Round</th><th>Player</th><th>Final rank</th><th>Adjusted rank change</th><th>Value over replacement</th><th>Games</th></tr></thead>
    <tbody>${allTeamPlayers.map(player => `<tr style="${outcomeStyle(player)}">
      <td>${esc(player.pick)}</td>
      <td>${esc(player.round)}</td>
      <td><strong>${esc(player.player_name)}</strong></td>
      <td>${esc(player.bbm_rank || "N/A")}</td>
      <td class="${num(player.draft_position_gain) >= 0 ? "good-text" : "bad-text"}">${player.bbm_rank ? `${num(player.draft_position_gain) >= 0 ? "+" : ""}${esc(player.draft_position_gain)}` : "—"}</td>
      <td>${num(player.value_above_replacement).toFixed(3)}</td>
      <td>${esc(player.games || "0")}</td>
    </tr>`).join("")}</tbody>
  </table></div></details>`;
  return `<article class="team-card ${tier}" id="team-${team.team_key.replaceAll(".", "-")}" data-team-key="${esc(team.team_key)}">
    <div class="team-hero">
      <div class="finish-badge"><span>Final</span><strong>#${esc(standing.rank)}</strong></div>
      <div>
        <h3>${esc(team.team_name)}</h3>
        <div class="meta">${esc(standing.manager_name)} · ${esc(standing.wins)}-${esc(standing.losses)}-${esc(standing.ties)} · playoff seed ${esc(standing.playoff_seed)}</div>
        <div class="hero-stats">
          <div class="hero-stat"><strong>#${esc(team.draft_rank)}</strong><span>Draft rank</span></div>
          <div class="hero-stat"><strong>${averagePower.toFixed(1)} / 100</strong><span>Average of weekly 9-category positions</span></div>
          <div class="hero-stat"><strong>${peakPower.toFixed(1)} / 100</strong><span>Best weekly 9-category average</span></div>
          <div class="hero-stat"><strong>${esc(activity?.number_of_moves || 0)}</strong><span>Moves</span></div>
          <div class="hero-stat"><strong>${esc(activity?.action_count || 0)}</strong><span>Actions</span></div>
        </div>
      </div>
    </div>
    <div class="team-body">
      <div class="spotlight-grid">
        <div class="spotlight good"><span>Best draft hit</span><strong>${esc(team.best_steal)}</strong><small>Pick ${esc(team.best_steal_pick)} → final #${esc(team.best_steal_final_rank)}</small></div>
        <div class="spotlight bad"><span>Biggest adjusted miss</span><strong>${esc(team.largest_miss)}</strong><small>Pick ${esc(team.largest_miss_pick)} → final #${esc(team.largest_miss_final_rank)} · ${esc(team.largest_miss_rank_loss)}</small></div>
        <div class="spotlight ochre"><span>Best pickup</span><strong>${esc(bestPickup?.player_name || "No positive pickup")}</strong><small>${bestPickup ? `${esc(shortDate(bestPickup.pickup_date))} · ${esc(bestPickup.held_days)} days · value × season held ${num(bestPickup.pickup_score).toFixed(3)}` : "—"}</small></div>
      </div>
      <details class="info team-info"><summary aria-label="Team summary">i</summary><div class="info-card">${esc(teamInsight(team, roster, standing))} Draft value share: ${pct(roster.drafted_value_share)}. Roster turnover: ${pct(roster.roster_turnover)}.</div></details>
      ${timelineMarkup(team.team_key, roster.last_active_week)}
      ${fullDraft}
      ${missing}
    </div>
  </article>`;
}).join("");

const teamSelect = document.querySelector("#team-select");
teamSelect.innerHTML = teamsByFinish.map(team => {
  const standing = standingsByTeam.get(team.team_key);
  return `<option value="${esc(team.team_key)}">#${esc(standing.rank)} · ${esc(team.team_name)}</option>`;
}).join("");

function showTeam(teamKey) {
  for (const card of document.querySelectorAll(".team-card")) {
    card.hidden = card.dataset.teamKey !== teamKey;
  }
}
showTeam(teamSelect.value);
teamSelect.addEventListener("change", () => showTeam(teamSelect.value));

for (const timeline of document.querySelectorAll(".timeline")) {
  const teamKey = timeline.dataset.team;
  const slider = timeline.querySelector(".week-slider");
  renderTimeline(timeline, teamKey, slider.value);
  slider.addEventListener("input", () => renderTimeline(timeline, teamKey, slider.value));
}

function activateTab(name) {
  for (const button of document.querySelectorAll(".tab-button")) {
    const selected = button.dataset.tab === name;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-selected", selected ? "true" : "false");
  }
  for (const panel of document.querySelectorAll(".tab-panel")) {
    const selected = panel.id === `view-${name}`;
    panel.classList.toggle("active", selected);
    panel.hidden = !selected;
  }
}

for (const button of document.querySelectorAll(".tab-button")) {
  button.addEventListener("click", () => activateTab(button.dataset.tab));
}

document.addEventListener("click", event => {
  for (const detail of document.querySelectorAll("details.info[open]")) {
    if (!detail.contains(event.target)) detail.removeAttribute("open");
  }
});
</script>
</body>
</html>
""".replace("__DATA__", json_for_html(data))

    OUTPUT.write_text(html, encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
