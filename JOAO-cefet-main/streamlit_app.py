import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path
import re

# ===== Config =====
st.set_page_config(page_title="Painel CEFET-MG", layout="wide")
DEFAULT_FILE = "data/Dados_CEFET_MG.xlsx"  # opcional: deixe este .xlsx dentro do repo (pasta /data)

# ===== Helpers =====
@st.cache_data(show_spinner=False)
def read_excel(path_or_buf):
    return pd.read_excel(path_or_buf, engine="openpyxl")

def _slugify(s: str) -> str:
    s = s.strip()
    s = re.sub(r'[\r\n]+', ' ', s)
    s = re.sub(r'["“”’]', '', s)
    s = re.sub(r'\(.*?\)', '', s)  # remove parenteses longos
    s = re.sub(r'[^0-9a-zA-ZÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç ]+', '', s)
    s = s.lower()
    s = re.sub(r'\s+', ' ', s)
    s = s.replace(' ', '_')
    return s[:140]

def _smart_label(s: str) -> str:
    # encurta textos muito longos para rótulos de gráfico
    s2 = re.sub(r'Caso.*?observado', '', s, flags=re.IGNORECASE)
    s2 = re.sub(r'O quanto as seguintes características estão presentes nos\(as\) ', '', s2, flags=re.IGNORECASE)
    s2 = re.sub(r'minha Instituição de Ensino Superior', 'IES', s2, flags=re.IGNORECASE)
    s2 = s2.replace('ALUNOS(AS)', 'Alunos').replace('PROFESSORES(AS)', 'Professores')
    s2 = s2.replace('Instituição de Ensino Superior', 'IES')
    s2 = re.sub(r'\s+', ' ', s2).strip(' ?:"')
    return s2 if s2 else s

def load_or_build_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """
    Procura 'columns_classification.csv' na raiz do app.
    Se não existir, cria automaticamente com alias amigáveis e salva para edição posterior.
    Colunas esperadas no CSV: column,class,alias,label
    """
    csv_path = Path("columns_classification.csv")
    if csv_path.exists():
        mp = pd.read_csv(csv_path)
        for c in ["column", "class", "alias", "label"]:
            if c not in mp.columns:
                raise ValueError("columns_classification.csv inválido (faltam colunas).")
    else:
        rows = []
        for col in df.columns:
            # classe heurística simples
            lc = col.lower()
            klass = "meta"
            if "alunos" in lc: klass = "alunos"
            if "professores" in lc: klass = "professores"
            if "infraestrutura" in lc or "internet" in lc: klass = "infraestrutura"
            if "empreendedor" in lc: klass = "empreendedorismo"
            if "projeto" in lc: klass = "projetos"
            if "motivo" in lc: klass = "motivos"

            rows.append({
                "column": col,
                "class": klass,
                "alias": _slugify(col),
                "label": _smart_label(col),
            })
        mp = pd.DataFrame(rows)
        mp.to_csv(csv_path, index=False, encoding="utf-8")
    return mp

def apply_column_mapping(df: pd.DataFrame):
    mp = load_or_build_mapping(df)
    col_map = {row["column"]: row["alias"] for _, row in mp.iterrows()}
    labels = {row["alias"]: row["label"] for _, row in mp.iterrows()}
    classes = {row["alias"]: row["class"] for _, row in mp.iterrows()}
    df2 = df.rename(columns=col_map)
    return df2, labels, classes

def kpi_cards(df: pd.DataFrame):
    cols = st.columns(4)
    total_respostas = len(df)
    total_respondentes = df["respondent_id"].nunique() if "respondent_id" in df.columns else np.nan

    # idade
    idade_col = None
    for c in df.columns:
        if c.lower() in ("idade", "idade_anos"):
            idade_col = c
            break

    if idade_col is not None:
        idade = pd.to_numeric(df[idade_col], errors="coerce")
        media_idade = idade.mean(skipna=True)
        idade_min = idade.min(skipna=True)
        idade_max = idade.max(skipna=True)
    else:
        media_idade = idade_min = idade_max = np.nan

    with cols[0]:
        st.metric("Total de respostas", f"{total_respostas:,}".replace(",", "."))
    with cols[1]:
        st.metric("Respondentes únicos", f"{int(total_respondentes):,}".replace(",", ".") if pd.notna(total_respondentes) else "—")
    with cols[2]:
        st.metric("Idade média", f"{media_idade:.1f}" if pd.notna(media_idade) else "—")
    with cols[3]:
        st.metric("Faixa etária", f"{int(idade_min)}–{int(idade_max)}" if pd.notna(idade_min) and pd.notna(idade_max) else "—")

def draw_charts(df: pd.DataFrame, labels: dict):
    st.subheader("Distribuições principais")
    left, right = st.columns(2)

    # Exemplo 1: VOCÊ É (perfil)
    col_genero = None
    for c in df.columns:
        if c.lower() in ("voce_é", "voce_e", "genero", "perfil"):
            col_genero = c
            break
    if col_genero:
        vc = df[col_genero].value_counts(dropna=False).reset_index()
        vc.columns = ["categoria", "qtd"]
        with left:
            st.plotly_chart(
                px.bar(vc, x="categoria", y="qtd", title=labels.get(col_genero, col_genero)),
                use_container_width=True,
            )

    # Exemplo 2: Instituição
    col_ies = None
    for c in df.columns:
        if "instituicao" in c.lower() or "instituição" in c.lower():
            col_ies = c
            break
    if col_ies:
        vc = df[col_ies].value_counts().head(20).reset_index()
        vc.columns = ["instituição", "qtd"]
        with right:
            st.plotly_chart(
                px.bar(vc, x="instituição", y="qtd", title=labels.get(col_ies, col_ies)),
                use_container_width=True,
            )

# ===== UI =====
def main():
    st.title("Painel CEFET-MG — Empreendedorismo e Infraestrutura")
    st.caption("Upload do Excel e normalização automática dos nomes de colunas (sem deduplicar múltiplas respostas por respondent_id).")

    with st.sidebar:
        st.header("Fonte de dados")
        uploaded = st.file_uploader("Carregue um Excel (.xlsx)", type=["xlsx"])
        use_default = st.toggle("Usar arquivo padrão do repositório", value=True)

    if uploaded is not None:
        df = read_excel(uploaded)
        src = f"Upload: {uploaded.name}"
    elif use_default and Path(DEFAULT_FILE).exists():
        df = read_excel(DEFAULT_FILE)
        src = f"Arquivo padrão: {DEFAULT_FILE}"
    else:
        st.info("Carregue um arquivo ou ative 'Usar arquivo padrão'.")
        st.stop()

    # Normalização de colunas assistida por CSV (ou criada automaticamente)
    df, FRIENDLY_LABELS, CLASSES = apply_column_mapping(df)

    st.caption(f"Origem: {src}")
    kpi_cards(df)

    with st.expander("Prévia dos dados", expanded=False):
        st.dataframe(df.head(50), use_container_width=True)

    draw_charts(df, FRIENDLY_LABELS)

if __name__ == "__main__":
    main()
