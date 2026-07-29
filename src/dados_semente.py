"""
Dados-semente (fallback) de Guaranésia/MG.

Todo número aqui foi coletado de fonte oficial e carrega `fonte` e `ano`.
Servem para dois fins:
  1. o painel funciona mesmo sem rede (aula, apresentação offline);
  2. dão contexto histórico que as APIs de execução 2026 não trazem.

IMPORTANTE: quando a API responde, o dado ao vivo tem prioridade sobre isto.
Nunca apague a etiqueta de fonte/ano — ela é o que torna o painel auditável.
"""
from __future__ import annotations

# --- Demografia --------------------------------------------------------------
POPULACAO = [
    {"ano": 2010, "valor": 18714, "tipo": "Censo", "fonte": "IBGE — Censo 2010"},
    {"ano": 2022, "valor": 19150, "tipo": "Censo", "fonte": "IBGE — Censo 2022"},
    {"ano": 2025, "valor": 19600, "tipo": "Estimativa", "fonte": "IBGE — Estimativa 1º/jul/2025 (aprox.)"},
]

SEXO_2010 = {
    "Homens": 9498,
    "Mulheres": 9216,
    "_fonte": "IBGE — Censo 2010",
    "_ano": 2010,
}

COR_RACA_2010 = {
    "Branca": 12390,
    "Parda": 5422,
    "Preta": 840,
    "Amarela/Indígena": 62,
    "_fonte": "IBGE — Censo 2010",
    "_ano": 2010,
}

ESTRUTURA_ETARIA = {
    "0–14": 17.7,
    "15–24": 13.1,
    "25–39": 22.8,
    "40–64": 33.3,
    "65+": 13.0,
    "_fonte": "IBGE (estrutura recente)",
    "_ano": 2022,
}

INDICADORES_DEMO = {
    "densidade_hab_km2": 65,
    "indice_envelhecimento_pct": 73.7,
    "razao_dependencia_pct": 44.4,
    "eleitores": 13476,
    "alfabetizados_2010": 15644,
    "area_km2": 294.83,
    "_fonte": "IBGE Cidades / TSE",
}

# --- Economia ----------------------------------------------------------------
ECONOMIA = {
    "pib_reais": 811_200_000,
    "pib_per_capita_reais": 42_400,
    "empregos_formais": 6600,
    "remuneracao_media_reais": 3200,
    "empresas": 553,
    "_fonte": "IBGE — Contas Municipais / RAIS-CAGED",
    "_ano": 2021,
}

VALOR_ADICIONADO = {
    "Indústria": 36.5,
    "Serviços": 34.2,
    "Administração pública": 20.3,
    "Agropecuária": 9.0,
    "_fonte": "IBGE — Contas Municipais",
    "_ano": 2021,
}

# --- Educação ----------------------------------------------------------------
EDUCACAO = {
    "estabelecimentos": 19,
    "matriculas_fundamental": 2971,
    "matriculas_medio": 811,
    "docentes_fundamental": 155,
    "docentes_medio": 37,
    "idhm": 0.701,
    "idhm_ano": 2010,
    "_fonte": "IBGE / Atlas Brasil (PNUD-Ipea-FJP)",
}

# --- Saúde -------------------------------------------------------------------
SAUDE = {
    "estabelecimentos_total": 24,
    "estabelecimentos_sus": 10,
    "_fonte": "IBGE",
    "_ano": 2019,
}

# --- Saneamento / habitação (Censo 2010, indicador domiciliar consolidado) ---
SANEAMENTO = {
    "domicilios_permanentes": 5909,
    "com_agua_pct": 88.3,
    "com_energia_pct": 99.9,
    "urbanizacao_pct": 90.0,
    "enderecos_urbanos": 7392,
    "enderecos_rurais": 947,
    "_fonte": "IBGE — Censo 2010",
    "_ano": 2010,
}

# --- Orçamento (arcabouço legal + leis vigentes) -----------------------------
ORCAMENTO_LEGAL = {
    "leis": [
        {"tipo": "LOA — exercício 2025", "lei": "Lei nº 2.928/2024"},
        {"tipo": "LOA — exercício 2026", "lei": "Lei nº 3.045/2025"},
        {"tipo": "PPA 2022–2025", "lei": "Lei nº 2.616/2021"},
    ],
    "_fonte": "Câmara Municipal de Guaranésia",
}

# Despesa por função — SEMENTE ilustrativa (vazia de valores).
# Não fabricamos cifras: se a API do SICONFI não responder, o painel mostra a
# lista de funções sem valor e aponta a fonte, em vez de inventar números.
DESPESA_FUNCAO_INDISPONIVEL = {
    "_fonte": "SICONFI — RREO Anexo 02 (consultar ao vivo)",
    "_aviso": "Valores por função só entram no painel quando vêm da API oficial.",
}

FONTES = {
    "IBGE — Censo": "https://cidades.ibge.gov.br/brasil/mg/guaranesia",
    "SICONFI — Tesouro Nacional": "https://apidatalake.tesouro.gov.br/docs/siconfi/",
    "Portal da Transparência (Prefeitura)": "https://transparencia.guaranesia.mg.gov.br/",
    "Câmara Municipal": "https://www.legislador.com.br/legisladorweb.asp?WCI=ProjetoTramite&ID=364",
    "TCE-MG": "https://www.tce.mg.gov.br/",
}
