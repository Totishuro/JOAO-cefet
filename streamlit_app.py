
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.express as px

st.set_page_config(page_title="CEFET-MG | Dashboard", layout="wide")

DEFAULT_FILE = "data/dados_cefet.xlsx"

import re
import unicodedata
import pandas as pd

def _slugify(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    txt = re.sub(r"[^a-zA-Z0-9]+", "_", txt).strip("_").lower()
    return re.sub(r"_+", "_", txt)

def _clean_question(q: str) -> str:
    # remove instruções e observações repetitivas
    q = re.sub(r'Caso não saiba avaliar.*$', '', q, flags=re.IGNORECASE).strip()
    q = re.sub(r'Considerando o respondido na questão anterior,?\s*', '', q, flags=re.IGNORECASE)
    q = q.replace('"', '').replace("“","").replace("”","")
    return re.sub(r'\s+', ' ', q).strip()

_PATTERNS = [
    # Infra PCD
    (re.compile(r'Como você avalia a qualidade da infraestrutura destinada .*?\?\s*(.+)$', re.IGNORECASE),
     "Infra PCD", "Acessibilidade • {item}", "acessibilidade_{slug}"),
    # Infra Geral
    (re.compile(r'Como você avalia a qualidade da infraestrutura oferecida .*?\?\s*(.+)$', re.IGNORECASE),
     "Infra Geral", "Infraestrutura • {item}", "infraestrutura_{slug}"),
    # Internet
    (re.compile(r'Como você avalia a qualidade da internet .*?\?\s*(.+)$', re.IGNORECASE),
     "Internet", "Internet • {item}", "internet_{slug}"),
    # Presença em ALUNOS
    (re.compile(r'O quanto as seguintes características .*? ALUNOS\(AS\).*?\?\s*(.+)$', re.IGNORECASE),
     "Percepção Alunos", "Alunos • {item}", "alunos_{slug}"),
    # Presença em PROFESSORES
    (re.compile(r'O quanto as seguintes características .*? PROFESSORES\(AS\).*?\?\s*(.+)$', re.IGNORECASE),
     "Percepção Professores", "Professores • {item}", "professores_{slug}"),
    # Postura empreendedora dos alunos
    (re.compile(r'como você avalia .*? ALUNOS\(AS\) .*? postura empreendedora', re.IGNORECASE),
     "Percepção Alunos", "Alunos • Postura empreendedora", "alunos_postura_empreendedora"),
    # Motivos de permanência
    (re.compile(r'Quais motivos .*? fazem permanecer', re.IGNORECASE),
     "Permanência", "Permanência • Motivos", "permanencia_motivos"),
    # Motivos de evasão de colegas
    (re.compile(r'Você possui colegas .*? quais foram os motivos', re.IGNORECASE),
     "Evasão de colegas", "Evasão de colegas • Motivos", "evasao_colegas_motivos"),
]

def build_column_map(columns: list[str]) -> pd.DataFrame:
    rows = []
    for col in columns:
        original = col
        q = _clean_question(col)
        classe = "Outros"
        rotulo = q
        nome_tecnico = _slugify(q)[:80]
        for rx, fam, pub_tpl, tech_tpl in _PATTERNS:
            m = rx.search(q)
            if m:
                item = m.group(1).strip() if m.lastindex else ""
                # quando houver subitem
                if "{item}" in pub_tpl:
                    rotulo = pub_tpl.format(item=item)
                    nome_tecnico = tech_tpl.format(slug=_slugify(item))[:80]
                else:
                    rotulo = pub_tpl
                    nome_tecnico = tech_tpl
                classe = fam
                break
        # refinamentos de subitens comuns
        rotulo = rotulo.replace("Velocidade do acesso sem fio (Wi-Fi)", "Velocidade Wi-Fi")
        rows.append({
            "coluna_original": original,
            "classe": classe,
            "rotulo_publico": rotulo,
            "nome_tecnico": nome_tecnico
        })
    return pd.DataFrame(rows)

# Exemplo de uso dentro do fluxo:
# mdf = build_column_map(df.columns)
# st.dataframe(mdf)
# st.download_button("Baixar columns_classification.csv", mdf.to_csv(index=False).encode("utf-8"), "columns_classification.csv", "text/csv")


@st.cache_data(show_spinner=False)
def read_excel(path_or_file):
    try:
        return pd.read_excel(path_or_file, engine="openpyxl")
    except Exception:
        return pd.read_excel(path_or_file)

def kpi_block(df: pd.DataFrame, id_col="respondent_id", age_col="IDADE"):
    total_respostas = len(df)
    total_respondentes = df[id_col].nunique() if id_col in df.columns else np.nan
    linhas_duplicadas_por_id = total_respostas - total_respondentes if id_col in df.columns else np.nan
    pct_dup = (linhas_duplicadas_por_id / total_respostas) if total_respostas and not np.isnan(linhas_duplicadas_por_id) else np.nan

    idade_media = idade_min = idade_max = np.nan
    if age_col in df.columns and id_col in df.columns:
        idade_by_id = (
            df[[id_col, age_col]]
            .dropna(subset=[age_col])
            .drop_duplicates(subset=[id_col], keep="first")
        )
        if not idade_by_id.empty:
            idade_media = idade_by_id[age_col].mean()
            idade_min = idade_by_id[age_col].min()
            idade_max = idade_by_id[age_col].max()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total respostas (linhas)", f"{total_respostas:,}".replace(",", "."))
    c2.metric("Respondentes únicos", f"{int(total_respondentes):,}".replace(",", ".") if not np.isnan(total_respondentes) else "—")
    c3.metric("Repetições por ID (técnicas)", f"{int(linhas_duplicadas_por_id):,}".replace(",", ".") if not np.isnan(linhas_duplicadas_por_id) else "—",
              help="Atenção: não são 'duplicadas' verdadeiras; refletem opções múltiplas que viraram linhas.")
    c4.metric("% repetição por ID", f"{(pct_dup*100):.2f}%" if not np.isnan(pct_dup) else "—")
    c5.metric("Idade média", f"{idade_media:.1f}" if not np.isnan(idade_media) else "—")
    c6.metric("Idade (min–máx.)", f"{int(idade_min)}–{int(idade_max)}" if not np.isnan(idade_min) and not np.isnan(idade_max) else "—")

def categorical_explorer(df: pd.DataFrame, id_col="respondent_id"):
    st.subheader("Explorador de perguntas e opções")
    categorical_cols = [c for c in df.columns if df[c].dtype == "object" and c != id_col]
    if not categorical_cols:
        st.info("Não encontrei colunas categóricas para explorar.")
        return

    col = st.selectbox("Selecione a coluna (pergunta):", categorical_cols, index=0)
    top_n = st.slider("Top N", 5, 30, 15)

    linhas = (
        df.groupby(col, dropna=False)
        .size()
        .reset_index(name="linhas")
        .sort_values("linhas", ascending=False)
        .head(top_n)
    )

    if id_col in df.columns:
        resp = (
            df.dropna(subset=[col])
              .groupby(col)[id_col].nunique()
              .reset_index(name="respondentes_unicos")
              .sort_values("respondentes_unicos", ascending=False)
        )
        base = linhas.merge(resp, on=col, how="left")
    else:
        base = linhas
        base["respondentes_unicos"] = np.nan

    c1, c2 = st.columns(2)
    with c1:
        st.write("Linhas por opção (inclui múltipla escolha expandida)")
        fig1 = px.bar(base, x=col, y="linhas")
        fig1.update_layout(xaxis_title="", yaxis_title="Linhas")
        st.plotly_chart(fig1, use_container_width=True)
    with c2:
        st.write("Respondentes únicos por opção (presença ≥1x)")
        fig2 = px.bar(base, x=col, y="respondentes_unicos")
        fig2.update_layout(xaxis_title="", yaxis_title="Respondentes únicos")
        st.plotly_chart(fig2, use_container_width=True)

    st.dataframe(base, use_container_width=True)

def main():
    st.title("CEFET-MG • Dashboard de Pesquisa")
    st.caption("App em Streamlit com KPIs e exploração de múltipla escolha sem remover linhas por ID.")

    with st.sidebar:
        st.header("Entrada de dados")
        uploaded = st.file_uploader("Envie o Excel (.xlsx)", type=["xlsx"])
        use_default = st.toggle("Usar arquivo padrão do repositório", value=True, help="data/dados_cefet.xlsx")

        id_col = st.text_input("Nome da coluna de ID", value="respondent_id")
        age_col = st.text_input("Nome da coluna de idade (opcional)", value="IDADE")

    src = None
    if uploaded is not None:
        df = read_excel(uploaded)
        src = f"Upload: {uploaded.name}"
    elif use_default and Path(DEFAULT_FILE).exists():
        df = read_excel(DEFAULT_FILE)
        src = f"Arquivo padrão: {DEFAULT_FILE}"
    else:
        st.warning("Envie um Excel pela barra lateral ou habilite 'Usar arquivo padrão'.")
        st.stop()

    st.success(f"Fonte de dados: {src}")
    st.write(f"Formato: {df.shape[0]:,} linhas × {df.shape[1]:,} colunas".replace(",", "."))

    kpi_block(df, id_col=id_col, age_col=age_col)
    categorical_explorer(df, id_col=id_col)

if __name__ == "__main__":
    main()
