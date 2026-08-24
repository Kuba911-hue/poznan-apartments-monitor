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

def wyslij_zdjecie_telegram(sciezka_pliku, podpis):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(sciezka_pliku, "rb") as photo:
        requests.post(
            url, 
            data={"chat_id": CHAT_ID, "caption": podpis, "parse_mode": "HTML"}, 
            files={"photo": photo}
        )

def zapisz_historie(odczytane_dane):
    """Zapisz dane w prawidłowym formacie z polem 'dane' zawierającym listę terminów"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    historia = []
    
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                historia = json.load(f)
        except Exception:
            historia = []

    # Nowy wpis w prawidłowym formacie
    historia.append({
        "timestamp": now_str,
        "dane": odczytane_dane  # Lista słowników z "termin" i "pokoje"
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
        :root { --bg: #f8fafc; --card-bg: #ffffff; --text-main: #0f172a; --text-muted: #64748b; --primary: #2563eb; --border: #e2e8f0; --success: #10b981; --danger: #ef4444; }
        body { font-family: 'Inter', sans-serif; margin: 0; padding: 24px; background: var(--bg); color: var(--text-main); }
        .container { max-width: 1200px; margin: 0 auto; }
        header { margin-bottom: 24px; text-align: center; }
        h1 { font-size: 26px; font-weight: 700; margin: 0 0 6px 0; }
        .control-panel { background: var(--card-bg); padding: 18px 24px; border-radius: 12px; border: 1px solid var(--border); margin-bottom: 24px; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
        select { padding: 10px 14px; font-size: 15px; border-radius: 8px; border: 1px solid var(--border); background: #fff; cursor: pointer; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card { background: var(--card-bg); padding: 18px 20px; border-radius: 12px; border: 1px solid var(--border); }
        .stat-title { font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 6px; }
        .stat-value { font-size: 22px; font-weight: 700; color: var(--primary); }
        .stat-change { font-size: 13px; margin-top: 6px; }
        .stat-change.up { color: var(--danger); }
        .stat-change.down { color: var(--success); }
        .main-card { background: var(--card-bg); padding: 24px; border-radius: 12px; border: 1px solid var(--border); margin-bottom: 24px; }
        .chart-box { position: relative; height: 420px; width: 100%; }
        .price-table { width: 100%; border-collapse: collapse; margin-top: 16px; }
        .price-table th { text-align: left; padding: 12px; background: var(--bg); border-bottom: 2px solid var(--border); font-weight: 600; }
        .price-table td { padding: 12px; border-bottom: 1px solid var(--border); }
        .price-table tr:hover { background: var(--bg); }
        .price-trend { font-size: 13px; font-weight: 600; }
        .price-trend.up { color: var(--danger); }
        .price-trend.down { color: var(--success); }
        .price-trend.stable { color: var(--text-muted); }
        .debug-console { background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 8px; border: 1px solid var(--border); margin-top: 24px; font-family: 'Courier New', monospace; font-size: 12px; max-height: 200px; overflow-y: auto; }
        .debug-log { display: block; margin: 2px 0; }
        .debug-error { color: #f87171; }
        .debug-success { color: #86efac; }
        .debug-info { color: #93c5fd; }
        .debug-warning { color: #fbbf24; }
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
                <div class="stat-change" id="minPriceChange"></div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Najtańszy apartament</div>
                <div class="stat-value" id="minRoom" style="font-size: 15px;">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Liczba odczytów</div>
                <div class="stat-value" id="totalChecks" style="color: var(--text-main);">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Średnia zmiana ceny</div>
                <div class="stat-value" id="avgChange" style="font-size: 18px;">-</div>
                <div class="stat-change" id="avgChangeIndicator"></div>
            </div>
        </div>

        <div class="main-card">
            <div style="font-size: 16px; font-weight: 600; margin-bottom: 20px;">📈 Wykres zmian cen</div>
            <div class="chart-box">
                <canvas id="priceChart"></canvas>
            </div>
        </div>

        <div class="main-card">
            <div style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">📋 Zestawienie cen w czasie</div>
            <div style="overflow-x: auto;">
                <table class="price-table" id="priceTable">
                    <thead>
                        <tr>
                            <th>Data/Godzina</th>
                            <th id="apartamentHeader"></th>
                        </tr>
                    </thead>
                    <tbody id="priceTableBody">
                    </tbody>
                </table>
            </div>
        </div>

        <div class="debug-console" id="debugConsole"></div>
    </div>

    <script>
        let historiaData = [];
        let myChart = null;

        function addDebugLog(msg, type = 'info') {
            const debugConsole = document.getElementById('debugConsole');
            const logEntry = document.createElement('div');
            logEntry.className = `debug-log debug-${type}`;
            logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
            debugConsole.appendChild(logEntry);
            debugConsole.scrollTop = debugConsole.scrollHeight;
        }

        async function wczytajDane() {
            try {
                addDebugLog('Ładowanie historia.json...', 'info');
                const res = await fetch('historia.json');
                
                if (!res.ok) {
                    addDebugLog(`❌ Błąd HTTP ${res.status}`, 'error');
                    throw new Error(`HTTP ${res.status}`);
                }

                historiaData = await res.json();
                addDebugLog(`✓ Załadowano ${historiaData.length} wpisów`, 'success');
                
                if (!Array.isArray(historiaData) || historiaData.length === 0) {
                    addDebugLog('❌ Brak danych!', 'error');
                    return;
                }

                const terminySet = new Set();
                historiaData.forEach((entry) => {
                    if (entry.dane && Array.isArray(entry.dane)) {
                        entry.dane.forEach(item => {
                            if (item.termin) {
                                terminySet.add(item.termin);
                            }
                        });
                    }
                });

                addDebugLog(`✓ Znaleziono ${terminySet.size} terminów`, 'success');
                
                const select = document.getElementById('terminSelect');
                select.innerHTML = '';
                Array.from(terminySet).sort().forEach(t => {
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
                addDebugLog(`❌ Błąd: ${e.message}`, 'error');
            }
        }

        function parseCena(cenaStr) {
            if (!cenaStr) return null;
            const liczba = cenaStr.replace(/[^0-9,.]/g, '').replace(',', '.');
            return parseFloat(liczba) || null;
        }

        function aktualizujStrone() {
            const wybranyTermin = document.getElementById('terminSelect').value;
            if (!wybranyTermin) return;
            
            const czasy = [];
            const pokojeMap = {};
            const pokojeHistory = {}; // Historyczne zmiany cen

            historiaData.forEach((entry) => {
                if (!entry.dane || !Array.isArray(entry.dane)) return;
                
                const daneTerminu = entry.dane.find(d => d.termin === wybranyTermin);
                if (!daneTerminu || !daneTerminu.pokoje) return;

                czasy.push(entry.timestamp);
                
                daneTerminu.pokoje.forEach(p => {
                    const nazwa = p.nazwa;
                    const kwota = parseCena(p.cena);
                    
                    if (!pokojeMap[nazwa]) pokojeMap[nazwa] = [];
                    if (!pokojeHistory[nazwa]) pokojeHistory[nazwa] = [];
                    
                    pokojeMap[nazwa].push(kwota);
                    pokojeHistory[nazwa].push({ timestamp: entry.timestamp, cena: kwota });
                });
            });

            // Statystyki
            let lowestPrice = Infinity;
            let lowestRoomName = "-";
            let lowestPriceChange = "";
            let sumChanges = 0;
            let changeCount = 0;

            for (const nazwa in pokojeHistory) {
                const prices = pokojeHistory[nazwa];
                if (prices.length > 0) {
                    const lastPrice = prices[prices.length - 1].cena;
                    const firstPrice = prices[0].cena;
                    
                    if (lastPrice !== null && lastPrice < lowestPrice) {
                        lowestPrice = lastPrice;
                        lowestRoomName = nazwa;
                        if (firstPrice !== null && firstPrice !== 0) {
                            lowestPriceChange = ((lastPrice - firstPrice) / firstPrice * 100).toFixed(1);
                        }
                    }

                    if (lastPrice !== null && firstPrice !== null && firstPrice !== 0) {
                        const change = (lastPrice - firstPrice) / firstPrice * 100;
                        sumChanges += change;
                        changeCount++;
                    }
                }
            }

            document.getElementById('minPrice').textContent = lowestPrice !== Infinity ? lowestPrice.toFixed(2) + ' zł' : '-';
            document.getElementById('minRoom').textContent = lowestRoomName;
            document.getElementById('totalChecks').textContent = czasy.length;

            if (lowestPriceChange !== "") {
                const changeElem = document.getElementById('minPriceChange');
                const isUp = parseFloat(lowestPriceChange) > 0;
                changeElem.className = 'stat-change ' + (isUp ? 'up' : 'down');
                changeElem.textContent = (isUp ? '📈' : '📉') + ' ' + Math.abs(lowestPriceChange) + '%';
            }

            if (changeCount > 0) {
                const avgChg = sumChanges / changeCount;
                document.getElementById('avgChange').textContent = Math.abs(avgChg).toFixed(1) + '%';
                const avgElem = document.getElementById('avgChangeIndicator');
                avgElem.className = 'stat-change ' + (avgChg > 0 ? 'up' : 'down');
                avgElem.textContent = (avgChg > 0 ? '📈 wzrost' : '📉 spadek');
            }

            // Tabela cen
            const tableBody = document.getElementById('priceTableBody');
            const headerCell = document.getElementById('apartamentHeader');
            tableBody.innerHTML = '';
            
            if (Object.keys(pokojeMap).length === 0) {
                tableBody.innerHTML = '<tr><td colspan="2">Brak danych</td></tr>';
                return;
            }

            const apartamenty = Object.keys(pokojeMap).sort();
            headerCell.textContent = apartamenty[0];

            czasy.forEach((czas, idx) => {
                const row = document.createElement('tr');
                const timeCell = document.createElement('td');
                timeCell.textContent = czas;
                row.appendChild(timeCell);

                apartamenty.forEach(nazwa => {
                    if (idx === 0) {
                        const th = document.createElement('th');
                        th.textContent = nazwa;
                        document.querySelector('.price-table thead tr').appendChild(th);
                    }

                    const cell = document.createElement('td');
                    const history = pokojeHistory[nazwa] || [];
                    const priceData = history.find(h => h.timestamp === czas);
                    
                    if (priceData && priceData.cena !== null) {
                        const cena = priceData.cena.toFixed(0);
                        let trend = '→';
                        
                        if (history.length > 1) {
                            const idx = history.findIndex(h => h.timestamp === czas);
                            if (idx > 0) {
                                const prevPrice = history[idx - 1].cena;
                                if (prevPrice !== null) {
                                    if (priceData.cena > prevPrice) trend = '📈';
                                    else if (priceData.cena < prevPrice) trend = '📉';
                                }
                            }
                        }
                        
                        cell.innerHTML = `<span class="price-trend">${trend} ${cena} zł</span>`;
                    } else {
                        cell.textContent = '-';
                    }
                    row.appendChild(cell);
                });

                tableBody.appendChild(row);
            });

            // Wykres
            const colors = ['#2563eb', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#4b5563', '#ec4899'];
            const datasets = apartamenty.map((nazwa, idx) => ({
                label: nazwa,
                data: pokojeMap[nazwa],
                borderColor: colors[idx % colors.length],
                backgroundColor: colors[idx % colors.length] + '20',
                borderWidth: 2,
                pointRadius: 4,
                fill: true,
                tension: 0.2
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
                    plugins: { legend: { position: 'top' } },
                    scales: {
                        y: { grid: { color: '#f1f5f9' } },
                        x: { grid: { display: false } }
                    }
                }
            });
            
            addDebugLog('✓ Strona zaktualizowana', 'success');
        }

        wczytajDane();
    </script>
</body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

async def sprawdz_termin(page, check_in, check_out):
    """Sprawdzaj cenę dla danego terminu i zwróć wynik w prawidłowym formacie"""
    print(f"Sprawdzanie terminu: {check_in} do {check_out}...")
    target_url = f"https://booking.profitroom.com/pl/poznanapartments/pricelist/rooms/?check-in={check_in}&check-out={check_out}&currency=PLN&r1_adults=2"
    wynik_terminu = {"termin": f"{check_in} - {check_out}", "pokoje": []}

    try:
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)

        # Usunięcie banera RODO
        try:
            await page.click("text=Zaakceptuj wszystko", timeout=3000)
            await asyncio.sleep(1)
        except Exception:
            pass

        await page.evaluate('''() => {
            const overlays = document.querySelectorAll('[class*="cookie"], [id*="cookie"], [class*="modal"], [class*="overlay"]');
            overlays.forEach(el => el.remove());
        }''')

        # Scrollowanie dla załadowania elementów i obrazów
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

        # Robienie zrzutu ekranu dla bota
        foto_path = f"cennik_{check_in}.png"
        await page.screenshot(path=foto_path, full_page=True)

        # Pobieranie struktur cen z kodu strony
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
            
            # Wysyłka zdjęcia WRAZ z tekstem na Telegram
            wyslij_zdjecie_telegram(foto_path, msg)

        # Usunięcie pliku lokalnego po wysłaniu
        if os.path.exists(foto_path):
            os.remove(foto_path)

    except Exception as e:
        print(f"Błąd dla {check_in}: {e}")

    return wynik_terminu

async def pobierz_i_wyslij():
    """Główna funkcja - sprawdzaj terminy, zapisuj wyniki i generuj HTML"""
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

    # Zapisz nowe dane
    zapisz_historie(wszystkie_dane)
    
    # Wygeneruj stronę
    wygeneruj_strone_html()

if __name__ == "__main__":
    asyncio.run(pobierz_i_wyslij())
