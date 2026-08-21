import datetime
import json
import os
import re
from urllib.parse import quote_plus
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


def pobierz_cene_api(cin, cout):
  # Bezpośrednie API Profitroom / Upperbooking dla Poznań Apartments
  target_url = f"https://wis.upperbooking.com/poznanapartments/be-api/booking/offers?checkIn={cin}&checkOut={cout}&occupancy=2"

  if API_KEY:
    proxy_url = f"http://api.scraperapi.com?api_key={API_KEY}&url={quote_plus(target_url)}"
  else:
    proxy_url = target_url

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      ),
      "Accept": "application/json, text/plain, */*",
      "Referer": "https://www.poznanapartments.com/",
  }

  try:
    resp = requests.get(proxy_url, headers=headers, timeout=40)

    # Jeśli dostaniemy prawidłowy JSON
    if resp.status_code == 200:
      try:
        data = resp.json()

        # Przeszukiwanie listy pokoi w odpowiednich strukturach API
        items = (
            data.get("offers", [])
            or data.get("rooms", [])
            or data.get("results", [])
        )
        for item in items:
          nazwa = item.get("name", "") or item.get("roomName", "")
          if "Delux" in nazwa or "Deluxe" in nazwa:
            cena_val = (
                item.get("price")
                or item.get("minPrice")
                or item.get("finalPrice")
            )
            if cena_val:
              return f"{float(cena_val):.2f}".replace(".", ",") + " zł"

        # Parsowanie po tekście, jeśli struktura jest niestandardowa
        tekst_json = json.dumps(data)
        m = re.search(
            r'Delux[^\}]{0,300}?"price":\s*(\d+[\.\,]?\d*)',
            tekst_json,
            re.IGNORECASE,
        )
        if m:
          return f"{float(m.group(1)):.2f}".replace(".", ",") + " zł"
      except Exception:
        pass

    # Metoda zapasowa: odpytanie skryptu z wymuszoną sesją Hotres/Profitroom
    fallback_url = f"https://r.profitroom.com/poznanapartments/booking?check-in={cin}&check-out={cout}&adults=2"
    if API_KEY:
      proxy_fb = f"http://api.scraperapi.com?api_key={API_KEY}&url={quote_plus(fallback_url)}&render=true&wait=5000"
      r_fb = requests.get(proxy_fb, timeout=50)
      m_fb = re.search(
          r"Delux[^\n\r<]{0,400}?(\d{3,4}[,\.]\d{2})\s*zł",
          r_fb.text,
          re.IGNORECASE | re.DOTALL,
      )
      if m_fb:
        return f"{m_fb.group(1).replace('.', ',')} zł"

    return "Brak wolnych"

  except Exception as e:
    return f"Błąd: {str(e)[:15]}"


def main():
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

  # Wczytanie historii
  historia = []
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        historia = json.load(f)
    except:
      historia = []

  # Czyszczenie błędnych logów
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

  # Generowanie tabeli HTML
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
