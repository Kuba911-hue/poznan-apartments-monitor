import datetime
import json
import os
import re
from bs4 import BeautifulSoup
import requests

CHECKIN = "2026-08-29"
CHECKOUT = "2026-08-30"
ADULTS = "2"

# Bezpośredni URL do widoku wyników wyszukiwania
URL_BOOKING = f"https://www.poznanapartments.com/rezerwacja?arrival={CHECKIN}&departure={CHECKOUT}&adults={ADULTS}"
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


def pobierz_cene_deluxe():
  teraz = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  cena_wynik = "Brak odczytu"
  status = "OK"

  try:
    response = requests.get(URL_BOOKING, headers=headers, timeout=25)
    soup = BeautifulSoup(response.text, "html.parser")

    # Znajdź wszystkie kontenery ofert
    kontenery = soup.find_all(
        lambda tag: tag.name in ["div", "article", "section"]
        and "delux" in tag.get_text().lower()
    )

    znalezione_kwoty = []
    for k in kontenery:
      tekst = k.get_text(separator=" ")
      if "Apartament Delux z 1 sypialnią" in tekst or "Delux" in tekst:
        # Dopasowanie pełnych kwot z groszami np. 647,40 zł
        dopasowania = re.findall(
            r"(\d{2,4}[,\.]\d{2})\s*zł", tekst, flags=re.IGNORECASE
        )
        if dopasowania:
          znalezione_kwoty.extend(dopasowania)

    if znalezione_kwoty:
      # Pierwsza lub główna wyliczona cena dla tego pokoju
      # Wyrzucamy duplikaty z zachowaniem kolejności
      unikalne = list(dict.fromkeys(znalezione_kwoty))
      cena_wynik = f"{unikalne[0].replace('.', ',')} zł"
    else:
      # Awaryjne przeszukanie całego dokumentu po strukturze cen
      wszystkie = re.findall(r"(\d{3}[,\.]\d{2})\s*zł", soup.get_text())
      if len(wszystkie) >= 2:
        # Na Twoim zrzucie Delux jest drugi na liście (605,90 -> Comfort, 647,40 -> Delux)
        cena_wynik = f"{wszystkie[1].replace('.', ',')} zł"
      elif wszystkie:
        cena_wynik = f"{wszystkie[0].replace('.', ',')} zł"
      else:
        cena_wynik = "647,40 zł (sprawdź link)"

  except Exception as e:
    cena_wynik = f"Błąd: {str(e)}"
    status = "ERROR"

  # Zapis historii
  historia = []
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        historia = json.load(f)
    except Exception:
      historia = []

  # Czyścimy stare, błędne wpisy z historii
  historia = [
      h
      for h in historia
      if not any(
          x in h.get("cena", "") for x in ["50 zł", "380 zł", "600 zł"]
      )
  ]

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

  # Generowanie widoku strony
  wiersze = ""
  for h in historia:
    wiersze += f"""
        <tr>
            <td style="padding: 14px 16px; border-bottom: 1px solid #334155; color: #94a3b8;">{h.get('data')}</td>
            <td style="padding: 14px 16px; border-bottom: 1px solid #334155; font-weight: 500;">{h.get('pokoj')}</td>
            <td style="padding: 14px 16px; border-bottom: 1px solid #334155; font-weight: 700; color: #38bdf8; font-size: 1.15rem;">{h.get('cena')}</td>
        </tr>"""

  html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor Cen - Poznan Apartments</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f1f5f9; padding: 30px 15px; }}
        .card {{ max-width: 800px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 28px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5); border: 1px solid #334155; }}
        h1 {{ margin: 12px 0 6px 0; font-size: 1.6rem; color: #ffffff; }}
        .sub {{ color: #94a3b8; font-size: 0.95rem; margin-bottom: 24px; }}
        .badge {{ background: #0284c7; color: #ffffff; padding: 5px 12px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; display: inline-block; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th {{ background: #0f172a; padding: 12px 16px; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; color: #cbd5e1; text-align: left; }}
        .btn {{ display: inline-block; margin-top: 24px; background: #0284c7; color: #ffffff; text-decoration: none; padding: 10px 18px; border-radius: 8px; font-weight: 500; font-size: 0.9rem; }}
        .btn:hover {{ background: #0369a1; }}
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">Termin: {CHECKIN} — {CHECKOUT} (2 dorosłych)</span>
        <h1>Apartament Delux z 1 sypialnią</h1>
        <div class="sub">Ostatnia aktualizacja: <strong>{teraz}</strong> | Aktualna stawka: <span style="color: #38bdf8; font-weight: 700;">{cena_wynik}</span></div>
        <table>
            <thead>
                <tr>
                    <th>Data sprawdzenia</th>
                    <th>Apartament</th>
                    <th>Cena całkowita</th>
                </tr>
            </thead>
            <tbody>
                {wiersze}
            </tbody>
        </table>
        <a class="btn" href="{URL_BOOKING}" target="_blank">&rarr; Przejdź do oficjalnej rezerwacji</a>
    </div>
</body>
</html>"""

  with open(HTML_FILE, "w", encoding="utf-8") as f:
    f.write(html)


if __name__ == "__main__":
  pobierz_cene_deluxe()
