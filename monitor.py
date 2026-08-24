name: ✈️ Daily Google Flights Price Check

on:
  schedule:
    - cron: '0 7,12,19 * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  run-bot:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout kodu
        uses: actions/checkout@v4

      - name: Konfiguracja Pythona
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Instalacja bibliotek
        run: pip install -r requirements.txt

      - name: Uruchomienie bota i generowanie strony
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          SERPAPI_KEY: ${{ secrets.SERPAPI_KEY }}
        run: python flight_tracker.py

      - name: Publikacja strony na GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: .
