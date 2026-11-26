"""Holt (verzögerte) Kurse für alle Positionen aus data/holdings.json und schreibt data/portfolio.json.

Läuft über GitHub Actions (.github/workflows/update.yml), nur Python-Standardbibliothek.
Quelle: Yahoo-Finance-Chart-Schnittstelle (inoffiziell, Kurse ca. 15 Min. verzögert).
"""
import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
HOLD = ROOT / "data" / "holdings.json"
OUT = ROOT / "data" / "portfolio.json"
BER = ZoneInfo("Europe/Berlin")
HOSTS = ["https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com"]


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (depot-dashboard)", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def chart(symbol, rng, interval):
    q = urllib.parse.urlencode({"range": rng, "interval": interval, "includePrePost": "false"})
    last = None
    for h in HOSTS:
        try:
            j = get_json(f"{h}/v8/finance/chart/{urllib.parse.quote(symbol)}?{q}")
            res = (j.get("chart") or {}).get("result")
            if res:
                return res[0]
            last = (j.get("chart") or {}).get("error")
        except Exception as e:  # nächster Host
            last = e
        time.sleep(1)
    raise RuntimeError(f"{symbol}: {last}")


def series(res, daily):
    ts = res.get("timestamp") or []
    cl = ((res.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    out = []
    for t, c in zip(ts, cl):
        if c is None:
            continue
        key = dt.datetime.fromtimestamp(t, BER).date().isoformat() if daily else int(t)
        out.append([key, round(float(c), 4)])
    if daily:  # ein Wert je Tag (letzter gewinnt)
        out = list({d: [d, c] for d, c in out}.values())
    return out


def fetch_position(p):
    err = []
    for sym in p["symbols"]:
        try:
            d = chart(sym, "2y", "1d")
            daily = series(d, True)
            if not daily:
                raise RuntimeError("keine Tageskurse")
            m = d.get("meta") or {}
            intr, prev = [], None
            try:
                i = chart(sym, "1d", "5m")
                intr = series(i, False)
                mi = i.get("meta") or {}
                prev = mi.get("chartPreviousClose") or mi.get("previousClose")
                m = {**m, **{k: v for k, v in mi.items() if v is not None}}
            except Exception as e:
                err.append(f"{sym} intraday: {e}")
            price = m.get("regularMarketPrice") or daily[-1][1]
            if prev is None:
                prev = daily[-2][1] if len(daily) > 1 else price
            return {"symbol": sym, "currency": m.get("currency", "EUR"), "price": round(float(price), 4),
                    "prevClose": round(float(prev), 4), "time": m.get("regularMarketTime"),
                    "daily": daily, "intraday": intr}, err
        except Exception as e:
            err.append(f"{sym}: {e}")
            time.sleep(1)
    return None, err


def main():
    hold = json.loads(HOLD.read_text(encoding="utf-8"))
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    old_pos = {p["key"]: p for p in old.get("positions", [])}
    positions, errors, ok, hold_changed = [], [], 0, False

    for p in hold["positions"]:
        data, err = fetch_position(p)
        errors += err
        if data is None:
            if p["key"] in old_pos:  # alten Stand behalten, als veraltet markieren
                q = dict(old_pos[p["key"]]); q["stale"] = True; positions.append(q)
            continue
        ok += 1
        qty = p.get("qty")
        if qty is None and p.get("amount_eur"):  # Stückzahl einmalig aus Betrag berechnen
            ref = [c for d, c in data["daily"] if d <= p["as_of"]]
            ref_price = ref[-1] if ref else data["price"]
            qty = round(p["amount_eur"] / ref_price, 4)
            p["qty"] = qty; p["qty_from"] = f"{p['amount_eur']} EUR / {ref_price} ({p['as_of']})"
            hold_changed = True
        positions.append({"key": p["key"], "name": p["name"], "isin": p["isin"], "qty": qty,
                          "note": p.get("note", ""), "stale": False, **data})

    if hold_changed:
        HOLD.write_text(json.dumps(hold, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = {"updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "source": "Yahoo Finance (verzögert)", "positions": positions, "errors": errors[-20:]}
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{ok}/{len(hold['positions'])} Positionen aktualisiert")
    for e in errors:
        print("Hinweis:", e)
    if ok == 0:
        sys.exit("Keine Position konnte abgerufen werden.")


if __name__ == "__main__":
    main()
