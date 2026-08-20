import datetime
import json
import os
import re
from playwright.sync_api import sync_playwright

# Terminy do sprawdzenia
DATES = [
    ("2026-10-03", "2026-10-04"),
    ("2026-10-10", "2026-10-11"),
    ("2026-10-17", "2026-10-18"),
    ("2026-10-24", "2026-10-25"),
]

DATA_FILE = "dane.json"
HTML_FILE = "index.html"


def pobierz_dane(page, cin, cout):
  # Bezpośrednie wejście do silnika rezerwacji z parametrami
  url = f"https://www.poznanapartments.com/rezerwacja?arrival={cin}&departure={cout}&adults=2"
  cena = "Brak wolnych"

  try:
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    # 1. Próba znalezienia bloku Delux w kodzie
    elementy = page.locator("text=/Delux/i").all()
    for el in elementy:
      parent = el.locator("xpath=ancestor::div[contains(., 'zł')][1]")
      if parent.count() > 0:
        tekst = parent.inner_text()
        kwoty = re.findall(r"(\d{2,4}[,\.]\d{2})\s*zł", tekst)
        if kwoty:
          cena = f"{kwoty[-1].replace('.', ',')} zł"
          return cena

    # 2. Awaryjny odczyt wszystkich cen na stronie
    pelny_tekst = page.locator("body").inner_text()
    ceny = re.findall(r"(\d{3}[,\.]\d{2})\s*zł", pelny_tekst)
    if len(ceny) >= 2:
      cena = f"{ceny[1].replace('.', ',')} zł"
    elif ceny:
      cena = f"{ceny[0].replace('.', ',')} zł"

  except Exception as e:
    cena = "Błąd pobierania"

  return cena


def main():
  # Czas UTC+1 / UTC+2 (Polska)
  teraz = (
      datetime.datetime.utcnow() + datetime.timedelta(hours=2)
  ).strftime("%Y-%m-%d %H:%M:%S")
  odczyty = []

  with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-gpu", "--single-process"],
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    page = context.new_page()

    for cin, cout in DATES:
      c = pobierz_dane(page, cin, cout)
      odczyty.append({
          "data": teraz,
          "termin": f"{cin} — {cout}",
          "cena": c,
      })

    browser.close()

  # Zapis historii do JSON
  historia = []
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        historia = json.load(f)
    except:
      historia = []

  # Wyrzucamy stare błędy
  historia = [h for h in historia if "Brak wolnych" not in h.get("cena", "")]

  for o in reversed(odczyty):
    historia.insert(0, o)

  historia = historia[:40]

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(historia, f, ensure_ascii=False, indent=2)

  # Generowanie prostej, czytelnej tabeli
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
    <title>Ceny: Apartament Deluxe</title>
    <style>
        body {{ font-family: -apple-system, system-ui, sans-serif; background: #0f172a; color: #e2e8f0; padding: 20px; max-width: 650px; margin: 0 auto; }}
        h2 {{ margin-bottom: 4px; font-size: 1.25rem; }}
        .time {{ color: #94a3b8; font-size: 0.85rem; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px 14px; text-align: left; border-bottom: 1px solid #334155; font-size: 0.9rem; }}
        th {{ background: #111827; color: #94a3b8; font-weight: 600; }}
        .price {{ font-weight: bold; color: #38bdf8; font-size: 1rem; }}
    </style>
</head>
<body>
    <h2>Apartament Delux (2 os.)</h2>
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
