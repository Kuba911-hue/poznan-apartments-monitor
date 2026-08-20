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
  przechwycone_dane = []

  # 1. Przechwytujemy odpowiedzi sieciowe JSON w tle
  def on_response(response):
    try:
      if "hotres" in response.url or "booking" in response.url or "api" in response.url:
        ct = response.headers.get("content-type", "")
        if "json" in ct or "javascript" in ct:
          przechwycone_dane.append(response.text())
    except:
      pass

  page.on("response", on_response)

  cena_wynik = "Brak odczytu"

  try:
    url = f"https://www.poznanapartments.com/rezerwacja?arrival={cin}&departure={cout}&adults=2&checkin={cin}&checkout={cout}"
    page.goto(url, wait_until="load", timeout=45000)
    page.wait_for_timeout(4000)

    # 2. Próba odczytu bezpośrednio z przechwyconego ruchu sieciowego JSON
    for surowy_tekst in przechwycone_dane:
      if "Delux" in surowy_tekst or "564" in surowy_tekst or "price" in surowy_tekst:
        m = re.search(r"Delux[^\}]*?price[\":\s]+(\d+[\.,]?\d*)", surowy_tekst, re.IGNORECASE)
        if m:
          cena_wynik = f"{m.group(1).replace('.', ',')} zł"
          return cena_wynik

    # 3. Jeśli nie z sieci, skanujemy elementy DOM we wszystkich klatkach
    for frame in [page] + page.frames:
      tekst_ramki = frame.content()
      if "Apartament Delux" in tekst_ramki:
        # Szukamy wzorca kwoty przypisanej do Delux
        dopasowanie = re.search(
            r"Apartament\s+Delux[^\n\r<]{0,400}?(\d{2,4}[,\.]\d{2})\s*zł",
            frame.locator("body").inner_text(),
            re.IGNORECASE | re.DOTALL,
        )
        if dopasowanie:
          cena_wynik = f"{dopasowanie.group(1).replace('.', ',')} zł"
          return cena_wynik

        # Pobranie przez kafelki z przyciskiem "Wybierz"
        karty = frame.locator("xpath=//*[contains(text(), 'Apartament Delux')]/ancestor::*[contains(., 'zł')][last()]").all()
        for k in karty:
          t = k.inner_text()
          stawki = re.findall(r"(\d{2,4}[,\.]\d{2})\s*zł", t)
          if stawki:
            cena_wynik = f"{stawki[-1].replace('.', ',')} zł"
            return cena_wynik

    # 4. Jeśli wciąż brak, odczytujemy stawkę 4. pokoju z rzędu z całej listy (standardowy układ: Studio -> Standard -> Comfort -> Delux)
    caly_tekst = page.locator("body").inner_text()
    wszystkie_kwoty = re.findall(r"(\d{2,4}[,\.]\d{2})\s*zł", caly_tekst)
    if len(wszystkie_kwoty) >= 4:
      cena_wynik = f"{wszystkie_kwoty[3].replace('.', ',')} zł"

  except Exception as e:
    cena_wynik = f"Błąd: {str(e)[:15]}"
  finally:
    context.close()

  return cena_wynik


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
