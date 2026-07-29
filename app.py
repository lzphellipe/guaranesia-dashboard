"""
Painel de Dados Públicos — Guaranésia/MG
========================================
Dashboard interativo em Streamlit. Prioriza a execução orçamentária de 2026
(SICONFI, ao vivo) e recua para a referência oficial mais recente onde 2026
ainda não foi publicado. Cada bloco carimba a proveniência do dado.

Executar:
    streamlit run app.py
    PAINEL_OFFLINE=1 streamlit run app.py   # só base-semente (sem rede)
    PAINEL_DEMO=1 streamlit run app.py       # layout completo com ILUSTRATIVOS
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import config
from src import (ingestao, processamento as proc, dados_semente as sem,
                 formatacao as fmt, persistencia)

INK, BRASS, TEAL, RUST, SLATE = "#16352C", "#C0862E", "#35707A", "#9E4A2C", "#8A9188"
SEQ = [INK, TEAL, BRASS, RUST, "#5B655E", "#7FA98C", "#D9A441", "#B5675A", "#4E7C6B", "#C98A5E"]

st.set_page_config(page_title="Painel Guaranésia/MG", page_icon="📊", layout="wide")
st.markdown(f"""
<style>
  .stApp {{ background:#F5F6F1; }}
  h1,h2,h3 {{ color:{INK}; font-family:'Trebuchet MS',sans-serif; }}
  [data-testid="stMetricValue"] {{ color:{INK}; font-weight:700; }}
  .proc {{ font-family:monospace; font-size:11px; color:{BRASS};
           border:1px solid #DDE0D6; border-radius:3px; padding:2px 7px;
           display:inline-block; margin-top:4px; background:#fff; }}
  .semente {{ color:{RUST}; border-color:{RUST}; }}
</style>
""", unsafe_allow_html=True)


def carimbo(meta: ingestao.Meta) -> None:
    rotulo = {"api": "● AO VIVO", "cache": "● CACHE",
              "semente": "○ SEMENTE", "demo": "◐ DEMONSTRAÇÃO"}[meta.origem]
    classe = "proc semente" if meta.origem in ("semente", "demo") else "proc"
    txt = f"{rotulo} · {meta.fonte}"
    if meta.ano:
        txt += f" · {meta.ano}"
    if meta.detalhe:
        txt += f" · {meta.detalhe}"
    st.markdown(f'<span class="{classe}">{txt}</span>', unsafe_allow_html=True)


def fmt_kpi(kpi: dict) -> str:
    t, v = kpi["tipo"], kpi["valor"]
    if v is None:
        return "—"
    if t == "int":
        return fmt.inteiro(v)
    if t == "reais_compacto":
        return fmt.reais_compacto(v)
    if t == "idhm":
        return f"{v:.3f}".replace(".", ",")
    return str(v)


@st.cache_data(ttl=3600, show_spinner="Consultando fontes oficiais…")
def carregar(ano: int, periodo_manual: int | None):
    serie_pop, meta_pop = ingestao.serie_populacao()
    if periodo_manual:
        bim = periodo_manual
        desp, meta_desp = ingestao.despesa_por_funcao(ano, bim)
    else:
        bim, desp, meta_desp = ingestao.bimestre_mais_recente(ano)
    rec, meta_rec = ingestao.receita_e_despesa(ano, bim or 6)
    pisos, meta_pisos = ingestao.indicadores_pisos(ano, bim or 6)
    # snapshot histórico quando o dado é real (não semente vazia)
    if desp and meta_desp.origem in ("api", "cache", "demo"):
        try:
            persistencia.salvar_snapshot(ano, bim or 0, desp)
        except Exception:
            pass
    return dict(serie_pop=serie_pop, meta_pop=meta_pop, bimestre=bim,
                despesa=desp, meta_desp=meta_desp, recdesp=rec, meta_rec=meta_rec,
                pisos=pisos, meta_pisos=meta_pisos)


# ============================================================ SIDEBAR
with st.sidebar:
    st.title("⚙️ Parâmetros")
    ano = st.selectbox("Ano de exercício", [2026, 2025, 2024, 2023], index=0)
    modo = st.radio("Bimestre (RREO)", ["Mais recente publicado", "Escolher"], index=0)
    bim_manual = None
    if modo == "Escolher":
        bim_manual = st.select_slider("Bimestre", options=[1, 2, 3, 4, 5, 6], value=3)
    st.divider()
    st.caption("**Guaranésia/MG** · cód. IBGE 3128303")
    st.caption("Fonte primária de 2026: SICONFI/Tesouro (execução orçamentária). "
               "Demografia e economia usam a referência oficial mais recente.")
    if st.button("🔄 Limpar cache e recarregar"):
        st.cache_data.clear()
        for p in config.CACHE_DIR.glob("*.json"):
            p.unlink(missing_ok=True)
        st.rerun()

dados = carregar(ano, bim_manual)

# ============================================================ CABEÇALHO
st.title("📊 Painel de Dados Públicos — Guaranésia / MG")
st.caption("Cada bloco indica se o número veio da API ao vivo (● AO VIVO / CACHE) "
           "ou da base-semente verificada (○ SEMENTE).")
if ingestao.DEMO:
    st.warning("**Modo demonstração ativo.** Os valores de execução orçamentária e de "
               "pisos abaixo são **ilustrativos** (◐ DEMONSTRAÇÃO). Rode sem "
               "`PAINEL_DEMO=1` para puxar os dados reais do SICONFI.", icon="⚠️")

cols = st.columns(4)
for c, kpi in zip(cols, proc.kpis_cabecalho(dados["serie_pop"])):
    c.metric(kpi["rotulo"], fmt_kpi(kpi), kpi["nota"])
carimbo(dados["meta_pop"])
st.divider()

# ============================================================ ORÇAMENTO
st.header("💰 Execução orçamentária por função")
bim = dados["bimestre"]
st.subheader(f"Despesa empenhada por área — {ano}" + (f" · {bim}º bimestre" if bim else ""))

df_desp = proc.df_despesa_funcao(dados["despesa"])
if not df_desp.empty:
    cA, cB = st.columns([3, 2])
    with cA:
        fig = px.bar(df_desp, x="empenhado", y="funcao", orientation="h",
                     color_discrete_sequence=[INK])
        fig.update_layout(height=430, plot_bgcolor="white", paper_bgcolor="white",
                          yaxis={"categoryorder": "total ascending", "title": ""},
                          xaxis={"title": "R$ empenhado (acumulado)"},
                          margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")
    with cB:
        fig2 = px.pie(df_desp, values="empenhado", names="funcao", hole=.55,
                      color_discrete_sequence=SEQ)
        fig2.update_layout(height=430, paper_bgcolor="white",
                           margin=dict(l=10, r=10, t=10, b=10),
                           legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig2, width="stretch")

    tab = df_desp.copy()
    tab["empenhado"] = tab["empenhado"].map(fmt.reais)
    tab["participacao_pct"] = tab["participacao_pct"].map(lambda v: fmt.pct(v))
    tab = tab[["funcao", "empenhado", "participacao_pct"]]
    tab.columns = ["Função", "Empenhado (até o bimestre)", "Participação"]
    st.dataframe(tab, width="stretch", hide_index=True)
    st.download_button("⬇️ Baixar CSV (despesa por função)",
                       df_desp.to_csv(index=False).encode("utf-8"),
                       file_name=f"despesa_funcao_guaranesia_{ano}_b{bim}.csv", mime="text/csv")
else:
    st.info(f"A execução por função de {ano} ainda não foi publicada no SICONFI ou a API "
            "está indisponível agora. O painel **não estampa valores estimados** aqui — "
            "tente outro bimestre ou consulte o portal da prefeitura.")
carimbo(dados["meta_desp"])

# ---- Receita × Despesa
rec = dados["recdesp"]
if rec.get("receita_realizada") or rec.get("despesa_empenhada"):
    st.subheader("Receita realizada × Despesa empenhada")
    fig3 = go.Figure(go.Bar(
        x=["Receita realizada", "Despesa empenhada"],
        y=[rec.get("receita_realizada") or 0, rec.get("despesa_empenhada") or 0],
        text=[fmt.reais_compacto(rec.get("receita_realizada")),
              fmt.reais_compacto(rec.get("despesa_empenhada"))],
        textposition="outside", marker_color=[TEAL, BRASS]))
    fig3.update_layout(height=300, plot_bgcolor="white", paper_bgcolor="white",
                       yaxis_title="R$", margin=dict(l=10, r=10, t=10, b=40))
    st.plotly_chart(fig3, width="stretch")
    carimbo(dados["meta_rec"])

# ---- Cumprimento dos pisos (fecha o laço que faltava)
st.subheader("Cumprimento dos pisos constitucionais")
pisos = dados["pisos"]
dfp = proc.df_pisos(pisos.get("saude_pct"), pisos.get("educacao_pct"))
if dfp["aplicado_pct"].notna().any():
    gcols = st.columns(2)
    for col, (_, row) in zip(gcols, dfp.iterrows()):
        aplicado = row["aplicado_pct"]
        piso = row["piso_pct"]
        with col:
            if aplicado is None or pd.isna(aplicado):
                st.metric(f"{row['area']} — piso {fmt.pct(piso,0)}", "—", "sem dado")
                continue
            cor = TEAL if row["cumpre"] else RUST
            g = go.Figure(go.Indicator(
                mode="gauge+number", value=aplicado,
                number={"suffix": "%"},
                title={"text": f"{row['area']} · aplicado (piso {fmt.pct(piso,0)})"},
                gauge={"axis": {"range": [0, max(35, aplicado + 5)]},
                       "bar": {"color": cor},
                       "threshold": {"line": {"color": INK, "width": 3},
                                     "thickness": 0.85, "value": piso},
                       "steps": [{"range": [0, piso], "color": "#F0E4D4"}]}))
            g.update_layout(height=230, margin=dict(l=20, r=20, t=50, b=10),
                            paper_bgcolor="white")
            st.plotly_chart(g, width="stretch")
            status = "✅ cumpre" if row["cumpre"] else "❌ abaixo do piso"
            st.caption(f"{status} · folga {row['folga_pp']:+.1f} pp".replace(".", ","))
else:
    st.info("Percentuais de aplicação em saúde (Anexo 12) e educação (Anexo 08) ainda não "
            "disponíveis para o período. São lidos direto do relatório oficial quando publicados.")
carimbo(dados["meta_pisos"])

# ---- Série histórica acumulada (do SQLite local)
snaps = persistencia.snapshots_disponiveis()
if len(snaps) > 1 and not df_desp.empty:
    with st.expander("📈 Série histórica acumulada (snapshots já consultados)"):
        alvo = st.selectbox("Função", df_desp["funcao"].tolist(), key="hist")
        serie = persistencia.serie_funcao(alvo)
        if len(serie) > 1:
            dfh = pd.DataFrame(serie)
            dfh["rotulo"] = dfh["ano"].astype(str) + "·" + dfh["periodo"].astype(str) + "b"
            figh = px.line(dfh, x="rotulo", y="empenhado", markers=True,
                           color_discrete_sequence=[BRASS])
            figh.update_layout(height=280, plot_bgcolor="white", paper_bgcolor="white",
                               xaxis_title="", yaxis_title="R$ empenhado")
            st.plotly_chart(figh, width="stretch")
        else:
            st.caption("Ainda só há um ponto para esta função. Consulte outros bimestres "
                       "para montar a série.")

with st.expander("📎 Arcabouço legal e leis orçamentárias vigentes"):
    cE, cL = st.columns(2)
    with cE:
        st.markdown("**Pisos constitucionais de gasto**")
        st.markdown(f"- Educação (MDE): **≥ {int(config.PISO_EDUCACAO*100)}%** — CF art. 212\n"
                    f"- Saúde (ASPS): **≥ {int(config.PISO_SAUDE*100)}%** — LC 141/2012\n"
                    f"- FUNDEB: **≥ 70%** para o magistério — EC 108/2020")
    with cL:
        st.markdown("**Leis vigentes**")
        for l in sem.ORCAMENTO_LEGAL["leis"]:
            st.markdown(f"- {l['tipo']}: **{l['lei']}**")
        st.caption("Fonte: Câmara Municipal de Guaranésia")
st.divider()

# ============================================================ DEMOGRAFIA
st.header("👥 Demografia")
d1, d2, d3 = st.columns(3)
with d1:
    st.markdown("**Evolução da população**")
    dfpop = proc.df_populacao(dados["serie_pop"])
    figp = px.bar(dfpop, x="ano", y="valor", text="valor", color_discrete_sequence=[INK])
    figp.update_traces(textposition="outside")
    figp.update_layout(height=300, plot_bgcolor="white", paper_bgcolor="white",
                       xaxis={"type": "category", "title": ""}, yaxis={"title": "hab."},
                       margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(figp, width="stretch")
with d2:
    st.markdown("**Estrutura etária (%)**")
    dfe = proc.df_estrutura_etaria()
    fige = px.bar(dfe, x="percentual", y="faixa", orientation="h", color_discrete_sequence=[TEAL])
    fige.update_layout(height=300, plot_bgcolor="white", paper_bgcolor="white",
                       yaxis={"title": "", "categoryorder": "array",
                              "categoryarray": ["65+", "40–64", "25–39", "15–24", "0–14"]},
                       xaxis={"title": "%"}, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fige, width="stretch")
with d3:
    st.markdown("**Cor ou raça (Censo 2010)**")
    dfr = proc.df_cor_raca()
    figr = px.pie(dfr, values="pessoas", names="cor_raca", hole=.5, color_discrete_sequence=SEQ)
    figr.update_layout(height=300, paper_bgcolor="white", margin=dict(l=10, r=10, t=10, b=10),
                       legend=dict(orientation="h", y=-0.1))
    st.plotly_chart(figr, width="stretch")
st.markdown(f'<span class="proc semente">○ SEMENTE · {sem.COR_RACA_2010["_fonte"]} · '
            f'estrutura etária {sem.ESTRUTURA_ETARIA["_fonte"]}</span>', unsafe_allow_html=True)
st.divider()

# ============================================================ ECONOMIA + SANEAMENTO
cEco, cSan = st.columns(2)
with cEco:
    st.header("🏭 Economia")
    dfv = proc.df_valor_adicionado()
    figv = px.pie(dfv, values="percentual", names="setor", hole=.5,
                  color_discrete_sequence=[INK, TEAL, BRASS, RUST])
    figv.update_layout(height=320, paper_bgcolor="white", title="Composição do valor adicionado",
                       margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=-0.1))
    st.plotly_chart(figv, width="stretch")
    e = sem.ECONOMIA
    st.markdown(f"Empregos formais: **{fmt.inteiro(e['empregos_formais'])}** · "
                f"Remuneração média: **{fmt.reais(e['remuneracao_media_reais'], 0)}** · "
                f"Empresas: **{e['empresas']}**")
    st.markdown(f'<span class="proc semente">○ SEMENTE · {e["_fonte"]} · {e["_ano"]}</span>',
                unsafe_allow_html=True)
with cSan:
    st.header("🚰 Saneamento e habitação")
    dfs = proc.df_saneamento()
    figs = px.bar(dfs, x="indicador", y="cobertura_pct", text="cobertura_pct",
                  color_discrete_sequence=[TEAL])
    figs.update_traces(textposition="outside", texttemplate="%{text}%")
    figs.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white",
                       yaxis={"title": "% dos domicílios", "range": [0, 110]},
                       xaxis={"title": ""}, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(figs, width="stretch")
    st.caption("Esgotamento sanitário atualizado: consultar SNIS e Censo 2022 por domicílio.")
    st.markdown(f'<span class="proc semente">○ SEMENTE · {sem.SANEAMENTO["_fonte"]} · '
                f'{sem.SANEAMENTO["_ano"]}</span>', unsafe_allow_html=True)
st.divider()

# ============================================================ EDUCAÇÃO + SAÚDE
cEdu, cSau = st.columns(2)
with cEdu:
    st.header("📚 Educação")
    ed = sem.EDUCACAO
    st.metric("Estabelecimentos de ensino", ed["estabelecimentos"])
    a, b = st.columns(2)
    a.metric("Matrículas · fundamental", fmt.inteiro(ed["matriculas_fundamental"]))
    b.metric("Matrículas · médio", ed["matriculas_medio"])
    st.markdown(f'<span class="proc semente">○ SEMENTE · {ed["_fonte"]}</span>', unsafe_allow_html=True)
with cSau:
    st.header("🏥 Saúde (rede instalada)")
    sa = sem.SAUDE
    a, b = st.columns(2)
    a.metric("Estabelecimentos (total)", sa["estabelecimentos_total"])
    b.metric("Vinculados ao SUS", sa["estabelecimentos_sus"])
    st.caption("Gasto e cumprimento do piso: ver seção de orçamento acima (Anexo 12).")
    st.markdown(f'<span class="proc semente">○ SEMENTE · {sa["_fonte"]} · {sa["_ano"]}</span>',
                unsafe_allow_html=True)
st.divider()

# ============================================================ FONTES
st.header("🔗 Fontes oficiais")
for nome, url in sem.FONTES.items():
    st.markdown(f"- [{nome}]({url})")
st.caption("Atenção: não confundir Guaranésia (3128303) com Guarani/MG. "
           "Valores por função mudam a cada bimestre — para uso oficial, puxe o dado ao vivo.")
