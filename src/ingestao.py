"""
Camada de ingestão: fala com as APIs abertas do IBGE e do SICONFI.

Princípios de engenharia:
  * sessão HTTP com retry exponencial (falha de rede é regra, não exceção);
  * cache em disco com TTL — evita martelar as APIs a cada rerun do Streamlit;
  * PARSERS PUROS separados da rede (`parse_*`) — testáveis com fixtures, sem
    depender de conexão; é o que estava faltando na versão anterior;
  * toda função de rede devolve `(dado, Meta)` com origem/fonte/ano, para o
    painel carimbar a proveniência de cada número.

Nada aqui levanta exceção para cima: se a fonte oficial falha, devolvemos a
semente verificada e sinalizamos.
"""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config
from src import dados_semente as sem

# --- Modos de execução -------------------------------------------------------
OFFLINE = os.getenv("PAINEL_OFFLINE", "0") == "1"   # pula a rede, usa semente
DEMO = os.getenv("PAINEL_DEMO", "0") == "1"         # preenche com ILUSTRATIVOS

_DEMO_FUNCOES = [
    {"funcao": "Saúde", "empenhado": 12_480_000.0},
    {"funcao": "Educação", "empenhado": 11_760_000.0},
    {"funcao": "Administração", "empenhado": 6_180_000.0},
    {"funcao": "Urbanismo", "empenhado": 3_090_000.0},
    {"funcao": "Assistência social", "empenhado": 2_420_000.0},
    {"funcao": "Previdência social", "empenhado": 1_980_000.0},
    {"funcao": "Saneamento", "empenhado": 940_000.0},
    {"funcao": "Segurança pública", "empenhado": 610_000.0},
    {"funcao": "Cultura", "empenhado": 520_000.0},
    {"funcao": "Desporto e lazer", "empenhado": 410_000.0},
]
_DEMO_RECDESP = {"receita_realizada": 46_800_000.0, "despesa_empenhada": 43_200_000.0}
_DEMO_PISOS = {"saude_pct": 22.4, "educacao_pct": 27.1}


# ===========================================================================
# Utilidades de normalização / parsing PURO (sem rede — testável isolado)
# ===========================================================================
def normaliza(texto: str) -> str:
    """Maiúsculo, sem acento, espaços colapsados. Base de todo casamento."""
    if texto is None:
        return ""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().upper()


_RE_FUNCAO = re.compile(r"^\s*(\d{2})\s*-\s*(.+?)\s*$")


def _coluna_empenhado(coluna: str) -> bool:
    n = normaliza(coluna)
    if any(x in n for x in map(normaliza, config.COL_EMPENHADO_EXCLUI)):
        return False
    return all(tok in n for tok in map(normaliza, config.COL_EMPENHADO_TOKENS))


def _valor(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_despesa_funcao(items: list[dict]) -> tuple[list[dict], dict]:
    """
    PARSER PURO do RREO Anexo 02. Recebe a lista `items` da API e devolve
    ([{funcao, codigo, empenhado}], diagnostico).

    Regras (corrigidas em relação à v1, que usava max() cego entre colunas):
      1. só a coluna de empenhado ACUMULADO até o bimestre;
      2. função identificada pelo CÓDIGO de 2 dígitos em `conta` ("10 - Saúde"),
         o que separa função (2 díg.) de subfunção (3 díg.) automaticamente;
      3. linhas intra-orçamentárias são excluídas (evita dupla contagem);
      4. nome canônico vem do código, não do texto livre;
      5. sanidade: se houver duplicata da mesma função, fica a maior e avisa.
    """
    achados: dict[int, float] = {}
    duplicatas: list[str] = []
    total_reportado: Optional[float] = None

    for it in items:
        coluna = it.get("coluna", "")
        if not _coluna_empenhado(coluna):
            continue
        conta = str(it.get("conta", ""))
        rotulo = normaliza(it.get("rotulo", ""))
        conta_n = normaliza(conta)

        # captura o TOTAL para validação posterior
        if "TOTAL" in conta_n and ("III" in conta_n or "I + II" in conta_n):
            total_reportado = _valor(it.get("valor")) or total_reportado
            continue

        # exclui intra-orçamentárias (não dobrar)
        if "INTRA" in conta_n or "INTRA" in rotulo:
            continue

        m = _RE_FUNCAO.match(conta)
        if not m:
            continue
        codigo = int(m.group(1))
        if codigo not in config.FUNCAO_CODIGOS:
            continue
        val = _valor(it.get("valor"))
        if val is None:
            continue
        if codigo in achados:
            duplicatas.append(config.FUNCAO_CODIGOS[codigo])
            achados[codigo] = max(achados[codigo], val)
        else:
            achados[codigo] = val

    linhas = [
        {"funcao": config.FUNCAO_CODIGOS[c], "codigo": c, "empenhado": v}
        for c, v in sorted(achados.items(), key=lambda x: -x[1])
    ]
    soma = sum(achados.values())
    diag = {
        "n_funcoes": len(linhas),
        "soma_funcoes": soma,
        "total_reportado": total_reportado,
        "duplicatas": duplicatas,
        "confere_total": (total_reportado is not None
                          and abs(soma - total_reportado) / total_reportado < 0.02)
        if total_reportado else None,
    }
    return linhas, diag


def parse_percentual_aplicado(items: list[dict], tokens: tuple[str, ...]) -> Optional[float]:
    """
    Extrai o percentual OFICIAL aplicado (ex.: em ASPS no Anexo 12, em MDE no
    Anexo 08). Procura a linha cujo `conta` contém todos os tokens e cujo valor
    é um percentual plausível (0–100).
    """
    toks = [normaliza(t) for t in tokens]
    candidatos = []
    for it in items:
        conta_n = normaliza(it.get("conta", ""))
        if all(t in conta_n for t in toks):
            v = _valor(it.get("valor"))
            if v is not None and 0 <= v <= 100:
                candidatos.append(v)
    if not candidatos:
        return None
    # a linha do percentual aplicado costuma ser única; se houver várias, a
    # última tende a ser o consolidado "até o bimestre"
    return candidatos[-1]


def parse_receita_despesa(items: list[dict]) -> dict:
    """Totais de receita realizada e despesa empenhada do RREO Anexo 01."""
    receita = despesa = None
    for it in items:
        conta = normaliza(it.get("conta", ""))
        coluna = normaliza(it.get("coluna", ""))
        v = _valor(it.get("valor"))
        if v is None:
            continue
        if "TOTAL RECEITAS" in conta and "REALIZADAS" in coluna and "ATE O BIMESTRE" in coluna:
            receita = v if receita is None else max(receita, v)
        if "TOTAL DESPESAS" in conta and "EMPENHADAS" in coluna and "ATE O BIMESTRE" in coluna:
            despesa = v if despesa is None else max(despesa, v)
    return {"receita_realizada": receita, "despesa_empenhada": despesa}


# ===========================================================================
# Infraestrutura HTTP + cache
# ===========================================================================
@dataclass
class Meta:
    origem: str          # 'api' | 'cache' | 'semente' | 'demo'
    fonte: str
    ano: Optional[int] = None
    detalhe: str = ""

    def dict(self) -> dict:
        return asdict(self)


def _sessao() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=4, backoff_factor=0.6,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=("GET",))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept": "application/json"})
    return s


def _cache_path(chave: str) -> Path:
    seguro = "".join(c if c.isalnum() else "_" for c in chave)
    return config.CACHE_DIR / f"{seguro}.json"


def _ler_cache(chave: str) -> Optional[Any]:
    p = _cache_path(chave)
    if not p.exists():
        return None
    if (time.time() - p.stat().st_mtime) / 3600 > config.CACHE_TTL_HORAS:
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _gravar_cache(chave: str, dado: Any) -> None:
    try:
        _cache_path(chave).write_text(json.dumps(dado, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _get_json(url: str, params: dict | None, chave: str, timeout: int = 25):
    """GET com cache+retry. Devolve (json, origem) ou (None, 'erro')."""
    if OFFLINE:
        return None, "erro"
    cache = _ler_cache(chave)
    if cache is not None:
        return cache, "cache"
    try:
        resp = _sessao().get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        dado = resp.json()
        _gravar_cache(chave, dado)
        return dado, "api"
    except Exception:
        return None, "erro"


def _items(dado) -> list[dict]:
    return dado.get("items", []) if isinstance(dado, dict) else []


# ===========================================================================
# IBGE — população
# ===========================================================================
def populacao_estimativa() -> tuple[dict, Meta]:
    url = config.IBGE_AGREGADOS.format(
        agregado=config.SIDRA_ESTIMATIVA_POP, periodos="-1", variavel="9324")
    dado, origem = _get_json(url, {"localidades": f"N6[{config.COD_MUNICIPIO}]"},
                             chave=f"ibge_pop_est_{config.COD_MUNICIPIO}")
    try:
        serie = dado[0]["resultados"][0]["series"][0]
        ano, valor = next(iter(serie["serie"].items()))
        return ({"ano": int(ano), "valor": int(valor)},
                Meta(origem, "IBGE — Estimativa da População (SIDRA 6579)", int(ano)))
    except Exception:
        ultima = sem.POPULACAO[-1]
        return ({"ano": ultima["ano"], "valor": ultima["valor"]},
                Meta("semente", ultima["fonte"], ultima["ano"]))


def serie_populacao() -> tuple[list[dict], Meta]:
    serie = [{"ano": p["ano"], "valor": p["valor"], "tipo": p["tipo"]} for p in sem.POPULACAO]
    est, meta = populacao_estimativa()
    if meta.origem in ("api", "cache"):
        serie = [s for s in serie if s["ano"] != est["ano"]]
        serie.append({"ano": est["ano"], "valor": est["valor"], "tipo": "Estimativa"})
    serie.sort(key=lambda x: x["ano"])
    return serie, meta


# ===========================================================================
# SICONFI — execução orçamentária
# ===========================================================================
def _rreo(ano: int, periodo: int, anexo: str, chave: str):
    return _get_json(f"{config.SICONFI_BASE}/rreo", {
        "an_exercicio": ano, "nr_periodo": periodo, "co_tipo_demonstrativo": "RREO",
        "no_anexo": anexo, "id_ente": config.COD_MUNICIPIO}, chave=chave)


def periodos_publicados(ano: int) -> list[int]:
    """
    Consulta o extrato de entregas para saber QUAIS bimestres já foram
    homologados — evita a varredura cega de 6 chamadas com retry da v1.
    """
    dado, origem = _get_json(config.SICONFI_EXTRATOS, {
        "an_exercicio": ano, "id_ente": config.COD_MUNICIPIO,
        "co_tipo_demonstrativo": "RREO"},
        chave=f"siconfi_extratos_{config.COD_MUNICIPIO}_{ano}")
    periodos = set()
    for it in _items(dado):
        p = it.get("nr_periodo")
        try:
            periodos.add(int(p))
        except (TypeError, ValueError):
            continue
    return sorted(periodos, reverse=True)


def despesa_por_funcao(ano: int, periodo: int) -> tuple[list[dict], Meta]:
    dado, origem = _rreo(ano, periodo, config.ANEXO_DESPESA_FUNCAO,
                         chave=f"siconfi_rreo02_{config.COD_MUNICIPIO}_{ano}_{periodo}")
    linhas, diag = parse_despesa_funcao(_items(dado))
    if linhas:
        det = f"empenhado até o {periodo}º bim."
        if diag["confere_total"] is False:
            det += " ⚠ soma≠total"
        return linhas, Meta(origem, "SICONFI — RREO Anexo 02", ano, det)
    if DEMO:
        return [dict(x) for x in _DEMO_FUNCOES], Meta(
            "demo", "VALORES ILUSTRATIVOS — não são dados reais", ano, "modo demonstração")
    return [], Meta("semente", "SICONFI — RREO Anexo 02 (consultar ao vivo)", ano,
                    "execução ainda não publicada / API indisponível")


def receita_e_despesa(ano: int, periodo: int) -> tuple[dict, Meta]:
    dado, origem = _rreo(ano, periodo, config.ANEXO_BALANCO,
                         chave=f"siconfi_rreo01_{config.COD_MUNICIPIO}_{ano}_{periodo}")
    r = parse_receita_despesa(_items(dado))
    if r["receita_realizada"] is not None or r["despesa_empenhada"] is not None:
        return r, Meta(origem, "SICONFI — RREO Anexo 01", ano, f"até o {periodo}º bim.")
    if DEMO:
        return dict(_DEMO_RECDESP), Meta("demo", "VALORES ILUSTRATIVOS", ano, "demonstração")
    return {"receita_realizada": None, "despesa_empenhada": None}, Meta(
        "semente", "SICONFI (consultar ao vivo)", ano, "indisponível")


def indicadores_pisos(ano: int, periodo: int) -> tuple[dict, Meta]:
    """
    Percentual OFICIAL aplicado em saúde (ASPS, Anexo 12) e educação (MDE,
    Anexo 08) — lido direto da linha reportada no relatório. Fecha o cálculo
    de cumprimento dos pisos que faltava na v1.
    """
    d12, o12 = _rreo(ano, periodo, config.ANEXO_SAUDE,
                    chave=f"siconfi_rreo12_{config.COD_MUNICIPIO}_{ano}_{periodo}")
    d08, o08 = _rreo(ano, periodo, config.ANEXO_MDE,
                    chave=f"siconfi_rreo08_{config.COD_MUNICIPIO}_{ano}_{periodo}")
    saude = parse_percentual_aplicado(_items(d12), ("APLICAD", "ASPS"))
    if saude is None:
        saude = parse_percentual_aplicado(_items(d12), ("APLICAD", "SAUDE"))
    educ = parse_percentual_aplicado(_items(d08), ("APLICA", "MDE"))
    if educ is None:
        educ = parse_percentual_aplicado(_items(d08), ("APLICA", "MANUTENCAO"))

    if saude is not None or educ is not None:
        return ({"saude_pct": saude, "educacao_pct": educ},
                Meta("api" if "api" in (o12, o08) else "cache",
                     "SICONFI — RREO Anexos 08 e 12", ano, f"até o {periodo}º bim."))
    if DEMO:
        return dict(_DEMO_PISOS), Meta("demo", "VALORES ILUSTRATIVOS", ano, "demonstração")
    return ({"saude_pct": None, "educacao_pct": None},
            Meta("semente", "SICONFI — RREO Anexos 08/12 (consultar ao vivo)", ano,
                 "indisponível"))


def bimestre_mais_recente(ano: int) -> tuple[Optional[int], list[dict], Meta]:
    """Usa o extrato de entregas; se indisponível, tenta do 6º ao 1º."""
    candidatos = periodos_publicados(ano) or list(range(6, 0, -1))
    for b in candidatos:
        linhas, meta = despesa_por_funcao(ano, b)
        if linhas and meta.origem in ("api", "cache"):
            return b, linhas, meta
    if DEMO:
        linhas, meta = despesa_por_funcao(ano, 3)
        return 3, linhas, meta
    return None, [], Meta("semente", "SICONFI — RREO Anexo 02", ano, "nenhum bimestre publicado")
