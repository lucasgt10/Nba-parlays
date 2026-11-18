#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 17 19:15:33 2026

@author: Alberto
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

# The cleaned tables built by the starting code
from NBA_DATA_PROGRAMING import regular, teams, STAKE

os.makedirs("charts", exist_ok=True)


# HELPER FUNCTION: returns multiple values (Session 9)
def summarise(df):
    bets = len(df)
    if bets == 0:
        return 0, 0.0, 0.0, 0.0
    win_rate = round(df["won"].mean() * 100, 2)
    profit = round(df["profit"].sum(), 2)
    roi = round(profit / (bets * STAKE) * 100, 2)
    return bets, win_rate, profit, roi


# 1. ODDS BANDS 
teams["odds_band"] = pd.cut(
    teams["odds"],
    bins=[1.0, 1.5, 2.0, 3.0, 1000],
    labels=["1.0-1.5", "1.5-2.0", "2.0-3.0", "3.0+"],
    right=False
)

# 2. TABLE + BAR CHART PER BAND 
bands = ["1.0-1.5", "1.5-2.0", "2.0-3.0", "3.0+"]
bets_list = []
win_rate_list = []
profit_list = []
roi_list = []

for band in bands:
    filtered = teams[teams["odds_band"] == band]
    b, wr, p, r = summarise(filtered)
    bets_list.append(b)
    win_rate_list.append(wr)
    profit_list.append(p)
    roi_list.append(r)

band_table = pd.DataFrame({
    "odds_band": bands,
    "bets": bets_list,
    "win_rate": win_rate_list,
    "profit": profit_list,
    "roi": roi_list
})

print("=" * 60)
print("ODDS BANDS: betting", STAKE, "euros on every team in each band")
print("=" * 60)
print(band_table)

# Build bar colors 
bar_colors = []
for r in roi_list:
    if r >= 0:
        bar_colors.append("green")
    else:
        bar_colors.append("red")

plt.figure(figsize=(8, 5))
plt.bar(bands, roi_list, color=bar_colors, edgecolor="black", linewidth=1.5)
plt.axhline(0, color="black", linewidth=1)
plt.title("ROI by odds band (betting 10 on every team)")
plt.xlabel("Decimal odds band")
plt.ylabel("ROI (%)")
plt.grid(axis="y", linestyle="--", alpha=0.7)
plt.tight_layout()
plt.savefig("charts/part2_roi_by_odds_band.png", dpi=150)
plt.show()


# 3. FAVOURITES vs UNDERDOGS 
fav_b, fav_wr, fav_p, fav_roi = summarise(teams[teams["is_favourite"] == True])
dog_b, dog_wr, dog_p, dog_roi = summarise(teams[teams["is_favourite"] == False])

fav_dog_table = pd.DataFrame({
    "type": ["Favourites", "Underdogs"],
    "bets": [fav_b, dog_b],
    "win_rate": [fav_wr, dog_wr],
    "profit": [fav_p, dog_p],
    "roi": [fav_roi, dog_roi]
})

print("\n" + "=" * 60)
print("FAVOURITES vs UNDERDOGS")
print("=" * 60)
print(fav_dog_table)


# 4. HOME ADVANTAGE PER SEASON 
home_by_season = regular.groupby("season")["home_won"].mean()*100
# Identify the 2019-20 bubble season 
bubble_games = regular[(regular["date"] >= "2020-07-30") & (regular["date"] < "2020-12-01")]
bubble_season = bubble_games["season"].mode()[0]

print("\n" + "=" * 60)
print("HOME WIN % PER SEASON")
print("=" * 60)
print(home_by_season.round(2))

# Prepare lists for plotting using a for loop 
seasons_list = list(home_by_season.index)
home_win_list = list(home_by_season.values)
season_colors = []

for s in seasons_list:
    if s == bubble_season:
        season_colors.append("orange")
    else:
        season_colors.append("skyblue")

fig, ax = plt.subplots(figsize=(12, 5))
ax.bar(seasons_list, home_win_list, color=season_colors, edgecolor="black")
ax.axhline(50, color="red", linestyle="--", label="50% (no home advantage)")
ax.set_title("Home team win % per season (orange = 2019-20 bubble season)")
ax.set_xlabel("Season")
ax.set_ylabel("Home win (%)")
ax.legend()
plt.xticks(rotation=45)
plt.grid(axis="y", linestyle="--", alpha=0.7)
plt.tight_layout()
plt.savefig("charts/part2_home_win_by_season.png", dpi=150)
plt.show()


# 5. BUBBLE EFFECT: before vs from 2020-07-30 
season_1920 = regular[regular["season"] == bubble_season]
with_fans = season_1920[season_1920["date"] < "2020-07-30"]
bubble = season_1920[season_1920["date"] >= "2020-07-30"]

fans_win_pct = round(with_fans["home_won"].mean() * 100, 2)
bubble_win_pct = round(bubble["home_won"].mean() * 100, 2)

print("\n" + "=" * 60)
print("BUBBLE EFFECT (season " + str(bubble_season) + ")")
print("=" * 60)
print("Before 2020-07-30 (with fans):", len(with_fans), "games, home win % =", fans_win_pct)
print("From 2020-07-30 (bubble, no fans):", len(bubble), "games, home win % =", bubble_win_pct)
print("Note: the bubble has only", len(bubble), "games, a small sample, so this result is only an indication.")


# 6. KEY NUMBERS & SAVING REPORT TO FILE 
# Sort band_table by ROI descending to find best and worst bands 
sorted_bands = band_table.sort_values(by="roi", ascending=False)
best_band_row = sorted_bands.head(1)
worst_band_row = sorted_bands.tail(1)

if fav_roi > dog_roi:
    best_side = "favourites"
else:
    best_side = "underdogs"

overall_home_win = round(regular["home_won"].mean() * 100, 2)
highest_season_val = round(home_by_season.max(), 2)
lowest_season_val = round(home_by_season.min(), 2)

print("\n" + "=" * 60)
print("KEY NUMBERS FOR THE REPORT")
print("=" * 60)
print("Best band:\n", best_band_row)
print("Worst band:\n", worst_band_row)
print("Favourites ROI:", fav_roi, "% vs Underdogs ROI:", dog_roi, "% -> Less bad:", best_side)
print("Overall home win %:", overall_home_win)
print("Highest season home win %:", highest_season_val, "| Lowest season home win %:", lowest_season_val)

# Write summary results to a text file using with open(..., "w") (Session 11)
with open("part2_report_summary.txt", "w") as file:
    file.write("PART 2 ANALYSIS SUMMARY\n")
    file.write("Favourites ROI: " + str(fav_roi) + "%\n")
    file.write("Underdogs ROI: " + str(dog_roi) + "%\n")
    file.write("Overall Home Win %: " + str(overall_home_win) + "%\n")
    file.write("Bubble Season (" + str(bubble_season) + ") Home Win %: " + str(bubble_win_pct) + "%\n")
