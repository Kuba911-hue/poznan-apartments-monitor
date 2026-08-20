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


def pobierz_cene(browser, cin, cout):
  context = browser.new_context(
      viewport={"width": 1440, "height": 900},
      locale="pl-PL",
      user_agent=(
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
      ),
  )
  page = context.new_page()
  cena = "Brak odczytu"

  try:
    url = f"https://www.poznanapartments.com/rezerwacja?arrival={cin}&departure={cout}&adults=2"
    page.goto(url, wait_until="domcontentloaded", timeout=45000)

    # Czekamy na załadowanie ramek i ofert
    page.wait_for_timeout(6000)

    # Przeszukujemy stronę główną oraz wszystkie ramki (iframe)
    wszystkie_ramki = [page] + page.frames

    for target in wszystkie_ramki:
      delux = target.locator("text=/Apartament Delux/i")
      if delux.count() > 0:
        # Znaleziono sekcję Delux w tej ramce
        el = delux.first
        # Szukamy kafelka z ceną
        karta = el.locator("xpath=ancestor::*[contains(., 'zł')][last()]")
        tekst = karta.inner_text() if karta.count() > 0 else target.content()

        # Wyciągamy kwotę z kafelka
        stawki = re.findall(
            r"(\d{2,4}[,\.]\d{2})\s*zł", tekst, flags=re.IGNORECASE
        )
        if stawki:
          cena = f"{stawki[-1].replace('.', ',')} zł"
          break

    # Jeśli kafelki są inaczej zagnieżdżone w ramce
    if cena == "Brak odczytu":
      for target in wszystkie_ramki:
        tekst_ramki = target.locator("body").inner_text()
        if "Apartament Delux" in tekst_ramki and "zł" in tekst_ramki:
          match = re.search(
              r"Apartament\s+Delux[^\n\r]{0,350}?(\d{2,4}[,\.]\d{2})\s*zł",
              tekst_ramki,
              re.IGNORECASE | re.DOTALL,
          )
          if match:
            cena = f"{match.group(1).replace('.', ',')} zł"
            break

  except Exception as e:
    cena = f"Błąd: {str(e)[:20]}"
  finally:
    context.close()

  return cena


def main():
  teraz = (
      datetime.datetime.utcnow() + datetime.timedelta(hours=2)
  ).strftime("%Y-%m-%d %H:%M:%S")
  odczyty = []

  with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
    )

    for cin, cout in DATES:
      c = pobierz_cene(browser, cin, cout)
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

  # Usunięcie starych wpisów "Brak odczytu"
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
