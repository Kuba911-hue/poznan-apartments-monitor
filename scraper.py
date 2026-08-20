import datetime
import json
import os
import re
from bs4 import BeautifulSoup
import requests

# 4 terminy weekendowe
DATES = [
    ("2026-10-03", "2026-10-04"),
    ("2026-10-10", "2026-10-11"),
    ("2026-10-17", "2026-10-18"),
    ("2026-10-24", "2026-10-25"),
]

DATA_FILE = "dane.json"
HTML_FILE = "index.html"


def pobierz_cene_dla_pojedynczej_daty(cin, cout):
  # Osobna, czysta sesja dla każdej daty (izolowane ciasteczka)
  session = requests.Session()
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
      ),
      "Accept-Language": "pl-PL,pl;q=0.9",
      "Referer": "https://www.poznanapartments.com/",
  }

  cena = "Brak odczytu"
  url = f"https://www.poznanapartments.com/rezerwacja?arrival={cin}&departure={cout}&adults=2&checkin={cin}&checkout={cout}&from={cin}&to={cout}"

  try:
    # 1. Wejście na stronę silnika
    res = session.get(url, headers=headers, timeout=20)
    soup = BeautifulSoup(res.text, "html.parser")
    tekst = soup.get_text(separator=" ")

    # 2. Szukamy kafelka z Deluxem
    kontenery = soup.find_all(
        lambda tag: tag.name in ["div", "article", "section"]
        and "delux" in tag.get_text().lower()
    )

    for k in kontenery:
      t_karty = k.get_text(separator=" ")
      if "Delux z 1 sypialnią" in t_karty or "Apartament Delux" in t_karty:
        stawki = re.findall(r"(\d{2,4}[,\.]\d{2})\s*zł", t_karty)
        if stawki:
          return f"{stawki[-1].replace('.', ',')} zł"

    # 3. Jeśli struktura kafelków jest spłaszczona, wyciągamy regexem z okolicy Deluxa
    match = re.search(
        r"Delux[^\n\r]{0,350}?(\d{2,4}[,\.]\d{2})\s*zł",
        tekst,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
      return f"{match.group(1).replace('.', ',')} zł"

    # 4. Jeśli nic nie dopasowało, wyciągamy wszystkie stawki z tej konkretnej odpowiedzi
    wszystkie = re.findall(
        r"(\d{3}[,\.]\d{2})\s*zł", tekst, flags=re.IGNORECASE
    )
    if len(wszystkie) >= 3:
      # Na liście pokoi: Standard -> Comfort -> Delux (3 pozycja)
      cena = f"{wszystkie[2].replace('.', ',')} zł"
    elif wszystkie:
      cena = f"{wszystkie[-1].replace('.', ',')} zł"

  except Exception as e:
    cena = "Błąd połączenia"
  finally:
    session.close()

  return cena


def main():
  # Czas polski (UTC+2)
  teraz = (
      datetime.datetime.utcnow() + datetime.timedelta(hours=2)
  ).strftime("%Y-%m-%d %H:%M:%S")
  odczyty = []

  # Wykonujemy 4 osobne, niezależne zapytania
  for cin, cout in DATES:
    c = pobierz_cene_dla_pojedynczej_daty(cin, cout)
    odczyty.append({
        "data": teraz,
        "termin": f"{cin} — {cout}",
        "cena": c,
    })

  # Zapis historii
  historia = []
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        historia = json.load(f)
    except:
      historia = []

  # Czyścimy nieudane wpisy "Brak odczytu"
  historia = [
      h
      for h in historia
      if h.get("cena") != "Brak odczytu"
      and "Brak wolnych" not in h.get("cena", "")
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
