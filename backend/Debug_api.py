"""
Run this to see what fields and dates the World Bank API actually returns.
    python debug_api.py
"""
import requests, json

API_BASE = "https://search.worldbank.org/api/v2/procnotices"

params = {
    "format":                  "json",
    "rows":                    5,
    "os":                      0,
    "apilang":                 "en",
    "project_ctry_name_exact": "Kenya^Rwanda^Uganda^Tanzania^Ethiopia",
    "srt":                     "pdate",
    "order":                   "desc",
}

resp = requests.get(API_BASE, params=params, timeout=20)
data = resp.json()

raw = data.get("procnotices", {})
items = list(raw.values()) if isinstance(raw, dict) else raw

print(f"Total available: {data.get('total')}\n")

for i, n in enumerate(items[:5]):
    print(f"─── Record {i+1} ───")
    # Print every field that contains a date-like value or is about type/date
    for key, val in n.items():
        if val and any(word in key.lower() for word in ['date', 'type', 'country', 'title', 'id']):
            print(f"  {key}: {str(val)[:80]}")
    print()