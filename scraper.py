import datetime
import json
import os
import re
from bs4 import BeautifulSoup
import requests

CHECKIN = "2026-08-29"
CHECKOUT = "2026-08-30"
URL = "https://www.poznanapartments.com/pokoje/apartament-delux-z-1-sypialnia"
DATA_FILE = "dane.json"
HTML_FILE = "index.html"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def sprawdz_cene():
  teraz = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  try:
    response = requests.get(URL, headers=headers, timeout=20)
    soup = BeautifulSoup(response.text, "html.parser")

    # Wyszukanie kwot w zł na stronie
    tekst_strony = soup.get_text()
    ceny = re.findall(r"\d+[\s.,]?\d*\s*zł", tekst_strony, re.IGNORECASE)

    if ceny:
      unikalne_ceny = list(dict.fromkeys([c.strip() for c in ceny]))
      cena_tekst = ", ".join(unikalne_ceny[:3])
    else:
      cena_tekst = "Brak jednoznacznej stawki na stronie"
    status = "OK"
  except Exception as e:
    cena_tekst = f"Blad: {str(e)}"
    status = "ERROR"

  # Wczytaj dotychczasowa historie
  historia = []
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        historia = json.load(f)
    except:
      historia = []

  historia.insert(
      0,
      {
          "data": teraz,
          "termin": f"{CHECKIN} - {CHECKOUT}",
          "cena": cena_tekst,
          "status": status,
      },
  )

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(historia, f, ensure_ascii=False, indent=2)

  # Generowanie tabeli HTML
  wiersze_tabeli = ""
  for wpis in historia:
    wiersze_tabeli += f"""
        <tr>
            <td>{wpis['data']}</td>
            <td>{wpis['termin']}</td>
            <td style="font-weight: bold; color: #2563eb;">{wpis['cena']}</td>
        </tr>
        """

  html_content = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor Cen - Poznan Apartments</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; color: #1e293b; padding: 20px; }}
        .container {{ max-width: 750px; margin: 0 auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
        h1 {{ margin-top: 0; font-size: 1.4rem; color: #0f172a; }}
        .badge {{ display: inline-block; background: #e0f2fe; color: #0369a1; padding: 4px 10px; border-radius: 6px; font-size: 0.85rem; margin-bottom: 15px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 0.95rem; }}
        th {{ background: #f1f5f9; color: #475569; }}
        tr:hover {{ background: #f8fafc; }}
        .link {{ display: block; margin-top: 20px; font-size: 0.9rem; color: #0284c7; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Monitor Cen: Apartament Deluxe</h1>
        <div class="badge">Termin: {CHECKIN} do {CHECKOUT}</div>
        <div style="font-size: 0.85rem; color: #64748b;">Ostatnie sprawdzenie: <strong>{teraz}</strong></div>

        <table>
            <thead>
                <tr>
                    <th>Data i godzina</th>
                    <th>Termin</th>
                    <th>Wykryta cena</th>
                </tr>
            </thead>
            <tbody>
                {wiersze_tabeli}
            </tbody>
        </table>

        <a class="link" href="{URL}" target="_blank">🔗 Przejdź do oferty na stronie hotelu &rarr;</a>
    </div>
</body>
</html>"""

  with open(HTML_FILE, "w", encoding="utf-8") as f:
    f.write(html_content)


if __name__ == "__main__":
  sprawdz_cene()
 
              
