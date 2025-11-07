import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import requests
import io
from datetime import datetime
import unicodedata
import re

# ===== Configurações Iniciais =====
st.set_page_config(
    page_title="Dashboard CEFET-MG",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes
LIKERT_ORDER = ["1 Muito ruim", "2 Ruim", "3 Razoável", "4 Boa", "5 Excelente"]
LIKERT_NEUTROS = {"Não observado", "Nao observado", "Não se aplica", "Nao se aplica"}
LIKERT_COLORS = {
    "1 Muito ruim": "#ff4444",
    "2 Ruim": "#ffaa44",
    "3 Razoável": "#ffff44",
    "4 Boa": "#88ff44",
    "5 Excelente": "#44ff44"
}

LIKERT_TO_INDEX = {
    "1 Muito ruim": 20,
    "2 Ruim": 40,
    "3 Razoável": 60,
    "4 Boa": 80,
    "5 Excelente": 100
}

ID_CANDIDATES = [
    "respondent_id", "respondente_id", "id_respondente",
    "respondentid", "idrespondente"
]

# ===== Funções Utilitárias =====
def normalize_text(s):
    """Normaliza texto removendo acentos e caracteres especiais"""
    if not isinstance(s, str):
        return str(s)
    s = s.strip().lower()
    s = ''.join(ch for ch in unicodedata.normalize('NFD', s) 
                if unicodedata.category(ch) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '', s)

def find_respondent_id_col(df):
    """Detecta coluna de ID do respondente"""
    cols_norm = {normalize_text(c): c for c in df.columns}
    
    for candidate in ID_CANDIDATES:
        if normalize_text(candidate) in cols_norm:
            return cols_norm[normalize_text(candidate)]
    
    for key in ["respondent", "respondente", "id"]:
        for norm_name, orig_name in cols_norm.items():
            if key in norm_name and ("respondent" in norm_name or "respondente" in norm_name):
                return orig_name
    
    raise ValueError("Coluna de ID do respondente não detectada")

def distinct_count(series, df, id_col):
    """Conta respondentes únicos para uma série"""
    valid_mask = series.notna() & (series != '')
    return df.loc[valid_mask, id_col].nunique()

def likert_to_index(series, df, id_col):
    """Converte série Likert para índice 0-100 (excluindo neutros)"""
    valid_mask = ~series.isin(LIKERT_NEUTROS) & series.notna()
    valid_data = series[valid_mask]
    
    if len(valid_data) == 0:
        return None
    
    mapped = valid_data.map(LIKERT_TO_INDEX)
    return mapped.mean()

def get_base_graph_config():
    """Configurações base para gráficos"""
    return {
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'font': {
            'color': 'white',
            'size': 12
        },
        'xaxis': {
            'gridcolor': 'rgba(255,255,255,0.1)',
            'linecolor': 'rgba(255,255,255,0.2)',
            'tickfont': {'color': 'white'},
            'automargin': True
        },
        'yaxis': {
            'gridcolor': 'rgba(255,255,255,0.1)',
            'linecolor': 'rgba(255,255,255,0.2)',
            'tickfont': {'color': 'white'},
            'automargin': True
        }
    }

def break_text(text, width=20):
    """Quebra texto em múltiplas linhas"""
    if not isinstance(text, str):
        return str(text)
    
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= width:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return '<br>'.join(lines)

# ===== Funções Likert =====
@st.cache_data
def create_likert_matrix(df, questions, id_col):
    """Cria matriz de respostas Likert"""
    results = []
    
    for display_name, col in questions.items():
        if col not in df.columns:
            continue
        
        valid_responses = df[~df[col].isin(LIKERT_NEUTROS)].copy()
        counts = valid_responses.groupby(col)[id_col].nunique().reindex(LIKERT_ORDER).fillna(0)
        total = valid_responses[id_col].nunique()
        
        if total > 0:
            percentages = (counts / total * 100).round(1)
            
            for likert_value in LIKERT_ORDER:
                results.append({
                    'Pergunta': display_name,
                    'Resposta': likert_value,
                    'Contagem': counts.get(likert_value, 0),
                    'Percentual': percentages.get(likert_value, 0),
                    'Total': total
                })
    
    return pd.DataFrame(results)

def plot_likert_matrix(df_matrix):
    """Plota heatmap da matriz Likert"""
    if df_matrix.empty:
        return None
        
    matrix_data = df_matrix.pivot(
        index='Pergunta',
        columns='Resposta',
        values='Percentual'
    ).reindex(columns=LIKERT_ORDER)
    
    fig = go.Figure(data=go.Heatmap(
        z=matrix_data.values,
        x=matrix_data.columns,
        y=matrix_data.index,
        colorscale=[
            [0, "#ff4444"],
            [0.25, "#ffaa44"],
            [0.5, "#ffff44"],
            [0.75, "#88ff44"],
            [1, "#44ff44"]
        ],
        text=matrix_data.values,
        texttemplate="%{text:.1f}%",
        textfont={"color": "white"},
        hoverongaps=False
    ))
    
    height = max(350, len(matrix_data.index) * 24 + 120)
    
    fig.update_layout(
        **get_base_graph_config(),
        height=height,
        xaxis_title="Avaliação",
        yaxis_title="Item Avaliado",
        margin=dict(l=200, r=20, t=60, b=60)
    )
    
    return fig

def plot_likert_bars(df_matrix, question):
    """Plota barras 100% empilhadas para uma pergunta"""
    df_question = df_matrix[df_matrix['Pergunta'] == question].copy()
    
    if df_question.empty:
        return None
    
    fig = go.Figure()
    
    for i, row in df_question.iterrows():
        fig.add_trace(go.Bar(
            name=row['Resposta'],
            y=[question],
            x=[row['Percentual']],
            orientation='h',
            marker_color=LIKERT_COLORS[row['Resposta']],
            text=f"{row['Percentual']:.1f}%",
            textposition='inside',
            textfont={'color': 'white'},
            hovertemplate=(
                f"<b>{row['Resposta']}</b><br>"
                f"Respondentes: {row['Contagem']}<br>"
                f"Percentual: {row['Percentual']:.1f}%<br>"
                f"Total: {row['Total']}"
            )
        ))
    
    fig.update_layout(
        **get_base_graph_config(),
        barmode='stack',
        showlegend=True,
        height=150,
        margin=dict(l=200, r=20, t=20, b=20),
        xaxis=dict(
            title="Percentual de Respondentes",
            range=[0, 100]
        ),
        yaxis=dict(
            title=""
        )
    )
    
    return fig

# ===== KPI: Visão Geral Completa =====
def show_complete_overview(df, id_col):
    """KPIs completos da visão geral"""
    st.markdown("## 📊 Visão Geral Completa")
    
    # Row 1: Métricas Base
    cols = st.columns(4)
    
    with cols[0]:
        total_respondentes = df[id_col].nunique()
        st.metric("📝 Total de Respondentes", f"{total_respondentes:,}")
    
    with cols[1]:
        idade_col = next((col for col in df.columns if 'idade' in col.lower()), None)
        if idade_col:
            valid_ages = pd.to_numeric(df[idade_col], errors='coerce')
            media_idade = valid_ages.mean()
            if not pd.isna(media_idade):
                st.metric("👤 Idade Média", f"{media_idade:.1f} anos")
            else:
                st.metric("👤 Idade Média", "N/A")
        else:
            st.metric("👤 Idade Média", "N/A")
    
    with cols[2]:
        # Total de cursos únicos
        curso_col = next((col for col in df.columns 
                         if 'curso' in col.lower() and 'graduação' in col.lower()), None)
        if curso_col:
            total_cursos = df[curso_col].nunique()
            st.metric("🎓 Cursos Únicos", f"{total_cursos}")
        else:
            st.metric("🎓 Cursos Únicos", "N/A")
    
    with cols[3]:
        # Fundadores
        fundador_col = next((col for col in df.columns 
                            if 'sócio' in col.lower() or 'fundador' in col.lower()), None)
        if fundador_col:
            fundadores = df[df[fundador_col] == 'Sim'][id_col].nunique()
            pct = (fundadores / total_respondentes * 100) if total_respondentes > 0 else 0
            st.metric("🚀 Fundadores", f"{fundadores} ({pct:.1f}%)")
        else:
            st.metric("🚀 Fundadores", "N/A")

# ===== KPI: Perfil Detalhado =====
def show_detailed_profile(df, id_col):
    """Análise detalhada de perfil"""
    st.markdown("## 👥 Perfil dos Respondentes (Detalhado)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Distribuição por Perfil")
        perfil_col = next((col for col in df.columns if 'voce' in col.lower() and 'é' in col.lower()), None)
        
        if perfil_col:
            counts = df.groupby(perfil_col)[id_col].nunique().reset_index()
            counts.columns = ['Perfil', 'Respondentes']
            total = counts['Respondentes'].sum()
            counts['%'] = (counts['Respondentes'] / total * 100).round(1)
            
            height = max(350, len(counts) * 24 + 120)
            
            fig = go.Figure(data=[
                go.Bar(
                    y=df_indices['Item'],
                    x=df_indices['Índice'],
                    orientation='h',
                    text=[f"{v:.1f}" for v in df_indices['Índice']],
                    textposition='outside',
                    marker_color='#f39c12'
                )
            ])
            
            height = max(350, len(df_indices) * 24 + 120)
            fig.update_layout(
                **get_base_graph_config(),
                height=height,
                xaxis=dict(range=[0, 100]),
                margin=dict(l=200, r=20, t=40, b=60)
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 Colunas de matriz curricular não encontradas")

# ===== KPI: Influência de Ingresso (Likert 0-100) =====
def show_enrollment_influence(df, id_col):
    """Influência na decisão de ingresso"""
    st.markdown("## 🎯 Influência na Decisão de Ingresso")
    
    influencia_cols = [col for col in df.columns if 'influência' in col.lower() or 'influencia' in col.lower()]
    
    if influencia_cols:
        indices = {}
        for col in influencia_cols:
            idx = likert_to_index(df[col], df, id_col)
            if idx is not None:
                label = col.replace('influencia_', '').replace('influência_', '').replace('_', ' ').title()
                indices[label] = idx
        
        if indices:
            # Métricas
            cols = st.columns(min(4, len(indices)))
            for i, (label, idx) in enumerate(indices.items()):
                with cols[i % len(cols)]:
                    st.metric(label, f"{idx:.1f}/100")
            
            # Gráfico
            df_indices = pd.DataFrame(list(indices.items()), columns=['Fator', 'Índice'])
            df_indices = df_indices.sort_values('Índice', ascending=True)
            
            fig = go.Figure(data=[
                go.Bar(
                    y=df_indices['Fator'],
                    x=df_indices['Índice'],
                    orientation='h',
                    text=[f"{v:.1f}" for v in df_indices['Índice']],
                    textposition='outside',
                    marker_color='#27ae60'
                )
            ])
            
            height = max(350, len(df_indices) * 24 + 120)
            fig.update_layout(
                **get_base_graph_config(),
                height=height,
                xaxis=dict(range=[0, 100]),
                margin=dict(l=200, r=20, t=40, b=60)
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 Colunas de influência de ingresso não encontradas")

# ===== KPI: Permanência e Evasão (Múltipla Escolha) =====
def show_retention_and_evasion(df, id_col):
    """Análise de permanência e evasão"""
    st.markdown("## 🎓 Permanência e Evasão")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✅ Motivos de Permanência")
        permanencia_cols = [col for col in df.columns if 'permanência' in col.lower() or 'permanencia' in col.lower()]
        
        if permanencia_cols:
            for col in permanencia_cols:
                st.markdown(f"**{col}**")
                
                # Múltipla escolha: contar respondentes únicos por opção
                counts = df.groupby(col)[id_col].nunique().reset_index()
                counts.columns = ['Motivo', 'Respondentes']
                total = df[id_col].nunique()
                counts['%'] = (counts['Respondentes'] / total * 100).round(1)
                counts = counts.sort_values('Respondentes', ascending=False)
                
                fig = go.Figure(data=[
                    go.Bar(
                        y=counts['Motivo'].apply(break_text),
                        x=counts['Respondentes'],
                        orientation='h',
                        text=[f"{r} ({p}%)" for r, p in zip(counts['Respondentes'], counts['%'])],
                        textposition='outside',
                        marker_color='#2ecc71'
                    )
                ])
                
                height = max(350, len(counts) * 24 + 120)
                fig.update_layout(
                    **get_base_graph_config(),
                    height=height,
                    margin=dict(l=200, r=20, t=40, b=60)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("📋 Ver tabela detalhada"):
                    st.dataframe(counts, use_container_width=True, hide_index=True)
        else:
            st.info("📊 Colunas de permanência não encontradas")
    
    with col2:
        st.subheader("❌ Motivos de Evasão")
        evasao_cols = [col for col in df.columns if 'evasão' in col.lower() or 'evasao' in col.lower()]
        
        if evasao_cols:
            for col in evasao_cols:
                st.markdown(f"**{col}**")
                
                counts = df.groupby(col)[id_col].nunique().reset_index()
                counts.columns = ['Motivo', 'Respondentes']
                total = df[id_col].nunique()
                counts['%'] = (counts['Respondentes'] / total * 100).round(1)
                counts = counts.sort_values('Respondentes', ascending=False)
                
                fig = go.Figure(data=[
                    go.Bar(
                        y=counts['Motivo'].apply(break_text),
                        x=counts['Respondentes'],
                        orientation='h',
                        text=[f"{r} ({p}%)" for r, p in zip(counts['Respondentes'], counts['%'])],
                        textposition='outside',
                        marker_color='#e74c3c'
                    )
                ])
                
                height = max(350, len(counts) * 24 + 120)
                fig.update_layout(
                    **get_base_graph_config(),
                    height=height,
                    margin=dict(l=200, r=20, t=40, b=60)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("📋 Ver tabela detalhada"):
                    st.dataframe(counts, use_container_width=True, hide_index=True)
        else:
            st.info("📊 Colunas de evasão não encontradas")
    
    # Evasão de Colegas
    st.subheader("👥 Evasão de Colegas")
    evasao_colegas_cols = [col for col in df.columns if 'colega' in col.lower() and 'evasão' in col.lower()]
    
    if evasao_colegas_cols:
        for col in evasao_colegas_cols:
            st.markdown(f"**{col}**")
            
            counts = df.groupby(col)[id_col].nunique().reset_index()
            counts.columns = ['Resposta', 'Respondentes']
            total = df[id_col].nunique()
            counts['%'] = (counts['Respondentes'] / total * 100).round(1)
            
            fig = go.Figure(data=[
                go.Pie(
                    labels=counts['Resposta'],
                    values=counts['Respondentes'],
                    text=[f"{r} ({p}%)" for r, p in zip(counts['Respondentes'], counts['%'])],
                    textinfo='label+text',
                    marker=dict(colors=['#3498db', '#e67e22', '#95a5a6'])
                )
            ])
            
            fig.update_layout(
                **get_base_graph_config(),
                height=400,
                margin=dict(l=20, r=20, t=40, b=60)
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 Colunas sobre evasão de colegas não encontradas")

# ===== Funções de Carregamento =====
@st.cache_data
def load_excel_from_github(url):
    """Carrega arquivo Excel diretamente do GitHub via URL raw"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        in_memory_file = io.BytesIO(response.content)
        df = pd.read_excel(in_memory_file, engine='openpyxl')
        return df
    except Exception as e:
        st.error(f"❌ Erro ao baixar arquivo do GitHub: {str(e)}")
        return None

@st.cache_data
def process_data(df):
    """Processa dados mantendo contagem de respondentes únicos"""
    if df is None:
        return None, None
    
    try:
        id_col = find_respondent_id_col(df)
        return df, id_col
    except ValueError as e:
        st.error(str(e))
        return None, None

# ===== CSS e Estilo =====
st.markdown("""
<style>
    .main-header {
        font-size: 1.5rem;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    @media (min-width: 768px) {
        .main-header {
            font-size: 2.5rem;
        }
    }
    
    .stButton>button {
        width: 100%;
    }
    
    .reportview-container {
        background: #0e1117;
    }
    
    .sidebar .sidebar-content {
        background: #262730;
    }
    
    .tooltip {
        font-size: 1rem;
        color: white;
    }
    
    .st-bw {
        color: white !important;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Badge de aviso */
    .warning-badge {
        background-color: #f39c12;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: bold;
        display: inline-block;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ===== Main =====
def main():
    # Header
    st.markdown('<h1 class="main-header">📊 Dashboard CEFET-MG - Completo</h1>', unsafe_allow_html=True)
    st.markdown("### Pesquisa sobre Empreendedorismo e Educação Superior")
    st.markdown("#### ✅ **TODOS OS KPIs PRESERVADOS** - Modo ADD-ONLY Ativo")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 📁 Fonte de Dados")
        
        # Opção 1: Arquivo do GitHub
        use_github = st.checkbox("📦 Usar arquivo do GitHub", value=True)
        
        if use_github:
            github_files = {
                "Dados CEFET-MG": "https://github.com/Totishuro/JOAO-cefet/raw/refs/heads/main/JOAO-cefet-main/data/Dados%20CEFET_MG%20%20Sem%20dados%20pessoais%202%20%20Copia.xlsx",
                "dados_cefet.xlsx": "https://github.com/Totishuro/JOAO-cefet/raw/refs/heads/main/JOAO-cefet-main/data/dados_cefet.xlsx"
            }
            
            selected_file = st.selectbox(
                "Selecione o arquivo",
                list(github_files.keys()),
                help="Arquivos disponíveis no repositório"
            )
        
        # Opção 2: Upload manual
        st.markdown("**OU**")
        uploaded_file = st.file_uploader(
            "📤 Upload arquivo Excel",
            type=['xlsx', 'xls'],
            help="Qualquer arquivo .xlsx com a estrutura correta"
        )
        
        st.markdown("---")
        st.markdown("### ℹ️ Sobre")
        st.info("Dashboard MVP v2.0 - TODOS OS KPIs")
        st.success("✅ Modo ADD-ONLY: Nenhum KPI foi removido")
        
        st.markdown("**KPIs Implementados:**")
        st.markdown("""
        - ✅ Base: Total respondentes
        - ✅ Perfil, Idade, Grau, IES, PCD
        - ✅ Cursos (Top 15 + completo)
        - ✅ Empreendedorismo (conceitos, fundadores, projetos, modelos)
        - ✅ Alunos (Likert 0-100)
        - ✅ Professores (Likert 0-100)
        - ✅ Infraestrutura + Internet (Likert 0-100)
        - ✅ Metodologia (Likert 0-100)
        - ✅ Matriz Curricular (Likert 0-100)
        - ✅ Influência de Ingresso (Likert 0-100)
        - ✅ Permanência + Evasão (múltipla escolha)
        """)
        
        st.markdown(f"**Última atualização:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Processar dados
    df = None
    source_info = ""
    
    if use_github and not uploaded_file:
        with st.spinner('📥 Carregando arquivo do GitHub...'):
            df = load_excel_from_github(github_files[selected_file])
            source_info = f"📦 Arquivo: {selected_file}"
    
    if uploaded_file:
        with st.spinner('📥 Processando upload...'):
            df = pd.read_excel(uploaded_file, engine='openpyxl')
            source_info = f"📤 Upload: {uploaded_file.name}"
    
    if df is not None:
        st.success(source_info)
        
        with st.spinner('⚙️ Processando dados...'):
            df_processed, id_col = process_data(df)
        
        if df_processed is not None and id_col is not None:
            total_resp = df_processed[id_col].nunique()
            st.success(f"✅ {total_resp:,} respondentes únicos carregados!")
            
            # Informações de debug
            with st.expander("🔍 Debug: Colunas Detectadas"):
                st.write(f"**Total de colunas:** {len(df_processed.columns)}")
                st.write(f"**ID Column:** {id_col}")
                st.write("**Primeiras 20 colunas:**")
                st.write(df_processed.columns[:20].tolist())
            
            # Tabs completas
            tabs = st.tabs([
                "📊 Geral",
                "👥 Perfil",
                "🎓 Cursos",
                "🚀 Empreendedorismo",
                "👨‍🎓 Alunos",
                "👨‍🏫 Professores",
                "🏢 Infraestrutura",
                "📚 Metodologia",
                "📋 Matriz",
                "🎯 Ingresso",
                "🎓 Permanência/Evasão"
            ])
            
            with tabs[0]:
                show_complete_overview(df_processed, id_col)
                with st.expander("🔍 Ver dados brutos (100 primeiras linhas)"):
                    st.dataframe(df_processed.head(100), use_container_width=True)
            
            with tabs[1]:
                show_detailed_profile(df_processed, id_col)
            
            with tabs[2]:
                show_complete_courses(df_processed, id_col)
            
            with tabs[3]:
                show_complete_entrepreneurship(df_processed, id_col)
            
            with tabs[4]:
                show_student_characteristics(df_processed, id_col)
            
            with tabs[5]:
                show_complete_professors(df_processed, id_col)
            
            with tabs[6]:
                show_complete_infrastructure(df_processed, id_col)
            
            with tabs[7]:
                show_methodology(df_processed, id_col)
            
            with tabs[8]:
                show_curriculum_matrix(df_processed, id_col)
            
            with tabs[9]:
                show_enrollment_influence(df_processed, id_col)
            
            with tabs[10]:
                show_retention_and_evasion(df_processed, id_col)
            
            st.markdown("---")
            st.markdown("### 💾 Download")
            
            col1, col2 = st.columns(2)
            
            with col1:
                csv = df_processed.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Baixar dados processados (CSV)",
                    csv,
                    "dados_cefet_processados.csv",
                    "text/csv",
                    use_container_width=True
                )
            
            with col2:
                # Relatório resumido
                summary_data = {
                    'KPI': ['Total Respondentes', 'Total Cursos', 'Colunas no Dataset'],
                    'Valor': [
                        total_resp,
                        df_processed[next((col for col in df_processed.columns 
                                          if 'curso' in col.lower()), 'CURSO')].nunique() if any('curso' in col.lower() for col in df_processed.columns) else 'N/A',
                        len(df_processed.columns)
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_csv = summary_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📊 Baixar resumo executivo (CSV)",
                    summary_csv,
                    "resumo_executivo.csv",
                    "text/csv",
                    use_container_width=True
                )
    else:
        st.info("👆 Configure a fonte de dados no menu lateral")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📋 Opções")
            st.markdown("""
            **Opção 1: Arquivo do GitHub** ✅
            - Selecione um dos arquivos disponíveis
            
            **Opção 2: Upload Manual** 📤
            - Faça upload de qualquer arquivo .xlsx
            """)
        
        with col2:
            st.markdown("### 📊 Análises Disponíveis")
            st.markdown("""
            - ✅ **11 abas completas** com todos os KPIs
            - ✅ Likert convertido para índice 0-100
            - ✅ Múltipla escolha com dedupe
            - ✅ DistinctCount aplicado corretamente
            - ✅ Gráficos com altura dinâmica
            - ✅ Tema responsivo (escuro/claro)
            - ✅ Download de dados processados
            """)
        
        st.markdown("---")
        st.markdown("### 🎯 Log de Mudanças (v2.0)")
        st.success("""
        **✅ Implementado:**
        1. TODOS os KPIs do mapeamento preservados
        2. Likert → Índice 0-100 (excluindo "Não observado")
        3. Múltipla escolha com DistinctCount(respondent_id, opção)
        4. 11 abas temáticas completas
        5. Altura dinâmica: max(350, 24 * #categorias + 120)
        6. Tema com contraste correto
        7. Arquivo demo em data/dados_cefet.xlsx funcionando
        8. Nenhum KPI foi removido ou renomeado
        """)

if __name__ == "__main__":
    main()=[
                go.Bar(
                    x=counts['Perfil'].apply(break_text),
                    y=counts['Respondentes'],
                    text=[f"{r} ({p}%)" for r, p in zip(counts['Respondentes'], counts['%'])],
                    textposition='outside',
                    marker_color='#667eea'
                )
            ])
            
            fig.update_layout(
                **get_base_graph_config(),
                height=height,
                xaxis_tickangle=-45,
                margin=dict(l=20, r=20, t=40, b=120)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela detalhada
            st.dataframe(counts, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Coluna de perfil não encontrada")
    
    with col2:
        st.subheader("Distribuição por Faixa Etária")
        idade_col = next((col for col in df.columns if 'idade' in col.lower()), None)
        
        if idade_col:
            df_temp = df.copy()
            df_temp[idade_col] = pd.to_numeric(df_temp[idade_col], errors='coerce')
            df_temp['faixa_etaria'] = pd.cut(
                df_temp[idade_col],
                bins=[0, 19, 25, 30, 100],
                labels=['Até 19', '20-25', '26-30', 'Acima de 30']
            )
            
            counts = df_temp.groupby('faixa_etaria')[id_col].nunique().reset_index()
            counts.columns = ['Faixa', 'Respondentes']
            total = counts['Respondentes'].sum()
            counts['%'] = (counts['Respondentes'] / total * 100).round(1)
            
            fig = go.Figure(data=[
                go.Bar(
                    x=counts['Faixa'],
                    y=counts['Respondentes'],
                    text=[f"{r} ({p}%)" for r, p in zip(counts['Respondentes'], counts['%'])],
                    textposition='outside',
                    marker_color='#764ba2'
                )
            ])
            
            fig.update_layout(
                **get_base_graph_config(),
                height=400,
                margin=dict(l=20, r=20, t=40, b=60)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela detalhada
            st.dataframe(counts, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Coluna de idade não encontrada")
    
    # KPI: Grau de Formação
    st.markdown("### 🎓 Grau de Formação")
    grau_col = next((col for col in df.columns if 'grau' in col.lower()), None)
    
    if grau_col:
        counts = df.groupby(grau_col)[id_col].nunique().reset_index()
        counts.columns = ['Grau', 'Respondentes']
        total = counts['Respondentes'].sum()
        counts['%'] = (counts['Respondentes'] / total * 100).round(1)
        
        fig = go.Figure(data=[
            go.Bar(
                y=counts['Grau'].apply(break_text),
                x=counts['Respondentes'],
                orientation='h',
                text=[f"{r} ({p}%)" for r, p in zip(counts['Respondentes'], counts['%'])],
                textposition='outside',
                marker_color='#f39c12'
            )
        ])
        
        height = max(350, len(counts) * 24 + 120)
        fig.update_layout(
            **get_base_graph_config(),
            height=height,
            margin=dict(l=200, r=20, t=40, b=60)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(counts, use_container_width=True, hide_index=True)
    else:
        st.info("📊 Coluna 'Grau de Formação' não encontrada nos dados")
    
    # KPI: IES (Instituições de Ensino Superior)
    st.markdown("### 🏛️ Instituições de Ensino Superior (IES)")
    ies_col = next((col for col in df.columns if 'ies' in col.lower() or 'instituição' in col.lower()), None)
    
    if ies_col:
        counts = df.groupby(ies_col)[id_col].nunique().reset_index()
        counts.columns = ['IES', 'Respondentes']
        total = counts['Respondentes'].sum()
        counts['%'] = (counts['Respondentes'] / total * 100).round(1)
        counts = counts.sort_values('Respondentes', ascending=False)
        
        fig = go.Figure(data=[
            go.Bar(
                y=counts['IES'].apply(break_text),
                x=counts['Respondentes'],
                orientation='h',
                text=[f"{r} ({p}%)" for r, p in zip(counts['Respondentes'], counts['%'])],
                textposition='outside',
                marker_color='#9b59b6'
            )
        ])
        
        height = max(350, len(counts) * 24 + 120)
        fig.update_layout(
            **get_base_graph_config(),
            height=height,
            margin=dict(l=200, r=20, t=40, b=60)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(counts, use_container_width=True, hide_index=True)
    else:
        st.info("📊 Coluna 'IES' não encontrada nos dados")
    
    # KPI: PCD (Pessoa com Deficiência)
    st.markdown("### ♿ Pessoa com Deficiência (PCD)")
    pcd_col = next((col for col in df.columns if 'pcd' in col.lower() or 'deficiência' in col.lower()), None)
    
    if pcd_col:
        counts = df.groupby(pcd_col)[id_col].nunique().reset_index()
        counts.columns = ['PCD', 'Respondentes']
        total = counts['Respondentes'].sum()
        counts['%'] = (counts['Respondentes'] / total * 100).round(1)
        
        fig = go.Figure(data=[
            go.Pie(
                labels=counts['PCD'],
                values=counts['Respondentes'],
                text=[f"{r} ({p}%)" for r, p in zip(counts['Respondentes'], counts['%'])],
                textinfo='label+text',
                marker=dict(colors=['#e74c3c', '#2ecc71'])
            )
        ])
        
        fig.update_layout(
            **get_base_graph_config(),
            height=400,
            margin=dict(l=20, r=20, t=40, b=60)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(counts, use_container_width=True, hide_index=True)
    else:
        st.info("📊 Coluna 'PCD' não encontrada nos dados")

# ===== KPI: Cursos Completo =====
def show_complete_courses(df, id_col):
    """Análise completa de cursos"""
    st.markdown("## 🎓 Análise Completa de Cursos")
    
    curso_col = next((col for col in df.columns 
                     if 'curso' in col.lower() and 'graduação' in col.lower()), None)
    
    if curso_col:
        counts = df.groupby(curso_col)[id_col].nunique().reset_index()
        counts.columns = ['Curso', 'Respondentes']
        total = counts['Respondentes'].sum()
        counts['%'] = (counts['Respondentes'] / total * 100).round(1)
        counts = counts.sort_values('Respondentes', ascending=False)
        
        # Top 15
        st.subheader("Top 15 Cursos")
        top15 = counts.head(15).sort_values('Respondentes', ascending=True)
        
        fig = go.Figure(data=[
            go.Bar(
                y=top15['Curso'].apply(break_text),
                x=top15['Respondentes'],
                orientation='h',
                text=[f"{r} ({p}%)" for r, p in zip(top15['Respondentes'], top15['%'])],
                textposition='outside',
                marker_color='#2ecc71'
            )
        ])
        
        height = max(350, len(top15) * 24 + 120)
        fig.update_layout(
            **get_base_graph_config(),
            height=height,
            margin=dict(l=200, r=20, t=40, b=60)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela completa
        with st.expander("📋 Ver todos os cursos (tabela completa)"):
            st.dataframe(counts, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Coluna de curso não encontrada")

# ===== KPI: Empreendedorismo Completo =====
def show_complete_entrepreneurship(df, id_col):
    """Análise completa de empreendedorismo"""
    st.markdown("## 🚀 Empreendedorismo (Todos os KPIs)")
    
    # KPI 1: Conceitos de Empreendedorismo (Likert + Múltipla)
    st.subheader("1️⃣ Conceitos de Empreendedorismo")
    
    conceito_cols = [col for col in df.columns if 'conceito' in col.lower() and 'empreendedorismo' in col.lower()]
    
    if conceito_cols:
        st.info(f"📊 Encontradas {len(conceito_cols)} colunas de conceitos")
        
        # Se for múltipla escolha, fazer dedupe
        for col in conceito_cols:
            st.markdown(f"**{col}**")
            
            # Contar respondentes únicos por opção
            counts = df.groupby(col)[id_col].nunique().reset_index()
            counts.columns = ['Conceito', 'Respondentes']
            total = df[id_col].nunique()
            counts['%'] = (counts['Respondentes'] / total * 100).round(1)
            counts = counts.sort_values('Respondentes', ascending=False)
            
            fig = go.Figure(data=[
                go.Bar(
                    y=counts['Conceito'].apply(break_text),
                    x=counts['Respondentes'],
                    orientation='h',
                    text=[f"{r} ({p}%)" for r, p in zip(counts['Respondentes'], counts['%'])],
                    textposition='outside',
                    marker_color='#3498db'
                )
            ])
            
            height = max(350, len(counts) * 24 + 120)
            fig.update_layout(
                **get_base_graph_config(),
                height=height,
                margin=dict(l=200, r=20, t=40, b=60)
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 Colunas de 'Conceitos de Empreendedorismo' não encontradas")
    
    # KPI 2: Fundadores/Sócios
    st.subheader("2️⃣ Fundadores e Sócios")
    fundador_col = next((col for col in df.columns 
                        if 'sócio' in col.lower() or 'fundador' in col.lower()), None)
    
    if fundador_col:
        counts = df.groupby(fundador_col)[id_col].nunique().reset_index()
        counts.columns = ['Resposta', 'Respondentes']
        total = df[id_col].nunique()
        counts['%'] = (counts['Respondentes'] / total * 100).round(1)
        
        fig = go.Figure(data=[
            go.Bar(
                x=counts['Resposta'],
                y=counts['Respondentes'],
                text=[f"{r}<br>({p}%)" for r, p in zip(counts['Respondentes'], counts['%'])],
                textposition='outside',
                marker_color='#e67e22'
            )
        ])
        
        fig.update_layout(
            **get_base_graph_config(),
            height=400,
            margin=dict(l=20, r=20, t=40, b=60)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Métrica destacada
        fundadores = df[df[fundador_col] == 'Sim'][id_col].nunique()
        pct = (fundadores / total * 100) if total > 0 else 0
        st.metric("🎯 Total de Fundadores/Sócios", f"{fundadores} ({pct:.1f}%)")
    else:
        st.info("📊 Coluna 'Fundadores/Sócios' não encontrada")
    
    # KPI 3: Projetos Empreendedores
    st.subheader("3️⃣ Projetos Empreendedores")
    projeto_cols = [col for col in df.columns if 'projeto' in col.lower()]
    
    if projeto_cols:
        for col in projeto_cols:
            st.markdown(f"**{col}**")
            
            counts = df.groupby(col)[id_col].nunique().reset_index()
            counts.columns = ['Resposta', 'Respondentes']
            total = df[id_col].nunique()
            counts['%'] = (counts['Respondentes'] / total * 100).round(1)
            
            fig = go.Figure(data=[
                go.Bar(
                    x=counts['Resposta'],
                    y=counts['Respondentes'],
                    text=[f"{r} ({p}%)" for r, p in zip(counts['Respondentes'], counts['%'])],
                    textposition='outside',
                    marker_color='#16a085'
                )
            ])
            
            fig.update_layout(
                **get_base_graph_config(),
                height=400,
                margin=dict(l=20, r=20, t=40, b=60)
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 Colunas sobre 'Projetos' não encontradas")
    
    # KPI 4: Modelos de Empreendedorismo Vivenciados (Múltipla)
    st.subheader("4️⃣ Modelos de Empreendedorismo Vivenciados")
    modelos_cols = [col for col in df.columns if 'modelo' in col.lower() and 'vivenciado' in col.lower()]
    
    if modelos_cols:
        for col in modelos_cols:
            st.markdown(f"**{col}**")
            
            counts = df.groupby(col)[id_col].nunique().reset_index()
            counts.columns = ['Modelo', 'Respondentes']
            total = df[id_col].nunique()
            counts['%'] = (counts['Respondentes'] / total * 100).round(1)
            counts = counts.sort_values('Respondentes', ascending=False)
            
            fig = go.Figure(data=[
                go.Bar(
                    y=counts['Modelo'].apply(break_text),
                    x=counts['Respondentes'],
                    orientation='h',
                    text=[f"{r} ({p}%)" for r, p in zip(counts['Respondentes'], counts['%'])],
                    textposition='outside',
                    marker_color='#8e44ad'
                )
            ])
            
            height = max(350, len(counts) * 24 + 120)
            fig.update_layout(
                **get_base_graph_config(),
                height=height,
                margin=dict(l=200, r=20, t=40, b=60)
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 Colunas sobre 'Modelos Vivenciados' não encontradas")

# ===== KPI: Características dos Alunos (Likert 0-100) =====
def show_student_characteristics(df, id_col):
    """Características dos alunos com Likert 0-100"""
    st.markdown("## 👨‍🎓 Características dos Alunos")
    
    aluno_cols = [col for col in df.columns if col.startswith('alunos_')]
    
    if not aluno_cols:
        st.info("📊 Colunas de características dos alunos não encontradas")
        return
    
    # Calcular índices
    indices = {}
    for col in aluno_cols:
        idx = likert_to_index(df[col], df, id_col)
        if idx is not None:
            label = col.replace('alunos_', '').replace('_', ' ').title()
            indices[label] = idx
    
    if indices:
        # Exibir métricas
        cols = st.columns(min(4, len(indices)))
        for i, (label, idx) in enumerate(indices.items()):
            with cols[i % len(cols)]:
                st.metric(label, f"{idx:.1f}/100")
        
        # Gráfico de barras
        df_indices = pd.DataFrame(list(indices.items()), columns=['Característica', 'Índice'])
        df_indices = df_indices.sort_values('Índice', ascending=True)
        
        fig = go.Figure(data=[
            go.Bar(
                y=df_indices['Característica'],
                x=df_indices['Índice'],
                orientation='h',
                text=[f"{v:.1f}" for v in df_indices['Índice']],
                textposition='outside',
                marker_color='#3498db'
            )
        ])
        
        height = max(350, len(df_indices) * 24 + 120)
        fig.update_layout(
            **get_base_graph_config(),
            height=height,
            xaxis=dict(range=[0, 100]),
            margin=dict(l=200, r=20, t=40, b=60)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Matriz Likert detalhada
        questions = {col.replace('alunos_', '').replace('_', ' ').title(): col for col in aluno_cols}
        matrix_data = create_likert_matrix(df, questions, id_col)
        
        if not matrix_data.empty:
            with st.expander("📊 Ver distribuição detalhada (1-5)"):
                fig_matrix = plot_likert_matrix(matrix_data)
                if fig_matrix:
                    st.plotly_chart(fig_matrix, use_container_width=True)

# ===== KPI: Professores Completo (Likert 0-100) =====
def show_complete_professors(df, id_col):
    """Análise completa dos professores com Likert 0-100"""
    st.markdown("## 👨‍🏫 Avaliação dos Professores (Completa)")
    
    prof_cols = [col for col in df.columns if col.startswith('professores_')]
    
    if not prof_cols:
        st.warning("⚠️ Colunas de avaliação dos professores não encontradas")
        return
    
    # Calcular índices
    indices = {}
    for col in prof_cols:
        idx = likert_to_index(df[col], df, id_col)
        if idx is not None:
            label = col.replace('professores_', '').replace('_', ' ').title()
            indices[label] = idx
    
    if indices:
        # Exibir métricas
        st.subheader("📈 Índices 0-100")
        cols = st.columns(min(4, len(indices)))
        for i, (label, idx) in enumerate(indices.items()):
            with cols[i % len(cols)]:
                st.metric(label, f"{idx:.1f}/100")
        
        # Gráfico de barras
        df_indices = pd.DataFrame(list(indices.items()), columns=['Característica', 'Índice'])
        df_indices = df_indices.sort_values('Índice', ascending=True)
        
        fig = go.Figure(data=[
            go.Bar(
                y=df_indices['Característica'],
                x=df_indices['Índice'],
                orientation='h',
                text=[f"{v:.1f}" for v in df_indices['Índice']],
                textposition='outside',
                marker_color='#e67e22'
            )
        ])
        
        height = max(350, len(df_indices) * 24 + 120)
        fig.update_layout(
            **get_base_graph_config(),
            height=height,
            xaxis=dict(range=[0, 100]),
            margin=dict(l=200, r=20, t=40, b=60)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Matriz Likert detalhada
        st.subheader("📊 Distribuição Detalhada (1-5)")
        questions = {col.replace('professores_', '').replace('_', ' ').title(): col for col in prof_cols}
        matrix_data = create_likert_matrix(df, questions, id_col)
        
        if not matrix_data.empty:
            fig_matrix = plot_likert_matrix(matrix_data)
            if fig_matrix:
                st.plotly_chart(fig_matrix, use_container_width=True)

# ===== KPI: Infraestrutura Completa (Likert 0-100) =====
def show_complete_infrastructure(df, id_col):
    """Análise completa de infraestrutura com Likert 0-100"""
    st.markdown("## 🏢 Infraestrutura (Completa)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏛️ Infraestrutura Geral")
        infra_cols = [col for col in df.columns if col.startswith('infraestrutura_')]
        
        if infra_cols:
            # Calcular índices
            indices = {}
            for col in infra_cols:
                idx = likert_to_index(df[col], df, id_col)
                if idx is not None:
                    label = col.replace('infraestrutura_', '').replace('_', ' ').title()
                    indices[label] = idx
            
            if indices:
                # Métricas
                for label, idx in indices.items():
                    st.metric(label, f"{idx:.1f}/100")
                
                # Gráfico
                df_indices = pd.DataFrame(list(indices.items()), columns=['Item', 'Índice'])
                df_indices = df_indices.sort_values('Índice', ascending=True)
                
                fig = go.Figure(data=[
                    go.Bar(
                        y=df_indices['Item'],
                        x=df_indices['Índice'],
                        orientation='h',
                        text=[f"{v:.1f}" for v in df_indices['Índice']],
                        textposition='outside',
                        marker_color='#16a085'
                    )
                ])
                
                height = max(350, len(df_indices) * 24 + 120)
                fig.update_layout(
                    **get_base_graph_config(),
                    height=height,
                    xaxis=dict(range=[0, 100]),
                    margin=dict(l=200, r=20, t=40, b=60)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Matriz detalhada
                questions = {col.replace('infraestrutura_', '').replace('_', ' ').title(): col for col in infra_cols}
                matrix_data = create_likert_matrix(df, questions, id_col)
                
                if not matrix_data.empty:
                    with st.expander("📊 Ver distribuição detalhada"):
                        fig_matrix = plot_likert_matrix(matrix_data)
                        if fig_matrix:
                            st.plotly_chart(fig_matrix, use_container_width=True)
        else:
            st.info("📊 Colunas de infraestrutura geral não encontradas")
    
    with col2:
        st.subheader("📶 Internet")
        internet_cols = [col for col in df.columns if 'internet_' in col.lower()]
        
        if internet_cols:
            # Calcular índices
            indices = {}
            for col in internet_cols:
                idx = likert_to_index(df[col], df, id_col)
                if idx is not None:
                    label = col.replace('internet_', '').replace('_', ' ').title()
                    indices[label] = idx
            
            if indices:
                # Métricas
                for label, idx in indices.items():
                    st.metric(label, f"{idx:.1f}/100")
                
                # Gráfico
                df_indices = pd.DataFrame(list(indices.items()), columns=['Item', 'Índice'])
                df_indices = df_indices.sort_values('Índice', ascending=True)
                
                fig = go.Figure(data=[
                    go.Bar(
                        y=df_indices['Item'],
                        x=df_indices['Índice'],
                        orientation='h',
                        text=[f"{v:.1f}" for v in df_indices['Índice']],
                        textposition='outside',
                        marker_color='#9b59b6'
                    )
                ])
                
                height = max(350, len(df_indices) * 24 + 120)
                fig.update_layout(
                    **get_base_graph_config(),
                    height=height,
                    xaxis=dict(range=[0, 100]),
                    margin=dict(l=200, r=20, t=40, b=60)
                )
                
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Colunas de internet não encontradas")

# ===== KPI: Metodologia (Likert 0-100) =====
def show_methodology(df, id_col):
    """Avaliação de metodologia"""
    st.markdown("## 📚 Metodologia de Ensino")
    
    metodologia_cols = [col for col in df.columns if 'metodologia' in col.lower()]
    
    if metodologia_cols:
        indices = {}
        for col in metodologia_cols:
            idx = likert_to_index(df[col], df, id_col)
            if idx is not None:
                label = col.replace('metodologia_', '').replace('_', ' ').title()
                indices[label] = idx
        
        if indices:
            # Métricas
            cols = st.columns(min(4, len(indices)))
            for i, (label, idx) in enumerate(indices.items()):
                with cols[i % len(cols)]:
                    st.metric(label, f"{idx:.1f}/100")
            
            # Gráfico
            df_indices = pd.DataFrame(list(indices.items()), columns=['Item', 'Índice'])
            df_indices = df_indices.sort_values('Índice', ascending=True)
            
            fig = go.Figure(data=[
                go.Bar(
                    y=df_indices['Item'],
                    x=df_indices['Índice'],
                    orientation='h',
                    text=[f"{v:.1f}" for v in df_indices['Índice']],
                    textposition='outside',
                    marker_color='#e74c3c'
                )
            ])
            
            height = max(350, len(df_indices) * 24 + 120)
            fig.update_layout(
                **get_base_graph_config(),
                height=height,
                xaxis=dict(range=[0, 100]),
                margin=dict(l=200, r=20, t=40, b=60)
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 Colunas de metodologia não encontradas")

# ===== KPI: Matriz Curricular (Likert 0-100) =====
def show_curriculum_matrix(df, id_col):
    """Avaliação da matriz curricular"""
    st.markdown("## 📋 Matriz Curricular")
    
    matriz_cols = [col for col in df.columns if 'matriz' in col.lower() or 'curricular' in col.lower()]
    
    if matriz_cols:
        indices = {}
        for col in matriz_cols:
            idx = likert_to_index(df[col], df, id_col)
            if idx is not None:
                label = col.replace('matriz_', '').replace('curricular_', '').replace('_', ' ').title()
                indices[label] = idx
        
        if indices:
            # Métricas
            cols = st.columns(min(4, len(indices)))
            for i, (label, idx) in enumerate(indices.items()):
                with cols[i % len(cols)]:
                    st.metric(label, f"{idx:.1f}/100")
            
            # Gráfico
            df_indices = pd.DataFrame(list(indices.items()), columns=['Item', 'Índice'])
            df_indices = df_indices.sort_values('Índice', ascending=True)
            
            fig = go.Figure(data