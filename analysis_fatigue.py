# PART 3 - FATIGUE (BACK-TO-BACK GAMES)
# Question: do tired teams lose more, and are the odds already aware of it?

import matplotlib.pyplot as plt
import os
from NBA_DATA_PROGRAMING import regular, teams, STAKE

# 1. Compare rested teams (False) and back-to-back teams (True).
print('\nPART 3: FATIGUE COMPARISON')
print(f"{'Group':<14}{'Team-games':>12}{'Actual win %':>15}{'Expected win %':>17}{'Profit EUR':>13}{'ROI %':>9}")

expected_rates = []
actual_rates = []
for tired in [False, True]:
    group = teams[teams['back_to_back'] == tired]
    bets = len(group)
    actual = group['won'].mean() * 100          # how often they really won
    expected = group['fair_prob'].mean() * 100  # how often the odds said they would win
    profit = group['profit'].sum()              # profit of betting 10 euros on every one
    roi = profit / (bets * STAKE) * 100         # profit as a % of the money bet

    expected_rates.append(expected)
    actual_rates.append(actual)

    if tired:
        name = 'Back-to-back'
    else:
        name = 'Rested'
    print(f"{name:<14}{bets:>12}{actual:>15.2f}{expected:>17.2f}{profit:>13.2f}{roi:>9.2f}")

# 2. Grouped bar chart: expected vs actual win rate.
labels = ['Rested', 'Back-to-back']
x_expected = [0, 2]
x_actual = [0.7, 2.7]

plt.figure(figsize=(8, 5))
plt.bar(x_expected, expected_rates, width=0.65, label='Expected', color='royalblue')
plt.bar(x_actual, actual_rates, width=0.65, label='Actual', color='darkorange')

# Write the value above each bar.
for i in range(2):
    plt.text(x_expected[i], expected_rates[i] + 0.5, str(round(expected_rates[i], 1)) + '%', ha='center')
    plt.text(x_actual[i], actual_rates[i] + 0.5, str(round(actual_rates[i], 1)) + '%', ha='center')

plt.xticks([0.35, 2.35], labels)
plt.ylabel('Win rate (%)')
plt.title('NBA: Rested vs Back-to-back Teams')
plt.ylim(0, 60)
plt.legend()
plt.tight_layout()

# Save the chart in a folder called charts.
os.makedirs('charts', exist_ok=True)
plt.savefig('charts/part3_back_to_back.png')
plt.show()

# 3. Extra: games where exactly ONE team played back-to-back.
one_tired = regular[regular['home_back_to_back'] != regular['away_back_to_back']]

# Games where the home team was rested, and games where the away team was rested.
rested_home = one_tired[one_tired['home_back_to_back'] == False]
rested_away = one_tired[one_tired['away_back_to_back'] == False]

# How many times did the rested team win?
rested_wins = (len(rested_home[rested_home['winner'] == 'Home']) +
               len(rested_away[rested_away['winner'] == 'Away']))
total_games = len(one_tired)

# What did the odds expect for the rested team?
expected_wins = rested_home['home_fair_prob'].sum() + rested_away['away_fair_prob'].sum()

print('\nGAMES WITH ONE RESTED TEAM AND ONE TIRED TEAM')
print('Games:', total_games)
print('Rested team actual win %:  ', round(rested_wins / total_games * 100, 2))
print('Rested team expected win %:', round(expected_wins / total_games * 100, 2))
