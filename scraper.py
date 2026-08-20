import datetime
import json
import os
import re
from bs4 import BeautifulSoup
import requests

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
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8",
}


def pobierz_cene_pojedyncza(cin, cout):
  url = f"https://www.poznanapartments.com/rezerwacja?arrival={cin}&departure={cout}&adults=2"
  cena_wynik = "Brak odczytu"

  try:
    response = requests.get(url, headers=headers, timeout=25)
    soup = BeautifulSoup(response.text, "html.parser")
    tekst_caly = soup.get_text()

    znaleziono = False
    for el in soup.find_all(
        ["div", "article", "section", "li"], class_=True
    ) or soup.find_all(["div"]):
      tekst_el = el.get_text()
      if (
          "Apartament Delux" in tekst_el
          or "Apartament Deluxe" in tekst_el
          or "Delux z 1 sypialnią" in tekst_el
      ):
        ceny = re.findall(
            r"(\d+[\s.,]?\d*)\s*zł", tekst_el, flags=re.IGNORECASE
        )
        if ceny:
          cena_wynik = f"{ceny[-1].strip()} zł"
          znaleziono = True
          break

    if not znaleziono:
      match = re.search(
          r"Delux[^\n\r]*?(\d+[\s.,]\d{2})\s*zł",
          tekst_caly,
          re.IGNORECASE | re.DOTALL,
      )
      if match:
        cena_wynik = f"{match.group(1).strip()} zł"
      else:
        wszystkie_ceny = re.findall(r"\d+,\d{2}\s*zł", tekst_caly)
        if len(wszystkie_ceny) >= 3:
          cena_wynik = wszystkie_ceny[2]
        elif wszystkie_ceny:
          cena_wynik = wszystkie_ceny[0]

  except Exception as e:
    cena_wynik = f"Błąd: {str(e)}"

  return cena_wynik


def main():
  teraz = (
      datetime.datetime.utcnow() + datetime.timedelta(hours=2)
  ).strftime("%Y-%m-%d %H:%M:%S")
  odczyty = []

  for cin, cout in DATES:
    cena = pobierz_cene_pojedyncza(cin, cout)
    odczyty.append({
        "data": teraz,
        "termin": f"{cin} — {cout}",
        "cena": cena,
    })

  # Wczytanie historii
  historia = []
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        historia = json.load(f)
    except Exception:
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
