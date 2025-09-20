import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone
import glob, re, os, math
import shutil
from matplotlib.ticker import MultipleLocator, MaxNLocator

DATA_DIR = "./data"
OUT_DIR = "./output"
EXCLUDE_OPEN = True  

if os.path.exists(OUT_DIR):
    shutil.rmtree(OUT_DIR)
os.makedirs(OUT_DIR, exist_ok=True)
files = sorted(glob.glob(f"{DATA_DIR}/**/ncaaf_spreads_*.csv", recursive=True))
rows = []
for f in files:
    m = re.search(r"ncaaf_spreads_(\d{8})_(\d{4})", f)
    if not m: 
        continue
    dt_utc = datetime.strptime(m.group(1)+m.group(2), "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
    try:
        df = pd.read_csv(f, low_memory=False)
    except Exception:
        continue
    if "Matchup" not in df.columns:
        continue
    df["__matchup__"] = df["Matchup"].astype(str).str.strip().replace(r"\s+", " ", regex=True)
    books = [c for c in df.columns if c not in ["Matchup", "__matchup__"]]
    if not books:
        continue
    for _, r in df.iterrows():
        matchup = r["__matchup__"]
        for col in books:
            raw = str(r.get(col)).strip().lower()
            if raw in ("", "-", "nan", "none"):
                continue
            if "pk" in raw or "pick" in raw:
                val = 0.0
            else:
                mnum = re.search(r"[+-]?\d+(?:\.\d+)?", raw)
                if not mnum:
                    continue
                try:
                    val = float(mnum.group(0))
                except Exception:
                    continue
            if not (-80.0 <= val <= 80.0):
                continue
            
            # Store both team spreads - one positive, one negative
            rows.append({"dt_utc": dt_utc, "matchup": matchup, "book": col.strip(), "team": "Team1", "spread": val})
            rows.append({"dt_utc": dt_utc, "matchup": matchup, "book": col.strip(), "team": "Team2", "spread": -val})
ts = pd.DataFrame(rows)
if ts.empty:
    raise SystemExit("No lines parsed from ./data.")
if EXCLUDE_OPEN:
    ts = ts[~ts["book"].str.contains("open", case=False, na=False)]
# convert to ET (already in EST, so no conversion needed)
# ts["dt"] = pd.to_datetime(ts["dt_utc"], utc=True).dt.tz_convert("America/New_York")
ts["dt"] = pd.to_datetime(ts["dt_utc"], utc=True)  # .dt.tz_convert("America/New_York")
ts.sort_values(["matchup","dt","book"]).to_csv(os.path.join(OUT_DIR, "all_games_by_book_long.csv"), index=False)
games = ts["matchup"].dropna().unique()
for game in sorted(games):
    sub = ts[ts["matchup"] == game]
    if sub.empty:
        continue
    
    # Create separate pivots for each team
    team1_data = sub[sub["team"] == "Team1"]
    team2_data = sub[sub["team"] == "Team2"]
    
    if team1_data.empty or team2_data.empty:
        continue
        
    pivot1 = team1_data.pivot_table(index="dt", columns="book", values="spread", aggfunc="median").sort_index()
    pivot2 = team2_data.pivot_table(index="dt", columns="book", values="spread", aggfunc="median").sort_index()
    
    if pivot1.shape[1] == 0 or pivot2.shape[1] == 0:
        continue
    
    # Additional filtering for insufficient data
    vals1 = pivot1.values[np.isfinite(pivot1.values)]
    vals2 = pivot2.values[np.isfinite(pivot2.values)]
    all_vals = np.concatenate([vals1, vals2])
    
    if len(all_vals) < 2:  # Need at least 2 valid data points
        continue
    if len(pivot1.index) < 2:  # Need at least 2 time points for movement
        continue
        
    ymin = float(np.min(all_vals)); ymax = float(np.max(all_vals))
    
    # # Dynamic y-axis scaling based on data range
    # # start = math.floor(ymin*2)/2 - 0.5
    # # end   = math.ceil(ymax*2)/2 + 0.5
    # # ticks = np.arange(start, end + 0.25, 0.5)
    # data_range = ymax - ymin
    # if data_range <= 2:
    #     tick_step = 0.5
    # elif data_range <= 5:
    #     # tick_step = 1.0
    #     tick_step = 0.5
    # elif data_range <= 10:
    #     # tick_step = 2.0
    #     tick_step = 1.0
    # else:
    #     tick_step = 5.0
    
    # # Add some padding
    # padding = tick_step
    # start = math.floor(ymin/tick_step)*tick_step - padding
    # end = math.ceil(ymax/tick_step)*tick_step + padding
    # ticks = np.arange(start, end + tick_step/2, tick_step)
    
    plt.figure(figsize=(12,6))
    
    # Plot Team1 lines (positive spreads)
    for book in pivot1.columns:
        plt.plot(pivot1.index, pivot1[book], label=f"{book} (Team1)", linestyle='-')
    
    # Plot Team2 lines (negative spreads) 
    for book in pivot2.columns:
        plt.plot(pivot2.index, pivot2[book], label=f"{book} (Team2)", linestyle='--')
    
    plt.title(f"{game} — Spread by Sportsbook")
    plt.xlabel("Time (ET)")
    plt.ylabel("Spread")
    
    # plt.yticks(ticks)
    
    # Smart auto-scaling for sports betting
    ymin = float(np.min(all_vals))
    ymax = float(np.max(all_vals))
    data_range = ymax - ymin

    '''
    Current Smart Auto-Scaling Levels:
    Level 1: Tight Spreads (≤8 points)
    Uses: 0.5-point intervals
    Examples: -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2
    Good for: Pick'em games, close spreads
    Level 2: Wide Spreads (>8 points)
    Uses: Max 12 ticks with smart intervals
    Preferred intervals: 1, 2, 5, or 10 points
    Examples:
    1-point: -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5
    2-point: -6, -4, -2, 0, 2, 4, 6
    5-point: -10, -5, 0, 5, 10
    Good for: Medium to wide spreads
    '''
    
    if data_range <= 8:
        plt.gca().yaxis.set_major_locator(MultipleLocator(0.5)) # Use 0.5 intervals for tight spreads
    else:
        plt.gca().yaxis.set_major_locator(MaxNLocator(nbins=12, steps=[1, 2, 5, 10])) # Use MaxNLocator for wider spreads with max 12 ticks
    
    plt.grid(True, axis="y", alpha=0.3)
    plt.legend(ncol=2, fontsize=8)
    # plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%a %m/%d %H:%M'))  # Mon 01/20 14:30
    # plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%a %m/%d %I:%M %p'))  # Mon 01/20 2:00 PM
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%a %-m/%d %-I:%M %p'))  # Mon 9/20 9:00 AM
    plt.xticks(rotation=45)
    plt.tight_layout()
    slug = re.sub(r"[^A-Za-z0-9]+", "_", game).strip("_")
    out_png = os.path.join(OUT_DIR, f"{slug}.png")
    plt.savefig(out_png, dpi=150)
    plt.close()
print(f"Wrote {len(games)} game plots to {OUT_DIR}")



# import pandas as pd
# import numpy as np
# import matplotlib.pyplot as plt
# import matplotlib.dates as mdates
# from datetime import datetime, timezone
# import glob, re, math
# DATA_DIR = "./data"
# files = sorted(glob.glob(f"{DATA_DIR}/**/ncaaf_spreads_*.csv", recursive=True))
# rows = []
# for f in files:
#     m = re.search(r"ncaaf_spreads_(\d{8})_(\d{4})", f)
#     if not m:
#         continue
#     dt_utc = datetime.strptime(m.group(1)+m.group(2), "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
#     try:
#         df = pd.read_csv(f, low_memory=False)
#     except Exception:
#         continue
#     if "Matchup" not in df.columns:
#         continue
#     mm = df["Matchup"].astype(str).str.lower()
#     mask = (
#         mm.str.contains("florida")
#         & mm.str.contains("miami")
#         & mm.str.contains(" vs ")
#         & ~mm.str.contains("florida state")
#         & ~mm.str.contains(r"miami\s*\(oh|miami-oh|miami ohio")
#     )
#     sub = df[mask]
#     if sub.empty:
#         continue
#     r = sub.iloc[0]
#     for col in df.columns:
#         if col == "Matchup":
#             continue
#         s = str(r.get(col)).strip().lower()
#         if s in ("", "-", "nan", "none"):
#             continue
#         if "pk" in s or "pick" in s:
#             val = 0.0
#         else:
#             mnum = re.search(r"[+-]?\d+(?:\.\d+)?", s)
#             if not mnum:
#                 continue
#             val = float(mnum.group(0))
#         rows.append({"dt_utc": dt_utc, "book": col.strip(), "spread_florida": val})
# ts = pd.DataFrame(rows)
# if ts.empty:
#     raise SystemExit("No Florida vs Miami rows found in ./data.")
# # Optional: exclude openers
# ts = ts[~ts["book"].str.contains("open", case=False, na=False)]
# # convert to ET (already in EST, so no conversion needed)
# # ts["dt"] = pd.to_datetime(ts["dt_utc"], utc=True).dt.tz_convert("America/New_York")
# ts["dt"] = pd.to_datetime(ts["dt_utc"], utc=True)  # .dt.tz_convert("America/New_York")
# pivot = ts.pivot_table(index="dt", columns="book", values="spread_florida", aggfunc="median").sort_index()
# if pivot.empty:
#     raise SystemExit("No lines to plot after filtering.")
# vals = pivot.values[np.isfinite(pivot.values)]
# ymin = float(np.min(vals)); ymax = float(np.max(vals))
# start = math.floor(ymin*2)/2 - 0.5
# end   = math.ceil(ymax*2)/2 + 0.5
# ticks = np.arange(start, end + 0.25, 0.5)
# plt.figure(figsize=(12,6))
# for book in pivot.columns:
#     plt.plot(pivot.index, pivot[book], label=book)
# plt.title("Florida vs Miami — Spread Line Movement by Sportsbook")
# plt.xlabel("Time (ET)")
# plt.ylabel("Spread (Florida)")
# plt.yticks(ticks)
# plt.grid(True, axis="y", alpha=0.3)
# plt.legend(ncol=2, fontsize=8)
# plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%a %m/%d %H:%M'))  # Mon 01/20 14:30
# plt.xticks(rotation=45)
# plt.tight_layout()
# plt.show()
