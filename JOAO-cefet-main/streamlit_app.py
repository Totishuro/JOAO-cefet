# -*- coding: utf-8 -*-
import os
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


APP_TITLE = "📊 Dashboard CEFET-MG — Empreendedorismo"
REPO_DEFAULT_REL = Path("JOAO-cefet-main/data/dados_cefet.xlsx")  # pedido do usuário
ALT_DEFAULT_REL = Path("data/dados_cefet.xlsx")                   # fallback comum
CSV_MAPPING = Path("columns_classification.csv")                  # se existir, ok

# ---------------------------------------------------------------------
# Aparência: ler cores do tema do Streamlit para aplicar nos gráficos
# ---------------------------------------------------------------------
def get_theme_colors():
    bg = st.get_option("theme.backgroundColor") or "#FFFFFF"
    txt = st.get_option("theme.textColor") or "#31333F"
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


# ---------------------------------------------------------------------
# Utilidades: leitura do Excel e descoberta do arquivo no repositório
# ---------------------------------------------------------------------
def find_repo_candidates() -> List[Path]:
    """Procura caminhos plausíveis dentro do projeto para o .xlsx."""
    here = Path(__file__).parent.resolve()
    candidates = [
        here / REPO_DEFAULT_REL,
        here / ALT_DEFAULT_REL,
        REPO_DEFAULT_REL,           # relativo à CWD
        ALT_DEFAULT_REL,
        Path.cwd() / REPO_DEFAULT_REL,
        Path.cwd() / ALT_DEFAULT_REL,
    ]
    # varre também por .xlsx no diretório "data" (se existir)
    for base in [here, here / "JOAO-cefet-main", here / "data", Path.cwd() / "data"]:
        if base.exists():
            for p in base.rglob("*.xlsx"):
                if p not in candidates:
                    candidates.append(p)
    # únicos e existentes
    uniq = []
    for p in candidates:
        try:
            if p.exists() and p not in uniq:
                uniq.append(p)
        except Exception:
            pass
    return uniq


@st.cache_data(show_spinner=False)
def read_excel_any(src) -> pd.DataFrame:
    """Lê Excel tanto de upload (BytesIO) quanto de caminho (Path/str)."""
    return pd.read_excel(src, engine="openpyxl")


# ---------------------------------------------------------------------
# Agregações com CONTAGEM DISTINTA por respondent_id
# ---------------------------------------------------------------------
def distinct_counts_by(df: pd.DataFrame, bucket_col: str,
                       respondent_col: str = "respondent_id",
                       drop_na: bool = True) -> pd.DataFrame:
    if bucket_col not in df.columns:
        return pd.DataFrame(columns=[bucket_col, "Respondentes"])

    tmp = df[[respondent_col, bucket_col]].copy()
    if drop_na:
        tmp = tmp.dropna(subset=[bucket_col])
    # remove repetições da MESMA pessoa na MESMA categoria
    tmp = tmp.drop_duplicates(subset=[respondent_col, bucket_col])
    out = (
        tmp.groupby(bucket_col, dropna=False)[respondent_col]
           .nunique()
           .sort_values(ascending=False)
           .reset_index(name="Respondentes")
    )
    return out


# ---------------------------------------------------------------------
# Gráficos prontos (Plotly) usando os counts distintos
# ---------------------------------------------------------------------
def bar_distinct(df: pd.DataFrame, bucket_col: str, title: str) -> px.bar:
    data = distinct_counts_by(df, bucket_col)
    fig = px.bar(
        data, x=bucket_col, y="Respondentes", title=title,
        text="Respondentes"
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    return apply_fig_theme(fig)


# Faixas etárias (converte texto para número quando possível)
def age_buckets(df: pd.DataFrame,
                age_col: str = "IDADE",
                respondent_col: str = "respondent_id") -> pd.DataFrame:
    if age_col not in df.columns:
        return pd.DataFrame(columns=["Faixa Etária", "Respondentes"])

    ages = pd.to_numeric(df[age_col], errors="coerce")
    tmp = pd.DataFrame({respondent_col: df[respondent_col], "IDADE_NUM": ages})
    # cria faixas
    bins = [-np.inf, 19, 25, 30, np.inf]
    labels = ["Até 19", "20-25", "26-30", "Acima de 30"]
    tmp["Faixa Etária"] = pd.cut(tmp["IDADE_NUM"], bins=bins, labels=labels)

    tmp = tmp.dropna(subset=["Faixa Etária"])
    tmp = tmp.drop_duplicates(subset=[respondent_col, "Faixa Etária"])
    out = (
        tmp.groupby("Faixa Etária")[respondent_col]
           .nunique()
           .reindex(labels)  # mantém a ordem das faixas
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


# ---------------------------------------------------------------------
# App
# ---------------------------------------------------------------------
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
            repo_files = find_repo_candidates()
            if not repo_files:
                st.warning(
                    "Não encontrei `data/dados_cefet.xlsx` no repositório. "
                    "Use *Fazer upload* ou verifique o caminho."
                )
            choice = st.selectbox(
                "Selecione o arquivo",
                options=repo_files,
                index=0 if repo_files else None,
                format_func=lambda p: str(Path(p).as_posix()),
                placeholder=str(REPO_DEFAULT_REL),
            )
            if choice:
                df = read_excel_any(choice)
                src_label = f"Repositório: {Path(choice).as_posix()}"
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

    # KPIs (DISTINCT)
    total_resp = df["respondent_id"].nunique() if "respondent_id" in df.columns else 0
    total_linhas = len(df)

    k1, k2 = st.columns(2)
    k1.metric("Respondentes (distintos)", f"{total_resp:,}".replace(",", "."))
    k2.metric("Linhas no arquivo", f"{total_linhas:,}".replace(",", "."))

    st.markdown("---")

    # 1) Perfil: VOCE É  (contagem distinta)
    if "VOCE É" in df.columns:
        fig1 = bar_distinct(df, "VOCE É", "Perfil dos Respondentes (distinct por respondent_id)")
        st.plotly_chart(fig1, use_container_width=True)

    # 2) Idade (faixas) — distinct
    if "IDADE" in df.columns:
        fig2 = bar_age(df, "Distribuição por Faixa Etária (distinct por respondent_id)")
        st.plotly_chart(fig2, use_container_width=True)

    # 3) Exemplo de outra pergunta categórica (substitua pelo que fizer sentido)
    #    Aqui só como modelo: professores com "Planejamento de atividades"
    col_ex = 'O quanto as seguintes características estão presentes nos(as) PROFESSORES(AS) da minha Instituição de Ensino Superior?Caso não saiba avaliar alguma delas, marcar a opção "Não observado"Planejamento de atividades'
    if col_ex in df.columns:
        fig3 = bar_distinct(df, col_ex, "Professores — Planejamento de atividades (distinct)")
        st.plotly_chart(fig3, use_container_width=True)

    st.caption("Todos os gráficos usam **contagem distinta de respondent_id** por categoria.")


if __name__ == "__main__":
    main()
