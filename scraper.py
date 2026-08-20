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


def pobierz_wszystkie_dla_daty(page, cin, cout):
  url = f"https://www.poznanapartments.com/rezerwacja?arrival={cin}&departure={cout}&adults=2"
  wynik_cenowy = "Brak wolnych"

  try:
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)

    # Pobieramy pełen tekst wyrenderowany na stronie (wraz ze wszystkimi ramkami)
    pelnra_zawartosc = []
    for f in [page] + page.frames:
      try:
        pelnra_zawartosc.append(f.locator("body").inner_text())
      except:
        pass

    tekst_zbiorczy = " \n ".join(pelnra_zawartosc)

    # 1. Sprawdzamy czy jest bezpośrednio Delux
    match_delux = re.search(
        r"Apartament\s+Delux[^\n\r]{0,300}?(\d{2,4}[,\.]\d{2})\s*zł",
        tekst_zbiorczy,
        re.IGNORECASE | re.DOTALL,
    )

    if match_delux:
      wynik_cenowy = f"{match_delux.group(1).replace('.', ',')} zł (Delux)"
    else:
      # 2. Wyciągamy wszystkie widoczne oferty z cenami
      wszystkie_stawki = re.findall(
          r"(\d{2,4}[,\.]\d{2})\s*zł", tekst_zbiorczy, flags=re.IGNORECASE
      )
      unikalne_stawki = list(
          dict.fromkeys([s.replace(".", ",") for s in wszystkie_stawki])
      )

      if unikalne_stawki:
        # Pokazujemy dostępne stawki
        wynik_cenowy = " | ".join([f"{s} zł" for s in unikalne_stawki[:4]])
      else:
        wynik_cenowy = "Brak wolnych pokoi"

  except Exception as e:
    wynik_cenowy = f"Błąd: {str(e)[:20]}"

  return wynik_cenowy


def main():
  # Czas polski (UTC+2)
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
      c = pobierz_wszystkie_dla_daty(page, cin, cout)
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

  # Czyścimy wcześniejsze błędy "Brak odczytu"
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
    <title>Ceny: Apartamenty Towarowa</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #e2e8f0; padding: 20px; max-width: 750px; margin: 0 auto; }}
        h2 {{ margin-bottom: 4px; font-size: 1.3rem; color: #fff; }}
        .time {{ color: #94a3b8; font-size: 0.85rem; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px 14px; text-align: left; border-bottom: 1px solid #334155; font-size: 0.9rem; }}
        th {{ background: #111827; color: #94a3b8; font-weight: 600; }}
        .price {{ font-weight: bold; color: #38bdf8; font-size: 0.95rem; }}
    </style>
</head>
<body>
    <h2>Monitor Cen – Październik 2026 (2 os.)</h2>
    <div class="time">Ostatnie sprawdzenie: <strong>{teraz}</strong></div>
    <table>
        <thead>
            <tr>
                <th>Data sprawdzenia</th>
                <th>Termin</th>
                <th>Wykryte stawki</th>
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
