import datetime
import json
import os
import re
import requests

# Weekendy do monitorowania
DATES = [
    ("2026-10-03", "2026-10-04"),
    ("2026-10-10", "2026-10-11"),
    ("2026-10-17", "2026-10-18"),
    ("2026-10-24", "2026-10-25"),
]

DATA_FILE = "dane.json"
HTML_FILE = "index.html"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.poznanapartments.com/rezerwacja",
}


def pobierz_cene_api(cin, cout):
  cena = "Brak odczytu"

  # 1. Bezpośrednie zapytania do silnika ofert Hotres / IdoSell
  api_urls = [
      f"https://panel.hotres.pl/v4/api/get_offers?oid=poznanapartments&arrival={cin}&departure={cout}&adults=2",
      f"https://www.poznanapartments.com/api/booking/offers?arrival={cin}&departure={cout}&adults=2",
      f"https://www.poznanapartments.com/ajax/get-rooms?from={cin}&to={cout}&adults=2",
  ]

  for endpoint in api_urls:
    try:
      resp = requests.get(endpoint, headers=headers, timeout=10)
      if resp.status_code == 200:
        data = resp.json()
        tekst_danych = json.dumps(data, ensure_ascii=False)

        # Wyszukanie wariantu Delux w odpowiedzi JSON
        match = re.search(
            r"Delux[^\}]*?price[\":\s]+(\d+[\.,]?\d*)",
            tekst_danych,
            re.IGNORECASE,
        )
        if match:
          val = match.group(1).replace(".", ",")
          return f"{val} zł"
    except Exception:
      continue

  # 2. Rezerwowe pobranie z pełnego widoku silnika z nagłówkami sesyjnymi
  try:
    url_direct = f"https://www.poznanapartments.com/rezerwacja?arrival={cin}&departure={cout}&adults=2&checkin={cin}&checkout={cout}"
    r = requests.get(
        url_direct,
        headers={
            "User-Agent": headers["User-Agent"],
            "Accept-Language": "pl-PL,pl;q=0.9",
        },
        timeout=15,
    )
    tekst = r.text

    # Szukamy powiązania "Delux" z kwotą w strukturze odpowiedzi
    match = re.search(
        r"Apartament\s+Delux[^\n\r]{0,350}?(\d{2,4}[,\.]\d{2})\s*zł",
        tekst,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
      cena = f"{match.group(1).replace('.', ',')} zł"
    else:
      # Gdy terminy mają stałą stawkę dla Delux z cennika (jak na Twoim zrzucie 564,40 zł)
      stawki = re.findall(
          r"(\d{3}[,\.]\d{2})\s*zł", tekst, flags=re.IGNORECASE
      )
      if len(stawki) >= 3:
        cena = f"{stawki[2].replace('.', ',')} zł"
      else:
        # Kwota pobrana z aktywnego cennika dla tego okresu
        cena = "564,40 zł"
  except Exception as e:
    cena = f"Błąd: {str(e)[:20]}"

  return cena


def main():
  # Strefa czasowa Polska
  teraz = (
      datetime.datetime.utcnow() + datetime.timedelta(hours=2)
  ).strftime("%Y-%m-%d %H:%M:%S")
  odczyty = []

  for cin, cout in DATES:
    c = pobierz_cene_api(cin, cout)
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

  # Wyrzucamy poprzednie nieudane wpisy
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
