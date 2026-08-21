import datetime
import json
import os
import re
import time
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
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
  if not API_KEY:
    return "Brak SCRAPER_API_KEY"

  docelowy_url = f"https://www.poznanapartments.com/rezerwacja?check-in={cin}&check-out={cout}&adults=2&rooms=1"
  encoded_url = quote_plus(docelowy_url)

  # ScraperAPI z natywnym parametrem wait=9000 (9 sekund na wykonanie JS widgetu)
  proxy_url = f"http://api.scraperapi.com?api_key={API_KEY}&url={encoded_url}&render=true&country_code=pl&wait=9000"

  try:
    resp = requests.get(proxy_url, timeout=90)
    tekst = resp.text

    if resp.status_code != 200:
      return f"Błąd HTTP {resp.status_code}"

    # 1. Szukanie w blokach z Apartamentem Delux
    soup = BeautifulSoup(tekst, "html.parser")
    for el in soup.find_all(["div", "article", "section", "li", "tr"]):
      t = el.get_text(separator=" ")
      if "Delux" in t and "zł" in t:
        kwoty = re.findall(r"(\d{3,4}[,\.]\d{2})\s*zł", t)
        if kwoty:
          return f"{kwoty[-1].replace('.', ',')} zł"

    # 2. Szukanie wyrażeniem regularnym bezpośrednio w kodzie
    m = re.search(
        r"Delux[^\n\r<]{0,450}?(\d{3,4}[,\.]\d{2})\s*zł",
        tekst,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
      return f"{m.group(1).replace('.', ',')} zł"

    # 3. Jeśli są jakiekolwiek wyrenderowane stawki na stronie
    wszystkie = re.findall(r"(\d{3,4}[,\.]\d{2})\s*zł", soup.get_text())
    poprawne = [
        s.replace(".", ",")
        for s in wszystkie
        if float(s.replace(",", ".")) < 2500
    ]
    unikalne = list(dict.fromkeys(poprawne))

    if len(unikalne) >= 5:
      # Pozycja Delux (5. kafelek na liście)
      return f"{unikalne[4]} zł"
    elif unikalne:
      return f"{unikalne[-1]} zł"

    # Jeśli widget nadal nie załadował ofert po 9 sek
    return "Oczekiwanie na oferty (pusty widget)"

  except Exception as e:
    return f"Błąd: {str(e)[:18]}"


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
    time.sleep(2)

  # Historia
  historia = []
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        historia = json.load(f)
    except:
      historia = []

  # Czyścimy nieudane odczyty
  historia = [
      h
      for h in historia
      if h.get("cena")
      not in [
          "Brak wolnych",
          "Brak odczytu",
          "600 zł",
          "4090,20 zł",
          "Oczekiwanie na oferty (pusty widget)",
      ]
      and "Błąd" not in h.get("cena", "")
  ]

  for o in reversed(odczyty):
    historia.insert(0, o)

  historia = historia[:40]

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(historia, f, ensure_ascii=False, indent=2)

  # Czysta tabela HTML
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
