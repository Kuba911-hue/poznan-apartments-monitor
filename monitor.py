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
        except Exception:
            historia = []
            
    historia.append(nowy_wpis)
    
    with open(PLIK_HISTORIA, "w", encoding="utf-8") as f:
        json.dump(historia, f, ensure_ascii=False, indent=2)


async def sprawdz_termin(page, check_in, check_out):
    url = f"https://poznanapartments.com/pl/apartamenty?check-in={check_in}&check-out={check_out}"
    print(f"🔗 Otwieram stronę: {url}")
    
    try:
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(5)
        
        try:
            cookie_btn = page.locator("button:has-text('Akceptuj'), button:has-text('Zgadzam się')")
            if await cookie_btn.count() > 0:
                await cookie_btn.first.click(timeout=3000)
        except Exception:
            pass

        foto_path = "pobieranie.png"
        await page.screenshot(path=foto_path, full_page=True)

        pokoje_dane = await page.evaluate('''() => {
            const wyniki = [];
            const karty = document.querySelectorAll('.room-card, .apartment-item, div[class*="room"], div[class*="apartment"], .card');
            
            karty.forEach(karta => {
                const text = karta.innerText || '';
                if (text.includes('zł') && (text.includes('Apartament') || text.includes('Studio'))) {
                    const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                    
                    let nazwa = '';
                    let cena = '';
                    
                    for (let i = 0; i < lines.length; i++) {
                        if (lines[i].toLowerCase().startsWith('apartament') || lines[i].toLowerCase().startsWith('studio')) {
                            nazwa = lines[i];
                        }
                        if (lines[i].includes('zł') && !lines[i].toLowerCase().includes('najniższa')) {
                            cena = lines[i];
                        }
                    }
                    
                    if (nazwa && cena) {
                        if (!wyniki.some(w => w.nazwa === nazwa)) {
                            wyniki.push({ nazwa, cena });
                        }
                    }
                }
            });

            // Fallback gdyby karty nie wyłapały wszystkiego
            if (wyniki.length === 0) {
                const elms = document.querySelectorAll('h2, h3, h4, .title');
                elms.forEach(el => {
                    const parent = el.closest('div') || el.parentElement;
                    if (parent && parent.innerText.includes('zł')) {
                        const lines = parent.innerText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                        let nazwa = el.innerText.trim();
                        let cena = lines.find(l => l.includes('zł') && !l.toLowerCase().includes('najniższa')) || '';
                        if (nazwa && cena && !wyniki.some(w => w.nazwa === nazwa)) {
                            wyniki.push({ nazwa, cena });
                        }
                    }
                });
            }

            return wyniki;
        }''')

        if pokoje_dane and len(pokoje_dane) > 0:
            msg = f"📊 <b>Odczytane Ceny Poznań Apartments ({check_in} - {check_out}):</b>\n\n"
            for p in pokoje_dane:
                msg += f"• <b>{p['nazwa']}</b>: 🟢 <b>{p['cena']}</b>\n"
            
            wyslij_zdjecie_telegram(foto_path, msg)
            zapisz_do_historii(pokoje_dane)
        else:
            wyslij_zdjecie_telegram(
                foto_path, 
                f"⚠️ <b>Uwaga:</b> Wykonano zrzut ekranu dla terminu {check_in} - {check_out}, ale skrypt nie odnalazł ofert."
            )

    except Exception as e:
        print(f"❌ Błąd: {e}")


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

if __name__ == "__main__":
    asyncio.run(main())
