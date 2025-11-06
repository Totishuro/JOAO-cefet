# -*- coding: utf-8 -*-
import os
from pathlib import Path
from typing import List, Optional
import io
import requests
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

APP_TITLE = "📊 Dashboard CEFET-MG — Empreendedorismo"
REPO_DEFAULT_RAW = "https://raw.githubusercontent.com/Totishuro/JOAO-cefet/main/JOAO-cefet-main/data/dados_cefet.xlsx"
ALT_DEFAULT_RAW = "https://raw.githubusercontent.com/Totishuro/JOAO-cefet/main/data/dados_cefet.xlsx"
CSV_MAPPING = Path("columns_classification.csv")  # se existir, ok

def get_theme_colors():
    bg = st.get_option("theme.backgroundColor") or "#17171A"
    txt = st.get_option("theme.textColor") or "#EEE"
    primary = st.get_option("theme.primaryColor") or "#636EFA"
    return bg, txt, primary

def apply_fig_theme(fig):
    bg, txt, primary = get_theme_colors()
    fig.update_layout(
        paper_bgcolor=bg,
        plot_bgcolor=bg,
        font_color=txt,
        legend=dict(font=dict(color=txt)),
        xaxis=dict(showgrid=False, tickfont=dict(color=txt), titlefont=dict(color=txt)),
        yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.2)",
                   tickfont=dict(color=txt), titlefont=dict(color=txt)),
    )
    return fig

def read_excel_github(raw_url) -> pd.DataFrame:
    try:
        response = requests.get(raw_url)
        response.raise_for_status()
        return pd.read_excel(io.BytesIO(response.content), engine="openpyxl")
    except Exception as e:
        st.error(f"Erro ao baixar arquivo do GitHub: {str(e)}")
        return None

@st.cache_data(show_spinner=False)
def read_excel_any(src) -> pd.DataFrame:
    if isinstance(src, str) and src.startswith("http"):
        return read_excel_github(src)
    return pd.read_excel(src, engine="openpyxl")

def distinct_counts_by(df: pd.DataFrame, bucket_col: str,
                       respondent_col: str = "respondent_id",
                       drop_na: bool = True) -> pd.DataFrame:
    if bucket_col not in df.columns:
        return pd.DataFrame(columns=[bucket_col, "Respondentes"])
    tmp = df[[respondent_col, bucket_col]].copy()
    if drop_na:
        tmp = tmp.dropna(subset=[bucket_col])
    tmp = tmp.drop_duplicates(subset=[respondent_col, bucket_col])
    out = (
        tmp.groupby(bucket_col, dropna=False)[respondent_col]
           .nunique()
           .sort_values(ascending=False)
           .reset_index(name="Respondentes")
    )
    return out

def bar_distinct(df: pd.DataFrame, bucket_col: str, title: str) -> px.bar:
    data = distinct_counts_by(df, bucket_col)
    fig = px.bar(
        data, x=bucket_col, y="Respondentes", title=title,
        text="Respondentes"
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    return apply_fig_theme(fig)

def age_buckets(df: pd.DataFrame,
                age_col: str = "IDADE",
                respondent_col: str = "respondent_id") -> pd.DataFrame:
    if age_col not in df.columns:
        return pd.DataFrame(columns=["Faixa Etária", "Respondentes"])
    ages = pd.to_numeric(df[age_col], errors="coerce")
    tmp = pd.DataFrame({respondent_col: df[respondent_col], "IDADE_NUM": ages})
    bins = [-np.inf, 19, 25, 30, np.inf]
    labels = ["Até 19", "20-25", "26-30", "Acima de 30"]
    tmp["Faixa Etária"] = pd.cut(tmp["IDADE_NUM"], bins=bins, labels=labels)
    tmp = tmp.dropna(subset=["Faixa Etária"])
    tmp = tmp.drop_duplicates(subset=[respondent_col, "Faixa Etária"])
    out = (
        tmp.groupby("Faixa Etária")[respondent_col]
           .nunique()
           .reindex(labels)
           .reset_index(name="Respondentes")
    )
    return out

def bar_age(df: pd.DataFrame, title: str = "Distribuição por Faixa Etária") -> px.bar:
    data = age_buckets(df)
    fig = px.bar(
        data, x="Faixa Etária", y="Respondentes", title=title,
        text="Respondentes"
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    return apply_fig_theme(fig)

def main():
    st.set_page_config(page_title="CEFET-MG", page_icon="📊", layout="wide")
    st.title(APP_TITLE)

    with st.sidebar:
        st.header("Fonte dos dados")
        mode = st.radio(
            "Como deseja carregar o Excel?",
            options=["Arquivo do repositório", "Fazer upload"],
            index=0,
        )

        df = None
        src_label = ""

        if mode == "Arquivo do repositório":
            repo_files = [REPO_DEFAULT_RAW, ALT_DEFAULT_RAW]
            choice = st.selectbox(
                "Selecione o arquivo",
                options=repo_files,
                index=0,
            )
            if choice:
                df = read_excel_any(choice)
                src_label = f"Repositório: {choice}"
        else:
            uploaded = st.file_uploader(
                "Envie o Excel (.xlsx)", type=["xlsx"], accept_multiple_files=False
            )
            if uploaded:
                df = read_excel_any(uploaded)
                src_label = f"Upload: {uploaded.name}"

        st.caption(src_label if src_label else "Sem arquivo carregado.")

    if df is None:
        st.info("👈 Carregue um arquivo para começar.")
        return

    total_resp = df["respondent_id"].nunique() if "respondent_id" in df.columns else 0
    total_linhas = len(df)
    k1, k2 = st.columns(2)
    k1.metric("Respondentes (distintos)", f"{total_resp:,}".replace(",", "."))
    k2.metric("Linhas no arquivo", f"{total_linhas:,}".replace(",", "."))

    st.markdown("---")

    if "VOCE É" in df.columns:
        fig1 = bar_distinct(df, "VOCE É", "Perfil dos Respondentes (distinct por respondent_id)")
        st.plotly_chart(fig1, use_container_width=True)

    if "IDADE" in df.columns:
        fig2 = bar_age(df, "Distribuição por Faixa Etária (distinct por respondent_id)")
        st.plotly_chart(fig2, use_container_width=True)

    col_ex = 'O quanto as seguintes características estão presentes nos(as) PROFESSORES(AS) da minha Instituição de Ensino Superior?Caso não saiba avaliar alguma delas, marcar a opção "Não observado"Planejamento de atividades'
    if col_ex in df.columns:
        fig3 = bar_distinct(df, col_ex, "Professores — Planejamento de atividades (distinct)")
        st.plotly_chart(fig3, use_container_width=True)

    st.caption("Todos os gráficos usam **contagem distinta de respondent_id** por categoria.")

if __name__ == "__main__":
    main()
