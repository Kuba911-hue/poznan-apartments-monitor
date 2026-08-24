import os
import json
import asyncio
from datetime import datetime, timedelta
import requests
from playwright.async_api import async_playwright

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

PLIK_HISTORIA = "historia.json"

def wyslij_zdjecie_telegram(zdjecie_path, podpis):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Brak TELEGRAM_TOKEN lub CHAT_ID w zmiennych środowiskowych!")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(zdjecie_path, "rb") as foto:
            payload = {
                "chat_id": CHAT_ID,
                "caption": podpis,
                "parse_mode": "HTML"
            }
            files = {"photo": foto}
            res = requests.post(url, data=payload, files=files, timeout=30)
            if res.status_code == 200:
                print("✅ Powiadomienie Telegram zostało pomyślnie wysłane!")
            else:
                print(f"❌ Błąd wysyłania Telegram API: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ Wyjątek podczas wysyłania zdjęcia na Telegram: {e}")


def zapisz_do_historii(nowe_odczyty):
    nowy_wpis = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "odczyty": nowe_odczyty
    }
    
    historia = []
    if os.path.exists(PLIK_HISTORIA):
        try:
            with open(PLIK_HISTORIA, "r", encoding="utf-8") as f:
                historia = json.load(f)
        except Exception as e:
            print(f"⚠️ Nie udało się wczytać pliku historii, tworzę nowy: {e}")
            historia = []
            
    historia.append(nowy_wpis)
    
    with open(PLIK_HISTORIA, "w", encoding="utf-8") as f:
        json.dump(historia, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Zapisano najnowszy odczyt do {PLIK_HISTORIA}")


def wygeneruj_strone_html():
    historia_json_str = "[]"
    if os.path.exists(PLIK_HISTORIA):
        with open(PLIK_HISTORIA, "r", encoding="utf-8") as f:
            historia_json_str = f.read()

    html_content = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor Cen Poznań Apartments</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f4f6f9;
            color: #333;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            color: #1a252f;
        }}
        .card {{
            background: #fff;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-box {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        .stat-title {{
            font-size: 0.85em;
            color: #64748b;
            text-transform: uppercase;
            font-weight: bold;
        }}
        .stat-value {{
            font-size: 1.4em;
            font-weight: bold;
            color: #0284c7;
            margin-top: 5px;
        }}
        canvas {{
            width: 100% !important;
            max-height: 500px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Monitor Cen Poznań Apartments</h1>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-title">Ostatnie sprawdzenie</div>
                <div class="stat-value" id="lastUpdate">-</div>
            </div>
            <div class="stat-box">
                <div class="stat-title">Najtańszy apartament</div>
                <div class="stat-value" id="cheapestRoom">-</div>
            </div>
            <div class="stat-box">
                <div class="stat-title">Liczba odczytów</div>
                <div class="stat-value" id="totalReads">0</div>
            </div>
        </div>

        <div class="card">
            <h2>📈 Wykres zmian cen</h2>
            <canvas id="priceChart"></canvas>
        </div>
    </div>

    <script>
        const rawData = {historia_json_str};

        function sparsujCene(cenaStr) {{
            if (!cenaStr) return null;
            let clean = cenaStr.replace(/[^0-9.,]/g, '').replace(',', '.');
            let val = parseFloat(clean);
            return isNaN(val) ? null : val;
        }}

        if (rawData && rawData.length > 0) {{
            document.getElementById('totalReads').innerText = rawData.length;
            const lastEntry = rawData[rawData.length - 1];
            document.getElementById('lastUpdate').innerText = lastEntry.timestamp;

            let minPrice = Infinity;
            let minRoom = "-";

            const roomNames = new Set();
            rawData.forEach(entry => {{
                if (entry.odczyty) {{
                    entry.odczyty.forEach(p => {{
                        roomNames.add(p.nazwa);
                        let kwota = sparsujCene(p.cena);
                        if (kwota !== null && kwota < minPrice) {{
                            minPrice = kwota;
                            minRoom = p.nazwa + " (" + kwota.toFixed(2) + " zł)";
                        }}
                    }});
                }}
            }});

            if (minPrice !== Infinity) {{
                document.getElementById('cheapestRoom').innerText = minRoom;
            }}

            const labels = rawData.map(e => e.timestamp);
            const colors = [
                '#2563eb', '#16a34a', '#d97706', '#dc2626', '#9333ea',
                '#0891b2', '#4b5563', '#059669', '#c026d3', '#ea580c'
            ];

            const datasets = Array.from(roomNames).map((roomName, index) => {{
                const data = rawData.map(entry => {{
                    if (!entry.odczyty) return null;
                    const item = entry.odczyty.find(p => p.nazwa === roomName);
                    return item ? sparsujCene(item.cena) : null;
                }});

                return {{
                    label: roomName,
                    data: data,
                    borderColor: colors[index % colors.length],
                    backgroundColor: colors[index % colors.length],
                    tension: 0.2,
                    spanGaps: true
                }};
            }});

            const ctx = document.getElementById('priceChart').getContext('2d');
            new Chart(ctx, {{
                type: 'line',
                data: {{ labels: labels, datasets: datasets }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{ position: 'bottom' }}
                    }},
                    scales: {{
                        y: {{
                            title: {{ display: true, text: 'Cena (PLN)' }}
                        }},
                        x: {{
                            title: {{ display: true, text: 'Data i godzina sprawdzania' }}
                        }}
                    }}
                }}
            }});
        }}
    </script>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("🌐 Wygenerowano plik index.html")


async def sprawdz_termin(page, check_in, check_out):
    url = f"https://www.poznan-apartments.pl/pl/apartamenty?check-in={check_in}&check-out={check_out}"
    print(f"🔗 Otwieram stronę: {url}")
    
    try:
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(4)
        
        try:
            cookie_btn = page.locator("button:has-text('Akceptuj'), button:has-text('Zgadzam się'), .cookie-btn, #accept-cookies")
            if await cookie_btn.count() > 0:
                await cookie_btn.first.click(timeout=3000)
        except Exception:
            pass

        foto_path = "pobieranie.png"
        await page.screenshot(path=foto_path, full_page=True)
        print("📸 Wykonano zrzut ekranu strony.")

        pokoje_dane = await page.evaluate('''() => {
            const wyniki = [];
            const elms = document.querySelectorAll('div, section, article');
            
            elms.forEach(el => {
                const text = el.innerText || '';
                if (text.includes('Apartament') && text.includes('zł')) {
                    const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                    for (let i = 0; i < lines.length; i++) {
                        if (lines[i].startsWith('Apartament')) {
                            const nazwa = lines[i];
                            let cena = '';
                            for (let j = i; j < Math.min(i + 10, lines.length); j++) {
                                const line = lines[j];
                                if (line.includes('zł') && 
                                    !line.toLowerCase().includes('najniższa') && 
                                    !line.toLowerCase().includes('30 dni')) {
                                    cena = line;
                                    break;
                                }
                            }
                            if (nazwa && cena) {
                                if (!wyniki.some(w => w.nazwa === nazwa)) {
                                    wyniki.push({ nazwa, cena });
                                }
                            }
                        }
                    }
                }
            });
            return wyniki;
        }''')

        print(f"🔎 Odczytane pokoje i ceny: {pokoje_dane}")

        if pokoje_dane and len(pokoje_dane) > 0:
            msg = f"📊 <b>Odczytane Ceny Poznań Apartments ({check_in} - {check_out}):</b>\n\n"
            for p in pokoje_dane:
                msg += f"• <b>{p['nazwa']}</b>: 🟢 <b>{p['cena']}</b>\n"
            
            wyslij_zdjecie_telegram(foto_path, msg)
            zapisz_do_historii(pokoje_dane)
        else:
            print("⚠️ Nie odnaleziono cen na stronie – wysyłam powiadomienie ostrzegawcze.")
            wyslij_zdjecie_telegram(
                foto_path, 
                f"⚠️ <b>Uwaga:</b> Wykonano zrzut ekranu dla terminu {check_in} - {check_out}, ale skrypt nie zdołał odczytać bloku cen z widoku strony."
            )

    except Exception as e:
        print(f"❌ Błąd w sprawdz_termin: {e}")


async def main():
    dzis = datetime.now()
    dni_do_soboty = (5 - dzis.weekday()) % 7
    if dni_do_soboty == 0:
        dni_do_soboty = 7
        
    sobota = dzis + timedelta(days=dni_do_soboty)
    niedziela = sobota + timedelta(days=1)
    
    check_in = sobota.strftime("%Y-%m-%d")
    check_out = niedziela.strftime("%Y-%m-%d")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        await sprawdz_termin(page, check_in, check_out)
        await browser.close()

    wygeneruj_strone_html()

if __name__ == "__main__":
    asyncio.run(main())
