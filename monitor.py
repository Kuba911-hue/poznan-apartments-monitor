        # Pobieranie struktur cen z kodu strony (precyzyjne parsowanie kart)
        pokoje_dane = await page.evaluate('''() => {
            const wyniki = [];
            // Profitroom zwykle grupuje pokoje w dedykowanych kontenerach/kartach
            const cards = document.querySelectorAll('.room-card, .room-item, [class*="RoomCard"], [class*="room-row"]');
            
            if (cards.length > 0) {
                cards.forEach(card => {
                    const titleEl = card.querySelector('h2, h3, h4, [class*="title"], [class*="name"]');
                    const priceEl = card.querySelector('[class*="price-value"], [class*="price"], .amount');
                    
                    if (titleEl && priceEl) {
                        const nazwa = titleEl.innerText.trim();
                        const cena = priceEl.innerText.trim();
                        if (nazwa && cena && cena.includes('zł')) {
                            wyniki.push({ nazwa, cena });
                        }
                    }
                });
            }

            // Fallback: jeśli nie znaleziono specyficznych klas Profitrooma
            if (wyniki.length === 0) {
                const allElements = document.querySelectorAll('div, section');
                const przetworzone = new Set();

                allElements.forEach(el => {
                    const header = el.querySelector('h2, h3, h4');
                    if (header && header.innerText.includes('Apartament') && !przetworzone.has(header.innerText.trim())) {
                        const nazwa = header.innerText.trim();
                        // Szukamy ceny wewnątrz tego samego kontenera
                        const text = el.innerText;
                        const match = text.match(/(\\d+[\\d\\s,.]*\\s*zł)/);
                        if (match) {
                            wyniki.push({ nazwa: nazwa, cena: match[1] });
                            przetworzone.add(nazwa);
                        }
                    }
                });
            }

            return wyniki;
        }''')
