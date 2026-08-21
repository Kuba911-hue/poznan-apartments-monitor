import os
import asyncio
import requests
from playwright.async_api import async_playwright

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

CHECK_IN = "2026-09-05"
CHECK_OUT = "2026-09-06"

def wyslij_telegram(tekst):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": tekst, "parse_mode": "HTML"})

def wyslij_zdjecie_telegram(sciezka_pliku, podpis):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(sciezka_pliku, "rb") as photo:
        requests.post(
            url, 
            data={"chat_id": CHAT_ID, "caption": podpis, "parse_mode": "HTML"}, 
            files={"photo": photo}
        )

async def pobierz_i_wyslij():
    print("Otwieranie strony i pobieranie danych...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        page.set_default_timeout(60000)

        target_url = f"https://booking.profitroom.com/pl/poznanapartments/pricelist/rooms/?check-in={CHECK_IN}&check-out={CHECK_OUT}&currency=PLN&r1_adults=2"
        
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

            # Przewijanie pod ładowanie obrazów
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

            # Zdjęcie całej strony
            foto_path = "cennik_pelnastrona.png"
            await page.screenshot(path=foto_path, full_page=True)
            wyslij_zdjecie_telegram(foto_path, f"<b>📊 Cennik Poznań Apartments</b>\n🗓 {CHECK_IN} - {CHECK_OUT}")

            # Odczyt cen i nazw
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
                msg = f"<b>📊 Odczytane Ceny Poznań Apartments ({CHECK_IN} - {CHECK_OUT}):</b>\n\n"
                for p in pokoje_dane:
                    msg += f"• <b>{p['nazwa']}</b>: 🟢 <b>{p['cena']}</b>\n"
                wyslij_telegram(msg)
                print("Sukces!")

        except Exception as e:
            print(f"Błąd: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(pobierz_i_wyslij())
