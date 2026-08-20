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


def pobierz_cene_dla_terminu(cin, cout):
  if not API_KEY:
    return "Brak klucza SCRAPER_API_KEY"

  # Bezpośredni URL do podstrony wyliczania ofert w systemie Hotres dla tego obiektu
  target_url = f"https://panel.hotres.pl/v4_step1?oid=3292&lang=pl&arrival={cin}&departure={cout}&adults=2"
  proxy_url = f"http://api.scraperapi.com?api_key={API_KEY}&url={quote_plus(target_url)}&render=true&country_code=pl"

  try:
    resp = requests.get(proxy_url, timeout=60)
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # 1. Szukanie w kontenerze z Apartamentem Delux
    for element in soup.find_all(["div", "article", "section", "li", "tr"]):
      tekst_bloku = element.get_text(separator=" ")
      if "Apartament Delux" in tekst_bloku or "Delux z 1 sypialnią" in tekst_bloku:
        # Kwoty jednostkowe (od 300 zł do 1999 zł)
        kwoty = re.findall(r"(\d{3,4}[,\.]\d{2})\s*zł", tekst_bloku)
        if kwoty:
          return f"{kwoty[-1].replace('.', ',')} zł"

    # 2. Bezpośredni regex na cały kod
    m = re.search(
        r"Apartament\s+Delux[^\n\r<]{0,350}?(\d{3,4}[,\.]\d{2})\s*zł",
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
      return f"{m.group(1).replace('.', ',')} zł"

    # 3. Jeśli silnik zwrócił kafelki w standardowej kolejności (Studio, Standard, Comfort, Delux)
    wszystkie = re.findall(r"(\d{3,4}[,\.]\d{2})\s*zł", soup.get_text())
    unikalne = []
    for k in wszystkie:
      k_pl = k.replace(".", ",")
      if k_pl not in unikalne and float(k_pl.replace(",", ".")) < 2500:
        unikalne.append(k_pl)

    if len(unikalne) >= 4:
      return f"{unikalne[3]} zł"
    elif unikalne:
      return f"{unikalne[-1]} zł"

    return "Brak wolnych"

  except Exception as e:
    return f"Błąd: {str(e)[:20]}"


def main():
  teraz = (
      datetime.datetime.utcnow() + datetime.timedelta(hours=2)
  ).strftime("%Y-%m-%d %H:%M:%S")
  odczyty = []

  for cin, cout in DATES:
    cena = pobierz_cene_dla_terminu(cin, cout)
    odczyty.append({
        "data": teraz,
        "termin": f"{cin} — {cout}",
        "cena": cena,
    })

  # Wczytanie i oczyszczenie historii
  historia = []
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        historia = json.load(f)
    except:
      historia = []

  # Usunięcie starych, błędnych logów
  historia = [
      h
      for h in historia
      if h.get("cena")
      not in ["Brak odczytu", "Brak wolnych", "600 zł", "4090,20 zł"]
  ]

  for o in reversed(odczyty):
    historia.insert(0, o)

  historia = historia[:40]

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(historia, f, ensure_ascii=False, indent=2)

  # Generowanie widoku HTML
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
