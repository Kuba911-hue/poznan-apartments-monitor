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

def wyslij_wiadomosc_telegram(tekst):
    """Wyślij tekstową wiadomość na Telegram"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ Brak TELEGRAM_TOKEN lub CHAT_ID")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        response = requests.post(
            url, 
            json={"chat_id": CHAT_ID, "text": tekst, "parse_mode": "HTML"},
            timeout=10
        )
        if response.status_code == 200:
            print("✓ Wiadomość wysłana na Telegram")
            return True
        else:
            print(f"❌ Błąd Telegram: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Błąd wysyłania na Telegram: {e}")
        return False

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
        * { box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; margin: 0; padding: 24px; background: var(--bg); color: var(--text-main); }
        .container { max-width: 1400px; margin: 0 auto; }
        header { margin-bottom: 32px; text-align: center; }
        h1 { font-size: 32px; font-weight: 700; margin: 0 0 8px 0; background: linear-gradient(135deg, #2563eb, #059669); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { color: var(--text-muted); margin: 0; font-size: 16px; }
        .control-panel { background: var(--card-bg); padding: 20px 24px; border-radius: 12px; border: 1px solid var(--border); margin-bottom: 32px; display: flex; gap: 24px; align-items: center; }
        .control-panel label { font-weight: 600; color: var(--text-main); }
        select { padding: 10px 14px; font-size: 14px; border-radius: 8px; border: 1px solid var(--border); background: #fff; cursor: pointer; min-width: 250px; transition: all 0.2s; }
        select:hover { border-color: var(--primary); }
        .last-update { font-size: 13px; color: var(--text-muted); font-style: italic; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 32px; }
        .stat-card { background: var(--card-bg); padding: 24px; border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 1px 3px rgba(0,0,0,0.05); transition: transform 0.2s; }
        .stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .stat-title { font-size: 12px; font-weight: 700; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.5px; margin-bottom: 12px; }
        .stat-value { font-size: 28px; font-weight: 700; color: var(--primary); word-break: break-word; }
        .stat-change { font-size: 13px; margin-top: 8px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
        .stat-change.up { color: var(--danger); }
        .stat-change.down { color: var(--success); }
        .main-card { background: var(--card-bg); padding: 28px; border-radius: 12px; border: 1px solid var(--border); margin-bottom: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .main-card-title { font-size: 18px; font-weight: 700; margin-bottom: 24px; color: var(--text-main); }
        .chart-box { position: relative; height: 450px; width: 100%; margin-bottom: 12px; }
        .table-wrapper { overflow-x: auto; border-radius: 8px; }
        .price-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .price-table th { text-align: left; padding: 14px 16px; background: linear-gradient(135deg, #f8fafc, #f1f5f9); border-bottom: 2px solid var(--border); font-weight: 600; color: var(--text-main); }
        .price-table td { padding: 12px 16px; border-bottom: 1px solid var(--border); }
        .price-table tr:hover { background: #fafafa; }
        .price-cell { font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .price-up { color: var(--danger); }
        .price-down { color: var(--success); }
        .price-stable { color: var(--text-muted); }
        .time-cell { font-weight: 700; color: var(--primary); min-width: 140px; }
        .no-data { padding: 40px 20px; text-align: center; color: var(--text-muted); font-size: 15px; }
        .loading { display: none; text-align: center; padding: 40px; }
        .spinner { border: 3px solid var(--border); border-top-color: var(--primary); border-radius: 50%; width: 40px; height: 40px; animation: spin 0.8s linear infinite; margin: 0 auto 16px; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .error-box { background: #fee2e2; border: 1px solid #fca5a5; color: #991b1b; padding: 16px; border-radius: 8px; margin-bottom: 24px; }
        @media (max-width: 768px) {
            .control-panel { flex-direction: column; align-items: stretch; }
            select { min-width: auto; }
            .stats-grid { grid-template-columns: 1fr; }
            .chart-box { height: 300px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Monitor Ceny Poznań Apartments</h1>
            <p class="subtitle">Automatyczne śledzenie zmian stawek w czasie rzeczywistym</p>
        </header>

        <div class="control-panel">
            <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
                <label for="terminSelect">Wybierz termin:</label>
                <select id="terminSelect" onchange="aktualizujStrone()"></select>
            </div>
            <div class="last-update" id="lastUpdate">⏳ Wczytywanie...</div>
        </div>

        <div id="errorBox"></div>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Wczytywanie danych...</p>
        </div>

        <div id="content" style="display: none;">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-title">💰 Najniższa cena</div>
                    <div class="stat-value" id="minPrice">-</div>
                    <div class="stat-change" id="minPriceChange"></div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">🏠 Najtańszy apartament</div>
                    <div class="stat-value" style="font-size: 16px;" id="minRoom">-</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">📈 Liczba odczytów</div>
                    <div class="stat-value" id="totalChecks">-</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">📊 Średnia zmiana</div>
                    <div class="stat-value" id="avgChange">-</div>
                    <div class="stat-change" id="avgChangeIndicator"></div>
                </div>
            </div>

            <div class="main-card">
                <div class="main-card-title">📈 Wykres zmian cen w czasie</div>
                <div class="chart-box">
                    <canvas id="priceChart"></canvas>
                </div>
            </div>

            <div class="main-card">
                <div class="main-card-title">📋 Historia cen - Tabela zmian</div>
                <div class="table-wrapper">
                    <table class="price-table" id="priceTable"></table>
                </div>
            </div>
        </div>
    </div>

    <script>
        let historiaData = [];
        let myChart = null;

        async function wczytajDane() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('content').style.display = 'none';
            
            try {
                const res = await fetch('historia.json');
                if (!res.ok) throw new Error(`HTTP ${res.status}`);

                historiaData = await res.json();
                
                if (!Array.isArray(historiaData) || historiaData.length === 0) {
                    pokazBladBrakDanych();
                    return;
                }

                // Zbierz unikalne terminy z całej historii
                const terminySet = new Set();
                historiaData.forEach(entry => {
                    const dane = entry.dane || entry.odczyty;
                    if (dane && Array.isArray(dane)) {
                        dane.forEach(item => {
                            if (item.termin) terminySet.add(item.termin);
                        });
                    }
                });

                if (terminySet.size === 0) {
                    pokazBladBrakDanych();
                    return;
                }

                const select = document.getElementById('terminSelect');
                select.innerHTML = '';
                const sortedTerminy = Array.from(terminySet).sort();
                sortedTerminy.forEach(t => {
                    const opt = document.createElement('option');
                    opt.value = t;
                    opt.textContent = t;
                    select.appendChild(opt);
                });

                if (historiaData.length > 0) {
                    const lastEntry = historiaData[historiaData.length - 1];
                    document.getElementById('lastUpdate').textContent = '🕐 Ostatnia aktualizacja: ' + lastEntry.timestamp;
                }

                document.getElementById('loading').style.display = 'none';
                document.getElementById('content').style.display = 'block';
                aktualizujStrone();
            } catch (e) {
                console.error("Błąd ładowania:", e);
                document.getElementById('loading').style.display = 'none';
                pokazBladOgolny(e.message);
            }
        }

        function pokazBladBrakDanych() {
            document.getElementById('loading').style.display = 'none';
            const errorBox = document.getElementById('errorBox');
            errorBox.innerHTML = '<div class="error-box">❌ Brak danych - uruchom najpierw skrypt monitor.py aby zebrać dane cen.</div>';
        }

        function pokazBladOgolny(msg) {
            const errorBox = document.getElementById('errorBox');
            errorBox.innerHTML = '<div class="error-box">❌ Błąd ładowania danych: ' + msg + '</div>';
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
            const apartamenty = new Map();

            // Zbierz dane dla wybranego terminu ze całej historii
            historiaData.forEach(entry => {
                const dane = entry.dane || entry.odczyty;
                if (!dane || !Array.isArray(dane)) return;
                
                const termData = dane.find(d => d.termin === termin);
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
                headerRow.appendChild(th);
            });

            czasy.forEach(czas => {
                const row = table.insertRow();
                const tdTime = row.insertCell();
                tdTime.innerHTML = `<span class="time-cell">${czas}</span>`;

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
                const colors = ['#2563eb', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#4b5563', '#ec4899', '#14b8a6', '#f59e0b'];
                const data = apartamenty.get(nazwa).map(d => d.cena);
                const color = colors[idx % colors.length];

                return {
                    label: nazwa,
                    data: data,
                    borderColor: color,
                    backgroundColor: color + '15',
                    borderWidth: 2.5,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: color,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    fill: true,
                    tension: 0.4
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
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                usePointStyle: true,
                                padding: 15,
                                font: { size: 12, weight: '600' }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            padding: 12,
                            titleFont: { size: 13, weight: '600' },
                            bodyFont: { size: 12 },
                            borderColor: '#fff',
                            borderWidth: 1
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            grid: {
                                color: '#f1f5f9',
                                drawBorder: false
                            },
                            ticks: {
                                font: { size: 11 },
                                callback: function(value) {
                                    return value + ' zł';
                                }
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                font: { size: 11 }
                            }
                        }
                    }
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
    """Sprawdź cenę dla terminu - z debugowaniem"""
    print(f"\n🔍 Sprawdzanie terminu: {check_in} do {check_out}...")
    
    target_url = f"https://booking.profitroom.com/pl/poznanapartments/pricelist/rooms/?check-in={check_in}&check-out={check_out}&currency=PLN&r1_adults=2"
    wynik_terminu = {"termin": f"{check_in} - {check_out}", "pokoje": []}

    try:
        print(f"   📡 Otwieranie URL: {target_url}")
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)

        # Zaakceptuj cookies
        try:
            await page.click("text=Zaakceptuj wszystko", timeout=3000)
            await asyncio.sleep(1)
        except:
            print("   ℹ️ Brak przycisku cookies")

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

        # Zapisz surowy HTML do pliku debugowego
        html_content = await page.content()
        debug_file = f"debug_html_{check_in}.html"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"   💾 Zapisano HTML do {debug_file}")

        # Scrape ceny - ULEPSZONA WERSJA
        pokoje_dane = await page.evaluate('''() => {
            const wyniki = [];
            const seen = new Set();

            // METODA 1: Szukaj elementów z klasą zawierającą "apartment" lub "room"
            const apartmentElements = document.querySelectorAll('[class*="apartment"], [class*="room"], [class*="product"]');
            console.log("Znalezione elementy apartamentów:", apartmentElements.length);

            apartmentElements.forEach(el => {
                const text = el.innerText?.trim() || '';
                if (!text || text.length === 0) return;
                
                // Szukaj ceny
                const cenaMatch = text.match(/(\d+(?:\s*|\s)*zł)/);
                const nazwaMatch = text.match(/Apartament\s+([^\\n]*)/);
                
                if (cenaMatch && nazwaMatch) {
                    const nazwa = nazwaMatch[1].trim().substring(0, 100);
                    if (!seen.has(nazwa)) {
                        wyniki.push({
                            nazwa: nazwa,
                            cena: cenaMatch[1]
                        });
                        seen.add(nazwa);
                        console.log(`Znaleziono: ${nazwa} - ${cenaMatch[1]}`);
                    }
                }
            });

            // METODA 2: Jeśli metoda 1 nie znalazła, szukaj w całym tekście
            if (wyniki.length === 0) {
                const bodyText = document.body.innerText;
                const lines = bodyText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                
                for (let i = 0; i < lines.length; i++) {
                    if (lines[i].includes('Apartament')) {
                        const nazwa = lines[i].substring(0, 100);
                        // Szukaj ceny w następnych 10 linach
                        for (let j = i + 1; j < Math.min(i + 10, lines.length); j++) {
                            if (lines[j].match(/\\d+\\s*zł/)) {
                                if (!seen.has(nazwa)) {
                                    wyniki.push({
                                        nazwa: nazwa,
                                        cena: lines[j]
                                    });
                                    seen.add(nazwa);
                                    console.log(`Znaleziono (metoda 2): ${nazwa} - ${lines[j]}`);
                                }
                                break;
                            }
                        }
                    }
                }
            }

            console.log("Razem znaleziono apartamentów:", wyniki.length);
            return wyniki;
        }''')

        print(f"   📊 Znaleziono apartamentów: {len(pokoje_dane)}")

        if pokoje_dane and len(pokoje_dane) > 0:
            wynik_terminu["pokoje"] = pokoje_dane
            
            # Wyślij na Telegram NATYCHMIAST
            msg = f"<b>📊 Odczytane Ceny Poznań Apartments ({check_in} - {check_out}):</b>\n\n"
            for i, p in enumerate(pokoje_dane, 1):
                msg += f"{i}. <b>{p['nazwa']}</b>: {p['cena']}\n"
            
            msg += f"\n<i>Razem: {len(pokoje_dane)} apartamentów</i>"
            
            wyslij_wiadomosc_telegram(msg)
            print(f"   ✓ Wysłano na Telegram")
        else:
            # Wyślij alert na Telegram
            error_msg = f"⚠️ <b>BRAK DANYCH</b> dla {check_in} - {check_out}\n"
            error_msg += f"Sprawdź plik debug_html_{check_in}.html"
            wyslij_wiadomosc_telegram(error_msg)
            print(f"   ⚠️ Nie znaleziono danych dla terminu")

    except Exception as e:
        print(f"   ❌ Błąd: {e}")
        error_msg = f"❌ <b>BŁĄD SCRAPOWANIA</b>\nTermin: {check_in} - {check_out}\nBłąd: {str(e)}"
        wyslij_wiadomosc_telegram(error_msg)

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
    
    print("\n" + "=" * 60)
    print("✅ GOTOWE!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(pobierz_i_wyslij())
