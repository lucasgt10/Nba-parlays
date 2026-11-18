#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov 15 13:47:23 2026

@author: nachoreboredo
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov  2 11:57:33 2026

@author: pablozurdoalcantara
"""

# PROGRAMMING PROJECT
# CAN WE BEAT THE BOOKIES?
#
# STARTING CODE: loads and cleans the data and builds the tables that every other file uses:
#     regular : one row per regular-season game
#     teams   : one row per team per game (2 rows per game)
# Other files use:   from NBA_DATA_PROGRAMING import regular, teams

import os
import pandas as pd

# Import dataset (the Excel file must be in the SAME folder as this file)
FOLDER = os.path.dirname(os.path.abspath(__file__))
nbadata = pd.read_excel(os.path.join(FOLDER, "NBA_PROGRA.xlsx"))

# number of rows and columns
nbadata.shape
# type of each column
nbadata.dtypes

# PROBLEM: the moneylines and "spread" can show as text (object/str) and we want numbers
# some moneylines are written like "+145 " (with a + and a space); spread has "PK" (pick'em = 0)
for col in ["home_moneyline", "away_moneyline"]:
    nbadata[col] = nbadata[col].astype(str)                              # make sure every value is text
    nbadata[col] = nbadata[col].str.strip()                              # remove spaces at the start and end
    nbadata[col] = nbadata[col].str.replace("+", "", regex=False)        # remove the + sign
    nbadata[col] = pd.to_numeric(nbadata[col])                           # now convert the text to numbers

nbadata["spread"] = nbadata["spread"].astype(str).str.strip().replace("PK", "0")   # PK -> 0
nbadata["spread"] = pd.to_numeric(nbadata["spread"])

# the date must be a real date, not text
nbadata["date"] = pd.to_datetime(nbadata["date"])

# REMOVE POSTPONED GAMES
# A basketball game can't end 0-0. These 6 games were postponed
# and played again later
# ------------------------------------------------------------
postponed = (nbadata["home_score"] == 0) & (nbadata["away_score"] == 0)   # True for games that ended 0-0
nbadata = nbadata[postponed == False]                                     # keep only the games that are NOT postponed
nbadata = nbadata.reset_index(drop=True)

# FIX TEAM NAMES
# Some teams appear with two different names (32 names instead of 30 teams).
# ------------------------------------------------------------

# Charlotte has been called "Hornets" since 2014, so "Bobcats" is a mistake.
nbadata["home_team"] = nbadata["home_team"].replace("Charlotte Bobcats", "Charlotte Hornets")
nbadata["away_team"] = nbadata["away_team"].replace("Charlotte Bobcats", "Charlotte Hornets")

# "LA Clippers" and "Los Angeles Clippers" are the same team.
nbadata["home_team"] = nbadata["home_team"].replace("LA Clippers", "Los Angeles Clippers")
nbadata["away_team"] = nbadata["away_team"].replace("LA Clippers", "Los Angeles Clippers")


# Convert American odds to decimal odds
# American odds:  +150 = bet 100, win 150 profit
#                 -200 = bet 200, win 100 profit
# Decimal odds = how much you get back for every 1 euro you bet
#                +150 -> 2.50      -200 -> 1.50

def americantodecimal(odds):
    if odds > 0:                      # underdog (positive odds)
        return odds / 100 + 1
    else:                             # favourite (negative odds)
        return 100 / abs(odds) + 1

# .apply() runs the americantodecimal function on every value in the column, one by one,
# and saves all the results in a new column (needed because the function's if can only check one number at a time)

nbadata["home_odds"] = nbadata["home_moneyline"].apply(americantodecimal)   # use the function on every row
nbadata["away_odds"] = nbadata["away_moneyline"].apply(americantodecimal)

# Implied probability: the chance the bookmaker gives each team
nbadata["home_prob"] = 1 / nbadata["home_odds"]
nbadata["away_prob"] = 1 / nbadata["away_odds"]

# Bookmaker margin
# The two probabilities add up to MORE than 100%.
# The extra part is the bookmaker's profit.
# (We checked: every margin is between about 1% and 8%, which is normal,
#  so extreme odds like -9900 are real and we keep them.)
nbadata["margin"] = nbadata["home_prob"] + nbadata["away_prob"] - 1

# Fair probability: the implied probabilities with the margin removed (they add up to exactly 100%)
nbadata["home_fair_prob"] = nbadata["home_prob"] / (nbadata["home_prob"] + nbadata["away_prob"])
nbadata["away_fair_prob"] = 1 - nbadata["home_fair_prob"]

# Who was the favourite, and did they win?
nbadata["home_is_favourite"] = nbadata["home_odds"] < nbadata["away_odds"]          # True if home team has the lower odds
nbadata["home_won"] = nbadata["winner"] == "Home"                                   # True if the home team won
nbadata["favourite_won"] = nbadata["home_is_favourite"] == nbadata["home_won"]      # True if the favourite won

# Back-to-back games (team played yesterday = 1 day of rest)
nbadata["home_back_to_back"] = nbadata["home_rest_days"] == 1
nbadata["away_back_to_back"] = nbadata["away_rest_days"] == 1

# save the new data
nbadata.to_csv(os.path.join(FOLDER, "nba_betting_clean.csv"), index=False)   # save the clean table as a new CSV file


# ------------------------------------------------------------
# TABLES FOR THE ANALYSIS (used by Parts 1-6)
# ------------------------------------------------------------
# "regular" = regular-season games only (no playoffs)
regular = nbadata[nbadata["game_type"] == "Regular Season"].reset_index(drop=True)

# "teams" = one row per team per game, so we can study every bet on a single team.
# Profit of betting 10 euros on that team: win -> 10 * (odds - 1), lose -> -10
STAKE = 10

def build_teams(games):
    rows = []
    for side, other in [("home", "away"), ("away", "home")]:
        part = pd.DataFrame({
            "season": games["season"],
            "date": games["date"],
            "team": games[side + "_team"],
            "opponent": games[other + "_team"],
            "is_home": side == "home",
            "odds": games[side + "_odds"],
            "fair_prob": games[side + "_fair_prob"],
            "is_favourite": games["home_is_favourite"] if side == "home" else ~games["home_is_favourite"],
            "won": games["home_won"] if side == "home" else ~games["home_won"],
            "back_to_back": games[side + "_back_to_back"],
        })
        rows.append(part)
    t = pd.concat(rows, ignore_index=True)
    t["profit"] = (t["won"] * STAKE * (t["odds"] - 1)) - ((~t["won"]) * STAKE)
    return t.sort_values("date", kind="stable").reset_index(drop=True)

teams = build_teams(regular)

if __name__ == "__main__":
    print("Clean games:", len(nbadata), "| regular season:", len(regular), "| team-games:", len(teams))
    print("Teams:", nbadata["home_team"].nunique())
    
    