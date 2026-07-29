"""
Testes dos parsers do SICONFI e da formatação.

Rodam SEM REDE — usam fixtures que reproduzem o schema real da API
(tests/fixtures/*.json). É a validação que faltava na v1.

    pytest -q
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import ingestao as ing
from src import formatacao as fmt

FIX = Path(__file__).resolve().parent / "fixtures"


def carregar(nome):
    return json.loads((FIX / nome).read_text(encoding="utf-8"))["items"]


# ---------------------------------------------------------------- Anexo 02
def test_despesa_funcao_pega_coluna_certa_nao_dotacao():
    """Deve usar EMPENHADO ATÉ O BIMESTRE, nunca a DOTAÇÃO (que é maior)."""
    linhas, diag = ing.parse_despesa_funcao(carregar("rreo_anexo02.json"))
    saude = next(x for x in linhas if x["funcao"] == "Saúde")
    assert saude["empenhado"] == 12_480_000.0          # não 20.000.000 (dotação)


def test_despesa_funcao_ignora_subfuncoes_3_digitos():
    linhas, _ = ing.parse_despesa_funcao(carregar("rreo_anexo02.json"))
    nomes = {x["funcao"] for x in linhas}
    assert "Atenção Básica" not in nomes and "Ensino Fundamental" not in nomes
    # só funções de 2 dígitos entram
    assert {"Saúde", "Educação", "Segurança pública", "Cultura",
            "Administração"}.issubset(nomes)


def test_despesa_funcao_exclui_intra_orcamentarias():
    """Previdência veio só como intra -> não pode aparecer (evita dupla contagem)."""
    linhas, _ = ing.parse_despesa_funcao(carregar("rreo_anexo02.json"))
    assert "Previdência social" not in {x["funcao"] for x in linhas}


def test_despesa_funcao_valida_contra_total():
    linhas, diag = ing.parse_despesa_funcao(carregar("rreo_anexo02.json"))
    # soma das funções (excluindo intra) = 12.48M+11.76M+6.18M+0.61M+0.52M = 31.55M
    assert abs(diag["soma_funcoes"] - 31_550_000.0) < 1
    assert diag["total_reportado"] == 31_570_000.0
    assert diag["confere_total"] is True               # diferença < 2%


def test_despesa_funcao_ordenada_desc():
    linhas, _ = ing.parse_despesa_funcao(carregar("rreo_anexo02.json"))
    vals = [x["empenhado"] for x in linhas]
    assert vals == sorted(vals, reverse=True)


def test_despesa_funcao_lista_vazia_nao_quebra():
    linhas, diag = ing.parse_despesa_funcao([])
    assert linhas == [] and diag["n_funcoes"] == 0


# ---------------------------------------------------------------- Pisos
def test_percentual_saude_asps():
    v = ing.parse_percentual_aplicado(carregar("rreo_anexo12_saude.json"), ("APLICAD", "ASPS"))
    assert v == 22.40


def test_percentual_educacao_mde():
    v = ing.parse_percentual_aplicado(carregar("rreo_anexo08_educacao.json"), ("APLICA", "MDE"))
    assert v == 27.10


def test_percentual_ignora_valores_fora_de_faixa():
    """Linha de R$ (milhões) não pode ser confundida com percentual.
    Tokens exclusivos da linha em reais ('IMPOSTOS'+'LIQUIDA')."""
    v = ing.parse_percentual_aplicado(carregar("rreo_anexo12_saude.json"),
                                      ("IMPOSTOS", "LIQUIDA"))
    assert v is None                                   # 55,7M não é 0–100


# ---------------------------------------------------------------- Anexo 01
def test_receita_despesa_totais():
    r = ing.parse_receita_despesa(carregar("rreo_anexo01_balanco.json"))
    assert r["receita_realizada"] == 46_800_000.0
    assert r["despesa_empenhada"] == 43_200_000.0


# ---------------------------------------------------------------- Normalização
def test_normaliza_remove_acento_e_caixa():
    assert ing.normaliza("Saúde  Pública") == "SAUDE PUBLICA"


# ---------------------------------------------------------------- Formatação
def test_formatacao_reais():
    assert fmt.reais(1234567.8) == "R$ 1.234.567,80"
    assert fmt.reais_compacto(811_200_000) == "R$ 811,2 mi"
    assert fmt.inteiro(19150) == "19.150"
    assert fmt.reais(None) == "—"
