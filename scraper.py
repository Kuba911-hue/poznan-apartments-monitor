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

  # Bezpośredni URL do widgetu silnika rezerwacji
  docelowy_url = f"https://panel.hotres.pl/v4_step1?oid=3292&lang=pl&arrival={cin}&departure={cout}&adults=2"
  encoded_url = quote_plus(docelowy_url)

  # ScraperAPI z renderowaniem JS i polskim IP
  proxy_url = (
      f"http://api.scraperapi.com?api_key={API_KEY}&url={encoded_url}&render=true&country_code=pl"
  )

  try:
    resp = requests.get(proxy_url, timeout=60)
    tekst = resp.text

    # 1. Sprawdzamy czy w kodzie pojawił się Delux
    match_delux = re.search(
        r"Apartament\s+Delux[^\n\r<]{0,400}?(\d{2,4}[,\.]\d{2})\s*zł",
        tekst,
        re.IGNORECASE | re.DOTALL,
    )
    if match_delux:
      return f"{match_delux.group(1).replace('.', ',')} zł"

    # 2. Szukamy kafelków z cenami
    soup = BeautifulSoup(tekst, "html.parser")
    for el in soup.find_all(["div", "article", "section"]):
      t = el.get_text(separator=" ")
      if "Delux" in t and "zł" in t:
        kwoty = re.findall(r"(\d{2,4}[,\.]\d{2})\s*zł", t)
        if kwoty:
          return f"{kwoty[-1].replace('.', ',')} zł"

    # 3. Jeśli są jakiekolwiek stawki wygenerowane przez widget (Studio, Standard, Comfort, Delux)
    wszystkie = re.findall(r"(\d{2,4}[,\.]\d{2})\s*zł", tekst)
    if len(wszystkie) >= 5:
      return f"{wszystkie[4].replace('.', ',')} zł"
    elif wszystkie:
      return f"{wszystkie[-1].replace('.', ',')} zł"

    # 4. Fallback na standardowy link rezerwacji
    url_alt = quote_plus(
        f"https://www.poznanapartments.com/rezerwacja?arrival={cin}&departure={cout}&adults=2"
    )
    resp_alt = requests.get(
        f"http://api.scraperapi.com?api_key={API_KEY}&url={url_alt}&render=true&country_code=pl",
        timeout=60,
    )
    m_alt = re.search(
        r"Delux[^\n\r<]{0,400}?(\d{2,4}[,\.]\d{2})\s*zł",
        resp_alt.text,
        re.IGNORECASE,
    )
    if m_alt:
      return f"{m_alt.group(1).replace('.', ',')} zł"

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
