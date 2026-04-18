# Predikce fotbalových zápasů pomocí AI/ML


Projekt umí:
- predikovat výsledek zápasu: `HOME / DRAW / AWAY`
- odhadnout počet domácích a venkovních gólů
- dopočítat očekávaný počet gólů celkem
- určit predikci pro `Under / Over 2.5`
- exportovat výsledky do JSON souboru pro frontend

---

## Hlavní myšlenka projektu


- dataset vzniká vlastním crawlerem z reálných dat
- vstupní features jsou relativně snadno vysvětlitelné
- používají se pouze informace známé před zápasem
- trénink modelů probíhá v jednom notebooku
- frontend slouží jako lehká prezentační vrstva nad vygenerovaným JSON

---

## Použité ligy a sezóny

Používají se tyto ligy:
- `39` — Premier League
- `78` — Bundesliga
- `61` — Ligue 1
- `135` — Serie A
- `140` — La Liga

Výchozí sezóny:
- `2020 2021 2022 2023 2024 2025`

Poznámka:
- v API-Football je sezóna označena počátečním rokem
- sezóna `2025` tedy znamená sezonu `2025/2026`

---

## Struktura projektu

```text
README.md
requirements.txt
.env.example
spustit_projekt.bat
index.html
styles.css
script.js
src/
    config.py
    crawler.py
    fixtures.py
    feature_snapshots.py
    feature_updates.py
    model_runtime.py
    predict.py
    prediction_rows.py
    prediction_export.py
    utils.py
data/
    raw/
    processed/
models/
notebooks/
    training.ipynb