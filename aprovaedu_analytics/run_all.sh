#!/usr/bin/env bash
# Executa o pipeline completo: ETL -> análises -> dashboard
set -e
python src/etl.py
python src/analysis.py
python src/build_dashboard.py
echo "Pipeline concluído. Veja outputs/ e data/processed/."
