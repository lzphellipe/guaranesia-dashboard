"""
Camada de processamento: transforma dados crus em DataFrames prontos para o
painel. Sem chamadas de rede aqui — recebe o que a ingestão devolveu e aplica
pandas. Separar ingestão de transformação deixa cada parte testável sozinha.
"""
from __future__ import annotations

import pandas as pd

import config
from src import dados_semente as sem


# --- KPIs do cabeçalho (antes estavam CHUMBADOS no app.py) -------------------
def kpis_cabecalho(serie_pop: list[dict]) -> list[dict]:
    """Monta os cartões do topo a partir da camada de dados, não do app."""
    ultimo = serie_pop[-1] if serie_pop else {"valor": None, "ano": None}
    eco, edu = sem.ECONOMIA, sem.EDUCACAO
    return [
        {"rotulo": "População", "valor": ultimo["valor"], "tipo": "int",
         "nota": f'ref. {ultimo["ano"]}'},
        {"rotulo": "PIB municipal", "valor": eco["pib_reais"], "tipo": "reais_compacto",
         "nota": f'ref. {eco["_ano"]}'},
        {"rotulo": "PIB per capita", "valor": eco["pib_per_capita_reais"], "tipo": "reais_compacto",
         "nota": f'ref. {eco["_ano"]}'},
        {"rotulo": "IDHM", "valor": edu["idhm"], "tipo": "idhm",
         "nota": f'{edu["idhm_ano"]}'},
    ]


def df_populacao(serie: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(serie).sort_values("ano").reset_index(drop=True)
    df["variacao_pct"] = df["valor"].pct_change().mul(100).round(1)
    return df


def df_despesa_funcao(linhas: list[dict]) -> pd.DataFrame:
    if not linhas:
        return pd.DataFrame(columns=["funcao", "empenhado", "participacao_pct"])
    df = pd.DataFrame(linhas)
    total = df["empenhado"].sum()
    df["participacao_pct"] = (df["empenhado"] / total * 100).round(1) if total else 0
    return df.sort_values("empenhado", ascending=False).reset_index(drop=True)


def df_cor_raca() -> pd.DataFrame:
    d = {k: v for k, v in sem.COR_RACA_2010.items() if not k.startswith("_")}
    df = pd.DataFrame({"cor_raca": list(d), "pessoas": list(d.values())})
    df["participacao_pct"] = (df["pessoas"] / df["pessoas"].sum() * 100).round(1)
    return df


def df_estrutura_etaria() -> pd.DataFrame:
    d = {k: v for k, v in sem.ESTRUTURA_ETARIA.items() if not k.startswith("_")}
    return pd.DataFrame({"faixa": list(d), "percentual": list(d.values())})


def df_valor_adicionado() -> pd.DataFrame:
    d = {k: v for k, v in sem.VALOR_ADICIONADO.items() if not k.startswith("_")}
    return pd.DataFrame({"setor": list(d), "percentual": list(d.values())})


def df_saneamento() -> pd.DataFrame:
    s = sem.SANEAMENTO
    return pd.DataFrame({
        "indicador": ["Água encanada", "Energia elétrica", "Urbanização"],
        "cobertura_pct": [s["com_agua_pct"], s["com_energia_pct"], s["urbanizacao_pct"]],
    })


def df_pisos(saude_pct: float | None, educacao_pct: float | None) -> pd.DataFrame:
    """
    Compara o percentual OFICIAL aplicado (vindo dos Anexos 12/08) com o piso
    constitucional. Agora fecha o laço: usa o dado reportado, não um cálculo
    solto. Onde não há dado, marca como indisponível.
    """
    linhas = []
    for area, aplicado, piso in [
        ("Saúde", saude_pct, config.PISO_SAUDE * 100),
        ("Educação", educacao_pct, config.PISO_EDUCACAO * 100),
    ]:
        linhas.append({
            "area": area,
            "piso_pct": piso,
            "aplicado_pct": aplicado,
            "cumpre": (aplicado >= piso) if aplicado is not None else None,
            "folga_pp": round(aplicado - piso, 1) if aplicado is not None else None,
        })
    return pd.DataFrame(linhas)
