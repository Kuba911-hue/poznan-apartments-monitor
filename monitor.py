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
            --bg: #f8fafc; --card-bg: #ffffff; --text-main: #0f172a; 
            --text-muted: #64748b; --primary: #2563eb; --border: #e2e8f0; 
            --success: #16a34a; --danger: #dc2626;
        }
        @media (prefers-color-scheme: dark) {
            :root {
                --bg: #0f172a; --card-bg: #1e293b; --text-main: #f8fafc;
                --text-muted: #94a3b8; --primary: #3b82f6; --border: #334155;
            }
        }
        body { font-family: 'Inter', sans-serif; margin: 0; padding: 24px; background: var(--bg); color: var(--text-main); }
        .container { max-width: 1100px; margin: 0 auto; }
        header { margin-bottom: 24px; text-align: center; }
        h1 { font-size: 26px; font-weight: 700; margin: 0 0 6px 0; }
        .control-panel { background: var(--card-bg); padding: 18px 24px; border-radius: 12px; border: 1px solid var(--border); margin-bottom: 24px; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
        select { padding: 10px 14px; font-size: 15px; border-radius: 8px; border: 1px solid var(--border); background: var(--card-bg); color: var(--text-main); cursor: pointer; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card { background: var(--card-bg); padding: 18px 20px; border-radius: 12px; border: 1px solid var(--border); }
        .stat-title { font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 6px; }
        .stat-value { font-size: 22px; font-weight: 700; color: var(--primary); }
        .main-card { background: var(--card-bg); padding: 24px; border-radius: 12px; border: 1px solid var(--border); margin-bottom: 24px; }
        .chart-box { position: relative; height: 400px; width: 100%; }
        table { width: 100%; border-collapse: collapse; margin-top: 12px; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid var(--border); font-size: 14px; }
        th { color: var(--text-muted); font-weight: 600; }
        .badge-down { color: var(--success); font-weight: 600; }
        .badge-up { color: var(--danger); font-weight: 600; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Monitor Ceny Poznań Apartments</h1>
            <p style="color: var(--text-muted); margin:0;">Automatyczne śledzenie stawek w terminach weekendowych</p>
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
                <div class="stat-title">Średnia cena</div>
                <div class="stat-value" id="avgPrice" style="color: var(--text-main);">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Najtańszy apartament</div>
                <div class="stat-value" id="minRoom" style="font-size: 14px; color: var(--text-main); font-weight: 600;">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">Liczba odczytów</div>
                <div class="stat-value" id="totalChecks" style="color: var(--text-main);">-</div>
            </div>
        </div>

        <div class="main-card">
            <div style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">📈 Wykres zmian cen</div>
            <div class="chart-box">
                <canvas id="priceChart"></canvas>
            </div>
        </div>

        <div class="main-card">
            <div style="font-size: 16px; font-weight: 600; margin-bottom: 12px;">📋 Ostatnie aktualne ceny</div>
            <div style="overflow-x: auto;">
                <table id="priceTable">
                    <thead>
                        <tr>
                            <th>Apartament</th>
                            <th>Ostatnia cena</th>
                            <th>Poprzednia cena</th>
                            <th>Zmiana</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let historiaData = [];
        let myChart = null;

        async function wczytajDane() {
            try {
                // Dodajemy cache buster by unikać problemów z odświeżaniem na stronach np. GitHub Pages
                const res = await fetch('historia.json?t=' + new Date().getTime());
                historiaData = await res.json();
                
                const terminySet = new Set();
                historiaData.forEach(entry => {
                    if (entry.dane) {
                        entry.dane.forEach(item => {
                            if (item.pokoje && item.pokoje.length > 0) terminySet.add(item.termin);
                        });
                    }
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
            if (!wybranyTermin) return;

            const czasy = [];
            const pokojeMap = {};

            let lowestPrice = Infinity;
            let lowestRoomName = "-";
            let totalPriceSum = 0;
            let priceCount = 0;

            historiaData.forEach(entry => {
                if (!entry.dane) return;
                const daneTerminu = entry.dane.find(d => d.termin === wybranyTermin);
                if (daneTerminu && daneTerminu.pokoje) {
                    czasy.push(entry.timestamp);
                    daneTerminu.pokoje.forEach(p => {
                        if (!pokojeMap[p.nazwa]) pokojeMap[p.nazwa] = [];
                        const kwota = parseFloat(p.cena.replace(/[^0-9,.]/g, '').replace(',', '.'));
                        pokojeMap[p.nazwa].push(kwota || null);

                        if (kwota) {
                            totalPriceSum += kwota;
                            priceCount++;
                            if (kwota < lowestPrice) {
                                lowestPrice = kwota;
                                lowestRoomName = p.nazwa;
                            }
                        }
                    });
                }
            });

            document.getElementById('minPrice').textContent = lowestPrice !== Infinity ? lowestPrice.toFixed(2) + ' zł' : '-';
            document.getElementById('avgPrice').textContent = priceCount > 0 ? (totalPriceSum / priceCount).toFixed(2) + ' zł' : '-';
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
                pointRadius: 3,
                fill: false,
                tension: 0.1
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
                    plugins: { legend: { position: 'bottom' } },
                    scales: {
                        y: { grid: { color: 'rgba(226, 232, 240, 0.5)' }, title: { display: true, text: 'Cena (PLN)' } },
                        x: { grid: { display: false } }
                    }
                }
            });

            // Tabela
            const tbody = document.querySelector('#priceTable tbody');
            tbody.innerHTML = '';
            Object.keys(pokojeMap).forEach(nazwa => {
                const arr = pokojeMap[nazwa].filter(v => v !== null);
                if (arr.length === 0) return;
                const last = arr[arr.length - 1];
                const prev = arr.length > 1 ? arr[arr.length - 2] : null;

                let diffText = '-';
                let diffClass = '';
                if (prev !== null) {
                    const diff = last - prev;
                    if (diff > 0) {
                        diffText = `+${diff.toFixed(2)} zł ⬆`;
                        diffClass = 'badge-up';
                    } else if (diff < 0) {
                        diffText = `${diff.toFixed(2)} zł ⬇`;
                        diffClass = 'badge-down';
                    } else {
                        diffText = 'Bez zmian';
                    }
                }

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><b>${nazwa}</b></td>
                    <td>${last.toFixed(2)} zł</td>
                    <td>${prev !== null ? prev.toFixed(2) + ' zł' : '-'}</td>
                    <td class="${diffClass}">${diffText}</td>
                `;
                tbody.appendChild(tr);
            });
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
