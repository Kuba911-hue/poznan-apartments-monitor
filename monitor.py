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
            // Usuwamy spacje niełamliwe i zwykłe
            let clean = cenaStr.replace(/\\s+/g, '').replace(',', '.');
            // Wyciągamy pierwszą poprawną kwotę (cyfry i ew. kropka)
            let match = clean.match(/(\\d+(?:\\.\\d{{1,2}})?)/);
            return match ? parseFloat(match[1]) : null;
        }}

        if (rawData.length > 0) {{
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
                        if (kwota && kwota < minPrice) {{
                            minPrice = kwota;
                            minRoom = p.nazwa + " (" + kwota + " zł)";
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
