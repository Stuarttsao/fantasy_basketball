# Fantasy Basketball Project Plan

## Vision

Build toward a fast, polished fantasy basketball application while making every step useful on its own.

## Phase 1 — SAS 2025–26 Season Analysis

Start by downloading the historical Yahoo data for league **SAS (ID 95762)** and experimenting with analysis and visual storytelling.

### Step 1: Acquire and understand the data

- Download league settings, teams, standings, draft results, transactions, and all weekly matchups.
- Preserve the original Yahoo responses.
- Inspect data coverage and identify anything that must be imported separately.

### Step 2: Explore the season

- Calculate category and overall team strength by week.
- Trace how each team changed through acquisitions, drops, trades, and lineup decisions.
- Identify close matchups and the categories that decided them.
- Experiment with draft value and pickup value.

### Step 3: Create visual stories

- Team-strength trajectories and category profiles.
- Weekly standings and matchup timelines.
- Best and worst pickups.
- Best and worst draft values.
- Most active manager and best move.
- Other transparent, reproducible league superlatives.

### Step 4: Build the season-recap website

Create a fast, responsive, private-but-shareable website where league members can:

- Scroll through each team's season timeline.
- See how strengths, weaknesses, rosters, and standings evolved.
- Explore tight matchups and turning points.
- Browse league awards with the evidence behind each choice.

## Phase 2 — Full Application

Use Phase 1's data model, analytics, components, and league feedback to decide the best larger product direction.

Possible directions include:

- Live Yahoo league dashboards and matchup analysis.
- Waiver, streaming, trade, and lineup recommendations.
- Multi-season histories and automated season recaps.
- Support for multiple leagues and fantasy platforms.
- Personalized alerts and weekly reports.

The exact Phase 2 product will be chosen after the Phase 1 recap is working and league members have used it.

## Principles

- Build iteratively; every milestone should produce something useful.
- Keep calculations explainable and reproducible.
- Preserve raw data and separate ingestion, analysis, and presentation.
- Make architectural choices that can grow into a full application without delaying early exploration.
