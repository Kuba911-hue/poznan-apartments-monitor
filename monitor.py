async def sprawdz_termin(page, url):
    await page.goto(url, wait_until="networkidle")
    
    # Poprawne wcięcie: 4 spacje (lub 8 jeśli jest wewnątrz pętli/try)
    pokoje_dane = await page.evaluate('''() => {
        const wyniki = [];
        const headers = Array.from(document.querySelectorAll('h2, h3, h4, .room-name, [class*="title"]'))
            .filter(el => el.innerText && el.innerText.includes('Apartament'));

        headers.forEach(header => {
            const nazwa = header.innerText.trim();
            const card = header.closest('.room-card, .room-item, [class*="RoomCard"], [class*="room-row"]') || header.parentElement.parentElement;
            
            if (card) {
                const text = card.innerText;
                const lines = text.split('\\n').map(l => l.trim());
                
                const cenaLine = lines.find(l => 
                    l.includes('zł') && 
                    /\\d/.test(l) && 
                    !l.toLowerCase().includes('przed obniżką') && 
                    !l.toLowerCase().includes('30 dni') &&
                    !l.toLowerCase().includes('najniższa')
                );

                if (cenaLine) {
                    const match = cenaLine.match(/(\\d+[\\d\\s.]*(?:,\\d{2})?\\s*zł)/);
                    const czystaCena = match ? match[1] : cenaLine;
                    wyniki.push({ nazwa: nazwa, cena: czystaCena });
                }
            }
        });

        return wyniki;
    }''')

    return pokoje_dane
