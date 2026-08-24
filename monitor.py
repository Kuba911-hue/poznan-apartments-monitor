import os
import json
import asyncio
import requests
from datetime import datetime
from playwright.async_api import async_playwright

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

TERMINY = [
    ("2026-09-05", "2026-09-06"),
    ("2026-09-12", "2026-09-13"),
    ("2026-09-19", "2026-09-20"),
    ("2026-09-26", "2026-09-27")
]

HISTORY_FILE = "historia.json"

def wyslij_telegram(tekst):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": tekst, "parse_mode": "HTML"})

def zapisz_historie(odczytane_dane):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    historia = []
    
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                historia = json.load(f)
        except Exception:
            historia = []

    historia.append({
        "timestamp": now_str,
        "dane": odczytane_dane
    })

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(historia, f, ensure_ascii=False, indent=2)

def wygeneruj_strone_html():
    html_content = """<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor Ceny - Poznań Apartments</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --primary: #2563eb;
            --border: #e2e8f0;
        }
        body { 
            font-family: 'Inter', -apple-system, sans-serif; 
            margin: 0; 
            padding: 24px;
            background: var(--bg); 
            color: var(--text-main);
        }
        .container { 
            max-width: 1100px; 
            margin: 0 auto; 
        }
        header {
            margin-bottom: 28px;
            text-align: center;
        }
        h1 { 
            font-size: 26px; 
            font-weight: 700; 
            margin: 0 0 6px 0;
            color: var(--text-main);
        }
        p.subtitle {
            margin: 0;
            color: var(--text-muted);
            font-size: 14px;
        }
        .control-panel {
            background: var(--card-bg);
            padding: 18px 24px;
            border-radius: 12px;
            border: 1px solid var(--border);
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .control-group {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-grow: 1;
        }
        label {
            font-weight: 600;
            font-size: 14px;
            color: var(--text-main);
            white-space: nowrap;
        }
        select { 
            padding: 10px 14px; 
            font-size: 15px; 
            font-weight: 500;
            border-radius: 8px; 
            border: 1px solid var(--border); 
            background-color: #fff;
            color: var(--text-main);
            width: 100%;
            max-width: 320px;
            cursor: pointer;
            outline: none;
            transition: border-color 0.2s;
        }
        select:focus {
            border-color: var(--primary);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: var(--card-bg);
            padding: 18px 20px;
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .stat-title {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 6px;
        }
        .stat-value {
            font-size: 22px;
            font-weight: 700;
            color: var(--primary);
        }
        .main-card {
            background: var(--card-bg);
            padding: 24px;
            border-radius: 12px;
            border: 1px solid var(--border);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 24px;
        }
        .card-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .chart-box { 
            position: relative; 
            height: 420px; 
            width: 100%;
        }
        .screenshot-container {
            text-align: center;
        }
        .screenshot-container img {
            max-width: 100%;
            border-radius: 8px;
            border: 1px solid var(--border);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            margin-top: 12px;
        }
        @media (max-width: 640px) {
            body { padding: 12px; }
            .control-panel { flex-direction: column; align-items: stretch; }
            select { max-width: 100%; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Monitor Ceny Poznań Apartments</h1>
            <p class="subtitle">Automatyczne śledzenie stawek w wybranych terminach</p>
        </header>

        <div class="control-panel">
            <div class="control-group">
                <label for="terminSelect">Wybierz termin:</label>
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
            <div class="card-title">
                <span>📈 Wykres zmian cen</span>
            </div>
            <div class="chart-box">
                <canvas id="priceChart"></canvas>
            </div>
        </div>

        <div class="main-card screenshot-container">
            <div class="card-title">
                <span>📸 Ostatni zrzut ekranu oferty</span>
            </div>
            <img id="screenshotImg" src="" alt="Zrzut ekranu oferty" onerror="this.style.display='none';">
        </div>
    </div>

    <script>
        let historiaData = [];
        let myChart = null;

        async function wczytajDane() {
            try {
                const res = await fetch('historia.json');
                historiaData = await res.json();
                
                const terminySet = new Set();
                historiaData.forEach(entry => {
                    entry.dane.forEach(item => terminySet.add(item.termin));
                });

                const select = document.getElementById('terminSelect');
                select.innerHTML = '';
                terminySet.forEach(t => {
                    const opt = document.createElement('option');
                    opt.value = t;
                    opt.textContent = t;
                    select.appendChild(opt);
                });

                if (historiaData.length > 0) {
                    document.getElementById('lastUpdate').textContent = 'Ostatnia aktualizacja: ' + historiaData[historiaData.length - 1].timestamp;
                }

                aktualizujStrone();
            } catch (e) {
                console.error("Błąd ładowania danych", e);
            }
        }

        function aktualizujStrone() {
            const wybranyTermin = document.getElementById('terminSelect').value;
            const czasy = [];
            const pokojeMap = {};

            let lowestPrice = Infinity;
            let lowestRoomName = "-";

            historiaData.forEach(entry => {
                const daneTerminu = entry.dane.find(d => d.termin === wybranyTermin);
                if (daneTerminu) {
                    czasy.push(entry.timestamp);
                    daneTerminu.pokoje.forEach(p => {
                        if (!pokojeMap[p.nazwa]) pokojeMap[p.nazwa] = [];
                        const kwota = parseFloat(p.cena.replace(/[^0-9,.]/g, '').replace(',', '.'));
                        pokojeMap[p.nazwa].push(kwota || null);

                        if (kwota && kwota < lowestPrice) {
                            lowestPrice = kwota;
                            lowestRoomName = p.nazwa;
                        }
                    });
                }
            });

            // Aktualizacja kart podsumowania
            document.getElementById('minPrice').textContent = lowestPrice !== Infinity ? lowestPrice.toFixed(2) + ' zł' : '-';
            document.getElementById('minRoom').textContent = lowestRoomName;
            document.getElementById('totalChecks').textContent = czasy.length;

            // Wykres
            const colors = ['#2563eb', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#4b5563'];
            const datasets = Object.keys(pokojeMap).map((nazwa, idx) => ({
                label: nazwa,
                data: pokojeMap[nazwa],
                borderColor: colors[idx % colors.length],
                backgroundColor: colors[idx % colors.length],
                borderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                fill: false,
                tension: 0.15
            }));

            if (myChart) myChart.destroy();
            const ctx = document.getElementById('priceChart').getContext('2d');
            myChart = new Chart(ctx, {
                type: 'line',
                data: { labels: czasy, datasets: datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { position: 'bottom', labels: { boxWidth: 12, padding: 16, font: { family: 'Inter', size: 12 } } },
                        tooltip: { padding: 12, cornerRadius: 8 }
                    },
                    scales: {
                        y: { 
                            grid: { color: '#f1f5f9' },
                            title: { display: true, text: 'Cena (PLN)', font: { family: 'Inter', size: 12, weight: '600' } } 
                        },
                        x: { 
                            grid: { display: false },
                            title: { display: true, text: 'Data i godzina sprawdzania', font: { family: 'Inter', size: 12, weight: '600' } } 
                        }
                    }
                }
            });

            // Aktualizacja zdjęcia
            const checkInDate = wybranyTermin.split(" - ")[0];
            const imgEl = document.getElementById('screenshotImg');
            imgEl.style.display = 'block';
            imgEl.src = `cennik_${checkInDate}.png?t=` + new Date().getTime();
        }

        wczytajDane();
    </script>
</body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

async def sprawdz_termin(page, check_in, check_out):
    print(f"Sprawdzanie terminu: {check_in} do {check_out}...")
    target_url = f"https://booking.profitroom.com/pl/poznanapartments/pricelist/rooms/?check-in={check_in}&check-out={check_out}&currency=PLN&r1_adults=2"
    wynik_terminu = {"termin": f"{check_in} - {check_out}", "pokoje": []}

    try:
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)

        # Zamknięcie banera RODO
        try:
            await page.click("text=Zaakceptuj wszystko", timeout=3000)
            await asyncio.sleep(1)
        except Exception:
            pass

        await page.evaluate('''() => {
            const overlays = document.querySelectorAll('[class*="cookie"], [id*="cookie"], [class*="modal"], [class*="overlay"]');
            overlays.forEach(el => el.remove());
        }''')

        # Scrollowanie dla załadowania obrazów
        await page.evaluate('''async () => {
            await new Promise((resolve) => {
                let totalHeight = 0;
                const distance = 300;
                const timer = setInterval(() => {
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if (totalHeight >= scrollHeight) {
                        clearInterval(timer);
                        window.scrollTo(0, 0);
                        resolve();
                    }
                }, 150);
            });
        }''')
        await asyncio.sleep(2)

        # Robienie zrzutu ekranu dla podglądu na stronie WWW
        foto_path = f"cennik_{check_in}.png"
        await page.screenshot(path=foto_path, full_page=True)

        # Pobieranie struktur cen
        pokoje_dane = await page.evaluate('''() => {
            const wyniki = [];
            const cards = Array.from(document.querySelectorAll('div')).filter(el => 
                el.innerText && el.innerText.includes('Apartament') && el.innerText.includes('zł')
            );
            const przetworzone = new Set();

            for (const card of cards) {
                const lines = card.innerText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                const nazwa = lines.find(l => l.includes('Apartament') && l.length < 70);

                if (nazwa && !przetworzone.has(nazwa)) {
                    const cenaLine = lines.find(l => 
                        l.includes('zł') && 
                        /\\d/.test(l) &&
                        !l.toLowerCase().includes('od ') && 
                        !l.toLowerCase().includes('przed obniżką') &&
                        !l.toLowerCase().includes('30 dni')
                    );

                    if (cenaLine) {
                        wyniki.push({ nazwa: nazwa, cena: cenaLine });
                        przetworzone.add(nazwa);
                    }
                }
            }
            return wyniki;
        }''')

        if pokoje_dane:
            wynik_terminu["pokoje"] = pokoje_dane
            msg = f"<b>📊 Odczytane Ceny Poznań Apartments ({check_in} - {check_out}):</b>\n\n"
            for p in pokoje_dane:
                msg += f"• <b>{p['nazwa']}</b>: 🟢 <b>{p['cena']}</b>\n"
            wyslij_telegram(msg)

    except Exception as e:
        print(f"Błąd dla {check_in}: {e}")

    return wynik_terminu

async def pobierz_i_wyslij():
    wszystkie_dane = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for check_in, check_out in TERMINY:
            dane_t = await sprawdz_termin(page, check_in, check_out)
            wszystkie_dane.append(dane_t)
            await asyncio.sleep(1)

        await browser.close()

    zapisz_historie(wszystkie_dane)
    wygeneruj_strone_html()

if __name__ == "__main__":
    asyncio.run(pobierz_i_wyslij())
