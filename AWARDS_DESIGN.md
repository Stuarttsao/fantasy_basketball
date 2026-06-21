# Shareable Season Cards

## Purpose

The report should turn one clear analytical result or memorable matchup into
something that is:

- understandable in a few seconds;
- visually recognizable as part of the SAS season report;
- attractive enough to share outside the report;
- generated from data rather than written by hand;
- reusable in a future fantasy basketball application.

## Card format

- **Aspect ratio:** 4:5
- **Future export size:** 1080 × 1350 pixels
- **Web display:** one horizontal, snap-scrolling rail containing both awards
  and season moments; roughly three cards are visible on desktop and one large
  card is visible on mobile
- **Interaction:** clicking a card opens a larger 4:5 share preview

## Card anatomy

Every award uses the same hierarchy:

1. League and season
2. Award title
3. Winner
4. Manager or fantasy team context
5. One dominant number
6. One sentence explaining the number
7. A footer identifying the card as an award, record or matchup moment

The card should never require an information tooltip to understand why it was
awarded.

## Card types

- **Award:** a season-long achievement such as champion or best draft.
- **Category record:** the best weekly total in points, steals, assists or
  another scoring category.
- **Matchup moment:** a 5–4 result decided by a very small category margin.
- **Transaction moment:** a pickup or trade made immediately before a close
  result.
- **Rivalry or turning point:** a repeated matchup or event that changed a
  team's season.

This system should evolve beyond an awards shelf. The strongest cards are
specific stories a manager would actually send to the league chat.

## Initial awards and records

- League Champion
- Draft Room Winner
- Waiver Find of the Year
- Draft Night Heist
- Weekly Steals Record
- Transaction Machine

## Initial matchup moments

- Nick P's Team beat Ronit's Reasonable Team 5–4 in Week 22 after winning
  steals 45–44.
- go nembHard or go home beat Cade and em 5–4 in Week 5 after winning steals
  36–35.
- go nembHard or go home beat Shanghai Sharks 5–4 in Week 17 after winning
  field-goal percentage .460 to .459.
- Jet's Fascinating Team added Killian Hayes on the final day of Week 20 and
  beat Stuart's Three-Peat Team 5–4. The two narrow winning categories were
  assists, 163–161, and turnovers, 71–73.

The current data verifies transaction timing and matchup totals, but not each
player's day-by-day contribution. A card must not claim that one player caused
a category win until player-level daily stats support that statement.

## Design system

- Dark charcoal base creates a distinct, collectible “season yearbook” look.
- Featured moments can replace the abstract visual with a hand-drawn editorial
  basketball illustration. The visual owns the upper half and never contains
  live text. All titles, names and statistics sit on a solid light information
  panel below it, preventing contrast and overlap problems.
- Each award category has one accent color.
- Award titles and dominant numbers use the same bold editorial sans-serif as
  the report. Tight spacing and strong weight create character without a
  handwritten look.
- Supporting information uses the report’s normal sans-serif typography.
- Decorative geometry is intentionally abstract so the cards do not depend on
  copyrighted NBA or Yahoo artwork.

## Future application model

The app should render cards from a small award object:

```text
type
key
title
winner
manager_or_team
primary_stat
explanation
season
accent
week_or_date
opponent
evidence_level
linked_player_or_transaction
```

The same component can be rendered as:

- a card in the league report;
- a modal share preview;
- a server- or browser-generated PNG;
- a season recap carousel;
- a manager-specific award collection.

## Export path

A later version can add a “Download image” action using the browser’s canvas
rendering or a server-side screenshot service. The visual component should
remain HTML/CSS so report and exported-image designs stay synchronized.
