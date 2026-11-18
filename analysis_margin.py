#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov 15 14:40:46 2026

@author: nachoreboredo
"""

"""
analysis_margin.py  -  PART 1: Bookmaker margin and accuracy of the odds
Answers sub-questions 1 and 2:
    1. How much does the bookmaker keep on every bet (the margin)?
    2. Are the odds accurate (does a team with a 70% chance really win about 70% of the time)?
Needs NBA_DATA_PROGRAMING.py and NBA_PROGRA.xlsx in the same folder.
"""
import os
import pandas as pd
import matplotlib.pyplot as plt

# the two tables built in the starting code
#   regular = one row per regular-season game        (used for the margin)
#   teams   = one row per team per game (2 per game) (used for the accuracy)
from NBA_DATA_PROGRAMING import regular, teams

os.makedirs("charts", exist_ok=True)   # folder for the charts (no error if it already exists)

# ======================================================================
# TASK 1: average margin per season (in %)
# ======================================================================
# group the games by season, take the column "margin", average it, multiply by 100 to get %
margin_by_season = regular.groupby("season")["margin"].mean() * 100

plt.figure(figsize=(8, 4.5))
plt.plot(margin_by_season.index, margin_by_season.values, marker="o", color="tab:blue")
plt.title("Average bookmaker margin per season")
plt.xlabel("Season")
plt.ylabel("Average margin (%)")
plt.xticks(rotation=45)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("charts/part1_margin_by_season.png", dpi=150)
plt.show()

print("Average margin per season (%):")
print(margin_by_season.round(2).to_string())

# ======================================================================
# TASK 2: overall average margin (in %)
# ======================================================================
overall_margin = regular["margin"].mean() * 100
print(f"\nOverall average margin: {overall_margin:.2f}%")

# ======================================================================
# TASK 3: accuracy table (calibration)
# ======================================================================
# 10 groups ("bins") of 10% each, based on the fair probability the bookmaker gave the team
bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
labels = ["0-10%", "10-20%", "20-30%", "30-40%", "40-50%",
          "50-60%", "60-70%", "70-80%", "80-90%", "90-100%"]

calib = teams.copy()   # a copy, so we can add a column without changing "teams" (other parts use it)
# pd.cut puts every row in its group: a team with fair_prob 0.64 goes to "60-70%"
calib["bin"] = pd.cut(calib["fair_prob"], bins=bins, labels=labels, include_lowest=True)

# for each group: how many team-games, expected win rate, actual win rate
#   "won" is True/False, so its mean is directly the % of times the team won
table = calib.groupby("bin", observed=True).agg(
    team_games=("won", "size"),
    expected_win_rate=("fair_prob", "mean"),
    actual_win_rate=("won", "mean"),
)
table["difference"] = table["actual_win_rate"] - table["expected_win_rate"]

print("\nCalibration table (fair probability vs what really happened):")
print((table * [1, 100, 100, 100]).round(1).rename(columns={
    "expected_win_rate": "expected_%", "actual_win_rate": "actual_%", "difference": "diff_pp"}).to_string())

# ======================================================================
# TASK 4: calibration chart
# ======================================================================
plt.figure(figsize=(6, 6))
plt.plot([0, 1], [0, 1], linestyle="--", color="gray", label="perfect odds")   # the diagonal
plt.plot(table["expected_win_rate"], table["actual_win_rate"],
         marker="o", color="tab:red", label="bookmaker odds")                  # our points
plt.title("Are the odds accurate? Expected vs actual win rate")
plt.xlabel("Expected win rate (fair probability from the odds)")
plt.ylabel("Actual win rate")
plt.xlim(0, 1)
plt.ylim(0, 1)
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig("charts/part1_calibration.png", dpi=150)
plt.show()

# Extra number for the report: average distance to the diagonal (groups with more games count more)
weights = table["team_games"] / table["team_games"].sum()
avg_gap = (table["difference"].abs() * weights).sum() * 100
print(f"\nAverage gap to the perfect line: {avg_gap:.2f} percentage points")

# ======================================================================
# TASK 5: what the results mean (text for the report)
# ======================================================================
# - MARGIN: about 4%. Even with perfect odds, a bettor pays ~4% on every bet.
# - ACCURACY: the points are almost on the diagonal (average gap ~0.5 points),
#   so the odds are very accurate and it is very hard to find an edge.