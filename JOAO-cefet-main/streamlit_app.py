import io
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard CEFET-MG",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ADD-ONLY – NUNCA remover KPIs, abas ou funções sem autorização
ADD_ONLY = True

# URLs de dados no GitHub (Raw)
GITHUB_FILES = {
    "dados_cefet.xlsx":
        "https://raw.githubusercontent.com/Totishuro/JOAO-cefet/main/JOAO-cefet-main/data/dados_cefet.xlsx",
    "Dados CEFET_MG (Sem dados pessoais).xlsx":
        "https://raw.githubusercontent.com/Totishuro/JOAO-cefet/main/JOAO-cefet-main/data/Dados%20CEFET_MG%20-%20Sem%20dados%20pessoais%20(2).xlsx",
}

# Arquivo local de demonstração (deve existir no repositório)
LOCAL_DEMO = Path("data/dados_cefet.xlsx")

# -----------------------------------------------------------------------------
# REGRAS OBRIGATÓRIAS (RESUMO)
# -----------------------------------------------------------------------------
LIKERT_LABELS = ["1 Muito ruim", "2 Ruim", "3 Razoável", "4 Boa", "5 Excelente"]
LIKERT_NEUTROS = {"Não observado", "Nao observado", "Não se aplica", "Nao se aplica", "NA", "N/A", ""}
LIKERT_TO_1_5 = {
    "1": 1, "muitoruim": 1, "muito ruim": 1,
    "2": 2, "ruim": 2,
    "3": 3, "razoavel": 3, "razoável": 3,
    "4": 4, "boa": 4,
    "5": 5, "excelente": 5,
}
LIKERT_TO_INDEX = {1: 20, 2: 40, 3: 60, 4: 80, 5: 100}
LIKERT_COLORS = {
    "1 Muito ruim": "#ff4d4f",
    "2 Ruim": "#ffa940",
    "3 Razoável": "#fadb14",
    "4 Boa": "#73d13d",
    "5 Excelente": "#36cfc9",
}

ID_CANDIDATES = [
    "Respondent ID", "respondent_id", "respondente_id", "id_respondente",
    "respondentid", "idrespondente"
]

# -----------------------------------------------------------------------------
# UTILITÁRIAS
# -----------------------------------------------------------------------------
def normalize_text(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = s.strip().lower()
    s = ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn')
    return s

def contains_all(haystack: str, *needles: str) -> bool:
    h = normalize_text(haystack)
    return all(normalize_text(n) in h for n in needles)

def find_cols(df: pd.DataFrame, *keywords, require_all=True):
    cols = []
    for c in df.columns:
        ok = contains_all(c, *keywords) if require_all else any(normalize_text(k) in normalize_text(c) for k in keywords)
        if ok:
            cols.append(c)
    return cols

def find_first(df: pd.DataFrame, *keywords, require_all=True):
    cols = find_cols(df, *keywords, require_all=require_all)
    return cols[0] if cols else None

def find_respondent_id_col(df: pd.DataFrame) -> str:
    # 1) candidatos exatos
    norm_map = {normalize_text(c): c for c in df.columns}
    for c in ID_CANDIDATES:
        if normalize_text(c) in norm_map:
            return norm_map[normalize_text(c)]
    # 2) heurística
    for c in df.columns:
        n = normalize_text(c)
        if "respondent" in n or "respondente" in n:
            return c
    raise ValueError("Coluna de ID do respondente não encontrada. Candidatos esperados: " + ", ".join(ID_CANDIDATES))

def distinct_count(series: pd.Series, df: pd.DataFrame, id_col: str) -> int:
    mask = series.notna() & (series.astype(str).str.strip() != "")
    return df.loc[mask, id_col].nunique()

def parse_likert_value(v) -> int | None:
    if pd.isna(v):
        return None
    s = normalize_text(str(v))
    if s in normalize_text("|".join(LIKERT_NEUTROS)):
        return None
    # Formatos: "4 - Boa", "4 Boa", "Boa", "4"
    # tenta número na frente
    m = re.match(r"^\s*([1-5])", s)
    if m:
        return int(m.group(1))
    # tenta mapeamento textual
    return LIKERT_TO_1_5.get(s)

def likert_index(series: pd.Series) -> float | None:
    values_1_5 = [parse_likert_value(v) for v in series if parse_likert_value(v) is not None]
    if not values_1_5:
        return None
    indexes = [LIKERT_TO_INDEX[v] for v in values_1_5]
    return float(np.mean(indexes))

def base_layout():
    # Herda fundo do app (transparente) e ajusta contraste
    theme_base = st.get_option("theme.base") or "dark"
    font_color = "#111" if theme_base == "light" else "#fff"
    grid = "rgba(0,0,0,0.15)" if theme_base == "light" else "rgba(255,255,255,0.1)"
    axis = "rgba(0,0,0,0.4)" if theme_base == "light" else "rgba(255,255,255,0.2)"
    return dict(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=font_color, size=12),
        xaxis=dict(gridcolor=grid, linecolor=axis, automargin=True),
        yaxis=dict(gridcolor=grid, linecolor=axis, automargin=True),
        # ⬇️ Removido 'margin' para evitar conflito com chamadas que definem margin explicitamente
        # margin=dict(l=20, r=20, t=40, b=60),
    )



def wrap(text: str, width: int = 28) -> str:
    if not isinstance(text, str):
        text = str(text)
    words, line, out = text.split(), [], []
    for w in words:
        if sum(len(x) for x in line) + len(line) + len(w) <= width:
            line.append(w)
        else:
            out.append(" ".join(line))
            line = [w]
    if line:
        out.append(" ".join(line))
    return "<br>".join(out)

def dynamic_height(n_categories: int) -> int:
    return max(350, 24 * n_categories + 120)

def barh_from_counts(df_counts: pd.DataFrame, y_col: str, x_col: str, color="#3498db"):
    fig = go.Figure(
        data=[go.Bar(
            y=df_counts[y_col].apply(wrap),
            x=df_counts[x_col],
            text=[str(v) for v in df_counts[x_col]],
            textposition="outside",
            orientation="h",
            marker_color=color
        )]
    )
    fig.update_layout(**base_layout(), height=dynamic_height(len(df_counts)))
    return fig

def likert_stack(df_matrix: pd.DataFrame, pergunta: str):
    row = df_matrix[df_matrix["Pergunta"] == pergunta]
    if row.empty:
        return None
    fig = go.Figure()
    for _, r in row.iterrows():
        fig.add_bar(
            name=r["Resposta"],
            y=[pergunta],
            x=[r["Percentual"]],
            orientation="h",
            marker_color=LIKERT_COLORS.get(r["Resposta"], "#888"),
            text=f"{r['Percentual']:.1f}%",
            textposition="inside"
        )
    fig.update_layout(
        **base_layout(),
        barmode="stack",
        height=150,
        xaxis=dict(title="Percentual de Respondentes", range=[0, 100]),
        yaxis=dict(title="")
    )
    return fig

def likert_matrix(df: pd.DataFrame, mapping: dict, id_col: str) -> pd.DataFrame:
    """
    mapping: { "Rótulo curto na tela": "nome da coluna no df" }
    Retorna linhas com: Pergunta, Resposta (1..5 label), Contagem, Percentual, Total
    """
    out = []
    for display, col in mapping.items():
        if col not in df.columns:
            continue
        # filtra neutros
        mask_valid = df[col].notna() & (~df[col].isin(LIKERT_NEUTROS))
        tmp = df.loc[mask_valid, [col, id_col]].copy()
        if tmp.empty:
            continue
        # conta respondentes distintos por valor
        counts = tmp.groupby(col)[id_col].nunique()
        # normaliza ordem
        # converte valores para labels padronizados quando possível
        order = []
        for lab in LIKERT_LABELS:
            # aceita ambos “4 Boa” e “4 - Boa”
            order.append(lab)
        # para percentuais, usa total de respondentes válidos (distintos)
        total = tmp[id_col].nunique()
        for lab in order:
            # soma todos que “batem” com o lab pelo número 1..5
            n = parse_likert_value(lab.split()[0])  # 1..5
            # soma contagens cujos valores do df correspondam a esse n
            matching = [idx for idx in counts.index if parse_likert_value(idx) == n]
            c = int(sum(counts.loc[matching])) if matching else 0
            p = round((c / total * 100), 1) if total else 0.0
            out.append(dict(Pergunta=display, Resposta=lab, Contagem=c, Percentual=p, Total=total))
    return pd.DataFrame(out)

# -----------------------------------------------------------------------------
# CARREGAMENTO DE DADOS (GitHub + Upload + Local demo)
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_from_github(url: str) -> pd.DataFrame | None:
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return pd.read_excel(io.BytesIO(r.content), engine="openpyxl")
    except Exception as e:
        st.error(f"❌ Erro ao baixar do GitHub: {e}")
        return None

@st.cache_data(show_spinner=False)
def load_from_upload(uploaded) -> pd.DataFrame | None:
    try:
        return pd.read_excel(uploaded, engine="openpyxl")
    except Exception as e:
        st.error(f"❌ Erro ao ler upload: {e}")
        return None

@st.cache_data(show_spinner=False)
def load_from_local(p: Path) -> pd.DataFrame | None:
    try:
        if p.exists():
            return pd.read_excel(p, engine="openpyxl")
        return None
    except Exception as e:
        st.error(f"❌ Erro ao ler arquivo local: {e}")
        return None

# -----------------------------------------------------------------------------
# SEÇÕES (KPIs)
# -----------------------------------------------------------------------------
def kpi_base(df: pd.DataFrame, id_col: str):
    st.subheader("📌 Base")
    total = df[id_col].nunique()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("📝 Total de Respondentes", f"{total:,}")

    idade_col = find_first(df, "idade")
    with c2:
        if idade_col is not None:
            ages = pd.to_numeric(df[idade_col], errors="coerce")
            st.metric("👤 Idade média", f"{ages.mean():.1f} anos" if ages.notna().any() else "N/A")
        else:
            st.metric("👤 Idade média", "N/A")

    ies_col = find_first(df, "instituicao", "ensino", require_all=True) or find_first(df, "ies", require_all=False)
    with c3:
        if ies_col:
            st.metric("🏛️ IES únicas", df[ies_col].nunique())
        else:
            st.metric("🏛️ IES únicas", "N/A")

    fundador_col = find_first(df, "socio") or find_first(df, "fundador")
    with c4:
        if fundador_col:
            fund = df.loc[df[fundador_col].astype(str).str.lower().str.contains("sim"), id_col].nunique()
            pct = (fund / total * 100) if total else 0
            st.metric("🚀 Fundadores / Sócios", f"{fund} ({pct:.1f}%)")
        else:
            st.metric("🚀 Fundadores / Sócios", "N/A")

def kpi_perfil(df: pd.DataFrame, id_col: str):
    st.subheader("👥 Perfil")
    c1, c2 = st.columns(2)

    # VOCE É
    with c1:
        voce_col = find_first(df, "voce", "e")
        if voce_col:
            counts = df.groupby(voce_col)[id_col].nunique().reset_index().rename(columns={voce_col: "Perfil", id_col: "Respondentes"})
            counts["%"] = (counts["Respondentes"] / counts["Respondentes"].sum() * 100).round(1)
            fig = barh_from_counts(counts.sort_values("Respondentes", ascending=True), "Perfil", "Respondentes", color="#667eea")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(counts, hide_index=True, use_container_width=True)
        else:
            st.info("📎 Coluna de perfil (\"Você é\") não encontrada.")

    # Idade (faixas)
    with c2:
        idade_col = find_first(df, "idade")
        if idade_col:
            t = df[[idade_col, id_col]].copy()
            t[idade_col] = pd.to_numeric(t[idade_col], errors="coerce")
            t["Faixa"] = pd.cut(t[idade_col], bins=[0, 19, 25, 30, 120], labels=["Até 19", "20–25", "26–30", "31+"])
            counts = t.groupby("Faixa")[id_col].nunique().reset_index().rename(columns={id_col: "Respondentes"})
            counts["%"] = (counts["Respondentes"] / counts["Respondentes"].sum() * 100).round(1)
            fig = go.Figure([go.Bar(x=counts["Faixa"], y=counts["Respondentes"], text=[f"{r} ({p}%)" for r, p in zip(counts["Respondentes"], counts["%"])], textposition="outside", marker_color="#764ba2")])
            fig.update_layout(**base_layout(), height=400)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(counts, hide_index=True, use_container_width=True)
        else:
            st.info("📎 Coluna de idade não encontrada.")

    # Grau
    st.markdown("### 🎓 Grau de formação")
    grau_col = find_first(df, "grau", "graduacao", require_all=False)
    if grau_col:
        counts = df.groupby(grau_col)[id_col].nunique().reset_index().rename(columns={grau_col: "Grau", id_col: "Respondentes"})
        counts["%"] = (counts["Respondentes"] / counts["Respondentes"].sum() * 100).round(1)
        st.plotly_chart(barh_from_counts(counts.sort_values("Respondentes", ascending=True), "Grau", "Respondentes", color="#f39c12"), use_container_width=True)
        st.dataframe(counts, hide_index=True, use_container_width=True)
    else:
        st.info("📎 Coluna de grau não encontrada.")

    # IES
    st.markdown("### 🏛️ Instituições (IES)")
    ies_col = find_first(df, "instituicao", "ensino", require_all=True) or find_first(df, "ies", require_all=False)
    if ies_col:
        counts = df.groupby(ies_col)[id_col].nunique().reset_index().rename(columns={ies_col: "IES", id_col: "Respondentes"})
        counts["%"] = (counts["Respondentes"] / counts["Respondentes"].sum() * 100).round(1)
        counts = counts.sort_values("Respondentes", ascending=False)
        st.plotly_chart(barh_from_counts(counts, "IES", "Respondentes", color="#9b59b6"), use_container_width=True)
        with st.expander("📋 Tabela completa"):
            st.dataframe(counts, hide_index=True, use_container_width=True)
    else:
        st.info("📎 Coluna de IES não encontrada.")

def kpi_cursos(df: pd.DataFrame, id_col: str):
    st.subheader("🎓 Cursos")
    curso_col = find_first(df, "curso", "graduacao", require_all=False)
    if curso_col:
        counts = df.groupby(curso_col)[id_col].nunique().reset_index().rename(columns={curso_col: "Curso", id_col: "Respondentes"})
        counts["%"] = (counts["Respondentes"] / counts["Respondentes"].sum() * 100).round(1)
        top15 = counts.sort_values("Respondentes", ascending=False).head(15).sort_values("Respondentes")
        st.plotly_chart(barh_from_counts(top15, "Curso", "Respondentes", color="#2ecc71"), use_container_width=True)
        with st.expander("📋 Ver todos os cursos"):
            st.dataframe(counts.sort_values("Respondentes", ascending=False), hide_index=True, use_container_width=True)
    else:
        st.info("📎 Coluna de curso não encontrada.")

def kpi_emp_rela(df: pd.DataFrame, id_col: str):
    st.subheader("🚀 Empreendedorismo – Conceitos, Fundadores, Projetos")
    # Conceitos (múltipla ou single)
    conceitos_col = find_first(df, "o que voce entende como empreendedorismo")
    if conceitos_col:
        counts = df.groupby(conceitos_col)[id_col].nunique().reset_index().rename(columns={conceitos_col: "Conceito", id_col: "Respondentes"})
        counts["%"] = (counts["Respondentes"] / df[id_col].nunique() * 100).round(1)
        st.plotly_chart(barh_from_counts(counts.sort_values("Respondentes", ascending=True), "Conceito", "Respondentes", color="#3498db"), use_container_width=True)
    else:
        st.info("📎 Coluna de 'conceitos de empreendedorismo' não encontrada.")

    # Fundadores
    fundador_col = find_first(df, "socio") or find_first(df, "fundador")
    if fundador_col:
        counts = df.groupby(fundador_col)[id_col].nunique().reset_index().rename(columns={fundador_col: "Resposta", id_col: "Respondentes"})
        counts["%"] = (counts["Respondentes"] / df[id_col].nunique() * 100).round(1)
        fig = go.Figure([go.Bar(x=counts["Resposta"], y=counts["Respondentes"], text=[f"{r} ({p}%)" for r, p in zip(counts["Respondentes"], counts["%"])], textposition="outside", marker_color="#e67e22")])
        fig.update_layout(**base_layout(), height=400)
        st.plotly_chart(fig, use_container_width=True)
        fund = df.loc[df[fundador_col].astype(str).str.lower().str.contains("sim"), id_col].nunique()
        pct = (fund / df[id_col].nunique() * 100) if df[id_col].nunique() else 0
        st.metric("🎯 Total de Fundadores/Sócios", f"{fund} ({pct:.1f}%)")
    else:
        st.info("📎 Coluna de fundadores/sócios não encontrada.")

    # Projetos
    projetos_col = find_first(df, "ao longo da sua graduacao, quais projetos voce ja participou")
    if projetos_col:
        counts = df.groupby(projetos_col)[id_col].nunique().reset_index().rename(columns={projetos_col: "Projeto", id_col: "Respondentes"})
        counts["%"] = (counts["Respondentes"] / df[id_col].nunique() * 100).round(1)
        st.plotly_chart(barh_from_counts(counts.sort_values("Respondentes", ascending=True), "Projeto", "Respondentes", color="#16a085"), use_container_width=True)
    else:
        st.info("📎 Coluna de projetos não encontrada.")

def kpi_likert_block(df: pd.DataFrame, id_col: str, title: str, detect_keywords: list[str], prefix_label: str):
    st.subheader(title)
    # pega colunas que atendem aos keywords (todas)
    cols = []
    for c in df.columns:
        if all(normalize_text(k) in normalize_text(c) for k in detect_keywords):
            cols.append(c)
    if not cols:
        st.info("📎 Nenhuma coluna encontrada para este bloco.")
        return
    # mapping display -> col
    mapping = {}
    for c in cols:
        # tenta usar o “sufixo” mais legível
        # pega tudo após o último fechamento de aspas ou depois do último ponto de interrogação
        text = c
        if "?" in text:
            text = text.split("?")[-1]
        text = text.replace("Caso não saiba avaliar", "").replace("Caso nao saiba avaliar", "")
        text = text.strip(" :-—–")
        text = re.sub(r'\s+', ' ', text).strip()
        display = f"{prefix_label}: {text}" if text else c
        mapping[display] = c

    df_matrix = likert_matrix(df, mapping, id_col)
    if df_matrix.empty:
        st.info("Sem dados válidos (após remover neutros).")
        return

    # Heatmap (matriz)
    pivot = df_matrix.pivot(index="Pergunta", columns="Resposta", values="Percentual").reindex(columns=LIKERT_LABELS)
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=[wrap(x) for x in pivot.index],
        colorscale=[
            [0, LIKERT_COLORS["1 Muito ruim"]],
            [0.25, LIKERT_COLORS["2 Ruim"]],
            [0.5, LIKERT_COLORS["3 Razoável"]],
            [0.75, LIKERT_COLORS["4 Boa"]],
            [1, LIKERT_COLORS["5 Excelente"]],
        ],
        text=pivot.values,
        texttemplate="%{text:.1f}%",
        hoverongaps=False,
    ))
    fig.update_layout(**base_layout(), height=dynamic_height(len(pivot.index)), margin=dict(l=240, r=20, t=40, b=60))
    st.plotly_chart(fig, use_container_width=True)

def kpi_frases_likert(df: pd.DataFrame, id_col: str, title: str, *phrases):
    st.subheader(title)
    found = []
    for p in phrases:
        col = find_first(df, p)
        if col:
            found.append((p, col))
    if not found:
        st.info("📎 Nenhuma coluna dessas frases foi encontrada.")
        return
    metrics = []
    for _, col in found:
        idx = likert_index(df[col])
        if idx is not None:
            label = re.sub(r'^\W+|"', "", col).strip()
            metrics.append((label, idx))
    if not metrics:
        st.info("Sem dados válidos (após remover neutros).")
        return
    cols = st.columns(min(4, len(metrics)))
    for i, (label, val) in enumerate(metrics):
        with cols[i % len(cols)]:
            st.metric(wrap(label, 30).replace("<br>", " "), f"{val:.1f}/100")

def kpi_permanencia_evasao(df: pd.DataFrame, id_col: str):
    st.subheader("🎓 Permanência e Evasão")
    c1, c2 = st.columns(2)

    # Permanência
    with c1:
        col = find_first(df, "quais motivos voce considera que te fazem permanecer")
        if col:
            counts = df.groupby(col)[id_col].nunique().reset_index().rename(columns={col: "Motivo", id_col: "Respondentes"})
            counts["%"] = (counts["Respondentes"] / df[id_col].nunique() * 100).round(1)
            st.plotly_chart(barh_from_counts(counts.sort_values("Respondentes", ascending=True), "Motivo", "Respondentes", color="#2ecc71"), use_container_width=True)
            with st.expander("📋 Tabela"):
                st.dataframe(counts, hide_index=True, use_container_width=True)
        else:
            st.info("📎 Coluna de permanência não encontrada.")

    # Evasão
    with c2:
        col = find_first(df, "quais motivos voce considera que te fariam deixar")
        if col:
            counts = df.groupby(col)[id_col].nunique().reset_index().rename(columns={col: "Motivo", id_col: "Respondentes"})
            counts["%"] = (counts["Respondentes"] / df[id_col].nunique() * 100).round(1)
            st.plotly_chart(barh_from_counts(counts.sort_values("Respondentes", ascending=True), "Motivo", "Respondentes", color="#e74c3c"), use_container_width=True)
            with st.expander("📋 Tabela"):
                st.dataframe(counts, hide_index=True, use_container_width=True)
        else:
            st.info("📎 Coluna de evasão não encontrada.")

    # Evasão (colegas)
    st.markdown("### 👥 Evasão de colegas")
    col = find_first(df, "voce possui colegas que deixaram a instituicao de ensino superior sem concluir o curso")
    if col:
        counts = df.groupby(col)[id_col].nunique().reset_index().rename(columns={col: "Resposta", id_col: "Respondentes"})
        counts["%"] = (counts["Respondentes"] / df[id_col].nunique() * 100).round(1)
        fig = go.Figure([go.Pie(labels=counts["Resposta"], values=counts["Respondentes"], text=[f"{r} ({p}%)" for r, p in zip(counts["Respondentes"], counts["%"])], textinfo="label+text")])
        fig.update_layout(**base_layout(), height=420)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📎 Coluna sobre evasão de colegas não encontrada.")

# -----------------------------------------------------------------------------
# APP
# -----------------------------------------------------------------------------
st.markdown("""
<style>
.block-container { padding-top: 1.25rem; padding-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="text-align:center; margin-bottom:0;">📊 Dashboard CEFET-MG</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center; opacity:0.8;">Pesquisa sobre Empreendedorismo e Educação Superior — Modo <b>ADD-ONLY</b></p>', unsafe_allow_html=True)
st.markdown("---")

with st.sidebar:
    st.markdown("### 📁 Fonte de dados")
    use_github = st.checkbox("Usar arquivo do GitHub", value=True)
    selected_key = None
    if use_github:
        selected_key = st.selectbox("Selecione o arquivo", list(GITHUB_FILES.keys()))
    st.markdown("**OU**")
    uploaded = st.file_uploader("📤 Upload de Excel", type=["xlsx", "xls"])
    st.markdown("---")
    st.info("Regra de contagem: sempre **DistinctCount(Respondent ID)**.\nLikert → **0–100**, ignorando **“Não observado”**.\nSem sobreposição de eixos (altura dinâmica + automargem).")

# Carrega dados
df = None
src = ""
if use_github and selected_key:
    with st.spinner("Baixando do GitHub..."):
        df = load_from_github(GITHUB_FILES[selected_key])
        src = f"GitHub: {selected_key}"
elif uploaded is not None:
    with st.spinner("Lendo upload..."):
        df = load_from_upload(uploaded)
        src = f"Upload: {uploaded.name}"
elif LOCAL_DEMO.exists():
    with st.spinner("Abrindo arquivo local demo..."):
        df = load_from_local(LOCAL_DEMO)
        src = f"Arquivo local: {LOCAL_DEMO}"

if df is None:
    st.warning("Configure a fonte de dados na barra lateral. Opcionalmente, adicione `data/dados_cefet.xlsx` ao repositório.")
    st.stop()

# Detecta ID
try:
    id_col = find_respondent_id_col(df)
except Exception as e:
    st.error(str(e))
    st.stop()

st.success(f"✅ {src} • Respondentes únicos: **{df[id_col].nunique():,}**")

# TABS (sem remover KPIs)
tabs = st.tabs([
    "📌 Base",
    "👥 Perfil",
    "🎓 Cursos",
    "🚀 Empreendedorismo",
    "👨‍🎓 Alunos",
    "👨‍🏫 Professores",
    "🏢 Infraestrutura (PCD/Geral/Internet)",
    "📚 Metodologia / Matriz / Casos",
    "🎯 Ingresso",
    "🎓 Permanência / Evasão",
    "🗂️ Dados (preview)"
])

with tabs[0]:
    kpi_base(df, id_col)

with tabs[1]:
    kpi_perfil(df, id_col)

with tabs[2]:
    kpi_cursos(df, id_col)

with tabs[3]:
    kpi_emp_rela(df, id_col)

with tabs[4]:
    # Alunos – “O quanto as seguintes características estão presentes nos(as) ALUNOS(AS) ...”
    kpi_likert_block(
        df, id_col,
        "👨‍🎓 Alunos — características (Likert 0–100)",
        ["o quanto as seguintes caracteristicas estao presentes", "alunos"],
        "Alunos"
    )
    # Frase: "os(as) ALUNOS(AS) ... possuem postura empreendedora"
    kpi_frases_likert(
        df, id_col,
        "Frase avaliada — Postura empreendedora dos alunos",
        "considerando o respondido na questao anterior, como voce avalia a frase: \"os(as) alunos(as)"
    )

with tabs[5]:
    # Professores – características
    kpi_likert_block(
        df, id_col,
        "👨‍🏫 Professores — características (Likert 0–100)",
        ["o quanto as seguintes caracteristicas estao presentes", "professores"],
        "Professores"
    )
    # Frase: "os(as) PROFESSORES(AS) ... possuem postura empreendedora"
    kpi_frases_likert(
        df, id_col,
        "Frase avaliada — Postura empreendedora dos professores",
        "considerando o respondido na questao anterior, como voce avalia a frase: \"os(as) professores(as)"
    )
    # Experiência / Acessíveis (distribuição)
    for k in [
        "os(as) professores(as) da minha instituicao de ensino superior possuem experiencia no mercado de trabalho",
        "os(as) professores(as) da minha instituicao de ensino superior sao acessiveis para apoiar as iniciativas"
    ]:
        col = find_first(df, k)
        if col:
            counts = df.groupby(col)[id_col].nunique().reset_index().rename(columns={col: "Resposta", id_col: "Respondentes"})
            counts["%"] = (counts["Respondentes"] / df[id_col].nunique() * 100).round(1)
            st.plotly_chart(barh_from_counts(counts.sort_values("Respondentes", ascending=True), "Resposta", "Respondentes", color="#e67e22"), use_container_width=True)

with tabs[6]:
    # PCD – “Como você avalia a qualidade da infraestrutura destinada à pessoas com deficiência ...”
    kpi_likert_block(
        df, id_col,
        "♿ Infraestrutura — pessoas com deficiência (Likert 0–100)",
        ["como voce avalia a qualidade da infraestrutura destinada a pessoas com deficiencia"],
        "PCD"
    )
    # Geral – “Como você avalia a qualidade da infraestrutura oferecida ...”
    kpi_likert_block(
        df, id_col,
        "🏛️ Infraestrutura — geral (Likert 0–100)",
        ["como voce avalia a qualidade da infraestrutura oferecida pela sua instituicao de ensino superior"],
        "Infra"
    )
    # Internet – “Como você avalia a qualidade da internet oferecida ...”
    kpi_likert_block(
        df, id_col,
        "📶 Internet (Likert 0–100)",
        ["como voce avalia a qualidade da internet oferecida pela sua instituicao de ensino superior"],
        "Internet"
    )

with tabs[7]:
    # Metodologia / Matriz / Casos
    kpi_frases_likert(
        df, id_col,
        "📚 Metodologia / Matriz / Casos (Likert 0–100)",
        "o modelo/metodologia de ensino da minha instituicao de ensino superior contribui para que eu desenvolva postura empreendedora",
        "a matriz curricular do curso contribui para o desenvolvimento da minha postura empreendedora",
        "a minha instituicao de ensino superior oferece uma matriz curricular flexivel para que eu possa me engajar em atividades extra-curriculares",
        "a instituicao de ensino superior apresenta casos de sucesso de ex-alunos(as)"
    )

with tabs[8]:
    # Ingresso – influência
    col = find_first(df, "o quanto voce considera que a sua instituicao de ensino superior influenciou na sua decisao de ingresso")
    if col:
        idx = likert_index(df[col])
        if idx is not None:
            st.metric("Influência da IES no ingresso", f"{idx:.1f}/100")
    else:
        st.info("📎 Coluna de influência no ingresso não encontrada.")

with tabs[9]:
    kpi_permanencia_evasao(df, id_col)

with tabs[10]:
    st.caption("Pré-visualização (100 primeiras linhas)")
    st.dataframe(df.head(100), use_container_width=True)
    st.download_button(
        "📥 Baixar dados em CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="dados_cefet_export.csv",
        mime="text/csv",
        use_container_width=True
    )
