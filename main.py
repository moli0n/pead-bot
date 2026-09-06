"""
PEAD Bot — Daily pipeline runner.
"""
import os
import sqlite3
from datetime import datetime
import requests
import yfinance as yf

DB_PATH = "pead.db"
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
ALPACA_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE = "https://paper-api.alpaca.markets"

conn = sqlite3.connect(DB_PATH)
conn.execute("""CREATE TABLE IF NOT EXISTS signals (
    ticker TEXT, filing_date DATE, eps_q REAL, eps_q4 REAL,
    sue REAL, sue_percentile REAL, tone_score REAL, tone_label TEXT,
    entry_price REAL, entry_date REAL, status TEXT DEFAULT 'pending'
)""")
conn.execute("""CREATE TABLE IF NOT EXISTS logs (
    run_date DATE, ticker TEXT, action TEXT, message TEXT
)""")
conn.commit()

def log(ticker, action, msg):
    conn.execute("INSERT INTO logs VALUES (?,?,?,?)",
                 (datetime.now().date(), ticker, action, msg))
    conn.commit()

print("=== PEAD Bot ===", datetime.now())

if OPENROUTER_KEY:
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
    payload = {"model": "openrouter/auto",
               "messages": [{"role": "user", "content": "Say 'PEAD bot ready'"}]}
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                          headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            print("OpenRouter: OK")
            log("SYSTEM", "OPENROUTER_TEST", "OK")
        else:
            print(f"OpenRouter: {r.status_code}")
    except Exception as e:
        print(f"OpenRouter failed: {e}")

if ALPACA_KEY and ALPACA_SECRET:
    headers = {"APCA-API-KEY-ID": ALPACA_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET}
    try:
        r = requests.get(f"{ALPACA_BASE}/v2/account", headers=headers, timeout=15)
        if r.status_code == 200:
            acct = r.json()
            print(f"Alpaca: ${float(acct['equity']):.2f}")
            log("SYSTEM", "ALPACA_TEST", f"equity={acct['equity']}")
        else:
            print(f"Alpaca: {r.status_code}")
    except Exception as e:
        print(f"Alpaca failed: {e}")

# === PIPELINE: EDGAR → SUE ===
print("\n=== Pipeline SUE ===")
tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM", "V", "JNJ"]

for ticker in tickers:
    try:
        stock = yf.Ticker(ticker)
        earnings = stock.earnings_dates
        if earnings is None or earnings.empty:
            continue
        eps = stock.quarterly_earnings
        if eps is None or len(eps) < 5:
            continue
        eps_list = eps["Earnings"].dropna().values
        if len(eps_list) < 5:
            continue
        sue = eps_list[-1] - eps_list[-5]
        sue_std = eps_list[-8:].std() if len(eps_list) >= 8 else eps_list.std()
        sue_norm = round(sue / sue_std, 2) if sue_std != 0 else 0
        print(f"{ticker}: SUE={sue_norm}")
        log(ticker, "SUE", f"{sue_norm}")
    except Exception as e:
        print(f"{ticker}: error {e}")

print("\n=== Selesai ===")
conn.close()
