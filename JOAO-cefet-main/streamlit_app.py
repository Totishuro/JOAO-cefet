
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import unicodedata
import re
import csv

# =============================
# Configuração básica
# =============================
st.set_page_config(
    page_title="Dashboard CEFET-MG",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================
# Estilos (Mobile first)
# =============================
st.markdown("""
<style>
    .main-header { font-size: 1.6rem; color: #1f77b4; text-align:center; margin: 0.5rem 0 1rem; }
    .section-header { font-size: 1.2rem; color:#2c3e50; margin:1.2rem 0 0.8rem; border-bottom:2px solid #1f77b4; padding-bottom:0.4rem; }
    @media (min-width: 768px) {
        .main-header { font-size: 2.2rem; }
        .section-header { font-size: 1.6rem; }
    }
</style>
""", unsafe_allow_html=True)

# =============================
# Utilidades
# =============================
def slugify_pt(text: str) -> str:
    """Converte cabeçalhos variados para um nome técnico estável (snake_case, sem acentos)."""
    if not isinstance(text, str):
        text = str(text)

    # remove BOM e espaços
    text = text.replace("\ufeff", "").strip()

    # normaliza acentos
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))

    # substituições frequentes
    text = text.lower()
    text = re.sub(r'["“”’‘]', "", text)
    text = text.replace("(", " ").replace(")", " ")
    text = text.replace("/", " ").replace("\\", " ")
    text = text.replace(" – ", " ").replace(" — ", " ").replace("-", " ")
    text = text.replace("  ", " ")

    # converte para snake_case
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:120]  # limite de segurança

def robust_read_mapping(file_obj_or_path):
    """
    Lê o CSV de mapeamento tentando variações de encoding/separador.
    Deve conter as colunas:
      - coluna_original
      - nome_tecnico
      - rotulo_publico
      - classe
    """
    attempts = [
        dict(sep=",", encoding="utf-8-sig", engine="python", on_bad_lines="skip", quoting=csv.QUOTE_MINIMAL),
        dict(sep=";", encoding="utf-8-sig", engine="python", on_bad_lines="skip", quoting=csv.QUOTE_MINIMAL),
        dict(sep=",", encoding="latin-1", engine="python", on_bad_lines="skip", quoting=csv.QUOTE_MINIMAL),
        dict(sep=";", encoding="latin-1", engine="python", on_bad_lines="skip", quoting=csv.QUOTE_MINIMAL),
    ]
    last_err = None
    for kw in attempts:
        try:
            df = pd.read_csv(file_obj_or_path, **kw)
            # normaliza nomes esperados das colunas do mapping
            df.columns = [slugify_pt(c) for c in df.columns]
            # aliases aceitos
            aliases = {
                "coluna_original": {"coluna_original", "original", "coluna", "header_original"},
                "nome_tecnico": {"nome_tecnico", "tecnico", "nome_padrao", "slug"},
                "rotulo_publico": {"rotulo_publico", "rotulo", "label_publico", "label"},
                "classe": {"classe", "categoria", "grupo"},
            }
            rename_map = {}
            for target, opts in aliases.items():
                for c in df.columns:
                    if c in opts:
                        rename_map[c] = target
                        break
            df = df.rename(columns=rename_map)

            required = {"coluna_original", "nome_tecnico", "rotulo_publico", "classe"}
            if not required.issubset(df.columns):
                missing = required - set(df.columns)
                raise ValueError(f"CSV de mapeamento ausente de colunas obrigatórias: {missing}")
            return df
        except Exception as e:
            last_err = e
            continue
    raise last_err if last_err else RuntimeError("Falha ao ler CSV de mapeamento.")

def load_column_mapping(uploaded_mapping=None):
    """
    Carrega o mapeamento (CSV) a partir de:
      1) Upload do usuário (prioritário)
      2) Arquivo 'columns_classification.csv' no diretório
      3) Sem mapeamento → tenta normalização automática de nomes
    Retorna: (col_to_tech, tech_to_label, tech_to_class, mapping_sourcestr)
    """
    # 1) Se o usuário fez upload
    if uploaded_mapping is not None:
        try:
            df = robust_read_mapping(uploaded_mapping)
            col_to_tech = dict(zip(df["coluna_original"], df["nome_tecnico"]))
            tech_to_label = dict(zip(df["nome_tecnico"], df["rotulo_publico"]))
            tech_to_class = dict(zip(df["nome_tecnico"], df["classe"]))
            return col_to_tech, tech_to_label, tech_to_class, "CSV (upload)"
        except Exception as e:
            st.warning(f"⚠️ Erro ao ler CSV enviado: {e}. Vou tentar o arquivo local.")

    # 2) Arquivo local
    local = Path("columns_classification.csv")
    if local.exists():
        try:
            df = robust_read_mapping(local)
            col_to_tech = dict(zip(df["coluna_original"], df["nome_tecnico"]))
            tech_to_label = dict(zip(df["nome_tecnico"], df["rotulo_publico"]))
            tech_to_class = dict(zip(df["nome_tecnico"], df["classe"]))
            return col_to_tech, tech_to_label, tech_to_class, "CSV (local)"
        except Exception as e:
            st.error(f"❌ columns_classification.csv encontrado, mas ilegível: {e}. Usando nomes automáticos.")

    # 3) Sem CSV
    st.info("ℹ️ Mapeamento não fornecido. Usarei nomes técnicos automáticos.")
    return {}, {}, {}, "Automático"

def apply_mapping_or_slugify(df: pd.DataFrame, col_to_tech: dict) -> pd.DataFrame:
    """Aplica o mapping. Se vazio, cria nomes técnicos automáticos estáveis com slugify_pt."""
    if col_to_tech:
        rename = {orig: tech for orig, tech in col_to_tech.items() if orig in df.columns}
        return df.rename(columns=rename)

    # sem CSV → gerar nomes técnicos automaticamente
    new_cols = {}
    for c in df.columns:
        if c == "respondent_id":
            new_cols[c] = c
        else:
            new_cols[c] = slugify_pt(c)
    df2 = df.rename(columns=new_cols)
    return df2

@st.cache_data(show_spinner=False)
def read_excel(file):
    return pd.read_excel(file, engine="openpyxl")

def compute_stats(df: pd.DataFrame) -> dict:
    stats = {
        "total_linhas": int(len(df)),
        "total_respostas_unicas": int(len(df.drop_duplicates())),
        "linhas_duplicadas_exatas": int(df.duplicated().sum()),
    }
    if "respondent_id" in df.columns:
        stats["respondentes_unicos"] = int(df["respondent_id"].nunique())
    else:
        stats["respondentes_unicos"] = None
    return stats

# =============================
# Visualizações
# =============================
def show_kpis(df, stats):
    st.markdown('<h2 class="section-header">📊 Visão Geral</h2>', unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]:
        st.metric("Linhas (total)", f"{stats['total_linhas']:,}")
    with cols[1]:
        st.metric("Linhas únicas (exatas)", f"{stats['total_respostas_unicas']:,}")
    with cols[2]:
        st.metric("Duplicadas (exatas)", f"{stats['linhas_duplicadas_exatas']:,}")
    with cols[3]:
        if stats["respondentes_unicos"] is not None:
            st.metric("Respondentes únicos", f"{stats['respondentes_unicos']:,}")
        else:
            st.metric("Respondentes únicos", "—")

def show_profile(df):
    st.markdown('<h2 class="section-header">👥 Perfil</h2>', unsafe_allow_html=True)
    idade_col = "idade" if "idade" in df.columns else None
    voce_col = "voce_e" if "voce_e" in df.columns else None

    c1, c2 = st.columns(2)
    with c1:
        if voce_col:
            st.subheader("Distribuição por Perfil")
            st.bar_chart(df[voce_col].value_counts())
        else:
            st.info("Coluna de perfil não encontrada")

    with c2:
        if idade_col and pd.api.types.is_numeric_dtype(df[idade_col]):
            st.subheader("Idade")
            st.metric("Média", f"{df[idade_col].mean():.1f}")
            st.metric("Mínima", f"{df[idade_col].min():.0f}")
            st.metric("Máxima", f"{df[idade_col].max():.0f}")
        else:
            st.info("Coluna de idade não encontrada ou não numérica")

def show_professores(df):
    st.markdown('<h2 class="section-header">👨‍🏫 Professores</h2>', unsafe_allow_html=True)
    prof_cols = {
        "professores_inconformismo_transformacao": "Inconformismo",
        "professores_visao_oportunidades": "Visão",
        "professores_pensamento_inovador_criativo": "Inovação",
        "professores_coragem_riscos": "Coragem",
        "professores_curiosidade": "Curiosidade",
        "professores_comunicacao_sociabilidade": "Comunicação",
        "professores_planejamento_atividades": "Planejamento",
        "professores_apoio_iniciativas": "Apoio",
    }
    data = {}
    for col, label in prof_cols.items():
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce")
            if vals.notna().any():
                data[label] = vals.mean()
    if data:
        st.bar_chart(data)
    else:
        st.info("Sem colunas de avaliação dos professores após mapeamento.")

def show_infra(df):
    st.markdown('<h2 class="section-header">🏢 Infraestrutura</h2>', unsafe_allow_html=True)
    infra_cols = {
        "infraestrutura_biblioteca": "Biblioteca",
        "infraestrutura_labs_informatica": "Labs Informática",
        "infraestrutura_labs_pesquisa_exper": "Labs Pesquisa",
        "infraestrutura_espacos_convivencia": "Espaços Convivência",
        "infraestrutura_restaurante": "Restaurante",
    }
    data = {}
    for col, label in infra_cols.items():
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce")
            if vals.notna().any():
                data[label] = vals.mean()
    if data:
        st.bar_chart(data)
    else:
        st.info("Sem colunas de infraestrutura após mapeamento.")

def show_internet(df):
    st.markdown('<h2 class="section-header">🌐 Internet</h2>', unsafe_allow_html=True)
    internet_cols = {
        "internet_disponibilidade_acesso": "Disponibilidade",
        "internet_velocidade_wifi": "Velocidade Wi‑Fi",
    }
    data = {}
    for col, label in internet_cols.items():
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce")
            if vals.notna().any():
                data[label] = vals.mean()
    if data:
        st.bar_chart(data)
    else:
        st.info("Sem colunas de internet após mapeamento.")

def show_permanencia_evasao(df):
    st.markdown('<h2 class="section-header">📌 Permanência e Evasão</h2>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        col_perm = "permanencia_motivos"
        if col_perm in df.columns and df[col_perm].notna().any():
            top = df[col_perm].dropna().astype(str).str.split(",").explode().str.strip()
            st.bar_chart(top.value_counts().head(12))
        else:
            st.info("Sem coluna de motivos de permanência após mapeamento.")
    with c2:
        col_eva = "evasao_motivos"
        if col_eva in df.columns and df[col_eva].notna().any():
            top = df[col_eva].dropna().astype(str).str.split(",").explode().str.strip()
            st.bar_chart(top.value_counts().head(12))
        else:
            st.info("Sem coluna de motivos de evasão após mapeamento.")

# =============================
# MAIN
# =============================
def main():
    st.markdown('<h1 class="main-header">📊 Dashboard CEFET-MG</h1>', unsafe_allow_html=True)
    st.caption("Pesquisa sobre Empreendedorismo e Educação Superior — MVP")

    with st.sidebar:
        st.subheader("📁 Dados")
        uploaded = st.file_uploader("Excel (.xlsx)", type=["xlsx", "xls"])
        mapping_upload = st.file_uploader("CSV de mapeamento (opcional)", type=["csv"])
        st.markdown("---")
        st.checkbox("📱 Modo Mobile", value=False, key="mobile_view")

    if uploaded is None:
        st.info("Faça upload do Excel na barra lateral. Você pode, opcionalmente, enviar um CSV de mapeamento.")
        st.markdown("**Dica:** Sem CSV, os nomes técnicos serão criados automaticamente a partir dos cabeçalhos.")
        return

    # Carrega dados
    try:
        df_raw = read_excel(uploaded)
    except Exception as e:
        st.error(f"Erro ao ler Excel: {e}")
        return

    # Carrega mapping (se houver)
    col_to_tech, tech_to_label, tech_to_class, src_map = load_column_mapping(mapping_upload)

    # Aplica mapping ou slugify
    df = apply_mapping_or_slugify(df_raw, col_to_tech)

    # KPIs
    stats = compute_stats(df)
    with st.expander("📑 Visão de dados (amostra)", expanded=False):
        st.write(df.head(20))

    show_kpis(df, stats)

    # Abas
    tabs = st.tabs(["👥 Perfil", "👨‍🏫 Professores", "🏢 Infraestrutura", "🌐 Internet", "📌 Permanência/Evasão", "⬇️ Exportar"])

    with tabs[0]:
        show_profile(df)
    with tabs[1]:
        show_professores(df)
    with tabs[2]:
        show_infra(df)
    with tabs[3]:
        show_internet(df)
    with tabs[4]:
        show_permanencia_evasao(df)
    with tabs[5]:
        st.download_button(
            label="Baixar CSV processado",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="dados_processados.csv",
            mime="text/csv",
        )

    # Rodapé com info do mapping
    st.caption(f"Origem do mapeamento: {src_map}")
    if col_to_tech:
        with st.expander("🔎 Dicionário de dados (mapeamento ativo)"):
            dict_df = pd.DataFrame([
                {"coluna_original": k, "nome_tecnico": v, "rotulo_publico": tech_to_label.get(v, ""), "classe": tech_to_class.get(v, "")}
                for k, v in col_to_tech.items()
            ]).sort_values("nome_tecnico")
            st.dataframe(dict_df, use_container_width=True)


if __name__ == "__main__":
    main()
