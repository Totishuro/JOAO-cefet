# streamlit_app.py
# -*- coding: utf-8 -*-
# App: CEFET-MG Survey Explorer (Streamlit)
# Observação importante do Vinícius: NÃO remover "duplicados" por respondent_id,
# pois respostas de múltipla escolha foram normalizadas em linhas. Somente linhas
# 100% idênticas podem ser consideradas duplicadas técnicas.

import io
import os
import textwrap
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="CEFET-MG • Pesquisas", layout="wide")

# --------------------------------------------------------------------------------------
# CONFIGURAÇÕES
# --------------------------------------------------------------------------------------
DEFAULT_FILE = "Dados CEFET_MG - Sem dados pessoais (2).xlsx"

KPI_IDADE_COL = "IDADE"                 # Ajuste se o nome estiver diferente
RESP_ID_COL   = "respondent_id"         # Chave de respondente

HELP_DUP = (
    "Não deduplica por respondent_id. Múltipla escolha foi expandida em linhas. "
    "Somente linhas **100% idênticas** podem ser consideradas duplicadas técnicas."
)

# --------------------------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# --------------------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def read_excel(file) -> pd.DataFrame:
    return pd.read_excel(file, engine="openpyxl")

def has_col(df: pd.DataFrame, col: str) -> bool:
    return col in df.columns

def kpis_basicos(df: pd.DataFrame) -> dict:
    total_respostas = len(df)
    total_resp = df[RESP_ID_COL].nunique() if has_col(df, RESP_ID_COL) else None
    linhas_dups_tecnicas = int(df.duplicated(keep="first").sum())  # somente linhas 100% iguais
    pct_dups_tecnicas = (linhas_dups_tecnicas / total_respostas) if total_respostas else 0.0

    # "Linhas por respondent" NÃO é duplicidade a remover — serve só como diagnóstico.
    linhas_por_resp = (total_respostas / total_resp) if (total_respostas and total_resp) else None

    result = dict(
        total_respostas=total_respostas,
        total_respondentes=total_resp,
        linhas_dups_tecnicas=linhas_dups_tecnicas,
        pct_dups_tecnicas=pct_dups_tecnicas,
        linhas_por_respondente=linhas_por_resp,
    )
    return result

def idade_stats(df: pd.DataFrame) -> dict:
    if not has_col(df, KPI_IDADE_COL):
        return {}
    # Garante 1 idade por respondente para cálculo (equivalente ao SUMMARIZE no DAX)
    subset_cols = [c for c in [RESP_ID_COL, KPI_IDADE_COL] if has_col(df, c)]
    base = df.drop_duplicates(subset=subset_cols)
    serie = pd.to_numeric(base[KPI_IDADE_COL], errors="coerce").dropna()
    if serie.empty:
        return {}
    return dict(
        idade_media=float(serie.mean()),
        idade_min=int(serie.min()),
        idade_max=int(serie.max())
    )

def freq_por_linha(df: pd.DataFrame, col: str) -> pd.DataFrame:
    # Contagem simples por linha
    s = df[col].dropna()
    vc = s.value_counts()
    out = vc.rename_axis(col).reset_index(name="qtd_linhas")
    return out

def freq_por_respondente(df: pd.DataFrame, col: str) -> pd.DataFrame:
    # Considera presença da categoria (ao menos 1x) por respondente
    if not has_col(df, RESP_ID_COL):
        return pd.DataFrame(columns=[col, "respondentes"])
    aux = (
        df[[RESP_ID_COL, col]]
        .dropna()
        .drop_duplicates(subset=[RESP_ID_COL, col])
        .assign(flag=1)
    )
    g = aux.groupby(col, dropna=False)["flag"].sum().rename("respondentes").reset_index()
    # Percentual sobre o total de respondentes
    total_resp = df[RESP_ID_COL].nunique()
    if total_resp and total_resp > 0:
        g["pct_respondentes"] = g["respondentes"] / total_resp
    return g.sort_values("respondentes", ascending=False)

def pct(n: float) -> str:
    return f"{n*100:,.2f}%"

def card_kpi(label: str, value, help_text: str | None = None, fmt: str | None = None):
    with st.container(border=True):
        st.caption(label)
        if value is None:
            st.write("—")
        else:
            if fmt == "int":
                st.subheader(f"{int(value):,}".replace(",", "."))
            elif fmt == "pct":
                st.subheader(pct(value))
            elif fmt == "float1":
                st.subheader(f"{value:.1f}")
            else:
                st.subheader(str(value))
        if help_text:
            st.caption(help_text)

# --------------------------------------------------------------------------------------
# SIDEBAR
# --------------------------------------------------------------------------------------
st.sidebar.title("Configurações")
st.sidebar.info(HELP_DUP)

uploaded = st.sidebar.file_uploader(
    "Faça upload do Excel (xlsx)", type=["xlsx"], accept_multiple_files=False
)

use_default = st.sidebar.checkbox(
    f"Usar arquivo padrão do repositório ({DEFAULT_FILE}) quando não houver upload",
    value=True,
)

agg_mode = st.sidebar.radio(
    "Modo de agregação para gráficos categóricos",
    ["Por linha", "Por respondente (presença ≥1x)"],
    index=1,
    help=(
        "Por linha: cada linha conta 1 ocorrência. "
        "Por respondente: cada categoria conta **uma vez por respondente**, "
        "útil para perguntas de múltipla escolha normalizadas em linhas."
    ),
)

top_n = st.sidebar.slider("Top N categorias no gráfico", min_value=5, max_value=30, value=10, step=1)

# --------------------------------------------------------------------------------------
# CARGA DE DADOS
# --------------------------------------------------------------------------------------
df = None
src = None

if uploaded is not None:
    df = read_excel(uploaded)
    src = f"Upload: {uploaded.name}"
elif use_default and Path(DEFAULT_FILE).exists():
    df = read_excel(DEFAULT_FILE)
    src = f"Arquivo padrão: {DEFAULT_FILE}"

st.caption(f"Fonte de dados: {src or '—'}")

if df is None:
    st.warning("Envie um Excel para começar ou habilite o arquivo padrão no menu lateral.")
    st.stop()

# Normalização leve de colunas (apenas tira espaços nas extremidades)
df.columns = [str(c).strip() for c in df.columns]

# --------------------------------------------------------------------------------------
# KPIs (equivalentes aos mapeados para o Power BI)
# --------------------------------------------------------------------------------------
st.markdown("### KPIs Gerais")
col1, col2, col3, col4, col5 = st.columns(5)

kpi = kpis_basicos(df)
with col1:
    card_kpi("Total de linhas (respostas)", kpi["total_respostas"], fmt="int")
with col2:
    card_kpi("Respondentes únicos", kpi["total_respondentes"], fmt="int")
with col3:
    card_kpi("Linhas duplicadas técnicas", kpi["linhas_dups_tecnicas"], HELP_DUP, fmt="int")
with col4:
    card_kpi("% duplicadas técnicas", kpi["pct_dups_tecnicas"], HELP_DUP, fmt="pct")
with col5:
    card_kpi("Média de linhas por respondente", kpi["linhas_por_respondente"], fmt="float1")

idade = idade_stats(df)
if idade:
    c1, c2, c3 = st.columns(3)
    with c1: card_kpi("Idade média", idade["idade_media"], fmt="float1")
    with c2: card_kpi("Idade mínima", idade["idade_min"], fmt="int")
    with c3: card_kpi("Idade máxima", idade["idade_max"], fmt="int")

# --------------------------------------------------------------------------------------
# EXPLORADOR DE COLUNAS
# --------------------------------------------------------------------------------------
st.markdown("### Explorador de Colunas")
with st.expander("Prévia do dataset"):
    st.dataframe(df.head(50), use_container_width=True, height=300)

# Seleção de colunas categóricas candidatas
cat_cols_guess = (
    df.select_dtypes(include=["object"]).columns.tolist()
    + [c for c in df.columns if "?" in c or "O quanto" in c or "Qual" in c or "Quais" in c]
)
cat_cols_guess = sorted(list(dict.fromkeys(cat_cols_guess)))  # unique + keep order

sel_cols = st.multiselect(
    "Selecione colunas para analisar (categóricas):",
    options=cat_cols_guess or df.columns.tolist(),
    default=[c for c in cat_cols_guess if c != RESP_ID_COL][:3],
    help="Dica: escolha perguntas/itens categóricos. Para múltipla escolha expandida em linhas, use **Por respondente**."
)

for col in sel_cols:
    st.markdown(f"#### {col}")
    if agg_mode.startswith("Por linha"):
        base = freq_por_linha(df, col).head(top_n)
        if base.empty:
            st.info("Sem dados nesta coluna.")
            continue
        fig = px.bar(base.head(top_n), x="qtd_linhas", y=col, orientation="h", title=f"Top {top_n} por linha")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(base, use_container_width=True, hide_index=True)
    else:
        base = freq_por_respondente(df, col).head(top_n)
        if base.empty:
            st.info("Sem dados nesta coluna.")
            continue
        # Exibe tanto contagem de respondentes quanto percentual
        fig = px.bar(base.head(top_n), x="respondentes", y=col, orientation="h",
                     title=f"Top {top_n} por respondente (presença ≥1x)")
        st.plotly_chart(fig, use_container_width=True)

        base2 = base.copy()
        if "pct_respondentes" in base2.columns:
            base2["pct_respondentes"] = (base2["pct_respondentes"] * 100).round(2)
        st.dataframe(base2, use_container_width=True, hide_index=True)

# --------------------------------------------------------------------------------------
# DOWNLOADS
# --------------------------------------------------------------------------------------
st.markdown("### Exportar KPIs")
kpi_out = {**kpi, **{f"idade_{k}": v for k, v in idade.items()}} if idade else {**kpi}
kpi_df = pd.DataFrame([kpi_out])

colx, _ = st.columns([1, 3])
with colx:
    st.download_button(
        "Baixar KPIs (CSV)",
        data=kpi_df.to_csv(index=False).encode("utf-8"),
        file_name="kpis_cefet.csv",
        mime="text/csv",
    )

st.caption("Versão do app: 1.0 • Construído para o cenário do CEFET-MG • Streamlit")
