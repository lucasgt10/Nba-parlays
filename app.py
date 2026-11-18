"""
app.py - Part 6: the application (website)
CAN WE BEAT THE BOOKIES?

A website that puts the whole project together:
  - Next-day parlay : upload the next day's games + odds -> suggested parlay (Part 5)
  - Strategy tester : test one betting strategy on past seasons (Part 4)
  - Compare strategies, past parlays, parlays over a season (Parts 4 and 5)
  - Analysis charts : the charts made by Parts 1-5

How to run (in a terminal, inside the project folder):
    pip install streamlit pandas matplotlib openpyxl
    streamlit run app.py
The website opens in the browser (http://localhost:8501).

Structure of this file:
  1. Imports from the other parts
  2. LOGIC functions  (no Streamlit inside -> easy to test and reuse)
  3. PAGES            (one function per page: buttons, tables, charts)
  4. Main: sidebar menu that chooses the page
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# ---------------------------------------------------------------------------
# 1. IMPORTS FROM THE OTHER PARTS
# ---------------------------------------------------------------------------
# NBA_DATA_PROGRAMING.py : cleaned data ("regular") and the odds conversion function
# backtest.py  (Part 4)  : STRATEGIES, backtest(), compare_strategies()
# parlay.py    (Part 5)  : pick_legs(), parlay_stats(), backtest_parlays()
# All files must be in the same folder as app.py (with NBA_PROGRA.xlsx).
from NBA_DATA_PROGRAMING import regular, americantodecimal
from backtest import STRATEGIES, backtest, compare_strategies
from parlay import pick_legs, parlay_stats, backtest_parlays

FOLDER = os.path.dirname(os.path.abspath(__file__))
CHARTS_FOLDER = os.path.join(FOLDER, "charts")
START_BANKROLL = 1000

# Part 5 calculates away_fair_prob with the same formula as home_fair_prob
# (not 1 - home). We do the same, so the website picks exactly the same legs.
regular["away_fair_prob"] = regular["away_prob"] / (regular["home_prob"] + regular["away_prob"])

KNOWN_TEAMS = sorted(set(regular["home_team"]) | set(regular["away_team"]))
SEASONS = sorted(regular["season"].unique())


# ---------------------------------------------------------------------------
# 2. LOGIC FUNCTIONS
# ---------------------------------------------------------------------------
def filter_season(season):
    """Games of one season, or all games if season == 'All seasons'."""
    if season == "All seasons":
        return regular
    return regular[regular["season"] == season]


def clean_moneyline(column):
    """Same cleaning as NBA_DATA_PROGRAMING.py: '+145 ' -> 145 (number)."""
    text = column.astype(str).str.strip().str.replace("+", "", regex=False)
    return pd.to_numeric(text, errors="coerce")      # wrong values become NaN


def prepare_upcoming_games(raw):
    """
    Turns the uploaded file of next-day games into the same columns that
    pick_legs() (Part 5) needs: home_odds, away_odds, home_prob, away_prob,
    home_fair_prob, away_fair_prob, home_won.
    Returns (games, errors, warnings). If errors is not empty, games is None.
    """
    errors = []
    warnings = []
    games = raw.copy()
    games.columns = [str(c).strip().lower() for c in games.columns]

    # --- required columns ---
    for col in ["date", "home_team", "away_team"]:
        if col not in games.columns:
            errors.append(f"Missing column: '{col}'")

    has_moneylines = "home_moneyline" in games.columns and "away_moneyline" in games.columns
    has_decimal = "home_odds" in games.columns and "away_odds" in games.columns
    if not has_moneylines and not has_decimal:
        errors.append("Missing odds: add 'home_moneyline' and 'away_moneyline' "
                      "(e.g. -150 / +130) or 'home_odds' and 'away_odds' (e.g. 1.67 / 2.30).")
    if errors:
        return None, errors, warnings

    games = games.dropna(how="all")
    games["home_team"] = games["home_team"].astype(str).str.strip()
    games["away_team"] = games["away_team"].astype(str).str.strip()

    # same team-name fixes as the cleaning file
    for side in ["home_team", "away_team"]:
        games[side] = games[side].replace({"Charlotte Bobcats": "Charlotte Hornets",
                                           "LA Clippers": "Los Angeles Clippers"})

    games["date"] = pd.to_datetime(games["date"], errors="coerce")
    if games["date"].isna().any():
        errors.append("Some dates could not be read. Use the format YYYY-MM-DD, e.g. 2026-11-19.")

    # --- odds: American moneylines -> decimal odds (same function as the cleaning file) ---
    if has_moneylines:
        for side in ["home", "away"]:
            line = clean_moneyline(games[side + "_moneyline"])
            if line.isna().any():
                errors.append(f"Some values in '{side}_moneyline' are not numbers.")
            elif (line.abs() < 100).any():
                errors.append(f"'{side}_moneyline' must be +100 or more, or -100 or less "
                              "(American odds between -100 and +100 do not exist).")
            else:
                games[side + "_odds"] = line.apply(americantodecimal)
    else:
        for side in ["home", "away"]:
            odds = pd.to_numeric(games[side + "_odds"], errors="coerce")
            if odds.isna().any() or (odds <= 1).any():
                errors.append(f"'{side}_odds' must be decimal odds above 1.00 (e.g. 1.67).")
            games[side + "_odds"] = odds

    if errors:
        return None, errors, warnings

    # --- same probability columns as the cleaning file / Part 5 ---
    games["home_prob"] = 1 / games["home_odds"]
    games["away_prob"] = 1 / games["away_odds"]
    games["margin"] = games["home_prob"] + games["away_prob"] - 1
    total = games["home_prob"] + games["away_prob"]
    games["home_fair_prob"] = games["home_prob"] / total
    games["away_fair_prob"] = games["away_prob"] / total
    games["home_won"] = False          # the result is not known yet (pick_legs needs the column)

    # --- warnings (the file still works) ---
    unknown = (set(games["home_team"]) | set(games["away_team"])) - set(KNOWN_TEAMS)
    if unknown:
        warnings.append("These team names are not in our dataset (check the spelling): "
                        + ", ".join(sorted(unknown)))
    strange = games[(games["margin"] < 0) | (games["margin"] > 0.10)]
    if len(strange) > 0:
        warnings.append(f"{len(strange)} game(s) have an unusual bookmaker margin "
                        "(below 0% or above 10%). Check those odds.")

    return games.reset_index(drop=True), errors, warnings


def example_file():
    """A template the user can download, fill in and upload (MADE-UP odds)."""
    return pd.DataFrame({
        "date": ["2026-11-19"] * 5,
        "home_team": ["Boston Celtics", "Denver Nuggets", "Miami Heat",
                      "Golden State Warriors", "New York Knicks"],
        "away_team": ["Charlotte Hornets", "Utah Jazz", "Chicago Bulls",
                      "Los Angeles Lakers", "Milwaukee Bucks"],
        "home_moneyline": [-450, -600, -130, -160, 110],
        "away_moneyline": [350, 440, 110, 135, -130],
    })


@st.cache_data(show_spinner="Running the parlay backtest on 10 seasons...")
def historical_parlays(season, n_legs, mode, stake):
    """backtest_parlays() from Part 5. Cached: the same test is only run once."""
    bets, wins, win_rate, profit, roi, history = backtest_parlays(
        filter_season(season), n_legs, mode, stake, START_BANKROLL)
    return {"bets": bets, "wins": wins, "win_rate": win_rate,
            "profit": profit, "roi": roi, "bankroll_history": history}


@st.cache_data(show_spinner="Testing the strategy...")
def run_strategy(strategy_name, season, stake):
    return backtest(filter_season(season), strategy_name, stake=stake,
                    start_bankroll=START_BANKROLL)


@st.cache_data(show_spinner="Testing every strategy...")
def run_compare(season, stake):
    return compare_strategies(filter_season(season), stake=stake)


def bankroll_chart(history, title):
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(history, color="tab:blue")
    ax.axhline(START_BANKROLL, color="grey", linestyle="--", label=f"Start ({START_BANKROLL} euros)")
    ax.set_title(title)
    ax.set_xlabel("Number of bets")
    ax.set_ylabel("Bankroll (euros)")
    ax.legend()
    fig.tight_layout()
    return fig


def roi_chart(table):
    fig, ax = plt.subplots(figsize=(9, 4))
    colours = ["green" if r > 0 else "red" for r in table["roi"]]
    ax.bar(table["strategy"], table["roi"], color=colours)
    ax.axhline(0, color="black", linewidth=1)
    ax.set_title("ROI % per strategy")
    ax.set_ylabel("ROI (%)")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    fig.tight_layout()
    return fig


def legs_table(legs, show_result):
    """Readable version of the legs table returned by pick_legs()."""
    table = pd.DataFrame({
        "Bet on": legs["team"],
        "Against": legs["opponent"],
        "Decimal odds": legs["odds"].round(2),
        "Win chance (%)": (legs["fair_prob"] * 100).round(1),
    })
    if show_result:
        table["Result"] = ["Won" if w else "Lost" for w in legs["won"]]
    return table.reset_index(drop=True)


def show_parlay_numbers(legs, stake):
    combined_odds, combined_prob, expected_value = parlay_stats(legs)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Combined odds", f"{combined_odds:.2f}")
    c2.metric("Chance all legs win", f"{combined_prob * 100:.1f} %")
    c3.metric(f"Profit if it wins ({stake:g} € bet)", f"{stake * (combined_odds - 1):.2f} €")
    c4.metric("Expected value per 1 €", f"{expected_value:+.3f} €")
    return combined_odds, combined_prob, expected_value


def show_result_metrics(result):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bets", f"{result['bets']:,}")
    c2.metric("Win rate", f"{result['win_rate']:.2f} %")
    c3.metric("Profit", f"{result['profit']:,.2f} €")
    c4.metric("ROI", f"{result['roi']:.2f} %")


# ---------------------------------------------------------------------------
# 3. PAGES
# ---------------------------------------------------------------------------
def page_home():
    st.title("🏀 Can we beat the bookies?")
    st.write("We analysed **11,967 NBA regular-season games** (2015-16 to 2024-25) with the "
             "bookmaker's odds, to see if any betting strategy makes money.")

    favourite = run_strategy("Always favourite", "All seasons", 10)
    underdog = run_strategy("Always underdog", "All seasons", 10)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Average bookmaker margin", f"{regular['margin'].mean() * 100:.1f} %")
    c2.metric("Favourite won", f"{regular['favourite_won'].mean() * 100:.1f} %")
    c3.metric("ROI always favourite", f"{favourite['roi']:.2f} %")
    c4.metric("ROI always underdog", f"{underdog['roi']:.2f} %")

    st.subheader("What you can do here")
    st.markdown(
        "- **Next-day parlay**: upload the next day's games and odds, and get the parlay with the "
        "highest chance of winning, plus how that type of parlay did in the past.\n"
        "- **Test a strategy** / **Compare strategies**: bet on past seasons and follow the money.\n"
        "- **Past parlay** / **Parlays over a season**: see how parlays would have done.\n"
        "- **Analysis charts**: the main charts of our study.")
    st.info("Our results: every strategy lost money, because the bookmaker keeps about 4% "
            "of every bet. This site is a study tool, not betting advice.")


def page_next_day():
    st.title("🔮 Next-day parlay")
    st.write("Upload a file with the next day's games and the bookmaker's odds. The site turns the "
             "odds into each team's chance of winning (removing the bookmaker's margin) and uses "
             "our **parlay builder (Part 5)** to choose the legs.")

    with st.expander("What should the file look like?"):
        st.write("A CSV or Excel file with one row per game and these columns "
                 "(team names written as in our dataset, e.g. *Los Angeles Clippers*):")
        st.dataframe(example_file(), hide_index=True)
        st.write("Instead of moneylines you can use decimal odds, in columns "
                 "`home_odds` and `away_odds`. The example odds are made up.")
        st.download_button("Download template (CSV)", example_file().to_csv(index=False),
                           file_name="next_day_games_template.csv", mime="text/csv")

    uploaded = st.file_uploader("Next-day games", type=["csv", "xlsx"])
    if uploaded is None:
        return

    try:
        if uploaded.name.lower().endswith(".csv"):
            raw = pd.read_csv(uploaded)
        else:
            raw = pd.read_excel(uploaded)
    except Exception:
        st.error("The file could not be opened. Is it a real CSV or Excel file?")
        return

    games, errors, warnings = prepare_upcoming_games(raw)
    for message in errors:
        st.error(message)
    if errors:
        return
    for message in warnings:
        st.warning(message)

    # if the file has several dates, the user chooses one (one parlay per day, as in Part 5)
    dates = sorted(games["date"].dt.date.unique())
    if len(dates) > 1:
        day = st.selectbox("Date", dates)
    else:
        day = dates[0]
    day_games = games[games["date"].dt.date == day]

    st.subheader(f"Games on {day} ({len(day_games)})")
    overview = pd.DataFrame({
        "Home": day_games["home_team"],
        "Away": day_games["away_team"],
        "Home odds": day_games["home_odds"].round(2),
        "Away odds": day_games["away_odds"].round(2),
        "Home win chance (%)": (day_games["home_fair_prob"] * 100).round(1),
        "Away win chance (%)": (day_games["away_fair_prob"] * 100).round(1),
        "Margin (%)": (day_games["margin"] * 100).round(1),
    })
    st.dataframe(overview, hide_index=True)

    if len(day_games) < 2:
        st.warning("A parlay needs at least 2 games on the same day.")
        return

    c1, c2, c3 = st.columns(3)
    n_legs = c1.slider("Number of legs", 2, min(5, len(day_games)), min(3, len(day_games)))
    mode = c2.radio("Mode", ["safest", "best value"], horizontal=True,
                    help="safest = the most likely winners. best value = the favourites "
                         "of the games where the bookmaker keeps the least.")
    stake = c3.number_input("Stake (€)", min_value=1.0, max_value=1000.0, value=10.0, step=1.0)

    legs = pick_legs(day_games, n_legs, mode)
    st.subheader("Suggested parlay")
    st.dataframe(legs_table(legs, show_result=False), hide_index=True)
    show_parlay_numbers(legs, stake)

    past = historical_parlays("All seasons", n_legs, mode, stake)
    st.subheader("How this type of parlay did in the past")
    st.write(f"One **{n_legs}-leg {mode}** parlay per day, on every day of the 10 seasons:")
    c1, c2, c3 = st.columns(3)
    c1.metric("Parlays played", f"{past['bets']:,}")
    c2.metric("Won", f"{past['win_rate']:.1f} %")
    c3.metric("ROI", f"{past['roi']:.2f} %")
    st.warning("The win chance comes from the bookmaker's own odds, and the expected value is "
               "negative: on average this bet loses money. In the past, every parlay type lost "
               "more than a single bet (about -4%), because the margin is paid on every leg.")


def page_strategy():
    st.title("📈 Test a strategy")
    c1, c2, c3 = st.columns(3)
    strategy = c1.selectbox("Strategy", list(STRATEGIES.keys()))
    season = c2.selectbox("Season", ["All seasons"] + SEASONS)
    stake = c3.number_input("Stake per bet (€)", 1.0, 1000.0, 10.0, 1.0)

    result = run_strategy(strategy, season, stake)
    if result["bets"] == 0:
        st.warning("This strategy did not place any bet in that season.")
        return
    show_result_metrics(result)
    st.pyplot(bankroll_chart(result["bankroll_history"], f"{strategy} - {season}"))


def page_compare():
    st.title("⚖️ Compare all strategies")
    c1, c2 = st.columns(2)
    season = c1.selectbox("Season", ["All seasons"] + SEASONS)
    stake = c2.number_input("Stake per bet (€)", 1.0, 1000.0, 10.0, 1.0)
    table = run_compare(season, stake)
    st.dataframe(table, hide_index=True)
    st.pyplot(roi_chart(table))


def page_past_parlay():
    st.title("🗓️ Parlay for a past date")
    c1, c2, c3 = st.columns(3)
    day = c1.date_input("Date", value=pd.Timestamp("2024-03-15"),
                        min_value=regular["date"].min(), max_value=regular["date"].max())
    n_legs = c2.slider("Number of legs", 2, 5, 3)
    mode = c3.radio("Mode", ["safest", "best value"], horizontal=True)

    day_games = regular[regular["date"] == pd.Timestamp(day)]
    if len(day_games) == 0:
        st.warning("There were no regular-season games on that date. Try another day.")
        return
    legs = pick_legs(day_games, n_legs, mode)
    if len(legs) == 0:
        st.warning(f"Only {len(day_games)} game(s) that day: not enough for {n_legs} legs.")
        return

    st.dataframe(legs_table(legs, show_result=True), hide_index=True)
    show_parlay_numbers(legs, 10)
    if legs["won"].sum() == n_legs:
        st.success("This parlay would have WON: every leg won.")
    else:
        st.error("This parlay would have LOST: at least one leg lost.")


def page_parlay_season():
    st.title("🎲 Parlays over a season")
    st.write("One parlay every day, chosen by the parlay builder (Part 5).")
    c1, c2, c3, c4 = st.columns(4)
    season = c1.selectbox("Season", ["All seasons"] + SEASONS)
    n_legs = c2.slider("Number of legs", 2, 5, 3)
    mode = c3.radio("Mode", ["safest", "best value"])
    stake = c4.number_input("Stake (€)", 1.0, 1000.0, 10.0, 1.0)

    result = historical_parlays(season, n_legs, mode, stake)
    if result["bets"] == 0:
        st.warning(f"No day in that season had enough games for {n_legs} legs.")
        return
    show_result_metrics(result)
    st.pyplot(bankroll_chart(result["bankroll_history"],
                             f"{n_legs}-leg parlays ({mode}) - {season}"))


def page_charts():
    st.title("📊 Analysis charts")
    charts = [
        ("Part 1 - Bookmaker margin per season", "part1_margin_by_season.png"),
        ("Part 1 - Are the odds accurate?", "part1_calibration.png"),
        ("Part 2 - ROI by odds band", "part2_roi_by_odds_band.png"),
        ("Part 2 - Home win % per season", "part2_home_win_by_season.png"),
        ("Part 3 - Rested vs back-to-back teams", "part3_back_to_back.png"),
        ("Part 4 - ROI per strategy", "part4_strategy_roi.png"),
        ("Part 4 - Bankroll over time", "part4_bankroll.png"),
        ("Part 5 - Parlay ROI by number of legs", "part5_parlay_roi.png"),
    ]
    missing = []
    for title, file in charts:
        path = os.path.join(CHARTS_FOLDER, file)
        if os.path.exists(path):
            st.subheader(title)
            st.image(path)
        else:
            missing.append(file)
    if missing:
        st.info("Some charts are missing. Run the analysis files first "
                "(analysis_margin.py, analysis_teamsdef.py, analysis_fatigue.py, backtest.py, "
                "parlay.py): " + ", ".join(missing))


# ---------------------------------------------------------------------------
# 4. MAIN: the sidebar menu chooses which page to show
# ---------------------------------------------------------------------------
PAGES = {
    "Home": page_home,
    "Next-day parlay": page_next_day,
    "Test a strategy": page_strategy,
    "Compare strategies": page_compare,
    "Parlay for a past date": page_past_parlay,
    "Parlays over a season": page_parlay_season,
    "Analysis charts": page_charts,
}

st.set_page_config(page_title="Can we beat the bookies?", page_icon="🏀", layout="wide")
st.sidebar.title("Can we beat the bookies?")
choice = st.sidebar.radio("Go to", list(PAGES.keys()))
st.sidebar.caption("NBA regular seasons 2015-16 to 2024-25. Study project, not betting advice. "
                   "If gambling stops being fun, ask for help.")
PAGES[choice]()
