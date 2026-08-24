import os
import requests
import time
import json
from datetime import datetime
from serpapi import GoogleSearch

ORIGIN = "LTN"
DESTINATION = "POZ"

GITHUB_USER = "Kuba911-hue"
GITHUB_REPO = "wizz-fly-hunter"
SITE_URL = f"https://{GITHUB_USER}.github.io/{GITHUB_REPO}/"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SERP_KEY = os.environ.get("SERPAPI_KEY")

HISTORY_FILE = "history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_december_flights():
    if not SERP_KEY:
        return "⚠️ Błąd: Brak klucza SERPAPI_KEY.", [], {}

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    history = load_history()

    msg = f"✈️ Ceny lotów LTN ➔ POZ\n🗓️ 15–24 Grudnia 2026\n\n"
    current_data = []

    days_to_check = list(range(15, 25))

    for day in days_to_check:
        date_str = f"2026-12-{day:02d}"
        params = {
            "engine": "google_flights",
            "departure_id": ORIGIN,
            "arrival_id": DESTINATION,
            "outbound_date": date_str,
            "currency": "GBP",
            "hl": "pl",
            "type": "2",
            "api_key": SERP_KEY
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            flights = results.get("best_flights", []) + results.get("other_flights", [])
            
            day_flight_found = False
            for flight in flights:
                flight_details = flight.get("flights", [{}])[0]
                airline = flight_details.get("airline", "")
                
                if "Wizz" in airline:
                    price = flight.get("price", "N/A")
                    dep_time = flight_details.get("departure_airport", {}).get("time", "").split(" ")[-1]
                    
                    # Logika porównywania cen
                    trend = "🆕"
                    trend_html = "<span style='color: #666;'>🆕 Nowy</span>"
                    row_bg = ""

                    if date_str in history and len(history[date_str]) > 0:
                        last_price = history[date_str][-1]["price"]
                        if isinstance(price, int) and isinstance(last_price, int):
                            diff = price - last_price
                            if diff < 0:
                                trend = f"🟢 ↓ (-£{abs(diff)})"
                                trend_html = f"<span style='color: #28a745; font-weight: bold;'>🟢 ↓ (-£{abs(diff)})</span>"
                                row_bg = "style='background-color: #d4edda;'"
                            elif diff > 0:
                                trend = f"🔴 ↑ (+£{diff})"
                                trend_html = f"<span style='color: #dc3545; font-weight: bold;'>🔴 ↑ (+£{diff})</span>"
                                row_bg = "style='background-color: #f8d7da;'"
                            else:
                                trend = "⚪ ="
                                trend_html = "<span style='color: #6c757d;'>⚪ Bez zmian</span>"

                    msg += f"📅 {date_str} ({dep_time}): £{price} {trend}\n"
                    
                    current_data.append({
                        "date": date_str,
                        "time": dep_time,
                        "airline": "Wizz Air",
                        "price": price,
                        "trend_html": trend_html,
                        "row_bg": row_bg
                    })
                    
                    if date_str not in history:
                        history[date_str] = []
                    history[date_str].append({"timestamp": timestamp, "price": price})

                    day_flight_found = True
                    break
            
            if not day_flight_found:
                msg += f"📅 {date_str}: Brak lotu Wizz Air\n"
                current_data.append({
                    "date": date_str,
                    "time": "-",
                    "airline": "-",
                    "price": "Brak",
                    "trend_html": "-",
                    "row_bg": ""
                })

            time.sleep(0.5)

        except Exception as e:
            print(f"Błąd dla daty {date_str}: {e}")

    save_history(history)
    msg += f"\n🌐 Pełna historia na stronie:\n{SITE_URL}"

    return msg, current_data, history

def generate_html(current_data, history):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    current_rows = ""
    for row in current_data:
        p_val = row['price']
        price_str = f"£{p_val}" if isinstance(p_val, int) else p_val
        current_rows += f"<tr {row['row_bg']}><td>{row['date']}</td><td>{row['time']}</td><td>{row['airline']}</td><td><strong>{price_str}</strong></td><td>{row['trend_html']}</td></tr>\n"

    history_rows = ""
    for date_str in sorted(history.keys()):
        entries = history[date_str]
        changes = " ➔ ".join([f"£{e['price']} <small style='color:#777'>({e['timestamp']})</small>" for e in entries])
        history_rows += f"<tr><td><strong>{date_str}</strong></td><td>{changes}</td></tr>\n"

    html_content = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ceny lotów LTN -> POZ</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 20px; background-color: #f8f9fa; color: #333; }}
        .container {{ max-width: 850px; margin: 0 auto; }}
        h2, h3 {{ color: #0056b3; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 30px; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background-color: #0056b3; color: white; }}
        tr:hover {{ opacity: 0.9; }}
        .updated {{ font-size: 0.85em; color: #666; margin-top: 15px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>✈️ Ceny lotów London Luton (LTN) ➔ Poznań (POZ)</h2>
        <p>Grudzień 2026 (Wizz Air)</p>
        
        <h3>📊 Aktualne zestawienie i zmiana ceny</h3>
        <table>
            <thead>
                <tr>
                    <th>Data lotu</th>
                    <th>Godzina</th>
                    <th>Linia</th>
                    <th>Cena</th>
                    <th>Zmiana</th>
                </tr>
            </thead>
            <tbody>
                {current_rows}
            </tbody>
        </table>

        <h3>📜 Historia pomiarów</h3>
        <table>
            <thead>
                <tr>
                    <th>Data lotu</th>
                    <th>Historia zmian cen</th>
                </tr>
            </thead>
            <tbody>
                {history_rows}
            </tbody>
        </table>

        <p class="updated">Ostatnia aktualizacja: {now} UTC</p>
    </div>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Brak TOKENA lub CHAT_ID Telegrama")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": text,
        "disable_web_page_preview": False
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"⚠️ Błąd wysyłania Telegram: {response.status_code} - {response.text}")

def main():
    report, current_data, history = get_december_flights()
    generate_html(current_data, history)
    send_telegram(report)

if __name__ == "__main__":
    main()
