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
    
    # Tenta encontrar por nome exato
    for candidate in ID_CANDIDATES:
        if normalize_text(candidate) in cols_norm:
            return cols_norm[normalize_text(candidate)]
    
    # Busca heurística
    for key in ["respondent", "respondente", "id"]:
        for norm_name, orig_name in cols_norm.items():
            if key in norm_name and ("respondent" in norm_name or "respondente" in norm_name):
                return orig_name
    
    raise ValueError("Coluna de ID do respondente não detectada")

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
        
        # Conta respondentes únicos por resposta
        valid_responses = df[~df[col].isin(LIKERT_NEUTROS)].copy()
        counts = valid_responses.groupby(col)[id_col].nunique().reindex(LIKERT_ORDER).fillna(0)
        total = valid_responses[id_col].nunique()
        
        if total > 0:  # Só inclui se houver respostas válidas
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
    
    fig.update_layout(
        **get_base_graph_config(),
        height=max(400, len(matrix_data.index) * 40),
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
    
    # Calcula posições para labels
    cumsum = 0
    positions = []
    for pct in df_question['Percentual']:
        positions.append(cumsum + pct/2)
        cumsum += pct
    
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

# ===== Funções de Análise =====
def show_kpis(df, id_col):
    """Mostra KPIs principais"""
    st.markdown("## 📊 Visão Geral")
    
    cols = st.columns(2)
    
    with cols[0]:
        total_respondentes = df[id_col].nunique()
        st.metric("📝 Total de Respondentes", f"{total_respondentes:,}")
    
    with cols[1]:
        idade_col = next((col for col in ['idade', 'IDADE'] 
                         if col in df.columns), None)
        if idade_col:
            valid_ages = pd.to_numeric(df[idade_col], errors='coerce')
            media_idade = valid_ages.mean()
            if not pd.isna(media_idade):
                st.metric("👤 Idade Média", f"{media_idade:.1f} anos")
            else:
                st.metric("👤 Idade Média", "N/A")
        else:
            st.metric("👤 Idade Média", "N/A")

def show_profile_analysis(df, id_col):
    """Análise de perfil dos respondentes"""
    st.markdown("## 👥 Perfil dos Respondentes")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Distribuição por Perfil")
        perfil_col = next((col for col in ['voce_e', 'VOCE É'] 
                          if col in df.columns), None)
        if perfil_col:
            counts = df.groupby(perfil_col)[id_col].nunique().reset_index()
            counts.columns = ['Perfil', 'Respondentes']
            
            fig = go.Figure(data=[
                go.Bar(
                    x=counts['Perfil'].apply(break_text),
                    y=counts['Respondentes'],
                    text=counts['Respondentes'],
                    textposition='outside',
                    marker_color='#667eea'
                )
            ])
            
            fig.update_layout(
                **get_base_graph_config(),
                height=400,
                xaxis_tickangle=-45,
                margin=dict(l=20, r=20, t=40, b=120)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Coluna de perfil não encontrada")
    
    with col2:
        st.subheader("Distribuição por Idade")
        idade_col = next((col for col in ['idade', 'IDADE'] 
                         if col in df.columns), None)
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
            
            fig = go.Figure(data=[
                go.Bar(
                    x=counts['Faixa'],
                    y=counts['Respondentes'],
                    text=counts['Respondentes'],
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
        else:
            st.warning("⚠️ Coluna de idade não encontrada")

def show_courses_analysis(df, id_col):
    """Análise de cursos"""
    st.markdown("## 🎓 Análise de Cursos")
    
    curso_col = next((col for col in ['curso_graduacao', 'CURSO DE GRADUAÇÃO OF', 'curso'] 
                     if col in df.columns), None)
    if curso_col:
        counts = df.groupby(curso_col)[id_col].nunique().reset_index()
        counts.columns = ['Curso', 'Respondentes']
        counts = counts.sort_values('Respondentes', ascending=True).tail(15)
        
        fig = go.Figure(data=[
            go.Bar(
                y=counts['Curso'].apply(break_text),
                x=counts['Respondentes'],
                orientation='h',
                text=counts['Respondentes'],
                textposition='outside',
                marker_color='#2ecc71'
            )
        ])
        
        fig.update_layout(
            **get_base_graph_config(),
            height=max(400, len(counts) * 30),
            margin=dict(l=200, r=20, t=40, b=60)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Ver todos os cursos"):
            all_courses = df.groupby(curso_col)[id_col].nunique().reset_index()
            all_courses.columns = ['Curso', 'Respondentes']
            all_courses['%'] = (all_courses['Respondentes'] / 
                              df[id_col].nunique() * 100).round(2)
            st.dataframe(
                all_courses.sort_values('Respondentes', ascending=False),
                use_container_width=True
            )
    else:
        st.warning("⚠️ Coluna de curso não encontrada")

def show_entrepreneurship_analysis(df, id_col):
    """Análise de empreendedorismo"""
    st.markdown("## 🚀 Empreendedorismo")
    
    # Conceitos de Empreendedorismo (Likert)
    concept_questions = {
        'Negócio Próprio': 'emp_negocio',
        'Impacto Social': 'emp_social',
        'Inovação': 'emp_inovacao',
        'Sustentabilidade': 'emp_sustent'
    }
    
    matrix_data = create_likert_matrix(df, concept_questions, id_col)
    if not matrix_data.empty:
        st.subheader("Conceitos de Empreendedorismo")
        fig_matrix = plot_likert_matrix(matrix_data)
        if fig_matrix:
            st.plotly_chart(fig_matrix, use_container_width=True)
            
            st.markdown("### Detalhamento por Conceito")
            for question in concept_questions.keys():
                fig_bars = plot_likert_bars(matrix_data, question)
                if fig_bars:
                    st.plotly_chart(fig_bars, use_container_width=True)
    
    # Fundadores/Sócios
    st.subheader("Fundadores/Sócios")
    fundador_col = next((col for col in [
        'socio_ou_fundador',
        'Você é sócio(a) ou fundador(a) de alguma empresa?Response'
    ] if col in df.columns), None)
    
    if fundador_col:
        counts = df.groupby(fundador_col)[id_col].nunique().reset_index()
        counts.columns = ['Resposta', 'Respondentes']
        
        fig = go.Figure(data=[
            go.Bar(
                y=counts['Resposta'].apply(break_text),
                x=counts['Respondentes'],
                orientation='h',
                text=counts['Respondentes'],
                textposition='outside',
                marker_color='#3498db'
            )
        ])
        
        fig.update_layout(
            **get_base_graph_config(),
            height=200,
            margin=dict(l=200, r=20, t=20, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        total_resp = df[id_col].nunique()
        total_fund = df[df[fundador_col] == 'Sim'][id_col].nunique()
        pct = (total_fund / total_resp * 100)
        st.metric("Percentual de Fundadores", f"{pct:.1f}%")
    else:
        st.warning("⚠️ Dados sobre fundadores não encontrados")

def show_professors_analysis(df, id_col):
    """Análise dos professores"""
    st.markdown("## 👨‍🏫 Avaliação dos Professores")
    
    professor_questions = {
        'Inconformismo': 'prof_inconformismo',
        'Visão para Oportunidades': 'prof_visao',
        'Pensamento Inovador': 'prof_inovacao',
        'Coragem para Riscos': 'prof_coragem',
        'Curiosidade': 'prof_curiosidade',
        'Comunicação': 'prof_comunicacao',
        'Planejamento': 'prof_planejamento',
        'Apoio a Iniciativas': 'prof_apoio'
    }
    
    matrix_data = create_likert_matrix(df, professor_questions, id_col)
    if not matrix_data.empty:
        fig_matrix = plot_likert_matrix(matrix_data)
        if fig_matrix:
            st.plotly_chart(fig_matrix, use_container_width=True)
            
            st.markdown("### Detalhamento por Característica")
            for question in professor_questions.keys():
                fig_bars = plot_likert_bars(matrix_data, question)
                if fig_bars:
                    st.plotly_chart(fig_bars, use_container_width=True)
    else:
        st.warning("⚠️ Dados de avaliação dos professores não encontrados")

def show_infrastructure_analysis(df, id_col):
    """Análise de infraestrutura"""
    st.markdown("## 🏢 Infraestrutura")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Infraestrutura Geral")
        infra_questions = {
            'Biblioteca': 'infra_biblioteca',
            'Labs. Informática': 'infra_labs_info',
            'Labs. Pesquisa': 'infra_labs_pesq',
            'Espaços Convivência': 'infra_espacos',
            'Restaurante': 'infra_restaurante'
        }
        
        matrix_data = create_likert_matrix(df, infra_questions, id_col)
        if not matrix_data.empty:
            fig = plot_likert_matrix(matrix_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Dados de infraestrutura não encontrados")
    
    with col2:
        st.subheader("Acessibilidade (PCD)")
        access_questions = {
            'Calçadas': 'access_calcadas',
            'Vias de Acesso': 'access_vias',
            'Rotas Internas': 'access_rotas',
            'Sanitários': 'access_sanitarios',
            'Elevadores/Rampas': 'access_elevadores'
        }
        
        matrix_data = create_likert_matrix(df, access_questions, id_col)
        if not matrix_data.empty:
            fig = plot_likert_matrix(matrix_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Dados de acessibilidade não encontrados")

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
    
    /* Melhorias de acessibilidade */
    .tooltip {
        font-size: 1rem;
        color: white;
    }
    
    /* Ajustes de contraste */
    .st-bw {
        color: white !important;
    }
    
    /* Espaçamento vertical */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# ===== Main =====
def main():
    # Header
    st.markdown('<h1 class="main-header">📊 Dashboard CEFET-MG</h1>', unsafe_allow_html=True)
    st.markdown("### Pesquisa sobre Empreendedorismo e Educação Superior")
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
        st.info("Dashboard MVP v1.0 - CEFET/MG")
        
        # Data e hora atual
        st.markdown(f"**Última atualização:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        st.markdown(f"**Usuário:** {st.session_state.get('github_user', 'Visitante')}")
    
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
            st.success(f"✅ {df_processed[id_col].nunique():,} respondentes únicos carregados!")
            
            tabs = st.tabs([
                "📊 Geral",
                "👥 Perfil",
                "🎓 Cursos",
                "🚀 Empreendedorismo",
                "👨‍🏫 Professores",
                "🏢 Infraestrutura"
            ])
            
            with tabs[0]:
                show_kpis(df_processed, id_col)
                with st.expander("🔍 Ver dados brutos (100 primeiras linhas)"):
                    st.dataframe(df_processed.head(100), use_container_width=True)
            
            with tabs[1]:
                show_profile_analysis(df_processed, id_col)
            
            with tabs[2]:
                show_courses_analysis(df_processed, id_col)
            
            with tabs[3]:
                show_entrepreneurship_analysis(df_processed, id_col)
            
            with tabs[4]:
                show_professors_analysis(df_processed, id_col)
            
            with tabs[5]:
                show_infrastructure_analysis(df_processed, id_col)
            
            st.markdown("---")
            st.markdown("### 💾 Download")
            csv = df_processed.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Baixar dados processados (CSV)",
                csv,
                "dados_cefet_processados.csv",
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
            - ✅ Perfil dos respondentes
            - ✅ Cursos e distribuições
            - ✅ Empreendedorismo
            - ✅ Avaliação de professores
            - ✅ Infraestrutura e acessibilidade
            """)

if __name__ == "__main__":
    main()
