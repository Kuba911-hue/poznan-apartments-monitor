import os
import json
import asyncio
import requests
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HISTORY_FILE = "historia.json"

def wygeneruj_najblizsze_weekendy(ile_weekendow=4):
    dzis = datetime.now()
    weekendy = []
    dni_do_soboty = (5 - dzis.weekday()) % 7
    if dni_do_soboty == 0:
        dni_do_soboty = 7
    pierwsza_sobota = dzis + timedelta(days=dni_do_soboty)
    
    for i in range(ile_weekendow):
        sobota = pierwsza_sobota + timedelta(weeks=i)
        niedziela = sobota + timedelta(days=1)
        weekendy.append((sobota.strftime("%Y-%m-%d"), niedziela.strftime("%Y-%m-%d")))
    return weekendy

def wyslij_zdjecie_telegram(sciezka_pliku, podpis):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Brak TELEGRAM_TOKEN lub CHAT_ID w secrets!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(sciezka_pliku, "rb") as photo:
            res = requests.post(
                url, 
                data={"chat_id": CHAT_ID, "caption": podpis, "parse_mode": "HTML"}, 
                files={"photo": photo},
                timeout=30
            )
            print(f"Telegram API status: {res.status_code}")
    except Exception as e:
        print(f"❌ Błąd podczas wysyłania zdjęcia: {e}")

def zapisz_historie(odczytane_dane):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    historia = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                historia = json.load(f)
        except Exception:
            historia = []

    historia.append({"timestamp": now_str, "dane": odczytane_dane})

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(historia, f, ensure_ascii=False, indent=2)

def wygeneruj_strone_html():
    historia_json_str = "[]"
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                historia_json_str = f.read()
        except Exception as e:
            print(f"Błąd odczytu pliku historii: {e}")

    html_template = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor Ceny - Poznań Apartments</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --bg: #f8fafc; --card-bg: #ffffff; --text-main: #0f172a; --text-muted: #64748b; --primary: #2563eb; --border: #e2e8f0; }}
        body {{ font-family: 'Inter', sans-serif; margin: 0; padding: 24px; background: var(--bg); color: var(--text-main); }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        header {{ margin-bottom: 24px; text-align: center; }}
        h1 {{ font-size: 26px; font-weight: 700; margin: 0 0 6px 0; }}
        .control-panel {{ background: var(--card-bg); padding: 18px 24px; border-radius: 12px; border: 1px solid var(--border); margin-bottom: 24px; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }}
        select {{ padding: 10px 14px; font-size: 15px; border-radius: 8px; border: 1px solid var(--border); background: #fff; cursor: pointer; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .stat-card {{ background: var(--card-bg); padding: 18px 20px; border-radius: 12px; border: 1px solid var(--border); }}
        .stat-title {{ font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 6px; }}
        .stat-value {{ font-size: 22px; font-weight: 700; color: var(--primary); }}
        .main-card {{ background: var(--card-bg); padding: 24px; border-radius: 12px; border: 1px solid var(--border); margin-bottom: 24px; }}
        .chart-box {{ position: relative; height: 420px; width: 100%; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Monitor Ceny Poznań Apartments</h1>
            <p style="color: var(--text-muted); margin:0;">Automatyczne śledzenie stawek</p>
        </header>

        <div class="control-panel">
            <div>
                <label for="terminSelect" style="font-weight:600; margin-right:8px;">Wybierz termin:</label>
                <select id="terminSelect" onchange="aktualizujStrone()"></select>
            </div>
            <div id="lastUpdate" style="font-size: 13px; color: var(--text-muted);"></div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-title">Najniższa cena</div>
                <div class="stat-value" id="minPrice">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Najtańszy apartament</div>
                <div class="stat-value" id="minRoom" style="font-size: 15px; color: var(--text-main); font-weight: 600;">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Liczba odczytów</div>
                <div class="stat-value" id="totalChecks" style="color: var(--text-main);">-</div>
            </div>
        </div>

        <div class="main-card">
            <div style="font-size: 16px; font-weight: 600; margin-bottom: 20px;">📈 Wykres zmian cen</div>
            <div class="chart-box">
                <canvas id="priceChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        const historiaData = {historia_json_str};
        let myChart = null;

        function inicjalizuj() {{
            if (!historiaData || historiaData.length === 0) return;

            const terminySet = new Set();
            historiaData.forEach(entry => {{
                if (entry.dane) {{
                    entry.dane.forEach(item => {{
                        if (item.pokoje && item.pokoje.length > 0) terminySet.add(item.termin);
                    }});
                }}
            }});

            const select = document.getElementById('terminSelect');
            select.innerHTML = '';
            terminySet.forEach(t => {{
                const opt = document.createElement('option');
                opt.value = t;
                opt.textContent = t;
                select.appendChild(opt);
            }});

            if (historiaData.length > 0) {{
                document.getElementById('lastUpdate').textContent = 'Ostatnia aktualizacja: ' + historiaData[historiaData.length - 1].timestamp;
            }}

            aktualizujStrone();
        }}

        function aktualizujStrone() {{
            const select = document.getElementById('terminSelect');
            if (!select.value) return;
            
            const wybranyTermin = select.value;
            const czasy = [];
            const pokojeMap = {{}};

            let lowestPrice = Infinity;
            let lowestRoomName = "-";

            historiaData.forEach(entry => {{
                if (!entry.dane) return;
                const daneTerminu = entry.dane.find(d => d.termin === wybranyTermin);
                if (daneTerminu && daneTerminu.pokoje && daneTerminu.pokoje.length > 0) {{
                    czasy.push(entry.timestamp);
                    daneTerminu.pokoje.forEach(p => {{
                        if (!pokojeMap[p.nazwa]) pokojeMap[p.nazwa] = [];
                        const kwota = parseFloat(p.cena.replace(/[^0-9,.]/g, '').replace(',', '.'));
                        pokojeMap[p.nazwa].push(kwota || null);

                        if (kwota && kwota < lowestPrice) {{
                            lowestPrice = kwota;
                            lowestRoomName = p.nazwa;
                        }}
                    }});
                }}
            }});

            document.getElementById('minPrice').textContent = lowestPrice !== Infinity ? lowestPrice.toFixed(2) + ' zł' : '-';
            document.getElementById('minRoom').textContent = lowestRoomName;
            document.getElementById('totalChecks').textContent = czasy.length;

            const colors = ['#2563eb', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#4b5563'];
            const datasets = Object.keys(pokojeMap).map((nazwa, idx) => ({{
                label: nazwa,
                data: pokojeMap[nazwa],
                borderColor: colors[idx % colors.length],
                backgroundColor: colors[idx % colors.length],
                borderWidth: 2,
                pointRadius: 4,
                fill: false,
                tension: 0.15
            }}));

            if (myChart) myChart.destroy();
            const ctx = document.getElementById('priceChart').getContext('2d');
            myChart = new Chart(ctx, {{
                type: 'line',
                data: {{ labels: czasy, datasets: datasets }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{ mode: 'index', intersect: false }},
                    scales: {{
                        y: {{ grid: {{ color: '#f1f5f9' }}, title: {{ display: true, text: 'Cena (PLN)' }} }},
                        x: {{ grid: {{ display: false }}, title: {{ display: true, text: 'Data i godzina sprawdzania' }} }}
                    }}
                }}
            }});
        }}

        inicjalizuj();
    </script>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)

async def sprawdz_termin(page, check_in, check_out):
    print(f"Sprawdzanie terminu: {check_in} do {check_out}...")
    target_url = f"https://booking.profitroom.com/pl/poznanapartments/pricelist/rooms/?check-in={check_in}&check-out={check_out}&currency=PLN&r1_adults=2"
    wynik_terminu = {"termin": f"{check_in} - {check_out}", "pokoje": []}

    try:
        await page.goto(target_url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)

        try:
            await page.click("text=Zaakceptuj wszystko", timeout=3000)
            await asyncio.sleep(1)
        except Exception:
            pass

        foto_path = f"cennik_{check_in}.png"
        await page.screenshot(path=foto_path, full_page=True)

        pokoje_dane = await page.evaluate('''() => {
            const wyniki = [];
            const textNodes = document.body.innerText.split('\\n').map(t => t.trim()).filter(Boolean);
            
            for (let i = 0; i < textNodes.length; i++) {
                const line = textNodes[i];
                if (line.includes('Apartament') && line.length < 50) {
                    for (let j = i; j < Math.min(i + 10, textNodes.length); j++) {
                        if (textNodes[j].includes('zł')) {
                            wyniki.push({
                                nazwa: line,
                                cena: textNodes[j]
                            });
                            break;
                        }
                    }
                }
            }
            return wyniki;
        }''')

        if pokoje_dane:
            wynik_terminu["pokoje"] = pokoje_dane
            msg = f"<b>📊 Ceny Poznań Apartments ({check_in} - {check_out}):</b>\n\n"
            for p in pokoje_dane:
                msg += f"• <b>{p['nazwa']}</b>: 🟢 <b>{p['cena']}</b>\n"
            wyslij_zdjecie_telegram(foto_path, msg)

        if os.path.exists(foto_path):
            os.remove(foto_path)

    except Exception as e:
        print(f"Błąd dla {check_in}: {e}")

    return wynik_terminu

async def pobierz_i_wyslij():
    wszystkie_dane = []
    terminy = wygeneruj_najblizsze_weekendy(4)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for check_in, check_out in terminy:
            dane_t = await sprawdz_termin(page, check_in, check_out)
            wszystkie_dane.append(dane_t)
            await asyncio.sleep(2)

        await browser.close()

    zapisz_historie(wszystkie_dane)
    wygeneruj_strone_html()

if __name__ == "__main__":
    asyncio.run(pobierz_i_wyslij())
