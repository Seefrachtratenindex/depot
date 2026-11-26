# Depot-Dashboard

Website mit der Entwicklung des Depots, Kurse ca. 15 Min. verzögert (Yahoo Finance).

- `index.html` – die Website (lädt alle 5 Min. neue Daten)
- `data/holdings.json` – Positionen und Stückzahlen (hier ändern)
- `data/portfolio.json` – wird automatisch erzeugt
- `scripts/update.py` – Kursabruf
- `.github/workflows/update.yml` – Zeitplan: werktags alle 15 Min., 08:00–18:59 Uhr (Winterzeit)

## Einrichtung
1. Neues Repository anlegen (Public), Inhalt dieses Ordners per Drag & Drop hochladen (inkl. `.github`, `data`, `scripts`).
2. Settings → Actions → General → Workflow permissions → Read and write permissions.
3. Settings → Pages → Deploy from a branch → main / (root).
4. Actions → „Kurse aktualisieren“ → Run workflow.

Hinweis: Bei einem öffentlichen Repository sind Stückzahlen und Depotwert für jeden mit Link einsehbar.
