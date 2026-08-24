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
    """Wyślij zdjęcie z informacją o cenach na Telegram"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ Brak TELEGRAM_TOKEN lub CHAT_ID")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(sciezka_pliku, "rb") as photo:
            requests.post(
                url, 
                data={"chat_id": CHAT_ID, "caption": podpis, "parse_mode": "HTML"}, 
                files={"photo": photo},
                timeout=10
            )
    except Exception as e:
        print(f"Błąd wysyłania na Telegram: {e}")

def zapisz_historie(odczytane_dane):
    """Zapisz dane w prawidłowym formacie"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    historia = []
    
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                historia = json.load(f)
        except Exception as e:
            print(f"⚠️ Błąd czytania historii: {e}")
            historia = []

    # Nowy wpis
    historia.append({
        "timestamp": now_str,
        "dane": odczytane_dane
    })

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(historia, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Zapisano {len(historia)} wpisów do historia.json")

def wygeneruj_strone_html():
    """Generuj stronę HTML z interaktywnym dashboardem"""
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
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card { background: var(--card-bg); padding: 18px 20px; border-radius: 12px; border: 1px solid var(--border); }
        .stat-title { font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px; }
        .stat-value { font-size: 24px; font-weight: 700; color: var(--primary); }
        .stat-change { font-size: 13px; margin-top: 6px; font-weight: 600; }
        .stat-change.up { color: var(--danger); }
        .stat-change.down { color: var(--success); }
        .main-card { background: var(--card-bg); padding: 24px; border-radius: 12px; border: 1px solid var(--border); margin-bottom: 24px; }
        .chart-box { position: relative; height: 400px; width: 100%; }
        .price-table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }
        .price-table th { text-align: left; padding: 12px; background: var(--bg); border-bottom: 2px solid var(--border); font-weight: 600; }
        .price-table td { padding: 10px 12px; border-bottom: 1px solid var(--border); }
        .price-table tr:hover { background: #fafafa; }
        .price-cell { font-weight: 500; }
        .price-up { color: var(--danger); }
        .price-down { color: var(--success); }
        .price-stable { color: var(--text-muted); }
        .no-data { padding: 20px; text-align: center; color: var(--text-muted); }
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
                <div class="stat-value" style="font-size: 16px; word-break: break-word;" id="minRoom">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Liczba odczytów</div>
                <div class="stat-value" id="totalChecks">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Średnia zmiana</div>
                <div class="stat-value" id="avgChange">-</div>
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
            <div style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">📋 Tabela cen w czasie</div>
            <div style="overflow-x: auto;">
                <table class="price-table" id="priceTable"></table>
            </div>
        </div>
    </div>

    <script>
        let historiaData = [];
        let myChart = null;

        async function wczytajDane() {
            try {
                const res = await fetch('historia.json');
                if (!res.ok) throw new Error(`HTTP ${res.status}`);

                historiaData = await res.json();
                if (!Array.isArray(historiaData) || historiaData.length === 0) {
                    document.getElementById('priceTable').innerHTML = '<tr><td class="no-data" colspan="20">Brak danych - uruchom monitor.py</td></tr>';
                    return;
                }

                // Zbierz unikalne terminy
                const terminySet = new Set();
                historiaData.forEach(entry => {
                    if (entry.dane && Array.isArray(entry.dane)) {
                        entry.dane.forEach(item => {
                            if (item.termin) terminySet.add(item.termin);
                        });
                    }
                });

                const select = document.getElementById('terminSelect');
                select.innerHTML = '';
                Array.from(terminySet).sort().forEach(t => {
                    const opt = document.createElement('option');
                    opt.value = t;
                    opt.textContent = t;
                    select.appendChild(opt);
                });

                if (historiaData.length > 0) {
                    const lastEntry = historiaData[historiaData.length - 1];
                    document.getElementById('lastUpdate').textContent = '🕐 ' + lastEntry.timestamp;
                }

                aktualizujStrone();
            } catch (e) {
                console.error("Błąd:", e);
                document.getElementById('priceTable').innerHTML = '<tr><td class="no-data" colspan="20">❌ Błąd ładowania danych</td></tr>';
            }
        }

        function parseCena(cenaStr) {
            if (!cenaStr) return null;
            const num = cenaStr.replace(/[^0-9,.]/g, '').replace(',', '.');
            return parseFloat(num) || null;
        }

        function aktualizujStrone() {
            const termin = document.getElementById('terminSelect').value;
            if (!termin) return;

            const czasy = [];
            const apartamenty = new Map(); // nazwa -> [{timestamp, cena}]

            // Zbierz dane dla wybranego terminu
            historiaData.forEach(entry => {
                if (!entry.dane || !Array.isArray(entry.dane)) return;
                const termData = entry.dane.find(d => d.termin === termin);
                if (!termData || !termData.pokoje) return;

                czasy.push(entry.timestamp);

                termData.pokoje.forEach(p => {
                    if (!apartamenty.has(p.nazwa)) {
                        apartamenty.set(p.nazwa, []);
                    }
                    const kwota = parseCena(p.cena);
                    apartamenty.get(p.nazwa).push({
                        timestamp: entry.timestamp,
                        cena: kwota
                    });
                });
            });

            if (apartamenty.size === 0) {
                document.getElementById('priceTable').innerHTML = '<tr><td class="no-data" colspan="20">Brak danych dla tego terminu</td></tr>';
                return;
            }

            // Sortuj apartamenty alfabetycznie
            const sortedApartamenty = Array.from(apartamenty.keys()).sort();

            // Statystyki
            let minPrice = Infinity;
            let minRoom = '';
            let sumChange = 0, countChange = 0;

            sortedApartamenty.forEach(nazwa => {
                const prices = apartamenty.get(nazwa);
                if (prices.length > 0) {
                    const last = prices[prices.length - 1].cena;
                    const first = prices[0].cena;

                    if (last !== null && last < minPrice) {
                        minPrice = last;
                        minRoom = nazwa;
                    }

                    if (last !== null && first !== null && first !== 0) {
                        const chg = ((last - first) / first) * 100;
                        sumChange += chg;
                        countChange++;
                    }
                }
            });

            document.getElementById('minPrice').textContent = minPrice !== Infinity ? minPrice.toFixed(0) + ' zł' : '-';
            document.getElementById('minRoom').textContent = minRoom || '-';
            document.getElementById('totalChecks').textContent = czasy.length;

            if (countChange > 0) {
                const avg = sumChange / countChange;
                document.getElementById('avgChange').textContent = Math.abs(avg).toFixed(1) + '%';
                const elem = document.getElementById('avgChangeIndicator');
                elem.className = 'stat-change ' + (avg > 0 ? 'up' : 'down');
                elem.textContent = (avg > 0 ? '📈 wzrost' : '📉 spadek');
            }

            // Tabela
            const table = document.getElementById('priceTable');
            table.innerHTML = '';
            
            const headerRow = table.insertRow();
            const thTime = document.createElement('th');
            thTime.textContent = 'Data/Godzina';
            headerRow.appendChild(thTime);

            sortedApartamenty.forEach(nazwa => {
                const th = document.createElement('th');
                th.textContent = nazwa;
                th.style.maxWidth = '200px';
                headerRow.appendChild(th);
            });

            czasy.forEach(czas => {
                const row = table.insertRow();
                const tdTime = row.insertCell();
                tdTime.textContent = czas;
                tdTime.style.fontWeight = '600';

                sortedApartamenty.forEach(nazwa => {
                    const tdPrice = row.insertCell();
                    const history = apartamenty.get(nazwa);
                    const data = history.find(h => h.timestamp === czas);

                    if (data && data.cena !== null) {
                        let trend = '→';
                        let trendClass = 'price-stable';

                        const idx = history.indexOf(data);
                        if (idx > 0) {
                            const prev = history[idx - 1].cena;
                            if (prev !== null) {
                                if (data.cena > prev) {
                                    trend = '📈';
                                    trendClass = 'price-up';
                                } else if (data.cena < prev) {
                                    trend = '📉';
                                    trendClass = 'price-down';
                                }
                            }
                        }

                        tdPrice.innerHTML = `<span class="price-cell ${trendClass}">${trend} ${data.cena.toFixed(0)} zł</span>`;
                    } else {
                        tdPrice.textContent = '-';
                    }
                });
            });

            // Wykres
            const datasets = sortedApartamenty.map((nazwa, idx) => {
                const colors = ['#2563eb', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#4b5563', '#ec4899'];
                const data = apartamenty.get(nazwa).map(d => d.cena);
                const color = colors[idx % colors.length];

                return {
                    label: nazwa,
                    data: data,
                    borderColor: color,
                    backgroundColor: color + '20',
                    borderWidth: 2,
                    pointRadius: 5,
                    pointBackgroundColor: color,
                    fill: true,
                    tension: 0.3
                };
            });

            if (myChart) myChart.destroy();
            const ctx = document.getElementById('priceChart').getContext('2d');
            myChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: czasy,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top', labels: { usePointStyle: true } }
                    },
                    scales: {
                        y: { beginAtZero: false, grid: { color: '#f1f5f9' } },
                        x: { grid: { display: false } }
                    },
                    interaction: { mode: 'index', intersect: false }
                }
            });
        }

        wczytajDane();
    </script>
</body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✓ Wygenerowano index.html")

async def sprawdz_termin(page, check_in, check_out):
    """Sprawdź cenę dla terminu - dane wysyłane na Telegram i zapisywane do historia.json"""
    print(f"\\n🔍 Sprawdzanie terminu: {check_in} do {check_out}...")
    
    target_url = f"https://booking.profitroom.com/pl/poznanapartments/pricelist/rooms/?check-in={check_in}&check-out={check_out}&currency=PLN&r1_adults=2"
    wynik_terminu = {"termin": f"{check_in} - {check_out}", "pokoje": []}

    try:
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)

        # Zaakceptuj cookies
        try:
            await page.click("text=Zaakceptuj wszystko", timeout=3000)
            await asyncio.sleep(1)
        except:
            pass

        # Usuń overlaye
        await page.evaluate('''() => {
            document.querySelectorAll('[class*="cookie"], [id*="cookie"], [class*="modal"]').forEach(el => el.remove());
        }''')

        # Scroll dla załadowania
        await page.evaluate('''async () => {
            let height = 0;
            for (let i = 0; i < 5; i++) {
                window.scrollBy(0, 500);
                await new Promise(r => setTimeout(r, 100));
            }
            window.scrollTo(0, 0);
        }''')
        
        await asyncio.sleep(2)

        # Zrzut ekranu
        foto_path = f"cennik_{check_in}.png"
        await page.screenshot(path=foto_path, full_page=True)

        # Scrape ceny
        pokoje_dane = await page.evaluate('''() => {
            const wyniki = [];
            const seen = new Set();

            document.querySelectorAll('div').forEach(el => {
                const text = el.innerText;
                if (!text || !text.includes('Apartament') || !text.includes('zł')) return;

                const lines = text.split('\\n').map(l => l.trim()).filter(l => l);
                const nazwa = lines.find(l => l.includes('Apartament') && l.length < 100);
                if (!nazwa || seen.has(nazwa)) return;

                const cenaLine = lines.find(l => 
                    l.match(/\\d+\\s*zł/) && 
                    !l.toLowerCase().includes('przed')
                );

                if (cenaLine && !seen.has(nazwa)) {
                    wyniki.push({nazwa, cena: cenaLine});
                    seen.add(nazwa);
                }
            });

            return wyniki;
        }''')

        if pokoje_dane && pokoje_dane.length > 0:
            wynik_terminu["pokoje"] = pokoje_dane
            
            # Wiadomość na Telegram
            msg = f"<b>📊 Odczytane Ceny Poznań Apartments ({check_in} - {check_out}):</b>\\n\\n"
            for p in pokoje_dane:
                msg += f"• <b>{p['nazwa']}</b>: 🟢 <b>{p['cena']}</b>\\n"
            
            wyslij_zdjecie_telegram(foto_path, msg)
            print(f"   ✓ Znaleziono {len(pokoje_dane)} apartamentów")
        else:
            print(f"   ⚠️ Nie znaleziono danych dla terminu")

        # Usuń zrzut
        if os.path.exists(foto_path):
            os.remove(foto_path)

    except Exception as e:
        print(f"   ❌ Błąd: {e}")

    return wynik_terminu

async def pobierz_i_wyslij():
    """Główna funkcja"""
    print("=" * 60)
    print("🚀 Monitor Ceny Poznań Apartments - START")
    print("=" * 60)
    
    wszystkie_dane = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        for check_in, check_out in TERMINY:
            dane = await sprawdz_termin(page, check_in, check_out)
            wszystkie_dane.append(dane)
            await asyncio.sleep(2)

        await browser.close()

    # Zapisz do historia.json
    zapisz_historie(wszystkie_dane)
    
    # Wygeneruj stronę
    wygeneruj_strone_html()
    
    print("\\n" + "=" * 60)
    print("✅ GOTOWE!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(pobierz_i_wyslij())
