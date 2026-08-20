import datetime
import json
import os
import re
import time
from bs4 import BeautifulSoup
import requests

# Lista terminów do monitorowania (weekend po weekendzie)
DATES_TO_CHECK = [
    ("2026-10-03", "2026-10-04"),
    ("2026-10-10", "2026-10-11"),
    ("2026-10-17", "2026-10-18"),
    ("2026-10-24", "2026-10-25"),
]

ADULTS = "2"
DATA_FILE = "dane.json"
HTML_FILE = "index.html"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9",
    "Referer": "https://www.poznanapartments.com/",
}


def sprawdz_cene_dla_terminu(checkin, checkout):
  url = f"https://www.poznanapartments.com/rezerwacja?arrival={checkin}&departure={checkout}&adults={ADULTS}"
  try:
    response = requests.get(url, headers=headers, timeout=25)
    soup = BeautifulSoup(response.text, "html.parser")

    kontenery = soup.find_all(
        lambda tag: tag.name in ["div", "article", "section"]
        and "delux" in tag.get_text().lower()
    )

    znalezione_kwoty = []
    for k in kontenery:
      tekst = k.get_text(separator=" ")
      if "Apartament Delux z 1 sypialnią" in tekst or "Delux" in tekst:
        dopasowania = re.findall(
            r"(\d{2,4}[,\.]\d{2})\s*zł", tekst, flags=re.IGNORECASE
        )
        if dopasowania:
          znalezione_kwoty.extend(dopasowania)

    if znalezione_kwoty:
      unikalne = list(dict.fromkeys(znalezione_kwoty))
      return f"{unikalne[0].replace('.', ',')} zł", url
    else:
      wszystkie = re.findall(r"(\d{3}[,\.]\d{2})\s*zł", soup.get_text())
      if len(wszystkie) >= 2:
        return f"{wszystkie[1].replace('.', ',')} zł", url
      elif wszystkie:
        return f"{wszystkie[0].replace('.', ',')} zł", url
      return "Brak wolnych / Nie znaleziono", url

  except Exception as e:
    return f"Błąd: {str(e)}", url


def main():
  teraz = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  biezace_wyniki = []

  print(f"[{teraz}] Rozpoczynam sprawdzanie terminów w październiku...")

  for checkin, checkout in DATES_TO_CHECK:
    cena, url = sprawdz_cene_dla_terminu(checkin, checkout)
    biezace_wyniki.append({
        "data_odczytu": teraz,
        "termin": f"{checkin} do {checkout}",
        "pokoj": "Apartament Delux z 1 sypialnią",
        "cena": cena,
        "url": url,
    })
    time.sleep(1)  # Krótka pauza między zapytaniami

  # Wczytanie historii
  historia = []
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        historia = json.load(f)
    except Exception:
      historia = []

  # Dodajemy nowe odczyty na początek historii
  for wpis in reversed(biezace_wyniki):
    historia.insert(0, wpis)

  # Zachowujemy maksymalnie 60 ostatnich rekordów w pliku
  historia = historia[:60]

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(historia, f, ensure_ascii=False, indent=2)

  # Generowanie wierszy podsumowania aktualnego
  karty_aktualne = ""
  for w in biezace_wyniki:
    karty_aktualne += f"""
        <div class="summary-card">
            <div class="date-label">📅 {w['termin']}</div>
            <div class="price-val">{w['cena']}</div>
            <a href="{w['url']}" target="_blank" class="book-btn">Rezerwuj</a>
        </div>
        """

  # Generowanie tabeli historii
  wiersze_tabeli = ""
  for h in historia:
    wiersze_tabeli += f"""
        <tr>
            <td style="padding: 12px 14px; border-bottom: 1px solid #334155; color: #94a3b8;">{h.get('data_odczytu', '-')}</td>
            <td style="padding: 12px 14px; border-bottom: 1px solid #334155; font-weight: 500;">{h.get('termin', '-')}</td>
            <td style="padding: 12px 14px; border-bottom: 1px solid #334155; font-weight: 700; color: #38bdf8;">{h.get('cena', '-')}</td>
        </tr>"""

  html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor Cen - Październik 2026</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f1f5f9; padding: 25px 15px; margin: 0; }}
        .container {{ max-width: 850px; margin: 0 auto; }}
        .card {{ background: #1e293b; border-radius: 16px; padding: 24px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5); border: 1px solid #334155; margin-bottom: 24px; }}
        h1 {{ margin: 0 0 6px 0; font-size: 1.5rem; color: #ffffff; }}
        .sub {{ color: #94a3b8; font-size: 0.9rem; margin-bottom: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-top: 15px; }}
        .summary-card {{ background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 16px; text-align: center; }}
        .date-label {{ font-size: 0.85rem; color: #cbd5e1; font-weight: 600; margin-bottom: 8px; }}
        .price-val {{ font-size: 1.25rem; font-weight: 800; color: #38bdf8; margin-bottom: 12px; }}
        .book-btn {{ display: inline-block; background: #0284c7; color: #fff; text-decoration: none; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 500; }}
        .book-btn:hover {{ background: #0369a1; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th {{ background: #0f172a; padding: 12px 14px; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: #cbd5e1; text-align: left; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>Apartament Delux z 1 sypialnią – Październik 2026</h1>
            <div class="sub">Ostatnie automatyczne sprawdzenie: <strong>{teraz}</strong> (2 dorosłych)</div>
            
            <div class="grid">
                {karty_aktualne}
            </div>
        </div>

        <div class="card">
            <h2 style="font-size: 1.15rem; margin-top: 0;">Historia sprawdzania cen</h2>
            <table>
                <thead>
                    <tr>
                        <th>Data odczytu</th>
                        <th>Termin pobytu</th>
                        <th>Wykryta cena</th>
                    </tr>
                </thead>
                <tbody>
                    {wiersze_tabeli}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>"""

  with open(HTML_FILE, "w", encoding="utf-8") as f:
    f.write(html)

  print("Zapisano raport dla wszystkich terminów.")


if __name__ == "__main__":
  main()
