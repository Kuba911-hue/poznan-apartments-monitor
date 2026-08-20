import datetime
import json
import os
import re
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import requests

API_KEY = os.environ.get("SCRAPER_API_KEY")

# 4 weekendy w październiku 2026
DATES = [
    ("2026-10-03", "2026-10-04"),
    ("2026-10-10", "2026-10-11"),
    ("2026-10-17", "2026-10-18"),
    ("2026-10-24", "2026-10-25"),
]

DATA_FILE = "dane.json"
HTML_FILE = "index.html"


def pobierz_cene(cin, cout):
  # Format daty dla Hotres (YYYY-MM-DD oraz DD-MM-YYYY)
  d_cin = datetime.datetime.strptime(cin, "%Y-%m-%d").strftime("%d-%m-%Y")
  d_cout = datetime.datetime.strptime(cout, "%Y-%m-%d").strftime("%d-%m-%Y")

  # Bezpośredni URL do silnika rezerwacji Hotres z poprawnymi parametrami
  target_url = f"https://panel.hotres.pl/v4_step1?oid=3292&lang=pl&arrival={cin}&departure={cout}&adults=2&from={d_cin}&to={d_cout}"

  if API_KEY:
    proxy_url = f"http://api.scraperapi.com?api_key={API_KEY}&url={quote_plus(target_url)}&render=true&country_code=pl"
  else:
    proxy_url = target_url

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/124.0.0.0 Safari/537.36"
      ),
      "Accept-Language": "pl-PL,pl;q=0.9",
  }

  try:
    resp = requests.get(proxy_url, headers=headers, timeout=60)
    html_text = resp.text
    soup = BeautifulSoup(html_text, "html.parser")

    # 1. Szukanie w kontenerze z Apartamentem Delux
    for el in soup.find_all(["div", "article", "section", "li", "tr"]):
      t = el.get_text(separator=" ")
      if "Apartament Delux" in t or "Delux z 1 sypialnią" in t:
        kwoty = re.findall(r"(\d{3,4}[,\.]\d{2})\s*zł", t)
        if kwoty:
          return f"{kwoty[-1].replace('.', ',')} zł"

    # 2. Szukanie wyrażeniem regularnym w całym kodzie
    m = re.search(
        r"Apartament\s+Delux[^\n\r<]{0,350}?(\d{3,4}[,\.]\d{2})\s*zł",
        html_text,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
      return f"{m.group(1).replace('.', ',')} zł"

    # 3. Jeśli są kafelki w standardowym układzie: Studio, Standard, Comfort, Delux
    wszystkie = re.findall(r"(\d{3,4}[,\.]\d{2})\s*zł", soup.get_text())
    unikalne = []
    for k in wszystkie:
      k_norm = k.replace(".", ",")
      if k_norm not in unikalne and float(k_norm.replace(",", ".")) < 2500:
        unikalne.append(k_norm)

    if len(unikalne) >= 4:
      return f"{unikalne[3]} zł"
    elif unikalne:
      return f"{unikalne[-1]} zł"

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

  # Usunięcie wszystkich dotychczasowych błędnych wpisów
  historia = [
      h
      for h in historia
      if h.get("cena")
      not in [
          "Brak wolnych",
          "Brak odczytu",
          "600 zł",
          "4090,20 zł",
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
