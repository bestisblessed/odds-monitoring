import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone
import glob, re, os, math
import shutil

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
            rows.append({"dt_utc": dt_utc, "matchup": matchup, "book": col.strip(), "spread": val})
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
    pivot = sub.pivot_table(index="dt", columns="book", values="spread", aggfunc="median").sort_index()
    if pivot.shape[1] == 0:
        continue
    vals = pivot.values[np.isfinite(pivot.values)]
    ymin = float(np.min(vals)); ymax = float(np.max(vals))
    start = math.floor(ymin*2)/2 - 0.5
    end   = math.ceil(ymax*2)/2 + 0.5
    ticks = np.arange(start, end + 0.25, 0.5)
    plt.figure(figsize=(12,6))
    for book in pivot.columns:
        plt.plot(pivot.index, pivot[book], label=book)
    plt.title(f"{game} — Spread by Sportsbook")
    plt.xlabel("Time (ET)")
    plt.ylabel("Spread")
    plt.yticks(ticks)
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
