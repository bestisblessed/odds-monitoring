import pandas as pd
import matplotlib.pyplot as plt
import re
from matplotlib.backends.backend_pdf import PdfPages
import datetime

# Safe split function for odds columns
def s(x):
    if pd.isna(x): return [None, None]
    p = re.split(r'\s+\|\s+', x)
    if len(p) < 2: p.append(None)
    return p[:2]

# Load CSV data
d = pd.read_csv("data/ufc_odds_movements.csv")

# Extract timestamp from file2 column (format: ufc_odds_vsin_YYYYMMDD_HHMM.json)
def extract_timestamp(filename):
    match = re.search(r'(\d{8})_(\d{4})', filename)
    if match:
        date_str, time_str = match.groups()
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        hour = int(time_str[:2])
        minute = int(time_str[2:4])
        return datetime.datetime(year, month, day, hour, minute)
    return pd.NaT

# Create timestamp from file2
d['ts'] = d['file2'].apply(extract_timestamp)
d = d[d['ts'].notnull()]

# Split matchup into fighter names - safer approach
d['f1'] = d['matchup'].str.split(' vs ').str[0]
d['f2'] = d['matchup'].str.split(' vs ').str[1]
d['f1'] = d['f1'].fillna('Unknown Fighter 1')
d['f2'] = d['f2'].fillna('Unknown Fighter 2')

# Apply safe splitting for odds columns
d[['b1','b2']] = d['odds_before'].apply(s).tolist()
d[['a1','a2']] = d['odds_after'].apply(s).tolist()

# Convert odds columns to numeric
for c in ['b1','b2','a1','a2']:
    d[c] = pd.to_numeric(d[c], errors='coerce')

# Filter only 'Circa' sportsbook data
d = d[d['sportsbook']=='Circa']

# Create PDF for graphs
with PdfPages("UFC_ODDS_MOVEMENT_GRAPHS_CIRCA.pdf") as pdf:
    for _, r in d[['f1','f2']].drop_duplicates().iterrows():
        f = d[(d['f1']==r['f1']) & (d['f2']==r['f2'])].sort_values('ts')
        if f.empty: continue
        plt.figure(figsize=(10,5))
        plt.plot(f['ts'], f['a1'], marker='s', linestyle='-', label=f"{r['f1']} After")
        plt.plot(f['ts'], f['a2'], marker='s', linestyle='-', label=f"{r['f2']} After")
        plt.xlabel("Date")
        plt.ylabel("Odds")
        plt.title(f"Odds Movement: {r['f1']} vs {r['f2']} (Circa)")
        plt.legend()
        plt.grid(True)
        pdf.savefig()
        plt.close()

print("Saved to UFC_ODDS_MOVEMENT_GRAPHS_CIRCA.pdf") 