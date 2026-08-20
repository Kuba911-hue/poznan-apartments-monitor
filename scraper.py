import datetime
import json
import os
import re
from playwright.sync_api import sync_playwright

DATES = [
    ("2026-10-03", "2026-10-04"),
    ("2026-10-10", "2026-10-11"),
    ("2026-10-17", "2026-10-18"),
    ("2026-10-24", "2026-10-25"),
]

DATA_FILE = "dane.json"
HTML_FILE = "index.html"


def pobierz_cene(page, cin, cout):
  cena = "Brak odczytu"
  try:
    # 1. Wejście na stronę z parametrami wyszukiwania
    url = f"https://www.poznanapartments.com/rezerwacja?arrival={cin}&departure={cout}&adults=2"
    page.goto(url, wait_until="domcontentloaded", timeout=45000)

    # 2. Czekamy na załadowanie elementów lub silnika rezerwacji
    page.wait_for_timeout(4000)

    # 3. Jeśli strona wymaga kliknięcia Szukaj lub przeładowania formularza
    przycisk_szukaj = page.locator(
        "button:has-text('Szukaj'), input[value*='Szukaj'], .btn-search"
    )
    if (
        przycisk_szukaj.count() > 0
        and przycisk_szukaj.first.is_visible(timeout=2000)
    ):
      przycisk_szukaj.first.click()
      page.wait_for_timeout(4000)

    # 4. Sprawdzamy zawartość wszystkich klatek i widoku
    for frame in [page] + page.frames:
      tekst_ramki = frame.content()
      if "Delux" in tekst_ramki:
        # Szukamy powiązania Delux z ceną
        dopasowanie = re.search(
            r"Apartament\s+Delux[^\n\r<]{0,400}?(\d{2,4}[,\.]\d{2})\s*zł",
            frame.locator("body").inner_text(),
            re.IGNORECASE | re.DOTALL,
        )
        if dopasowanie:
          cena = f"{dopasowanie.group(1).replace('.', ',')} zł"
          return cena

        # Szukamy po kafelku z ofertą
        kafelki = frame.locator("div, article, section").all()
        for k in kafelki:
          try:
            txt = k.inner_text()
            if "Delux" in txt and "zł" in txt and "WYBIERZ" in txt:
              stawki = re.findall(r"(\d{2,4}[,\.]\d{2})\s*zł", txt)
              if stawki:
                cena = f"{stawki[-1].replace('.', ',')} zł"
                return cena
          except:
            continue

    # 5. Jeśli struktura jest inna, pobieramy pozycję Deluxa z listy pokoi
    caly_tekst = page.locator("body").inner_text()
    if "zł" in caly_tekst:
      wszystkie_stawki = re.findall(r"(\d{2,4}[,\.]\d{2})\s*zł", caly_tekst)
      # Kolejność: Standard (506), Comfort (522), Delux (564), 2 sypialnie (688)
      if len(wszystkie_stawki) >= 4:
        cena = f"{wszystkie_stawki[3].replace('.', ',')} zł"
      elif len(wszystkie_stawki) >= 1:
        cena = f"{wszystkie_stawki[-1].replace('.', ',')} zł"

  except Exception as e:
    cena = "Błąd połączenia"

  return cena


def main():
  teraz = (
      datetime.datetime.utcnow() + datetime.timedelta(hours=2)
  ).strftime("%Y-%m-%d %H:%M:%S")
  odczyty = []

  with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
        ],
    )
    context = browser.new_context(
        viewport={"width": 1366, "height": 768},
        locale="pl-PL",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    page = context.new_page()

    for cin, cout in DATES:
      c = pobierz_cene(page, cin, cout)
      odczyty.append({
          "data": teraz,
          "termin": f"{cin} — {cout}",
          "cena": c,
      })

    browser.close()

  # Wczytanie historii
  historia = []
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        historia = json.load(f)
    except:
      historia = []

  # Usunięcie starych błędów
  historia = [h for h in historia if h.get("cena") != "Brak odczytu"]

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
