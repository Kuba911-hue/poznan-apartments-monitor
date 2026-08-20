import datetime
import json
import os
import re
from playwright.sync_api import sync_playwright
from zoneinfo import ZoneInfo

# Terminy weekendowe
DATES_TO_CHECK = [
    ("2026-10-03", "2026-10-04"),
    ("2026-10-10", "2026-10-11"),
    ("2026-10-17", "2026-10-18"),
    ("2026-10-24", "2026-10-25"),
]

DATA_FILE = "dane.json"
HTML_FILE = "index.html"


def sprawdz_cene(page, checkin, checkout):
  url = f"https://www.poznanapartments.com/rezerwacja?arrival={checkin}&departure={checkout}&adults=2"
  cena_odczyt = "Brak wolnych miejsc"

  try:
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)

    # Odczytujemy tekst całej wyrenderowanej strony
    tresc = page.inner_text("body")

    # Wyszukanie wariantu Delux i jego kwoty
    match = re.search(
        r"Apartament Delux[^\n\r]{0,250}?(\d{2,4}[,\.]\d{2})\s*zł",
        tresc,
        re.IGNORECASE | re.DOTALL,
    )

    if match:
      cena_odczyt = f"{match.group(1).replace('.', ',')} zł"
    else:
      # Alternatywne dopasowanie w tabeli stawek
      wszystkie_stawki = re.findall(
          r"(\d{3}[,\.]\d{2})\s*zł", tresc, flags=re.IGNORECASE
      )
      if len(wszystkie_stawki) >= 2:
        cena_odczyt = f"{wszystkie_stawki[1].replace('.', ',')} zł"
      elif wszystkie_stawki:
        cena_odczyt = f"{wszystkie_stawki[0].replace('.', ',')} zł"

  except Exception as e:
    cena_odczyt = f"Błąd: {str(e)[:30]}"

  return cena_odczyt, url


def main():
  # Aktualny czas w strefie polskiej (UTC+2 / CEST)
  teraz = datetime.datetime.now(ZoneInfo("Europe/Warsaw")).strftime(
      "%Y-%m-%d %H:%M:%S"
  )
  wyniki = []

  with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(locale="pl-PL")
    page = context.new_page()

    for cin, cout in DATES_TO_CHECK:
      cena, url = sprawdz_cene(page, cin, cout)
      wyniki.append({
          "data_odczytu": teraz,
          "termin": f"{cin} do {cout}",
          "pokoj": "Apartament Delux z 1 sypialnią",
          "cena": cena,
          "url": url,
      })

    browser.close()

  # Wczytanie i aktualizacja historii
  historia = []
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        historia = json.load(f)
    except Exception:
      historia = []

  # Czyścimy nieudane odczyty
  historia = [h for h in historia if "Brak wolnych" not in h.get("cena", "")]

  for w in reversed(wyniki):
    historia.insert(0, w)

  historia = historia[:50]

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(historia, f, ensure_ascii=False, indent=2)

  # Generowanie kafelków
  karty = ""
  for w in wyniki:
    karty += f"""
        <div class="summary-card">
            <div class="date-label">📅 {w['termin']}</div>
            <div class="price-val">{w['cena']}</div>
            <a href="{w['url']}" target="_blank" class="book-btn">Rezerwuj</a>
        </div>"""

  # Generowanie tabeli historii
  wiersze = ""
  for h in historia:
    wiersze += f"""
        <tr>
            <td>{h.get('data_odczytu', '-')}</td>
            <td>{h.get('termin', '-')}</td>
            <td style="font-weight: 700; color: #38bdf8;">{h.get('cena', '-')}</td>
        </tr>"""

  html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <title>Monitor Cen - Październik 2026</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f1f5f9; padding: 20px; margin: 0; }}
        .container {{ max-width: 850px; margin: 0 auto; }}
        .card {{ background: #1e293b; border-radius: 16px; padding: 24px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); border: 1px solid #334155; margin-bottom: 20px; }}
        h1 {{ margin: 0 0 6px 0; font-size: 1.4rem; color: #fff; }}
        .sub {{ color: #94a3b8; font-size: 0.9rem; margin-bottom: 18px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
        .summary-card {{ background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 14px; text-align: center; }}
        .date-label {{ font-size: 0.82rem; color: #cbd5e1; font-weight: 600; margin-bottom: 6px; }}
        .price-val {{ font-size: 1.2rem; font-weight: 800; color: #38bdf8; margin-bottom: 10px; }}
        .book-btn {{ display: inline-block; background: #0284c7; color: #fff; text-decoration: none; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #334155; font-size: 0.9rem; }}
        th {{ background: #0f172a; color: #cbd5e1; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>Apartament Delux z 1 sypialnią – Październik 2026</h1>
            <div class="sub">Ostatnie sprawdzenie (czas PL): <strong>{teraz}</strong></div>
            <div class="grid">{karty}</div>
        </div>
        <div class="card">
            <h2 style="font-size: 1.1rem; margin-top: 0;">Historia sprawdzania cen</h2>
            <table>
                <thead>
                    <tr>
                        <th>Data odczytu (PL)</th>
                        <th>Termin pobytu</th>
                        <th>Wykryta cena</th>
                    </tr>
                </thead>
                <tbody>{wiersze}</tbody>
            </table>
        </div>
    </div>
</body>
</html>"""

  with open(HTML_FILE, "w", encoding="utf-8") as f:
    f.write(html)


if __name__ == "__main__":
  main()
