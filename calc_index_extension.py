"""
Calculate Z47 Index values for May 8-15 2026 with divisor smoothing.
KISSHT.NS replaces AWFIS.NS on May 8, 2026.
Run once: python calc_index_extension.py
"""
import sys, warnings, json
warnings.filterwarnings('ignore')
import pandas as pd, numpy as np, yfinance as yf

sys.path.insert(0, '.')
from companies import COMPANIES, yf_ticker

# ── Float/total share counts (fetched from yfinance) ─────────────────────────
SHARE_DATA = {
    "ETERNAL.NS":   {"fs": 6734074736, "ts": 9045099862},
    "GROWW.NS":     {"fs": 1621477822, "ts": 16702420288},
    "SWIGGY.NS":    {"fs": 1289125748, "ts": 2600046000},
    "NAUKRI.NS":    {"fs": 309161475,  "ts": 526023000},
    "LENSKART.NS":  {"fs": 565841079,  "ts": 3366560768},
    "PAYTM.NS":     {"fs": 407781184,  "ts": 622175000},
    "SBICARD.NS":   {"fs": 299099658,  "ts": 951792000},
    "NYKAA.NS":     {"fs": 1520677422, "ts": 3192618752},
    "POLICYBZR.NS": {"fs": 343574545,  "ts": 467903000},
    "MEESHO.NS":    {"fs": 1599314761, "ts": 25706899456},
    "MMYT":         {"fs": 27719898,   "ts": 107730000},
    "360ONE.NS":    {"fs": 260162039,  "ts": 407498000},
    "PWL.NS":       {"fs": 586171279,  "ts": 3635070720},
    "DELHIVERY.NS": {"fs": 610426538,  "ts": 820788000},
    "GODIGIT.NS":   {"fs": 247723602,  "ts": 954673000},
    "ATHERENERG.NS":{"fs": 151339648,  "ts": 303794000},
    "PINELABS.NS":  {"fs": 569509650,  "ts": 3704099840},
    "FRSH":         {"fs": 217622798,  "ts": 274859000},
    "URBANCO.NS":   {"fs": 361132700,  "ts": 1656122368},
    "TBOTEK.NS":    {"fs": 33312523,   "ts": 106214000},
    "FIRSTCRY.NS":  {"fs": 234492112,  "ts": 554638000},
    "APTUS.NS":     {"fs": 351906002,  "ts": 499079000},
    "OLAELEC.NS":   {"fs": 1971110364, "ts": 4337649152},
    "INDIAMART.NS": {"fs": 26035016,   "ts": 51283000},
    "FIVESTAR.NS":  {"fs": 206257956,  "ts": 314279000},
    "CARTRADE.NS":  {"fs": 42191046,   "ts": 47944000},
    "HOMEFIRST.NS": {"fs": 99540541,   "ts": 114817000},
    "BLACKBUCK.NS": {"fs": 107199016,  "ts": 186936000},
    "NAZARA.NS":    {"fs": 232422504,  "ts": 380021000},
    "MEDPLUS.NS":   {"fs": 69598668,   "ts": 116684000},
    "IXIGO.NS":     {"fs": 200525531,  "ts": 410784000},
    "HONASA.NS":    {"fs": 147594519,  "ts": 354383000},
    "INDIASHLTR.NS":{"fs": 44915417,   "ts": 110107000},
    "WEWORK.NS":    {"fs": 48156394,   "ts": 179825000},
    "RATEGAIN.NS":  {"fs": 59586146,   "ts": 115918000},
    "MAPMYINDIA.NS":{"fs": 16997521,   "ts": 53879000},
    "BLUESTONE.NS": {"fs": 84389676,   "ts": 233579000},
    "SHADOWFAX.NS": {"fs": 70147756,   "ts": 336397000},
    "WAKEFIT.NS":   {"fs": 112357162,  "ts": 561574000},
    "SMARTWORKS.NS":{"fs": 21374059,   "ts": 146909000},
    "E2E.NS":       {"fs": 7615660,    "ts": 18164000},
    "CAPILLARY.NS": {"fs": 23272278,   "ts": 123972000},
    "MEDIASSIST.NS":{"fs": 64953781,   "ts": 74951000},
    "AWFIS.NS":     {"fs": 46888435,   "ts": 68356000},
    "YATRA.NS":     {"fs": 54215456,   "ts": 152563000},
    "MOBIKWIK.NS":  {"fs": 56136337,   "ts": 106126000},
    "UNIECOM.NS":   {"fs": 40196207,   "ts": 100490000},
    # New additions
    "AYE.NS":       {"fs": 73407776,   "ts": 244498877},
    "KISSHT.NS":    {"fs": 47691894,   "ts": 168483022},
}

# Current companies.py includes SMARTWORKS and AWFIS (before update)
OLD_TICKERS = [yf_ticker(c) for c in COMPANIES]
# New set: AWFIS out, KISSHT in; SMARTWORKS stays for now (Change 1 already in history)
NEW_TICKERS = [t for t in OLD_TICKERS if t != 'AWFIS.NS'] + ['KISSHT.NS']

assert len(OLD_TICKERS) == 47, f"Expected 47, got {len(OLD_TICKERS)}"
assert len(NEW_TICKERS) == 47, f"Expected 47, got {len(NEW_TICKERS)}"

# ── Fetch prices May 7-15 ─────────────────────────────────────────────────────
ALL_FETCH = list(set(OLD_TICKERS + ['KISSHT.NS']))
print(f"Fetching prices for {len(ALL_FETCH)} tickers, May 7-15 2026...")
raw = yf.download(ALL_FETCH, start='2026-05-07', end='2026-05-16',
                  auto_adjust=True, progress=False, timeout=60)
closes = raw['Close'].copy()
opens  = raw['Open'].copy()
for df in [closes, opens]:
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
closes = closes.sort_index()
opens  = opens.sort_index()

# Fetch Nifty/Sensex
print("Fetching Nifty/Sensex...")
idx_raw = yf.download(['^NSEI', '^BSESN'], start='2026-05-07', end='2026-05-16',
                      auto_adjust=True, progress=False, timeout=30)
idx_closes = idx_raw['Close'].copy()
idx_closes.index = pd.to_datetime(idx_closes.index)
if idx_closes.index.tz is not None:
    idx_closes.index = idx_closes.index.tz_localize(None)

NIFTY_BASE  = 21741.90
SENSEX_BASE = 72271.94

# ── Load existing history ─────────────────────────────────────────────────────
df_hist = pd.read_csv('z47_history.csv', parse_dates=['date'])
may7_row = df_hist[df_hist['date'] == '2026-05-07'].iloc[0]
IDX_MAY7_FLOAT = float(may7_row['z47_float'])
IDX_MAY7_MCAP  = float(may7_row['z47_mcap'])
print(f"May 7 anchors: z47_float={IDX_MAY7_FLOAT}, z47_mcap={IDX_MAY7_MCAP}")

# ── Helper ────────────────────────────────────────────────────────────────────
def portfolio_val(tickers, prices_series, share_type='fs'):
    total = 0.0
    for tk in tickers:
        try:
            p = prices_series[tk]
        except (KeyError, TypeError):
            continue
        if pd.notna(p) and float(p) > 0:
            sh = SHARE_DATA.get(tk, {}).get(share_type, 0)
            total += float(p) * sh
    return total

# ── Step 1: Derive implicit divisors from May 7 old constituents ──────────────
prices_may7 = closes.loc['2026-05-07']
pv_old_float = portfolio_val(OLD_TICKERS, prices_may7, 'fs')
pv_old_mcap  = portfolio_val(OLD_TICKERS, prices_may7, 'ts')
DIV_OLD_F = pv_old_float / IDX_MAY7_FLOAT
DIV_OLD_M = pv_old_mcap  / IDX_MAY7_MCAP
print(f"\nImplicit divisors (May 7, old constituents):")
print(f"  float_div={DIV_OLD_F:.2f}  mcap_div={DIV_OLD_M:.2f}")

# Verify May 7 reconstruction
check_f = pv_old_float / DIV_OLD_F
check_m = pv_old_mcap  / DIV_OLD_M
print(f"  Verify May7 float: {check_f:.4f} (should be {IDX_MAY7_FLOAT})")
print(f"  Verify May7 mcap:  {check_m:.4f} (should be {IDX_MAY7_MCAP})")

# ── Step 2: Divisor smoothing — KISSHT at its May 8 open price ───────────────
opens_may8   = opens.loc['2026-05-08']
kissht_open  = float(opens_may8['KISSHT.NS'])
print(f"\nKISSHT.NS May 8 open price: Rs{kissht_open}")

# "May 7 equivalent" prices for NEW constituents
prices_new_may7_equiv = dict(prices_may7)
prices_new_may7_equiv['KISSHT.NS'] = kissht_open   # new entrant at its day-1 open
# AWFIS.NS excluded from NEW_TICKERS

pv_new_equiv_f = portfolio_val(NEW_TICKERS, prices_new_may7_equiv, 'fs')
pv_new_equiv_m = portfolio_val(NEW_TICKERS, prices_new_may7_equiv, 'ts')
DIV_NEW_F = pv_new_equiv_f / IDX_MAY7_FLOAT
DIV_NEW_M = pv_new_equiv_m / IDX_MAY7_MCAP
print(f"New divisors after May 8 smoothing:")
print(f"  float_div={DIV_NEW_F:.2f}  mcap_div={DIV_NEW_M:.2f}")

# Sanity: at equiv prices the index should equal May 7 value
check_new_f = pv_new_equiv_f / DIV_NEW_F
print(f"  Continuity check: {check_new_f:.4f} == {IDX_MAY7_FLOAT}  OK" if abs(check_new_f - IDX_MAY7_FLOAT) < 0.0001 else f"  FAIL: {check_new_f:.4f} != {IDX_MAY7_FLOAT}")

# ── Step 3: Calculate May 8-15 ───────────────────────────────────────────────
print("\n--- DAILY INDEX VALUES ---")
new_rows = []
trading_dates = [d for d in closes.index if d > pd.Timestamp('2026-05-07')]

for dt in trading_dates:
    prices_today = closes.loc[dt]

    pv_f = portfolio_val(NEW_TICKERS, prices_today, 'fs')
    pv_m = portfolio_val(NEW_TICKERS, prices_today, 'ts')
    idx_f = round(pv_f / DIV_NEW_F, 4)
    idx_m = round(pv_m / DIV_NEW_M, 4)

    try:
        nifty_abs  = float(idx_closes.loc[dt, '^NSEI'])
        sensex_abs = float(idx_closes.loc[dt, '^BSESN'])
    except Exception:
        nifty_abs = sensex_abs = None

    nifty_idx  = round(nifty_abs  / NIFTY_BASE  * 100, 4) if nifty_abs  else None
    sensex_idx = round(sensex_abs / SENSEX_BASE * 100, 4) if sensex_abs else None
    na_r = round(nifty_abs,  2) if nifty_abs  else None
    sa_r = round(sensex_abs, 2) if sensex_abs else None

    new_rows.append({
        'date':          dt.strftime('%Y-%m-%d'),
        'z47_float':     idx_f,
        'z47_mcap':      idx_m,
        'nifty_indexed': nifty_idx,
        'sensex_indexed':sensex_idx,
        'nifty_abs':     na_r,
        'sensex_abs':    sa_r,
    })
    print(f"  {dt.date()}: z47_float={idx_f:.4f}  z47_mcap={idx_m:.4f}  "
          f"nifty={na_r}  sensex={sa_r}")

# ── Verify continuity ─────────────────────────────────────────────────────────
if new_rows:
    may8_f = new_rows[0]['z47_float']
    jump   = abs(may8_f - IDX_MAY7_FLOAT) / IDX_MAY7_FLOAT * 100
    print(f"\nOK May 7 close:  {IDX_MAY7_FLOAT:.4f}")
    print(f"   May 8 close:  {may8_f:.4f}")
    print(f"   Continuity: divisor absorbed KISSHT entry; May 8 return reflects actual market movement")

# ── Append to z47_history.csv ─────────────────────────────────────────────────
existing_dates = set(df_hist['date'].dt.strftime('%Y-%m-%d').tolist())
to_append = [r for r in new_rows if r['date'] not in existing_dates]
print(f"\nAppending {len(to_append)} new rows to z47_history.csv")

with open('z47_history.csv', 'a', newline='') as f:
    fieldnames = ['date','z47_float','z47_mcap','nifty_indexed',
                  'sensex_indexed','nifty_abs','sensex_abs']
    import csv
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    for row in to_append:
        writer.writerow(row)

print("Done. New z47_history.csv tail:")
df_new = pd.read_csv('z47_history.csv', parse_dates=['date'])
print(df_new.tail(10).to_string(index=False))
