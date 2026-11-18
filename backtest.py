"""
Part 4 - Strategy backtester
File: backtest.py
Answers sub-question 6: can a simple betting strategy make money?

Other files (app.py, parlay.py) import from this file, so these names must NOT change:
    pick_home, pick_away, pick_favourite, pick_underdog, pick_big_favourite,
    pick_fade_tired, STRATEGIES, backtest(), compare_strategies()

Everything that prints or draws charts is inside  if __name__ == "__main__":
so nothing runs when another file imports this one.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt


# =============================================================================
# STARTING CODE (common context)
# NBA_DATA_PROGRAMING.py loads and cleans the Excel file and builds "regular"
# (one row per regular-season game). It must be in the SAME folder as this file.
# Columns used here: date, home_odds, away_odds, winner ("Home" / "Away"),
#                    home_is_favourite, home_back_to_back, away_back_to_back
# =============================================================================
from NBA_DATA_PROGRAMING import regular


# =============================================================================
# 1. STRATEGY FUNCTIONS
# Each one receives ONE game (one row of "regular") and returns
# "Home", "Away" or None (= do not bet on this game).
#
# Note: we write  == True  instead of  is True. Pandas stores True/False as
# numpy.bool_, and  numpy.bool_(True) is True  gives False, so "is True" would
# silently never match. "== True" works for both Python and numpy booleans.
# =============================================================================

def pick_home(game):
    """Always bet on the home team."""
    return "Home"


def pick_away(game):
    """Always bet on the away team."""
    return "Away"


def pick_favourite(game):
    """Bet on the favourite (the team with the lower odds)."""
    if game["home_is_favourite"] == True:
        return "Home"
    return "Away"


def pick_underdog(game):
    """Bet on the underdog: the opposite of pick_favourite."""
    if pick_favourite(game) == "Home":
        return "Away"
    return "Home"


def pick_big_favourite(game):
    """Bet on the favourite, but ONLY if its decimal odds are below 1.5."""
    side = pick_favourite(game)
    if side == "Home":
        odds = game["home_odds"]
    else:
        odds = game["away_odds"]

    if odds < 1.5:
        return side
    return None


def pick_fade_tired(game):
    """Bet against a team on a back-to-back, only if its opponent is rested."""
    home_tired = game["home_back_to_back"] == True
    away_tired = game["away_back_to_back"] == True

    if home_tired and not away_tired:
        return "Away"
    if away_tired and not home_tired:
        return "Home"
    return None   # both tired or both rested -> no bet


# Readable name -> strategy function (used by backtest() and by app.py)
STRATEGIES = {
    "Always home": pick_home,
    "Always away": pick_away,
    "Always favourite": pick_favourite,
    "Always underdog": pick_underdog,
    "Big favourite (odds under 1.5)": pick_big_favourite,
    "Bet against tired teams": pick_fade_tired,
}


# =============================================================================
# 2. BACKTEST: simulate betting with one strategy on past games
# =============================================================================

def backtest(games, strategy_name, stake=10, start_bankroll=1000):
    """
    Bets `stake` euros on every game the strategy picks, in date order.
    Returns a dictionary with: strategy, bets, wins, win_rate (%), profit,
    roi (%), bankroll_history (list of euros, starting with start_bankroll).
    """
    if strategy_name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    strategy = STRATEGIES[strategy_name]
    games = games.sort_values("date", kind="stable")

    bankroll = start_bankroll
    bankroll_history = [start_bankroll]
    bets = 0
    wins = 0

    for index, game in games.iterrows():
        side = strategy(game)
        if side is None:          # strategy says "no bet" -> skip the game
            continue

        if side == "Home":
            odds = game["home_odds"]
        else:
            odds = game["away_odds"]

        bets += 1
        if game["winner"] == side:
            wins += 1
            bet_profit = stake * (odds - 1)   # e.g. 10 at odds 1.80 -> +8.00
        else:
            bet_profit = -stake               # lost the stake

        bankroll = bankroll + bet_profit
        bankroll_history.append(float(bankroll))

    profit = bankroll - start_bankroll

    # avoid dividing by zero if the strategy never bets (e.g. empty season)
    if bets > 0:
        win_rate = wins / bets * 100
        roi = profit / (bets * stake) * 100
    else:
        win_rate = 0.0
        roi = 0.0

    return {
        "strategy": strategy_name,
        "bets": bets,
        "wins": wins,
        "win_rate": float(win_rate),
        "profit": float(profit),
        "roi": float(roi),
        "bankroll_history": bankroll_history,
    }


def compare_strategies(games, stake=10):
    """Runs backtest() for every strategy and returns one row per strategy."""
    columns = ["strategy", "bets", "wins", "win_rate", "profit", "roi"]
    rows = []
    for name in STRATEGIES:
        result = backtest(games, name, stake=stake)
        rows.append({col: result[col] for col in columns})

    table = pd.DataFrame(rows, columns=columns)
    return table.round(2)


# =============================================================================
# 3. RUN THE ANALYSIS (only when this file is run directly)
# =============================================================================

if __name__ == "__main__":
    os.makedirs("charts", exist_ok=True)

    # ---- Table: all strategies -------------------------------------------
    table = compare_strategies(regular)
    print("Betting 10 euros on every game the strategy picks (regular season):\n")
    print(table.to_string(index=False))

    # ---- Chart 1: ROI % per strategy -------------------------------------
    colors = ["green" if roi > 0 else "red" for roi in table["roi"]]
    plt.figure(figsize=(10, 5))
    plt.bar(table["strategy"], table["roi"], color=colors)
    plt.axhline(0, color="black", linewidth=1)
    plt.title("ROI % per betting strategy (10 euros per bet)")
    plt.ylabel("ROI %")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig("charts/part4_strategy_roi.png", dpi=150)
    plt.show()

    # ---- Chart 2: bankroll over time -------------------------------------
    plt.figure(figsize=(10, 5))
    for name in ["Always favourite", "Always underdog"]:
        result = backtest(regular, name)
        plt.plot(result["bankroll_history"], label=name)
    plt.axhline(1000, color="grey", linestyle="--", label="Start (1,000 euros)")
    plt.axhline(0, color="red", linestyle=":", label="0 euros (broke)")
    plt.title("Bankroll after each bet (start 1,000 euros, 10 euros per bet)")
    plt.xlabel("Number of bets")
    plt.ylabel("Bankroll (euros)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("charts/part4_bankroll.png", dpi=150)
    plt.show()

    # ---- Hand check: "Always favourite" on the first 5 games --------------
    # HOW THE CHECK WORKS:
    # We take the first 5 games by date and do the maths ourselves, game by game:
    #   - find the favourite (the side with home_is_favourite) and its decimal odds
    #   - if the favourite won:  profit = 10 * (odds - 1)   e.g. odds 1.50 -> +5.00
    #   - if it lost:            profit = -10
    # Then we add the 5 profits and compare with backtest() on the same 5 games.
    # If both totals are equal, backtest() is calculating correctly.
    #
    # RESULT WITH OUR DATA (American odds -> decimal odds -> profit of 10 euros):
    #   1) 2015-10-27 Hawks (-320 -> 1.31) vs Pistons: Hawks lost       -> -10.00
    #   2) 2015-10-27 Bulls (-180 -> 1.56) vs Cavaliers: Bulls won      -> 10*(1.56-1) = +5.56
    #   3) 2015-10-27 Warriors (-710 -> 1.14) vs Pelicans: Warriors won -> 10*(1.14-1) = +1.41
    #   4) 2015-10-28 Celtics (-1300 -> 1.08) vs 76ers: Celtics won     -> 10*(1.08-1) = +0.77
    #   5) 2015-10-28 Nets vs Bulls (away, -205 -> 1.49): Bulls won     -> 10*(1.49-1) = +4.88
    #   Hand total = -10.00 + 5.56 + 1.41 + 0.77 + 4.88 = +2.61 euros
    #   backtest() on the same 5 games = +2.61 euros -> they match.
    #   Note: the favourite won 4 of 5, but one loss (-10) almost cancels the
    #   4 small wins. That is why betting favourites loses money in the long run.
    first5 = regular.sort_values("date", kind="stable").head(5)
    print("\nHand check - 'Always favourite' on the first 5 games:")
    hand_total = 0
    for index, game in first5.iterrows():
        side = pick_favourite(game)
        if side == "Home":
            odds = game["home_odds"]
        else:
            odds = game["away_odds"]

        if game["winner"] == side:
            bet_profit = 10 * (odds - 1)
            outcome = "won "
        else:
            bet_profit = -10
            outcome = "lost"
        hand_total += bet_profit
        print(f"  {str(game['date'])[:10]}  bet {side:<4} at {odds:.2f} -> "
              f"{outcome}  {bet_profit:+.2f} euros")

    auto_total = backtest(first5, "Always favourite")["profit"]
    print(f"  Hand total: {hand_total:+.2f} euros | backtest(): {auto_total:+.2f} euros")
    print("  OK, they match." if round(hand_total, 2) == round(auto_total, 2)
          else "  WARNING: they do not match!")
