import datetime
import json
import os
import re
import requests

API_KEY = os.environ.get("SCRAPER_API_KEY")

DATES = [
    ("2026-10-03", "2026-10-04"),
    ("2026-10-10", "2026-10-11"),
    ("2026-10-17", "2026-10-18"),
    ("2026-10-24", "2026-10-25"),
]

DATA_FILE = "dane.json"
HTML_FILE = "index.html"


def pobierz_cene(cin, cout):
  # Bezpośrednie odpytanie Profitroom REST API
  url = f"https://r.profitroom.com/poznanapartments/booking?check-in={cin}&check-out={cout}&adults=2&lang=pl"

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
      ),
      "Accept": (
          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
      ),
      "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8",
  }

  try:
    # 1. Próba bezpośredniego połączenia ze stabilnym timeoutem
    resp = requests.get(url, headers=headers, timeout=15)
    tekst = resp.text

    # Szukanie ceny w kodzie odpowiedzi
    if "Delux" in tekst or "Deluxe" in tekst:
      m = re.search(
          r"Delux[^\n\r<]{0,450}?(\d{3,4}[,\.]\d{2})\s*zł",
          tekst,
          re.IGNORECASE | re.DOTALL,
      )
      if m:
        return f"{m.group(1).replace('.', ',')} zł"

    # 2. Zapasowy odczyt wzorca cenowego z odpowiedzi
    kwoty = re.findall(r"(\d{3,4}[,\.]\d{2})\s*zł", tekst)
    if kwoty:
      # Pomiń nieprawdopodobnie wysokie stawkowe wartości
      poprawne = [
          k.replace(".", ",")
          for k, in kwoty
          if float(k.replace(",", ".")) < 2500
      ]
      if poprawne:
        return f"{poprawne[0]} zł"

    return "Brak wolnych"

  except Exception:
    return "Błąd połączenia"


def main():
  teraz = (
      datetime.datetime.utcnow() + datetime.timedelta(hours=2)
  ).strftime("%Y-%m-%d %H:%M:%S")
  odczyty = []

  for cin, cout in DATES:
    c = pobierz_cene(cin, cout)
    odczyty.append({
        "data": teraz,
        "termin": f"{cin} — {cout}",
        "cena": c,
    })

  # Historia odczytów
  historia = []
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        historia = json.load(f)
    except Exception:
      historia = []

  # Odfiltrowanie błędów z tabeli
  historia = [
      h
      for h in historia
      if "Błąd" not in h.get("cena", "")
      and h.get("cena") not in ["Oczekiwanie na oferty (pusty widget)"]
  ]

  for o in reversed(odczyty):
    historia.insert(0, o)

  historia = historia[:40]

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(historia, f, ensure_ascii=False, indent=2)

  # Widok HTML
  wiersze = ""
  for h in historia:
    wiersze += f"""
        <tr>
            <td>{h.get('data')}</td>
            <td>{h.get('termin')}</td>
            <td class="price">{h.get('cena')}</td>
        </tr>"""

  html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <title>Ceny: Apartament Delux</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #e2e8f0; padding: 20px; max-width: 650px; margin: 0 auto; }}
        h2 {{ margin-bottom: 4px; font-size: 1.3rem; color: #fff; }}
        .time {{ color: #94a3b8; font-size: 0.85rem; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px 14px; text-align: left; border-bottom: 1px solid #334155; font-size: 0.9rem; }}
        th {{ background: #111827; color: #94a3b8; font-weight: 600; }}
        .price {{ font-weight: bold; color: #38bdf8; font-size: 1.05rem; }}
    </style>
</head>
<body>
    <h2>Apartament Delux z 1 sypialnią (2 os.)</h2>
    <div class="time">Ostatnie sprawdzenie: <strong>{teraz}</strong></div>
    <table>
        <thead>
            <tr>
                <th>Data sprawdzenia</th>
                <th>Termin</th>
                <th>Cena</th>
            </tr>
        </thead>
        <tbody>
            {wiersze}
        </tbody>
    </table>
</body>
</html>"""

  with open(HTML_FILE, "w", encoding="utf-8") as f:
    f.write(html)


if __name__ == "__main__":
  main()
