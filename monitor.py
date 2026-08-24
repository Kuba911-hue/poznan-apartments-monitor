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
    <title>Historia Ceny Poznań Apartments</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 20px; background: #f4f6f8; color: #333; }
        .container { max-width: 1000px; margin: auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        h1 { text-align: center; color: #1a202c; }
        .chart-box { margin-top: 30px; position: relative; height: 400px; }
        select { padding: 10px; font-size: 16px; border-radius: 8px; border: 1px solid #ccc; margin-bottom: 20px; width: 100%; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Historia Zmian Ceny Poznań Apartments</h1>
        <label for="terminSelect"><b>Wybierz termin:</b></label>
        <select id="terminSelect" onchange="aktualizujWykres()"></select>
        <div class="chart-box">
            <canvas id="priceChart"></canvas>
        </div>
    </div>

    <script>
        let historiaData = [];
        let myChart = null;

        async function wczytajDane() {
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

            aktualizujWykres();
        }

        function aktualizujWykres() {
            const wybranyTermin = document.getElementById('terminSelect').value;
            const czasy = [];
            const pokojeMap = {};

            historiaData.forEach(entry => {
                const daneTerminu = entry.dane.find(d => d.termin === wybranyTermin);
                if (daneTerminu) {
                    czasy.push(entry.timestamp);
                    daneTerminu.pokoje.forEach(p => {
                        if (!pokojeMap[p.nazwa]) pokojeMap[p.nazwa] = [];
                        const kwota = parseFloat(p.cena.replace(/[^0-9,.]/g, '').replace(',', '.'));
                        pokojeMap[p.nazwa].push(kwota || null);
                    });
                }
            });

            const datasets = Object.keys(pokojeMap).map((nazwa, idx) => {
                const kolory = ['#3182ce', '#38a169', '#dd6b20', '#e53e3e', '#805ad5', '#d69e2e', '#319795'];
                return {
                    label: nazwa,
                    data: pokojeMap[nazwa],
                    borderColor: kolory[idx % kolory.length],
                    backgroundColor: kolory[idx % kolory.length],
                    fill: false,
                    tension: 0.2
                };
            });

            if (myChart) myChart.destroy();
            const ctx = document.getElementById('priceChart').getContext('2d');
            myChart = new Chart(ctx, {
                type: 'line',
                data: { labels: czasy, datasets: datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { title: { display: true, text: 'Cena (PLN)' } },
                        x: { title: { display: true, text: 'Data odczytu' } }
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

async def sprawdz_termin(page, check_in, check_out):
    target_url = f"https://booking.profitroom.com/pl/poznanapartments/pricelist/rooms/?check-in={check_in}&check-out={check_out}&currency=PLN&r1_adults=2"
    wynik_terminu = {"termin": f"{check_in} - {check_out}", "pokoje": []}

    try:
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)

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
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
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
