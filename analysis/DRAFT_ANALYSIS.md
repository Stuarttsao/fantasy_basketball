# Draft and Roster Construction Analysis

## Method

- Replacement level is BBM rank 157, the first player beyond the league's 156 draft slots.
- Replacement player: **Collin Murray-Boyles**, value **-0.278**.
- Sensitivity check: the average value from ranks 145–168 is **-0.276**.
- Player draft value is `max(final BBM value - replacement value, 0)`.
- Draft-position losses are capped at replacement rank 157; worse final ranks do not create extra penalties.
- Team draft score is the sum of that value across all 13 draft picks.
- Draft reliance weights player value by weeks spent on that team's roster.
- Final roster means the roster at each team's last active matchup, avoiding post-elimination cleanup moves.

## Best Drafts

1. **Cade and em** — score 4.213; 12 above-replacement picks; best pick: Kevin Porter Jr..
2. **Sengooners** — score 3.861; 11 above-replacement picks; best pick: Victor Wembanyama.
3. **go nembHard or go home** — score 3.614; 10 above-replacement picks; best pick: Luka Dončić.
4. **Zach's Boss Team** — score 3.344; 10 above-replacement picks; best pick: Kawhi Leonard.
5. **Nick P's Team** — score 3.251; 8 above-replacement picks; best pick: Nikola Jokić.
6. **The Stock Market** — score 3.207; 9 above-replacement picks; best pick: Walker Kessler.
7. **James's Super Team** — score 3.152; 9 above-replacement picks; best pick: Trey Murphy III.
8. **Shanghai Sharks** — score 3.083; 10 above-replacement picks; best pick: Tyrese Maxey.
9. **Stuart’s Three-Peat Team** — score 3.054; 9 above-replacement picks; best pick: Shai Gilgeous-Alexander.
10. **4D Chess Master** — score 2.760; 12 above-replacement picks; best pick: Cade Cunningham.
11. **Jet's Fascinating Team** — score 2.551; 10 above-replacement picks; best pick: Anthony Davis.
12. **Ronit's Reasonable Team** — score 2.428; 9 above-replacement picks; best pick: Stephen Curry.

## Best Pickups

1. **Jayson Tatum** — The Stock Market; picked up 2025-10-08; held 173 days; final BBM rank 22; score 0.535.
2. **Nickeil Alexander-Walker** — Stuart’s Three-Peat Team; picked up 2025-10-25; held 163 days; final BBM rank 31; score 0.418.
3. **Kevin Porter Jr.** — Cade and em; picked up 2025-11-26; held 99 days; final BBM rank 15; score 0.371.
4. **Kon Knueppel** — James's Super Team; picked up 2025-11-04; held 153 days; final BBM rank 64; score 0.230.
5. **Reed Sheppard** — Stuart’s Three-Peat Team; picked up 2025-11-13; held 144 days; final BBM rank 70; score 0.196.
6. **Desmond Bane** — Sengooners; picked up 2026-01-15; held 81 days; final BBM rank 39; score 0.194.
7. **Keegan Murray** — Shanghai Sharks; picked up 2025-11-21; held 113 days; final BBM rank 86; score 0.129.
8. **Ajay Mitchell** — Stuart’s Three-Peat Team; picked up 2025-11-07; held 133 days; final BBM rank 101; score 0.116.
9. **Saddiq Bey** — Ronit's Reasonable Team; picked up 2026-01-14; held 82 days; final BBM rank 80; score 0.101.
10. **Grayson Allen** — Nick P's Team; picked up 2025-10-23; held 81 days; final BBM rank 84; score 0.096.
11. **Ty Jerome** — James's Super Team; picked up 2025-10-08; held 48 days; final BBM rank 35; score 0.087.
12. **Grayson Allen** — 4D Chess Master; picked up 2026-01-14; held 71 days; final BBM rank 84; score 0.084.

## Team-by-Team Draft Notes

- **Cade and em**: top contributor **Kevin Porter Jr.**; best rank value **Kevin Porter Jr.** at pick 108 (finished 15); largest rank miss **Trae Young** at pick 13 (finished 123).
- **Sengooners**: top contributor **Victor Wembanyama**; best rank value **VJ Edgecombe** at pick 146 (finished 65); largest rank miss **Darius Garland** at pick 47 (finished 99).
- **go nembHard or go home**: top contributor **Luka Dončić**; best rank value **Keyonte George** at pick 124 (finished 34); largest rank miss **Cam Thomas** at pick 69 (finished 448). No BBM season row: Fred VanVleet.
- **Zach's Boss Team**: top contributor **Kawhi Leonard**; best rank value **Kawhi Leonard** at pick 53 (finished 4); largest rank miss **Christian Braun** at pick 92 (finished 180).
- **Nick P's Team**: top contributor **Nikola Jokić**; best rank value **Jaden McDaniels** at pick 120 (finished 75); largest rank miss **Coby White** at pick 49 (finished 244).
- **The Stock Market**: top contributor **Walker Kessler**; best rank value **Walker Kessler** at pick 67 (finished 11); largest rank miss **Ivica Zubac** at pick 43 (finished 106).
- **James's Super Team**: top contributor **Trey Murphy III**; best rank value **Trey Murphy III** at pick 39 (finished 9); largest rank miss **Jordan Poole** at pick 58 (finished 286).
- **Shanghai Sharks**: top contributor **Tyrese Maxey**; best rank value **Mikal Bridges** at pick 86 (finished 44); largest rank miss **Devin Booker** at pick 11 (finished 69).
- **Stuart’s Three-Peat Team**: top contributor **Shai Gilgeous-Alexander**; best rank value **Immanuel Quickley** at pick 94 (finished 53); largest rank miss **Zion Williamson** at pick 22 (finished 116). No BBM season row: Kyrie Irving.
- **4D Chess Master**: top contributor **Cade Cunningham**; best rank value **Zach Edey** at pick 113 (finished 30); largest rank miss **Ja Morant** at pick 56 (finished 146).
- **Jet's Fascinating Team**: top contributor **Anthony Davis**; best rank value **Dejounte Murray** at pick 114 (finished 60); largest rank miss **Anfernee Simons** at pick 90 (finished 218).
- **Ronit's Reasonable Team**: top contributor **Stephen Curry**; best rank value **Stephen Curry** at pick 16 (finished 8); largest rank miss **Pascal Siakam** at pick 40 (finished 100).

## Most Reliant on Their Draft

1. **Jet's Fascinating Team** — 97.5% of rostered positive value from original draft picks; 70.5% of roster slots.
2. **Ronit's Reasonable Team** — 91.8% of rostered positive value from original draft picks; 59.1% of roster slots.
3. **go nembHard or go home** — 78.5% of rostered positive value from original draft picks; 48.1% of roster slots.
4. **Nick P's Team** — 72.4% of rostered positive value from original draft picks; 44.3% of roster slots.
5. **Sengooners** — 72.4% of rostered positive value from original draft picks; 47.2% of roster slots.
6. **Zach's Boss Team** — 72.1% of rostered positive value from original draft picks; 55.7% of roster slots.
7. **Stuart’s Three-Peat Team** — 68.2% of rostered positive value from original draft picks; 45.6% of roster slots.
8. **Shanghai Sharks** — 66.7% of rostered positive value from original draft picks; 44.6% of roster slots.
9. **The Stock Market** — 65.7% of rostered positive value from original draft picks; 46.6% of roster slots.
10. **Cade and em** — 55.5% of rostered positive value from original draft picks; 34.1% of roster slots.
11. **James's Super Team** — 52.8% of rostered positive value from original draft picks; 31.9% of roster slots.
12. **4D Chess Master** — 10.7% of rostered positive value from original draft picks; 12.6% of roster slots.

## Final Roster Changed Most From Draft

1. **4D Chess Master** — turnover 100.0%; retained 0 of 13 picks; 10 final-roster additions.
2. **James's Super Team** — turnover 91.7%; retained 2 of 13 picks; 11 final-roster additions.
3. **Cade and em** — turnover 88.0%; retained 3 of 13 picks; 12 final-roster additions.
4. **go nembHard or go home** — turnover 84.6%; retained 4 of 13 picks; 13 final-roster additions.
5. **Shanghai Sharks** — turnover 84.6%; retained 4 of 13 picks; 13 final-roster additions.
6. **The Stock Market** — turnover 80.0%; retained 5 of 13 picks; 12 final-roster additions.
7. **Stuart’s Three-Peat Team** — turnover 79.2%; retained 5 of 13 picks; 11 final-roster additions.
8. **Nick P's Team** — turnover 78.3%; retained 5 of 13 picks; 10 final-roster additions.
9. **Sengooners** — turnover 78.3%; retained 5 of 13 picks; 10 final-roster additions.
10. **Jet's Fascinating Team** — turnover 66.7%; retained 7 of 13 picks; 8 final-roster additions.
11. **Zach's Boss Team** — turnover 66.7%; retained 7 of 13 picks; 8 final-roster additions.
12. **Ronit's Reasonable Team** — turnover 60.0%; retained 8 of 13 picks; 7 final-roster additions.

## Data Quality

- Ownership reconstruction anomalies: 0.
- Details: {}.
- The team draft ranking is unchanged when replacement value uses the ranks 145–168 average instead of rank 157.
- Kyrie Irving and Fred VanVleet have no BBM row because they recorded no qualifying season data; they receive zero above-replacement value.
- This is retrospective: BBM final value measures season outcome, not what managers knew on draft day.
- Rostered-value share uses final player value weighted by roster duration; it is not exact production accrued while owned.
