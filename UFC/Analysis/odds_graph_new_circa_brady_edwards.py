import pandas as pd
import matplotlib.pyplot as plt

# Load your CSV file
df = pd.read_csv("data/ufc_odds_movements.csv")

# Filter to only Sean Brady vs Leon Edwards at Circa
fight = "Sean Brady vs  Leon Edwards"
df = df[df['matchup'] == fight]
df = df[df['sportsbook'] == 'Circa'].copy()

# Function to split odds strings like "-170 | +150"
def parse_moneyline(odds_str):
    try:
        left, right = odds_str.split('|')
        return float(left.strip().replace('+', '')), float(right.strip().replace('+', ''))
    except:
        return None, None

# Parse before and after odds into separate columns
df[['brady_before', 'edwards_before']] = df.apply(lambda row: parse_moneyline(row['odds_before']), axis=1, result_type='expand')
df[['brady_after', 'edwards_after']] = df.apply(lambda row: parse_moneyline(row['odds_after']), axis=1, result_type='expand')

# Drop rows with missing values
df = df.dropna(subset=['brady_before', 'brady_after', 'edwards_before', 'edwards_after'])

# Select the first valid row (most recent or earliest)
row = df.iloc[0]

# Print the values
print("📊 Circa Odds for Sean Brady vs Leon Edwards")
print(f"Sean Brady:  Before = {row['brady_before']}, After = {row['brady_after']}")
print(f"Leon Edwards: Before = {row['edwards_before']}, After = {row['edwards_after']}")

# Plotting the odds movement
plt.figure(figsize=(10, 6))
plt.plot(['Before', 'After'], [row['brady_before'], row['brady_after']], label='Sean Brady', marker='o')
plt.plot(['Before', 'After'], [row['edwards_before'], row['edwards_after']], label='Leon Edwards', marker='x')
plt.title('Circa Odds Movement: Sean Brady vs Leon Edwards')
plt.ylabel('Odds (Moneyline)')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
