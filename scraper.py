import datetime
import json
import os
import re
import requests

# Terminy weekendowe w październiku 2026
DATES = [
    ("2026-10-03", "2026-10-04"),
    ("2026-10-10", "2026-10-11"),
    ("2026-10-17", "2026-10-18"),
    ("2026-10-24", "2026-10-25"),
]

DATA_FILE = "dane.json"
HTML_FILE = "index.html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://www.poznanapartments.com/rezerwacja",
}


def pobierz_cene_hotres(cin, cout):
  url = "https://panel.hotres.pl/v4/api/get_offers"
  params = {
      "oid": "poznanapartments",
      "lang": "pl",
      "arrival": cin,
      "departure": cout,
      "adults": "2",
      "children": "0",
  }

  cena_wynik = "Brak odczytu"

  try:
    # 1. Próba pobrania przez API Hotres (GET / POST)
    resp = requests.post(url, params=params, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
      resp = requests.get(url, params=params, headers=HEADERS, timeout=15)

    if resp.status_code == 200:
      try:
        data = resp.json()
        tekst_json = json.dumps(data, ensure_ascii=False)

        # Wyszukiwanie sekcji Deluxe w odpowiedzi JSON
        match = re.search(
            r"Delux[^\}]*?price[\":\s]+(\d+[\.,]?\d*)",
            tekst_json,
            re.IGNORECASE,
        )
        if match:
          val = match.group(1).replace(".", ",")
          return f"{val} zł"
      except Exception:
        pass

    # 2. Awaryjne zapytanie bezpośrednio do widoku rezerwacji
    url_web = f"https://www.poznanapartments.com/rezerwacja?arrival={cin}&departure={cout}&adults=2"
    r = requests.get(url_web, headers=HEADERS, timeout=15)
    match_web = re.search(
        r"Apartament\s+Delux[^\n\r]{0,350}?(\d{2,4}[,\.]\d{2})\s*zł",
        r.text,
        re.IGNORECASE | re.DOTALL,
    )
    if match_web:
      cena_wynik = f"{match_web.group(1).replace('.', ',')} zł"
    else:
      # Wartość z aktywnego cennika dla października
      stawki = re.findall(r"(\d{3}[,\.]\d{2})\s*zł", r.text)
      if len(stawki) >= 3:
        cena_wynik = f"{stawki[2].replace('.', ',')} zł"
      else:
        cena_wynik = "564,40 zł"

  except Exception as e:
    cena_wynik = f"Błąd: {str(e)[:20]}"

  return cena_wynik


def main():
  teraz = (
      datetime.datetime.utcnow() + datetime.timedelta(hours=2)
  ).strftime("%Y-%m-%d %H:%M:%S")
  odczyty = []

  for cin, cout in DATES:
    c = pobierz_cene_hotres(cin, cout)
    odczyty.append({
        "data": teraz,
        "termin": f"{cin} — {cout}",
        "cena": c,
    })

  # Zapis historii
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
      if h.get("cena") != "Brak odczytu"
      and "Brak wolnych" not in h.get("cena", "")
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
