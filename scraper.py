import datetime
import json
import os
import re
from bs4 import BeautifulSoup
import requests

CHECKIN = "2026-08-29"
CHECKOUT = "2026-08-30"
ADULTS = "2"

URL_BOOKING = f"https://www.poznanapartments.com/rezerwacja?arrival={CHECKIN}&departure={CHECKOUT}&adults={ADULTS}"
DATA_FILE = "dane.json"
HTML_FILE = "index.html"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
}


def pobierz_cene_deluxe():
  teraz = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  cena_wynik = "Brak dostępności / Nie znaleziono"
  status = "OK"

  try:
    response = requests.get(URL_BOOKING, headers=headers, timeout=25)
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
        if wszystkie_ceny:
          cena_wynik = f"Wykryte stawki: {', '.join(wszystkie_ceny[:3])}"

  except Exception as e:
    cena_wynik = f"Błąd: {str(e)}"
    status = "ERROR"

  # Wczytanie historii
  historia = []
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        historia = json.load(f)
    except Exception:
      historia = []

  # Dodanie nowego wpisu
  historia.insert(
      0,
      {
          "data": teraz,
          "termin": f"{CHECKIN} do {CHECKOUT}",
          "pokoj": "Apartament Delux z 1 sypialnią",
          "cena": cena_wynik,
          "status": status,
      },
  )

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(historia, f, ensure_ascii=False, indent=2)

  # Generowanie tabeli z bezpiecznym odczytem .get()
  wiersze = ""
  for h in historia:
    data_str = h.get("data", teraz)
    pokoj_str = h.get("pokoj", "Apartament Delux z 1 sypialnią")
    cena_str = h.get("cena", "Brak danych")

    wiersze += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #334155;">{data_str}</td>
            <td style="padding: 12px; border-bottom: 1px solid #334155;">{pokoj_str}</td>
            <td style="padding: 12px; border-bottom: 1px solid #334155; font-weight: bold; color: #38bdf8; font-size: 1.1rem;">{cena_str}</td>
        </tr>"""

  html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor Ceny - Apartament Deluxe</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; }}
        .card {{ max-width: 800px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 24px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); }}
        h1 {{ margin: 0 0 8px 0; font-size: 1.5rem; }}
        .sub {{ color: #94a3b8; margin-bottom: 20px; font-size: 0.95rem; }}
        .badge {{ background: #0369a1; color: #e0f2fe; padding: 4px 12px; border-radius: 9999px; font-size: 0.85rem; display: inline-block; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; text-align: left; }}
        th {{ background: #334155; padding: 12px; font-weight: 600; color: #cbd5e1; }}
        a {{ color: #38bdf8; text-decoration: none; display: inline-block; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">Termin: {CHECKIN} — {CHECKOUT} (1 noc, 2 os.)</span>
        <h1>Apartament Delux z 1 sypialnią</h1>
        <div class="sub">Ostatni odczyt: <strong>{teraz}</strong> | Aktualna stawka: <span style="color: #38bdf8; font-weight: bold;">{cena_wynik}</span></div>
        <table>
            <thead>
                <tr>
                    <th>Data sprawdzenia</th>
                    <th>Typ apartamentu</th>
                    <th>Cena</th>
                </tr>
            </thead>
            <tbody>
                {wiersze}
            </tbody>
        </table>
        <a href="{URL_BOOKING}" target="_blank">&rarr; Przejdź bezpośrednio do rezerwacji</a>
    </div>
</body>
</html>"""

  with open(HTML_FILE, "w", encoding="utf-8") as f:
    f.write(html)


if __name__ == "__main__":
  pobierz_cene_deluxe()
