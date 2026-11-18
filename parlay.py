#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 18 18:38:09 2026

@author: pablozurdoalcantara
"""

# ============================================================
# parlay.py
# Part 5 of our project: the PARLAY BUILDER
#
# Question 7: Can we build the parlay with the highest chance of winning,
#             and is it a good bet?
# Before running: create a folder called "charts" in the project folder,
# next to nba_betting_clean.csv.
#
# A parlay = several bets (called "legs") combined into ONE bet.
# It only wins if ALL the legs win. If one leg loses, you lose everything.
#
#   Combined odds        = odds of leg 1 * odds of leg 2 * ...
#   Combined probability = chance of leg 1 * chance of leg 2 * ...
#   Expected value       = combined probability * combined odds - 1
#                          (average win or loss for every 1 euro bet;
#                           negative = you lose money in the long run)
# ============================================================
import pandas as pd
# WHAT: load the charts part of matplotlib (pyplot) with the nickname plt (session 13).
import matplotlib.pyplot as plt
# ------------------------------------------------------------
# FUNCTION 1: parlay_stats(legs)
# Input:  legs = a table (DataFrame) with one row per leg
#         and the columns "odds" and "fair_prob"
# Output: 3 values -> combined odds, combined probability, expected value
# ------------------------------------------------------------

# WHY: we need these 3 numbers for every parlay, so we write the calculation once and reuse it.
def parlay_stats(legs):

    #we are going to multiply all the odds together, so we need a starting value.
    combined_odds = 1

    # same with the probability
    combined_prob = 1

    # a parlay's odds = odds of leg 1 x odds of leg 2 x ...
    # go through the odds columns one value at a time 
    for odds in legs["odds"]:

        # multiply the running total by this leg's odds and save the new total.
        combined_odds = combined_odds * odds

    # the chance that ALL legs win = chance of leg 1 x chance of leg 2 x ...
    # now we do the same loop but in the fair_prob column
    for prob in legs["fair_prob"]:

        # multiply the running total by this leg's chance of winning.
        combined_prob = combined_prob * prob

    # tells us if the bet is good or bad on average (negative = we lose money in the long run).
    # chance of winning x what we get back, minus the 1 euro we bet.
    expected_value = combined_prob * combined_odds - 1
    return combined_odds, combined_prob, expected_value


# ------------------------------------------------------------
# FUNCTION 2: pick_legs(day_games, n_legs, mode)
# Chooses the best legs from the games of ONE day.
#
# mode "safest"     -> bet on the teams with the HIGHEST chance of winning
# mode "best value" -> bet on the favourites of the games where the bookmaker's
#                      margin is smallest (the bets that lose the least on average)
#
# Output: a table with one row per leg (columns: date, team, opponent, odds,
#         fair_prob, won, margin). An empty table if there are not enough games.
# ------------------------------------------------------------

# to build a parlay we must decide which teams to bet on each day.
# a function with 3 parameters. n_legs=3 and mode="safest" are DEFAULT values:

def pick_legs(day_games, n_legs=3, mode="safest"):

    
    #  len() counts the rows of the table (the games that day); "<" asks "is it smaller than?".
    if len(day_games) < n_legs:

        # return stops the function here and sends back an empty table (no legs).
        return pd.DataFrame()

    # --- 1. Create a table of legs: one row per game ---

    #  we need a new table to save the team we bet on in each game.
    # pd.DataFrame() creates an empty table.
    legs = pd.DataFrame()

    # to start, we bet on the HOME team in every game; in step 3 we change the games
    #      where the away team is better.
    # each line creates a new column in "legs" by copying a column from day_games.
    legs["date"] = day_games["date"]                   # date of the game
    legs["team"] = day_games["home_team"]              # the team we bet on (home for now)
    legs["opponent"] = day_games["away_team"]          # the team it plays against
    legs["odds"] = day_games["home_odds"]              # decimal odds of our team
    legs["fair_prob"] = day_games["home_fair_prob"]    # chance of our team winning
    legs["won"] = day_games["home_won"]                # True if our team really won

    # --- 2. Decide in which games the AWAY team is the better bet ---

    # in both modes we bet on the team that is more likely to win (the favourite).
    # compares the two columns game by game and gives True where the away team
    #       has the higher chance and False where it doesn't.
    away_better = day_games["away_fair_prob"] > day_games["home_fair_prob"]

    # --- 3. In those games, change the leg to the AWAY team ---

    # in the games where away_better is True, our bet must be the away team.
    # .loc[condition, "column"] = new value changes only the rows where the condition is True
    legs.loc[away_better, "team"] = day_games["away_team"]           # our team is now the away team
    legs.loc[away_better, "opponent"] = day_games["home_team"]       # and the opponent is the home team
    legs.loc[away_better, "odds"] = day_games["away_odds"]           # use the away team's odds
    legs.loc[away_better, "fair_prob"] = day_games["away_fair_prob"] # and the away team's chance

    # we need to know if the AWAY team won.
    # home_won == False gives True when the home team did NOT win, which means the away team won.
    legs.loc[away_better, "won"] = day_games["home_won"] == False

    # the bookmaker's margin in each game (what it keeps): both chances added together minus 100%.
    legs["margin"] = day_games["home_prob"] + day_games["away_prob"] - 1

    # --- 4. Keep the best legs ---

    # a parlay of n legs only uses the n best options of the day.
    # "safest": nlargest keeps the n legs with the HIGHEST chance of winning (session 16).
    # "best value": nsmallest keeps the n games where the bookmaker keeps the LEAST (session 16),
    #       a smaller margin means we lose less on average.
    if mode == "safest":
        best_legs = legs.nlargest(n_legs, "fair_prob")
    else:
        best_legs = legs.nsmallest(n_legs, "margin")

    # send the table of chosen legs back.
    return best_legs


# ------------------------------------------------------------
# FUNCTION 3: backtest_parlays(games, n_legs, mode, stake, start_bankroll)
# Plays ONE parlay every day of the data and follows the money.
# Output: 6 values -> bets, wins, win_rate, profit, roi, bankroll_history
# ------------------------------------------------------------

# to answer "is a parlay a good bet?" we test it on 10 seasons of real games.
# a function with 5 parameters; 4 have default values
#       (3 legs, "safest", 10 euros per parlay, 1000 euros to start).
def backtest_parlays(games, n_legs=3, mode="safest", stake=10, start_bankroll=1000):

    # we follow our money from the start to the end.
    # bankroll = the money we have right now; it starts with the start amount.
    bankroll = start_bankroll

    # we want to draw a chart of how our money changes over time.
    bankroll_history = [start_bankroll]

    # we need to count how many parlays we play and win, and the total profit.
    # three counters that start at 0.
    bets = 0
    wins = 0
    profit = 0

    # we play one parlay per day, so we need the list of all the different days, in order.
    # games["date"] takes the date column and drop_duplicates() removes repeated dates
    dates = games["date"].drop_duplicates().sort_values()

    #  repeat the same steps for every day.
    for date in dates:

        # we need only the games of that day.
        day_games = games.loc[games["date"] == date]
        #  choose the teams of today's parlay.
        #  call Function 2 with today's games and it returns a table of legs.
        legs = pick_legs(day_games, n_legs, mode)

        # if there weren't enough games, pick_legs returned an empty table.
        # len() counts its rows and if "== 0" asks "is it empty?"
        if len(legs) == 0:

            # goes to the next day
            continue

        # we need the combined odds to know how much we win
        combined_odds, combined_prob, expected_value = parlay_stats(legs)

        # the parlay only wins if EVERY leg won.
        # sum() adds the "won" column, True counts as 1 and False as 0,
        # so the result is the number of legs that won.
        legs_won = legs["won"].sum()

        # if the number of legs won equals the number of legs, ALL of them won.
        if legs_won == n_legs:

            # when we win, we get stake x odds back, so the profit is stake x (odds - 1).
            # example: 10 x (1.69 - 1) = 6.90 euros profit.
            result = stake * (combined_odds - 1)

            # add 1 to the wins counter.
            wins = wins + 1

        # "else" = at least one leg lost.
        else:

            # when we lose, we lose the money we bet.
            result = -stake

        # update all our totals after each parlay.
        bets = bets + 1                         # one more parlay played
        profit = profit + result                # add this result to the total profit
        bankroll = bankroll + result            # update the money we have now

        # .append() adds the new amount at the end of the list (session 10).
        bankroll_history.append(bankroll)

    # dividing by zero would crash the program, so first we check that we played at least once.
    #  "==" asks "is bets equal to 0?".
    if bets == 0:
        win_rate = 0                            # no parlays -> 0%
        roi = 0

    else:
        #  % of parlays won = wins / parlays x 100.
        win_rate = wins / bets * 100

        # ROI shows how much we won or lost for every 100 euros bet.
        # profit / total money bet (parlays x stake) x 100.
        roi = profit / (bets * stake) * 100

    #  the code that called the function needs all the results.
    return bets, wins, win_rate, profit, roi, bankroll_history


# ============================================================
# FROM HERE ON WE USE THE FUNCTIONS ABOVE
#
# everything below is inside  if __name__ == "__main__":
# it only runs when we press Run on THIS file.
# when the website does  from parlay import pick_legs  this part is skipped,
# so it can use our 3 functions without running the test and the chart.
# ============================================================

if __name__ == "__main__":

    # ------------------------------------------------------------
    # DATA: the shared table made by the cleaning file
    # ------------------------------------------------------------

    # every part uses the same cleaned data, made by NBA_DATA_PROGRAMING.py.
    # this runs the cleaning file and takes its table "regular" (one row per regular-season game).
    # NBA_DATA_PROGRAMING.py and NBA_PROGRA.xlsx must be in the same folder as this file.
    from NBA_DATA_PROGRAMING import regular

    # we calculate both fair chances again with the same formula as the guide.
    # the cleaning file does the away one as 1 - home, which rounds slightly differently
    # and can change which team is picked when two games have the same odds.
    regular["home_fair_prob"] = regular["home_prob"] / (regular["home_prob"] + regular["away_prob"])
    regular["away_fair_prob"] = regular["away_prob"] / (regular["home_prob"] + regular["away_prob"])


    # ------------------------------------------------------------
    # 1. EXAMPLE: the safest 3-leg parlay of one day
    # ------------------------------------------------------------

    # before testing 10 seasons, we show ONE parlay so it's easy to understand in the presentation.
    # filter the games played on 15 March 2024.
    example_games = regular.loc[regular["date"] == "2024-03-15"]

    # call pick_legs to choose the 3 safest legs of that day (returns a table).
    example_legs = pick_legs(example_games, 3, "safest")

    # print() shows text in the console.
    print("EXAMPLE: safest 3-leg parlay on 2024-03-15")

    # show the chosen teams.
    print(example_legs.loc[:, ["team", "opponent", "odds", "fair_prob", "won"]])

    # call parlay_stats, it returns 3 values, saved in 3 variables in the same order.
    combined_odds, combined_prob, expected_value = parlay_stats(example_legs)

    # show the parlay's numbers in a readable way.
    print("Combined odds:", round(combined_odds, 2))
    print("Chance of winning:", round(combined_prob * 100, 1), "%")
    print("Expected value per 1 euro:", round(expected_value, 3))


    print()


    # ------------------------------------------------------------
    # 2. TEST: parlays of 2, 3, 4 and 5 legs, in both modes
    # ------------------------------------------------------------

    # we want to see how the results change with more legs.
    # a LIST with the numbers of legs we are going to test.
    legs_list = [2, 3, 4, 5]

    #  we save the ROI of each test to draw them in the chart later.

    safest_roi = []
    value_roi = []


    print("PARLAY RESULTS (10 euros per parlay, regular season 2015-16 to 2024-25)")

    # run the test once for each number of legs, in "safest" mode.
    for n in legs_list:

        #  call backtest_parlays with n legs
        bets, wins, win_rate, profit, roi, history = backtest_parlays(regular, n, "safest")
        safest_roi.append(roi)
        print("Safest     |", n, "legs | parlays:", bets,
              "| win rate:", round(win_rate, 2), "% | profit:", round(profit, 2),
              "euros | ROI:", round(roi, 2), "%")

    #  the same loop, but in "best value" mode.
    for n in legs_list:
        bets, wins, win_rate, profit, roi, history = backtest_parlays(regular, n, "best value")
        value_roi.append(roi)
        print("Best value |", n, "legs | parlays:", bets,
              "| win rate:", round(win_rate, 2), "% | profit:", round(profit, 2),
              "euros | ROI:", round(roi, 2), "%")


    # ------------------------------------------------------------
    # 3. CHART: ROI % by number of legs, one line per mode (matplotlib, session 13)
    # ------------------------------------------------------------

    # a chart shows that parlays lose more money with every extra leg.
    # plt.figure creates a new empty chart, figsize=(8, 5) = 8 wide x 5 tall.
    plt.figure(figsize=(8, 5))

    # plt.plot(x, y) draws a line: x = number of legs, y = ROI.
    #       marker="o" puts a dot on each point, label = the name shown in the legend.
    plt.plot(legs_list, safest_roi, marker="o", label="Safest")
    plt.plot(legs_list, value_roi, marker="o", label="Best value")

    # the line at 0 shows where you would break even
    # axhline draws a horizontal line across the whole chart.
    plt.axhline(0, color="black")

    # to compare parlays with a normal single bet on the favourite (Part 4: -4.45%).
    #  a gray dashed horizontal line at -4.45, with its own name in the legend.
    plt.axhline(-4.45, color="gray", linestyle="--",
                label="Single bet on the favourite (-4.45%)")


    plt.title("Parlays lose more money with every extra leg")
    plt.xlabel("Number of legs in the parlay")
    plt.ylabel("Return on investment (%)")

    # WHY: the number of legs is always a whole number.
    plt.xticks(legs_list)


    plt.legend()

    # savefig saves it in the charts folder. 
    plt.savefig("charts/part5_parlay_roi.png")

    plt.show()