#!/usr/bin/env bash
# Sobe o painel de Guaranésia/MG.
set -e
python -m pip install -r requirements.txt
streamlit run app.py
