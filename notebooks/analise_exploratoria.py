"""
Análise exploratória — Guaranésia/MG
====================================
Roda a ingestão ao vivo e imprime um relatório no terminal. Serve para (a)
conferir se as APIs estão respondendo hoje e (b) inspecionar os dados brutos
antes de abrir o painel.

Uso:
    python notebooks/analise_exploratoria.py

Dá para colar cada bloco numa célula de Jupyter, se preferir notebook.
"""
from __future__ import annotations

import sys
from pathlib import Path

# permite rodar de dentro de notebooks/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import Pandas as pd
from src import ingestao, processamento as proc
import config

pd.set_option("display.width", 120)
pd.set_option("display.float_format", lambda v: f"{v:,.2f}")


def linha(txt=""):
    print(txt)


def secao(t):
    linha("\n" + "=" * 70)
    linha(t)
    linha("=" * 70)


secao(f"POPULAÇÃO — {config.NOME_MUNICIPIO}/{config.UF} (cód. {config.COD_MUNICIPIO})")
serie, meta = ingestao.serie_populacao()
print(proc.df_populacao(serie).to_string(index=False))
print(f"\n[proveniência] origem={meta.origem} | fonte={meta.fonte} | ano={meta.ano}")

secao(f"DESPESA POR FUNÇÃO — exercício {config.ANO_ALVO} (SICONFI RREO Anexo 02)")
bim, desp, metad = ingestao.bimestre_mais_recente(config.ANO_ALVO)
dff = proc.df_despesa_funcao(desp)
if not dff.empty:
    print(f"Bimestre publicado mais recente: {bim}º")
    print(dff.to_string(index=False))
    print(f"\nTotal empenhado (funções de interesse): "
          f"R$ {dff['empenhado'].sum():,.2f}")
else:
    print("Sem execução por função publicada para o ano (ou API fora do ar agora).")
print(f"\n[proveniência] origem={metad.origem} | fonte={metad.fonte} | {metad.detalhe}")

secao("RECEITA x DESPESA (totais)")
rec, metar = ingestao.receita_e_despesa(config.ANO_ALVO, bim or 6)
print(rec)
print(f"[proveniência] origem={metar.origem} | fonte={metar.fonte}")

secao("RESUMO DE PROVENIÊNCIA")
print("Legenda: 'api'/'cache' = dado oficial ao vivo | 'semente' = base verificada de fallback.")
print(f"  População ......... {meta.origem}")
print(f"  Despesa/função .... {metad.origem}")
print(f"  Receita/despesa ... {metar.origem}")
