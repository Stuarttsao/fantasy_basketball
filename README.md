# Fantasy Basketball Data Analysis

Build a useful fantasy basketball analysis workflow, with the option to grow it into a full application.

## Interactive Report

The generated report lives at `analysis/index.html`.

After GitHub Pages is enabled, the public site will be:

**https://stuarttsao.github.io/fantasy_basketball/**

Every push to `main` deploys the current generated HTML through
`.github/workflows/pages.yml`. The deployment publishes only the HTML report;
local OAuth tokens, certificates, raw downloads, and processed source files are
excluded.

## Current Status

**Stage:** Historical league analysis and report design
**Priority:** High

**Next action:** Continue improving the league and team visualizations.

## Download Yahoo Data

The first pass is intentionally simple and uses only Python's standard library.

```bash
cd "/Users/stuarttsao/Documents/Todo List/projects/fantasy-basketball-data-analysis"
python3 download_yahoo_data.py
```

The script prompts for the Yahoo Client Secret without displaying or saving it, opens Yahoo authorization in the browser, and writes raw responses to `data/raw/yahoo-2025-26/`.

See [LEAGUE.md](./LEAGUE.md) for the target league settings.
See [PLAN.md](./PLAN.md) for the two-phase project direction.

## Clean and Explore

```bash
python3 clean_yahoo_data.py
```

This leaves the raw Yahoo responses untouched and creates analysis-ready CSV files under `data/processed/`. The original BBM rankings and all-player workbooks are preserved under `data/raw/player-rankings-2025-26/`.

Important outputs include:

- `league_player_coverage.csv` — every player drafted or involved in a team transaction.
- `player_data_discrepancies.csv` — audited name aliases and players missing from BBM.
- `draft_analysis.csv` — Yahoo draft results joined to final BBM ranks.
- `weekly_team_strength.csv` — preliminary nine-category team strength by week.

## First Questions

- Which fantasy platform will this support?
- Is the league category-based, points-based, or another format?
- What are the roster, matchup, and transaction rules?
- Should the first feature focus on waivers, trades, rankings, or lineup decisions?
- Is this initially a personal tool or something other managers could use?
- How frequently does the data need to refresh?

## Potential Features

- Player rankings and category strengths.
- Waiver-wire and streaming recommendations.
- Trade evaluation.
- Schedule and games-played analysis.
- Team construction and category-punt strategies.
- Historical performance and trend analysis.
- Interactive dashboard or full-fledged web app.

## Suggested First Milestone

Create a small analysis that imports player statistics and produces a ranked waiver-wire shortlist for one specific league.

## Folder Structure

```text
fantasy-basketball-data-analysis/
├── data/
│   ├── raw/          # Original source data; do not edit manually
│   └── processed/    # Cleaned data ready for analysis
├── notebooks/        # Exploratory analysis
├── src/              # Reusable application and analysis code
├── tests/            # Automated tests
└── README.md         # Project plan and decisions
```

## Decisions

Record meaningful product, data, and technical decisions here as the project develops.

- No decisions recorded yet.

## Notes

- Keep credentials, API keys, and private league data out of Git.
- Validate data licensing and usage rules before building a public application.
