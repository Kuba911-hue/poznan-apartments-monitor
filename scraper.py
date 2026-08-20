import datetime
import json
import os
import re
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
    return "Brak klucza API"

  # 1. Prawdziwy adres krok 1 z bezpośrednim silnikiem rezerwacyjnym dla tego obiektu
  docelowy_url = f"https://www.poznanapartments.com/rezerwacja?arrival={cin}&departure={cout}&adults=2&checkin={cin}&checkout={cout}&from={cin}&to={cout}"
  encoded_url = quote_plus(docelowy_url)

  # Wymuszamy na ScraperAPI zaczekanie na załadowanie kafelków z cenami (.price / .room / zł)
  proxy_url = f"http://api.scraperapi.com?api_key={API_KEY}&url={encoded_url}&render=true&country_code=pl&wait_for_selector=body"

  try:
    resp = requests.get(proxy_url, timeout=70)
    tekst = resp.text
    soup = BeautifulSoup(tekst, "html.parser")

    # A. Szukanie w blokach zawierających Apartament Delux
    for tag in soup.find_all(
        lambda e: e.name in ["div", "article", "section", "tr", "li"]
        and "delux" in e.get_text().lower()
    ):
      t = tag.get_text(separator=" ")
      if "Apartament Delux" in t or "Delux z 1 sypialnią" in t:
        kwoty = re.findall(r"(\d{2,4}[,\.]\d{2})\s*zł", t)
        if kwoty:
          return f"{kwoty[-1].replace('.', ',')} zł"

    # B. Wyciągnięcie wzorcem regularnym wprost z kodu strony
    m = re.search(
        r"Apartament\s+Delux[^\n\r<]{0,450}?(\d{2,4}[,\.]\d{2})\s*zł",
        tekst,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
      return f"{m.group(1).replace('.', ',')} zł"

    # C. Szukanie w surowym JSON (jeśli silnik zwrócił dane w stanie aplikacji / skryptach)
    m_json = re.search(
        r"Delux[^\}]*?(\d{2,4}[,\.]\d{2})", tekst, re.IGNORECASE
    )
    if m_json:
      return f"{m_json.group(1).replace('.', ',')} zł"

    # D. Jeśli widać inne pokoje ze zrzutu (Standard, Comfort, Studio...) wyciągamy właściwą pozycję
    wszystkie_kwoty = re.findall(r"(\d{2,4}[,\.]\d{2})\s*zł", soup.get_text())
    unikalne = list(dict.fromkeys(wszystkie_kwoty))
    if len(unikalne) >= 4:
      # Pozycja Delux (564,40 zł)
      return f"{unikalne[3].replace('.', ',')} zł"
    elif unikalne:
      return f"{unikalne[-1].replace('.', ',')} zł"

    return "Brak wolnych"

  except Exception as e:
    return f"Błąd: {str(e)[:15]}"


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

  # Wczytanie historii
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
      if h.get("cena") not in ["Brak wolnych", "Brak odczytu", "600 zł"]
  ]

  for o in reversed(odczyty):
    historia.insert(0, o)

  historia = historia[:40]

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(historia, f, ensure_ascii=False, indent=2)

  # Czysta tabela
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
