"""
PEAD Bot — Daily pipeline runner.
Jalan otomatis tiap hari lewat GitHub Actions.
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
    entry_price REAL, entry_date DATE, status TEXT DEFAULT 'pending'
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
    payload = {"model": "meta-llama/llama-3.3-70b-instruct:free",
               "messages": [{"role": "user", "content": "Say 'PEAD bot ready'"}]}
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                          headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            msg = r.json()["choices"][0]["message"]["content"]
            print(f"OpenRouter: {msg[:50]}")
            log("SYSTEM", "OPENROUTER_TEST", msg[:50])
        else:
            print(f"OpenRouter error: {r.status_code}")
    except Exception as e:
        print(f"OpenRouter failed: {e}")

if ALPACA_KEY and ALPACA_SECRET:
    headers = {"APCA-API-KEY-ID": ALPACA_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET}
    try:
        r = requests.get(f"{ALPACA_BASE}/v2/account", headers=headers, timeout=15)
        if r.status_code == 200:
            acct = r.json()
            print(f"Alpaca: ${acct['equity']} equity")
            log("SYSTEM", "ALPACA_TEST", f"equity={acct['equity']}")
        else:
            print(f"Alpaca error: {r.status_code}")
    except Exception as e:
        print(f"Alpaca failed: {e}")

spy = yf.download("SPY", period="5d", interval="1d", progress=False)
if not spy.empty:
    print(f"SPY: {spy['Close'].iloc[-1]:.2f}")
    log("SPY", "PRICE", f"{spy['Close'].iloc[-1]:.2f}")

print("=== Done ===")
conn.close()
