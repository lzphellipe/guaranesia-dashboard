"""
Configuração central do painel de Guaranésia/MG.

Um único lugar para códigos, endpoints e constantes legais. Nenhuma
regra de negócio aqui — só parâmetros que o resto do projeto importa.
"""
from __future__ import annotations
from pathlib import Path

# --- Identidade do ente ------------------------------------------------------
COD_MUNICIPIO = "3128303"          # código IBGE de Guaranésia
NOME_MUNICIPIO = "Guaranésia"
UF = "MG"
COD_UF = "31"

# --- Diretórios --------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent
CACHE_DIR = RAIZ / "cache"
CACHE_DIR.mkdir(exist_ok=True)
DB_PATH = CACHE_DIR / "historico.sqlite"
CACHE_TTL_HORAS = 24               # relatórios fiscais mudam por bimestre

# --- Endpoints de APIs abertas ----------------------------------------------
IBGE_LOCALIDADES = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios/{cod}"
IBGE_AGREGADOS = "https://servicodados.ibge.gov.br/api/v3/agregados/{agregado}/periodos/{periodos}/variaveis/{variavel}"
SICONFI_BASE = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
SICONFI_EXTRATOS = f"{SICONFI_BASE}/extrato_entregas"   # o que já foi homologado

# Tabelas SIDRA usadas
SIDRA_ESTIMATIVA_POP = 6579        # estimativas anuais de população
SIDRA_CENSO_2022_POP = 9514        # população do Censo 2022 (por idade/sexo)

# --- SICONFI: nomes de anexo e rótulos de coluna (schema real da API) --------
ANEXO_DESPESA_FUNCAO = "RREO-Anexo+02"   # despesa por função/subfunção
ANEXO_BALANCO = "RREO-Anexo+01"          # receita/despesa (balanço orçamentário)
ANEXO_MDE = "RREO-Anexo+08"              # educação — aplicação em MDE
ANEXO_SAUDE = "RREO-Anexo+12"            # saúde — aplicação em ASPS

# Rótulo da coluna que traz o empenhado ACUMULADO até o bimestre no Anexo 02.
# A coluna exata é "DESPESAS EMPENHADAS ATÉ O BIMESTRE (f)"; casamos por tokens
# normalizados (sem acento, maiúsculo) para tolerar variações entre anos.
COL_EMPENHADO_TOKENS = ("EMPENHADAS", "ATE O BIMESTRE")
COL_EMPENHADO_EXCLUI = ("NO BIMESTRE",)

# --- Funções de governo (Portaria MOG 42/1999): código de 2 dígitos → nome ---
# Identificamos a função pelo CÓDIGO (robusto), não pelo texto livre.
FUNCAO_CODIGOS = {
    4: "Administração",
    6: "Segurança pública",
    8: "Assistência social",
    9: "Previdência social",
    10: "Saúde",
    12: "Educação",
    13: "Cultura",
    14: "Direitos da cidadania",
    15: "Urbanismo",
    16: "Habitação",
    17: "Saneamento",
    18: "Gestão ambiental",
    20: "Agricultura",
    23: "Comércio e serviços",
    26: "Transporte",
    27: "Desporto e lazer",
    28: "Encargos especiais",
}

# --- Regras legais de gasto mínimo (para leitura de accountability) ----------
PISO_SAUDE = 0.15                  # LC 141/2012 — mínimo em ASPS
PISO_EDUCACAO = 0.25               # CF art. 212 — mínimo em MDE

# Ano-alvo. O projeto tenta este ano primeiro e recua se ainda não publicado.
ANO_ALVO = 2026

USER_AGENT = "painel-guaranesia/1.1 (dados-publicos; ciencia-de-dados)"
