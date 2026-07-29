# Painel de Dados Públicos — Guaranésia / MG

Dashboard de ciência de dados em Python que reúne os dados públicos de
Guaranésia (código IBGE **3128303**) e **puxa a execução orçamentária de 2026
ao vivo** das APIs oficiais, com proveniência carimbada em cada número.

> Projetado para uso em accountability pública: o painel **nunca inventa
> valores**. Onde o dado oficial de 2026 ainda não foi publicado, ele recua
> para a referência oficial mais recente e sinaliza isso na tela.

---

## O que ele mostra

| Bloco | Dado | Fonte primária | Ano |
|---|---|---|---|
| Execução orçamentária | Despesa **por função** (saúde, educação, segurança, cultura, assistência…) | SICONFI — RREO Anexo 02 (API) | **2026** (ao vivo) |
| Receita × despesa | Totais realizados/empenhados | SICONFI — RREO Anexo 01 (API) | **2026** (ao vivo) |
| Demografia | População, estrutura etária, cor/raça, sexo | IBGE — Censos 2010/2022 + estimativa | 2010–2025 |
| Economia | PIB, valor adicionado, emprego formal | IBGE Contas Municipais / RAIS-CAGED | 2021 |
| Educação | Rede de ensino, matrículas, IDHM | IBGE / Atlas Brasil | 2010 |
| Saúde | Rede instalada (SUS e total) | IBGE | 2019 |
| Saneamento | Cobertura de água, energia, urbanização | IBGE — Censo 2010 | 2010 |

**Sobre "dados de 2026":** a estimativa populacional 2026 do IBGE só é
publicada por volta de agosto (a referência oficial vigente é 1º/jul/2025).
Já a **execução orçamentária de 2026 existe agora** — o RREO é bimestral, então
os bimestres de janeiro a junho já entram pela API do SICONFI. O painel busca
automaticamente o bimestre mais recente publicado.

---

## Como rodar

```bash
# 1. instalar dependências
pip install -r requirements.txt

# 2. subir o painel
streamlit run app.py
#   (ou: ./executar.sh)
```

Abre em `http://localhost:8501`. Sem chave de API, sem cadastro — todas as
fontes são públicas e abertas.

Para inspecionar os dados crus antes do painel:

```bash
python notebooks/analise_exploratoria.py
```

### Modos de execução

```bash
streamlit run app.py                      # normal: puxa dados reais das APIs
PAINEL_OFFLINE=1 streamlit run app.py      # offline: só base-semente (sem rede)
PAINEL_DEMO=1 streamlit run app.py         # demonstração: preenche a execução
                                           #   por função com valores ILUSTRATIVOS
                                           #   (rotulados ◐ DEMONSTRAÇÃO na tela)
```

O modo demonstração serve para apresentar o layout completo sem depender do
SICONFI. Os valores de exemplo **nunca** se confundem com dados reais — a
proveniência de cada bloco aparece na tela.

---

## Arquitetura

```
guaranesia-dashboard/
├── app.py                      # dashboard Streamlit (apresentação)
├── config.py                   # códigos, endpoints, funções, constantes legais
├── requirements.txt            # versões travadas (reprodutibilidade)
├── requirements-dev.txt        # + pytest / playwright
├── executar.sh
├── src/
│   ├── ingestao.py             # parsers PUROS + clientes IBGE/SICONFI
│   ├── processamento.py        # transformações com pandas + KPIs
│   ├── formatacao.py           # números pt-BR (sem locale do sistema)
│   ├── persistencia.py         # SQLite: série histórica dos snapshots
│   └── dados_semente.py        # base verificada de fallback (com fonte/ano)
├── tests/
│   ├── test_parsers.py         # 12 testes dos parsers do SICONFI
│   └── fixtures/*.json         # respostas sintéticas fiéis ao schema da API
├── notebooks/
│   └── analise_exploratoria.py # EDA / verificação das APIs
└── cache/                      # respostas + historico.sqlite
```

Camadas separadas de propósito: **ingestão** (rede) → **processamento**
(pandas) → **apresentação** (Streamlit). O parsing é **puro** (sem rede),
separado dos clientes HTTP, para ser testável com fixtures.

## Testes

```bash
pip install -r requirements-dev.txt
pytest -q          # 12 testes, sem rede
```

Os testes usam `tests/fixtures/*.json` — respostas que reproduzem o schema
real do SICONFI (colunas de dotação, empenhado-no-bimestre, empenhado-até-o-
bimestre, subfunções de 3 dígitos, linhas intra-orçamentárias e total). Eles
provam, entre outras coisas, que o parser:
- usa a coluna **empenhado até o bimestre**, nunca a dotação (que é maior);
- separa **função** (código de 2 dígitos) de **subfunção** (3 dígitos);
- **exclui intra-orçamentárias** (evita dupla contagem);
- **valida a soma** das funções contra o total reportado.

### Decisões de engenharia

- **Parser preciso do SICONFI** — casa a coluna exata e identifica a função
  pelo código, com testes contra fixtures (ver seção Testes).
- **Cumprimento dos pisos** — lê o percentual OFICIAL aplicado em saúde
  (Anexo 12) e educação (Anexo 08) e compara com os limites de 15% e 25%,
  com medidores no painel.
- **Descoberta de bimestres** via extrato de entregas do SICONFI — em vez de
  varrer 6 chamadas às cegas.
- **Sessão HTTP com retry exponencial** (429/5xx) — falha de rede é esperada.
- **Cache em disco (TTL 24h)** e **snapshot em SQLite** — o painel acumula
  série histórica dos gastos ao longo dos bimestres consultados.
- **Fallback que nunca quebra** e **proveniência em todo bloco**:
  `● AO VIVO` (API), `● CACHE`, `○ SEMENTE`, `◐ DEMONSTRAÇÃO`.
- **Formatação pt-BR própria**, sem depender de `locale` do sistema.

## Mudanças desde a v1

- Reescrito o parser do Anexo 02 (antes usava `max()` cego entre colunas e
  podia agarrar a dotação em vez do empenhado).
- Adicionados **12 testes** com fixtures fiéis ao schema.
- **Fechado o cálculo dos pisos** de saúde e educação (antes não era calculado).
- KPIs do cabeçalho migrados do `app.py` para a **camada de dados**.
- Substituída a formatação por `.replace()` por um módulo pt-BR dedicado.
- Versões **travadas** em `requirements.txt`.
- Adicionada **persistência em SQLite** para série histórica.

---

## APIs usadas

**SICONFI / Tesouro Nacional** (execução orçamentária, sem autenticação)
```
https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo
  ?an_exercicio=2026&nr_periodo=3&co_tipo_demonstrativo=RREO
  &no_anexo=RREO-Anexo+02&id_ente=3128303
```
Docs: https://apidatalake.tesouro.gov.br/docs/siconfi/

**IBGE — Agregados/SIDRA v3** (população)
```
https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/-1/variaveis/9324
  ?localidades=N6[3128303]
```
Docs: https://servicodados.ibge.gov.br/api/docs/agregados?versao=3

---

## Como estender

- **Segurança / cultura**: adicionar cliente para SSP-MG (dados abertos) e
  SNIIC (MinC) em `src/ingestao.py`, no mesmo padrão `(dado, Meta)`.
- **Série histórica de execução**: iterar `despesa_por_funcao` por vários anos
  e empilhar num DataFrame para gráfico de evolução.
- **Cruzar com receita de impostos** para calcular cumprimento real dos pisos
  de saúde (15%) e educação (25%) — a função `processamento.cumprimento_pisos`
  já está pronta, só falta plugar a receita do RREO Anexo 03.

---

## Fontes oficiais

IBGE (Censos, Cidades, Contas Municipais) · SICONFI/Tesouro Nacional ·
Atlas do Desenvolvimento Humano (PNUD/Ipea/FJP) · RAIS-CAGED (MTE) ·
Câmara Municipal de Guaranésia · Portal da Transparência da Prefeitura ·
TCE-MG · SNIS (Ministério das Cidades) · DATASUS/SIOPS.

> ⚠️ Não confundir **Guaranésia** (3128303) com o município de **Guarani/MG** —
> é um erro comum em buscadores e agregadores.
