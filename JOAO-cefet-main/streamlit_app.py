import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import io
import requests

# ===== Configuração =====
st.set_page_config(
    page_title="Dashboard CEFET-MG",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== Links Raw do GitHub =====
REPO_DEFAULT_RAW = "https://raw.githubusercontent.com/Totishuro/JOAO-cefet/main/JOAO-cefet-main/data/dados_cefet.xlsx"
CEFET_COPIA_RAW = "https://raw.githubusercontent.com/Totishuro/JOAO-cefet/main/JOAO-cefet-main/Dados%20CEFET_MG%20Sem%20dados%20pessoais%202%20Copia.xlsx"
ALT_DEFAULT_RAW = "https://raw.githubusercontent.com/Totishuro/JOAO-cefet/main/data/dados_cefet.xlsx"

# ===== CSS para responsividade e tema =====
def get_theme_colors():
    """Obtém cores do tema atual do Streamlit"""
    bg = st.get_option("theme.backgroundColor") or "#0E1117"
    txt = st.get_option("theme.textColor") or "#FAFAFA"
    primary = st.get_option("theme.primaryColor") or "#FF6B6B"
    secondary = st.get_option("theme.secondaryBackgroundColor") or "#262730"
    return bg, txt, primary, secondary

def apply_custom_css():
    """Aplica CSS customizado baseado no tema"""
    bg, txt, primary, secondary = get_theme_colors()
    
    st.markdown(f"""
    <style>
        .main-header {{
            font-size: 1.5rem;
            color: {primary};
            text-align: center;
            margin-bottom: 1rem;
        }}
        
        @media (min-width: 768px) {{
            .main-header {{
                font-size: 2.5rem;
            }}
        }}
        
        .stButton>button {{
            width: 100%;
        }}
        
        .metric-card {{
            background-color: {secondary};
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid {primary};
        }}
        
        /* Ajustar fundo dos gráficos */
        .js-plotly-plot {{
            background-color: {bg} !important;
        }}
    </style>
    """, unsafe_allow_html=True)

# ===== Funções de Carregamento =====
def read_excel_github(raw_url):
    """Carrega arquivo Excel diretamente do GitHub via URL raw"""
    try:
        response = requests.get(raw_url)
        response.raise_for_status()
        return pd.read_excel(io.BytesIO(response.content), engine='openpyxl')
    except Exception as e:
        st.error(f"❌ Erro ao baixar arquivo do GitHub: {str(e)}")
        return None

@st.cache_data(show_spinner=False)
def load_excel(file_or_url):
    """Carrega arquivo Excel (local ou URL)"""
    try:
        if isinstance(file_or_url, str) and file_or_url.startswith("http"):
            return read_excel_github(file_or_url)
        else:
            return pd.read_excel(file_or_url, engine='openpyxl')
    except Exception as e:
        st.error(f"❌ Erro ao ler arquivo: {str(e)}")
        return None

# ===== Funções de Processamento com Contagem Distinta =====
def process_data(df):
    """Processa dados mantendo respostas múltiplas válidas"""
    if df is None:
        return None, None
        
    if 'respondent_id' not in df.columns:
        st.error("❌ Coluna 'respondent_id' não encontrada!")
        st.info(f"Colunas disponíveis: {', '.join(df.columns[:10])}...")
        return None, None
    
    total_respostas = len(df)
    total_respondentes_unicos = df['respondent_id'].nunique()
    
    stats = {
        'total_linhas': total_respostas,
        'total_unicos': total_respondentes_unicos,
        'respostas_multiplas': total_respostas - total_respondentes_unicos
    }
    
    return df, stats

def get_distinct_counts(df, column_name, respondent_col='respondent_id'):
    """Retorna contagem distinta de respondentes por categoria"""
    if column_name not in df.columns:
        return {}
    
    # Remove NaN e duplicatas de respondent_id por categoria
    temp_df = df[[respondent_col, column_name]].dropna()
    temp_df = temp_df.drop_duplicates(subset=[respondent_col, column_name])
    
    # Conta respondentes únicos por categoria
    counts = temp_df.groupby(column_name)[respondent_col].nunique().sort_values(ascending=False)
    return counts.to_dict()

# ===== Funções de Plotagem com Tema =====
def apply_plotly_theme(fig):
    """Aplica tema do Streamlit aos gráficos Plotly"""
    bg, txt, primary, secondary = get_theme_colors()
    
    fig.update_layout(
        paper_bgcolor=bg,
        plot_bgcolor=bg,
        font_color=txt,
        title_font_color=txt,
        legend=dict(font=dict(color=txt)),
        xaxis=dict(
            showgrid=False,
            tickfont=dict(color=txt),
            titlefont=dict(color=txt)
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(128,128,128,0.2)",
            tickfont=dict(color=txt),
            titlefont=dict(color=txt)
        )
    )
    return fig

def create_bar_chart_distinct(df, column_name, title, color='#FF6B6B', max_items=15):
    """Cria gráfico de barras com contagem distinta de respondentes"""
    data_dict = get_distinct_counts(df, column_name)
    
    if not data_dict:
        return None
    
    # Pegar apenas os top items
    items = list(data_dict.items())[:max_items]
    df_plot = pd.DataFrame(items, columns=['Categoria', 'Respondentes Únicos'])
    
    fig = go.Figure(data=[
        go.Bar(
            x=df_plot['Categoria'],
            y=df_plot['Respondentes Únicos'],
            marker_color=color,
            text=df_plot['Respondentes Únicos'],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Respondentes: %{y}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title="Respondentes Únicos",
        height=450,
        margin=dict(b=120, l=60, r=30, t=60)
    )
    
    return apply_plotly_theme(fig)

def create_horizontal_bar_chart_distinct(df, column_name, title, color='#FF6B6B', max_items=15):
    """Cria gráfico de barras horizontal com contagem distinta"""
    data_dict = get_distinct_counts(df, column_name)
    
    if not data_dict:
        return None
    
    items = list(data_dict.items())[:max_items]
    df_plot = pd.DataFrame(items, columns=['Categoria', 'Respondentes Únicos'])
    df_plot = df_plot.sort_values('Respondentes Únicos', ascending=True)
    
    fig = go.Figure(data=[
        go.Bar(
            y=df_plot['Categoria'],
            x=df_plot['Respondentes Únicos'],
            orientation='h',
            marker_color=color,
            text=df_plot['Respondentes Únicos'],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Respondentes: %{x}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title=title,
        xaxis_title="Respondentes Únicos",
        yaxis_title="",
        height=max(400, len(df_plot) * 30),
        margin=dict(l=200, r=50, t=60, b=60)
    )
    
    return apply_plotly_theme(fig)

def create_age_distribution(df, respondent_col='respondent_id'):
    """Cria distribuição por faixa etária com contagem distinta"""
    idade_col = 'IDADE' if 'IDADE' in df.columns else 'idade'
    
    if idade_col not in df.columns:
        return None
    
    # Converter para numérico e criar faixas
    df_temp = df[[respondent_col, idade_col]].copy()
    df_temp[idade_col] = pd.to_numeric(df_temp[idade_col], errors='coerce')
    df_temp = df_temp.dropna()
    
    df_temp['faixa_etaria'] = pd.cut(
        df_temp[idade_col],
        bins=[0, 19, 25, 30, 100],
        labels=['Até 19', '20-25', '26-30', 'Acima de 30']
    )
    
    # Contagem distinta por faixa
    faixa_counts = df_temp.groupby('faixa_etaria')[respondent_col].nunique().reindex(
        ['Até 19', '20-25', '26-30', 'Acima de 30']
    ).fillna(0)
    
    fig = go.Figure(data=[
        go.Bar(
            x=faixa_counts.index,
            y=faixa_counts.values,
            marker_color='#764ba2',
            text=faixa_counts.values,
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title="Distribuição por Faixa Etária (Respondentes Únicos)",
        xaxis_title="Faixa Etária",
        yaxis_title="Respondentes Únicos",
        height=450
    )
    
    return apply_plotly_theme(fig)

# ===== Visualizações =====
def show_kpis(df, stats):
    """Mostra KPIs principais"""
    st.markdown("## 📊 Visão Geral")
    
    cols = st.columns(4)
    
    with cols[0]:
        st.metric("📝 Total de Respostas", f"{stats['total_linhas']:,}")
    
    with cols[1]:
        st.metric("👤 Respondentes Únicos", f"{stats['total_unicos']:,}")
    
    with cols[2]:
        if 'respostas_multiplas' in stats and stats['respostas_multiplas'] > 0:
            st.metric("📋 Respostas Múltiplas", f"{stats['respostas_multiplas']:,}")
        else:
            st.metric("📋 Respostas Múltiplas", "0")
    
    with cols[3]:
        idade_col = 'IDADE' if 'IDADE' in df.columns else 'idade'
        if idade_col in df.columns:
            media_idade = pd.to_numeric(df[idade_col], errors='coerce').mean()
            st.metric("👤 Idade Média", f"{media_idade:.1f} anos")
        else:
            st.metric("👤 Idade Média", "N/A")

def show_profile_analysis(df):
    """Análise de perfil dos respondentes"""
    st.markdown("## 👥 Perfil dos Respondentes")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Distribuição por Perfil")
        voce_col = 'VOCE É' if 'VOCE É' in df.columns else 'voce_e'
        if voce_col in df.columns:
            fig = create_bar_chart_distinct(df, voce_col, "Perfil dos Respondentes", '#667eea')
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Coluna de perfil não encontrada.")
    
    with col2:
        st.subheader("Distribuição por Idade")
        fig = create_age_distribution(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Coluna de idade não encontrada.")

def show_courses_analysis(df):
    """Análise de cursos"""
    st.markdown("## 🎓 Análise de Cursos")
    
    # Tentar encontrar coluna de curso
    curso_cols = ['CURSO DE GRADUAÇÃO OF', 'curso_graduacao', 'curso']
    curso_col = None
    
    for col in curso_cols:
        if col in df.columns:
            curso_col = col
            break
    
    if not curso_col:
        st.info("Coluna de curso não encontrada.")
        return
    
    st.subheader("Top 15 Cursos (Respondentes Únicos)")
    fig = create_horizontal_bar_chart_distinct(df, curso_col, "Cursos com Mais Respondentes", '#2ecc71', max_items=15)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

# ===== MAIN =====
def main():
    # Aplicar CSS customizado
    apply_custom_css()
    
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
            github_options = [
                ("Dados CEFET_MG Sem dados pessoais", CEFET_COPIA_RAW),
                ("dados_cefet.xlsx (data/)", REPO_DEFAULT_RAW),
                ("dados_cefet.xlsx (alternativo)", ALT_DEFAULT_RAW)
            ]
            
            selected_option = st.selectbox(
                "Selecione o arquivo",
                options=github_options,
                format_func=lambda x: x[0],
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
        st.info("Dashboard v2.0 - CEFET/MG\n\n✅ Contagem distinta de respondentes\n✅ Tema responsivo\n✅ Carregamento direto do GitHub")
    
    # Processar dados
    df = None
    source_info = ""
    
    # Tentar carregar do GitHub
    if use_github and not uploaded_file:
        with st.spinner('📥 Carregando arquivo do GitHub...'):
            df = load_excel(selected_option[1])
            source_info = f"📦 Arquivo: {selected_option[0]}"
    
    # Se upload manual
    if uploaded_file:
        with st.spinner('📥 Processando upload...'):
            df = load_excel(uploaded_file)
            source_info = f"📤 Upload: {uploaded_file.name}"
    
    if df is not None:
        st.success(source_info)
        
        # Processar dados
        with st.spinner('⚙️ Processando dados...'):
            df_processed, stats = process_data(df)
        
        if df_processed is None:
            st.stop()
        
        st.success(f"✅ {stats['total_linhas']:,} respostas de {stats['total_unicos']:,} respondentes carregadas!")
        
        if stats['respostas_multiplas'] > 0:
            st.info(f"📋 {stats['respostas_multiplas']:,} respostas múltiplas (válidas) detectadas")
        
        # Tabs de navegação
        tabs = st.tabs([
            "📊 Geral",
            "👥 Perfil", 
            "🎓 Cursos"
        ])
        
        with tabs[0]:
            show_kpis(df_processed, stats)
            
            with st.expander("🔍 Ver dados brutos (100 primeiras linhas)"):
                st.dataframe(df_processed.head(100), use_container_width=True)
        
        with tabs[1]:
            show_profile_analysis(df_processed)
        
        with tabs[2]:
            show_courses_analysis(df_processed)
        
        # Download
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
            st.markdown("### 📋 Melhorias v2.0")
            st.markdown("""
            ✅ **Contagem distinta de respondentes**
            ✅ **Carregamento direto do GitHub**
            ✅ **Tema responsivo com cores automáticas**
            ✅ **Gráficos otimizados para mobile**
            ✅ **Performance melhorada**
            """)
        
        with col2:
            st.markdown("### 📊 Análises Disponíveis")
            st.markdown("""
            - ✅ Perfil dos respondentes (único)
            - ✅ Cursos e distribuições (único)
            - ✅ Faixas etárias (único)
            - ✅ Visualizações horizontais
            - ✅ Export de dados processados
            """)

if __name__ == "__main__":
    main()
