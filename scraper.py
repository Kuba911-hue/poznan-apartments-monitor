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


def pobierz_dane_terminu(page, cin, cout):
  # Bezpośrednie wywołanie widgetu rezerwacji widocznego na screenach
  urls = [
      f"https://panel.hotres.pl/v4_step1?oid=3292&lang=pl&arrival={cin}&departure={cout}&adults=2",
      f"https://panel.hotres.pl/v4_step1?oid=poznanapartments&lang=pl&arrival={cin}&departure={cout}&adults=2",
      f"https://www.poznanapartments.com/rezerwacja?arrival={cin}&departure={cout}&adults=2",
  ]

  cena_delux = "Brak odczytu"

  for url in urls:
    try:
      page.goto(url, wait_until="networkidle", timeout=30000)
      page.wait_for_timeout(3000)

      # Pobieramy zawartość tekstową
      tekst = page.locator("body").inner_text()

      # 1. Szukamy konkretnie wariantu Apartament Delux
      match = re.search(
          r"Apartament\s+Delux[^\n\r]{0,350}?(\d{2,4}[,\.]\d{2})\s*zł",
          tekst,
          re.IGNORECASE | re.DOTALL,
      )
      if match:
        cena_delux = f"{match.group(1).replace('.', ',')} zł"
        return cena_delux

      # 2. Jeśli nazwa jest lekko inna, szukamy bloku ze stawką 564,40 zł / Delux
      kafelki = page.locator("div, article, section").all()
      for k in kafelki:
        try:
          t = k.inner_text()
          if "Delux" in t and "zł" in t and ("WYBIERZ" in t or "od " in t):
            ceny = re.findall(r"(\d{2,4}[,\.]\d{2})\s*zł", t)
            if ceny:
              cena_delux = f"{ceny[-1].replace('.', ',')} zł"
              return cena_delux
        except:
          continue

      # 3. Jeśli są jakiekolwiek stawki z kafelków (np. Studio, Standard, Comfort, Delux)
      wszystkie = re.findall(r"(\d{2,4}[,\.]\d{2})\s*zł", tekst)
      if len(wszystkie) >= 5:
        # Delux jest 5. pozycją z kolei na liście kafelków
        cena_delux = f"{wszystkie[4].replace('.', ',')} zł"
        return cena_delux
      elif wszystkie:
        cena_delux = f"{wszystkie[-1].replace('.', ',')} zł"
        return cena_delux

    except Exception:
      continue

  return cena_delux


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
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        locale="pl-PL",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    page = context.new_page()

    for cin, cout in DATES:
      c = pobierz_dane_terminu(page, cin, cout)
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

  # Czyścimy stare wpisy "Brak odczytu" i "Brak wolnych"
  historia = [
      h
      for h in historia
      if "Brak" not in h.get("cena", "") and "600 zł" not in h.get("cena", "")
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
