#!/usr/bin/env python3
"""
Market Divergence Dashboard — Data Fetcher
Pulls: S&P 500, XLE, UMich Sentiment, WTI Crude, Treasuries, Debt, JPY, M2, HY Spread, TIC
All free, no API key required. Runs locally and on GitHub Actions.
"""

import json, urllib.request, datetime, os, time, re

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT_DIR, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
YEARS = 5
CUTOFF = (datetime.datetime.now() - datetime.timedelta(days=365*YEARS)).strftime("%Y-%m-%d")

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8")

def yahoo_monthly(symbol):
    end = int(datetime.datetime.now().timestamp())
    start = int((datetime.datetime.now() - datetime.timedelta(days=365*YEARS)).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?interval=1mo&period1={start}&period2={end}&includeAdjustedClose=true")
    data = json.loads(fetch(url))
    result = data["chart"]["result"][0]
    ts = result["timestamp"]
    closes = result["indicators"]["adjclose"][0]["adjclose"]
    out = []
    for t, p in zip(ts, closes):
        if p is None: continue
        out.append({"date": datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d"), "value": round(p, 2)})
    return out

def fred(sid):
    raw = fetch(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}")
    out = []
    for line in raw.strip().split("\n")[1:]:
        parts = line.split(",")
        if len(parts) < 2: continue
        date, val = parts[0].strip(), parts[1].strip()
        if val in ("", ".", "NA") or date < CUTOFF: continue
        out.append({"date": date, "value": round(float(val), 4)})
    return out

def to_monthly(series):
    m = {}
    for d in series:
        m[d["date"][:7]] = d["value"]
    return [{"date": k+"-01", "value": v} for k, v in sorted(m.items())]

def norm(s):
    if not s: return s
    base = s[0]["value"]
    return [{"date": d["date"], "value": round(d["value"]/base*100, 2)} for d in s]

def tic_holdings():
    raw = fetch("https://ticdata.treasury.gov/Publish/mfh.txt").encode("latin-1").decode("latin-1")
    lines = raw.strip().split("\n")
    all_months = re.findall(r"[A-Z][a-z]{2}", lines[5])
    all_years  = re.findall(r"\d{4}", lines[6])
    dates = [f"{m} {y}" for m, y in zip(all_months, all_years)][::-1]
    holdings = {}
    for row in lines[9:32]:
        row = row.rstrip()
        if not row.strip(): continue
        country = re.sub(r"\s+\d\s*$", "", row[:33]).strip()
        vals = re.findall(r"\d[\d]*\.\d+", row[32:])
        if country.startswith("Japan") and vals and float(vals[0]) < 500:
            vals[0] = "1" + vals[0]
        if country and vals:
            holdings[country] = [float(v) for v in vals[:len(dates)]][::-1]
    top8 = ["Japan","China, Mainland","United Kingdom","Belgium","Luxembourg","Switzerland","Canada","Ireland"]
    return {
        "dates": dates,
        "holdings": {c: holdings[c] for c in top8 if c in holdings},
        "snapshot": {c: holdings[c][-1] for c in top8 if c in holdings}
    }

print("Fetching S&P 500..."); sp500 = yahoo_monthly("^GSPC"); time.sleep(1)
print(f"  {len(sp500)} months")
print("Fetching XLE..."); xle = yahoo_monthly("XLE"); time.sleep(1)
print(f"  {len(xle)} months")

print("Fetching FRED series...")
umich   = fred("UMCSENT");   time.sleep(0.3)
wti_d   = fred("DCOILWTICO"); time.sleep(0.3)
dgs3mo  = fred("DGS3MO");    time.sleep(0.3)
dgs2    = fred("DGS2");      time.sleep(0.3)
dgs10   = fred("DGS10");     time.sleep(0.3)
dgs30   = fred("DGS30");     time.sleep(0.3)
dff     = fred("DFF");       time.sleep(0.3)
dtb3    = fred("DTB3");      time.sleep(0.3)
jpy     = fred("DEXJPUS");   time.sleep(0.3)
m2      = fred("M2SL");      time.sleep(0.3)
hy      = fred("BAMLH0A0HYM2"); time.sleep(0.3)
debt_q  = fred("GFDEBTN");   time.sleep(0.3)
gdp     = fred("GDPC1");     time.sleep(0.3)
boj     = fred("IR3TIB01JPM156N"); time.sleep(0.3)

print("Fetching TIC holdings...")
try:
    tic = tic_holdings()
    print(f"  {len(tic['holdings'])} countries")
except Exception as e:
    print(f"  TIC failed: {e}")
    tic = {"dates": [], "holdings": {}, "snapshot": {}}

wti = to_monthly(wti_d)
debt_all = [{"date": d["date"], "value": round(d["value"]/1e6, 3)} for d in fred("GFDEBTN") if d["value"]]

out = {
    "generated": datetime.datetime.now().isoformat(),
    "series": {
        "sp500": sp500, "sp500_idx": norm(sp500),
        "xle": xle,     "xle_idx":   norm(xle),
        "umich": umich, "umich_idx": norm(umich),
        "wti": wti,     "wti_idx":   norm(wti),
        "dgs3mo": to_monthly(dgs3mo),
        "dgs2":   to_monthly(dgs2),
        "dgs10":  to_monthly(dgs10),
        "dgs30":  to_monthly(dgs30),
        "fed_funds": to_monthly(dff),
        "tbill_3mo": to_monthly(dtb3),
        "jpy":  to_monthly(jpy),
        "boj_rate": to_monthly(boj),
        "m2":   m2,
        "hy":   to_monthly(hy),
        "debt": debt_q,
        "gdp":  gdp,
        "total_debt": [{"date": d["date"], "value": round(d["value"]/1e6, 3)}
                       for d in fred("GFDEBTN")],
        "tic_dates":    tic["dates"],
        "tic_holdings": tic["holdings"],
        "tic_snapshot": tic["snapshot"],
    },
    "debt_breakdown": {
        "labels": ["T-Bills\n<1yr", "T-Notes\n2-10yr", "T-Bonds\n>10yr", "TIPS", "FRNs"],
        "values": [5800, 14700, 4500, 2000, 600],
        "colors": ["#58a6ff","#fbbf24","#f85149","#3fb950","#a371f7"]
    }
}

path = os.path.join(OUT_DIR, "market_divergence.json")
with open(path, "w") as f:
    json.dump(out, f)
print(f"\nSaved {path}")
print(f"SP500:{len(sp500)} XLE:{len(xle)} UMich:{len(umich)} WTI:{len(wti)} JPY:{len(to_monthly(jpy))} HY:{len(to_monthly(hy))}")
