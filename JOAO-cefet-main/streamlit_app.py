import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# ===== Configuração =====
st.set_page_config(
    page_title="Dashboard CEFET-MG",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Definir cor de fundo e fonte dinamicamente
def get_bg_and_font_color():
    bg = st.get_option("theme.backgroundColor") or "#f5f5f5"
    font_c = st.get_option("theme.textColor") or "#262730"
    return bg, font_c

bg_color, font_color = get_bg_and_font_color()

# CSS para mobile responsivo e tema
st.markdown("""
<style>
    .main-header {
        font-size: 1.5rem;
        color: var(--text-color);
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

    /* Ajustes de tema */
    :root {
        --text-color: """ + font_color + """;
        --bg-color: """ + bg_color + """;
    }
</style>
""", unsafe_allow_html=True)

# ===== Funções de Carregamento =====
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

def load_column_mapping():
    """Carrega o mapeamento de colunas do CSV"""
    csv_path = Path("columns_classification.csv")
    
    if csv_path.exists():
        try:
            mapping_df = pd.read_csv(csv_path)
            col_to_tech = dict(zip(mapping_df['coluna_original'], mapping_df['nome_tecnico']))
            tech_to_label = dict(zip(mapping_df['nome_tecnico'], mapping_df['rotulo_publico']))
            tech_to_class = dict(zip(mapping_df['nome_tecnico'], mapping_df['classe']))
            return col_to_tech, tech_to_label, tech_to_class
        except Exception as e:
            st.error(f"Erro ao carregar mapeamento: {str(e)}")
            return {}, {}, {}
    else:
        st.warning("⚠️ Arquivo columns_classification.csv não encontrado.")
        return {}, {}, {}

def apply_mapping(df, col_to_tech):
    """Aplica o mapeamento de colunas ao DataFrame"""
    if not col_to_tech:
        return df
    
    cols_to_rename = {orig: tech for orig, tech in col_to_tech.items() if orig in df.columns}
    df_renamed = df.rename(columns=cols_to_rename)
    
    mapped_count = len(cols_to_rename)
    st.sidebar.success(f"✅ {mapped_count} colunas mapeadas")
    
    return df_renamed

# ===== Funções de Visualização =====
def create_horizontal_bar_chart_distinct(df, categoria_col, title, color='#1f77b4', max_items=15):
    """Cria gráfico de barras horizontal com contagem distinta de respondentes"""
    if categoria_col not in df.columns or 'respondent_id' not in df.columns:
        return None
        
    counts = df.groupby(categoria_col)['respondent_id'].nunique().sort_values(ascending=True).tail(max_items)
    df_plot = counts.reset_index()
    
    fig = go.Figure(data=[
        go.Bar(
            y=df_plot[categoria_col],
            x=df_plot['respondent_id'],
            orientation='h',
            marker_color=color,
            text=df_plot['respondent_id'],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Respondentes únicos: %{x}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title=title,
        xaxis_title="Respondentes Únicos",
        yaxis_title="",
        height=max(400, len(df_plot) * 30),
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(color=font_color),
        margin=dict(l=200, r=30, t=60, b=60),
        hovermode='y unified'
    )
    
    fig.update_yaxes(
        showgrid=False,
        showline=True,
        linewidth=1,
        linecolor=font_color,
        tickmode='linear'
    )
    
    return fig

def create_bar_chart_distinct(df, categoria_col, title, color='#1f77b4'):
    """Cria gráfico de barras vertical com contagem distinta de respondentes"""
    if categoria_col not in df.columns or 'respondent_id' not in df.columns:
        return None
        
    counts = df.groupby(categoria_col)['respondent_id'].nunique().sort_values(ascending=False)
    df_plot = counts.reset_index()
    
    fig = go.Figure(data=[
        go.Bar(
            x=df_plot[categoria_col],
            y=df_plot['respondent_id'],
            marker_color=color,
            text=df_plot['respondent_id'],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Respondentes únicos: %{y}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title="Respondentes Únicos",
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
        font=dict(color=font_color),
        margin=dict(b=120, l=60, r=30, t=60),
        hovermode='x unified',
        yaxis=dict(rangemode='tozero', gridcolor='rgba(128, 128, 128, 0.2)')
    )
    
    fig.update_xaxes(
        showgrid=False,
        showline=True,
        linewidth=1,
        linecolor=font_color,
        tickangle=45
    )
    
    return fig

# ===== Funções de Análise =====
def show_kpis(df, stats, tech_to_label):
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
        idade_col = next((col for col in ['idade', 'IDADE'] if col in df.columns), None)
        if idade_col:
            media_idade = pd.to_numeric(df[idade_col], errors='coerce').mean()
            st.metric("👤 Idade Média", f"{media_idade:.1f} anos")
        else:
            st.metric("👤 Idade Média", "N/A")

def show_profile_analysis(df, tech_to_label):
    """Análise de perfil dos respondentes"""
    st.markdown("## 👥 Perfil dos Respondentes")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Distribuição por Perfil")
        voce_col = next((col for col in ['voce_e', 'VOCE É'] if col in df.columns), None)
        if voce_col:
            fig = create_bar_chart_distinct(df, voce_col, "Perfil dos Respondentes", '#667eea')
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Coluna de perfil não encontrada")
    
    with col2:
        st.subheader("Distribuição por Idade")
        idade_col = next((col for col in ['idade', 'IDADE'] if col in df.columns), None)
        if idade_col:
            df_temp = df.copy()
            df_temp[idade_col] = pd.to_numeric(df_temp[idade_col], errors='coerce')
            df_temp['faixa_etaria'] = pd.cut(
                df_temp[idade_col],
                bins=[0, 19, 25, 30, 100],
                labels=['Até 19', '20-25', '26-30', 'Acima de 30']
            )
            fig = create_bar_chart_distinct(df_temp, 'faixa_etaria', "Faixa Etária", '#764ba2')
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Coluna de idade não encontrada")

def show_courses_analysis(df, tech_to_label):
    """Análise de cursos"""
    st.markdown("## 🎓 Análise de Cursos")
    
    curso_col = next((col for col in ['curso_graduacao', 'CURSO DE GRADUAÇÃO OF', 'curso'] if col in df.columns), None)
    if not curso_col:
        st.info("Coluna de curso não encontrada")
        return
    
    fig = create_horizontal_bar_chart_distinct(df, curso_col, "Cursos com Mais Respondentes", '#2ecc71', max_items=15)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("Ver todos os cursos"):
        all_courses = df.groupby(curso_col)['respondent_id'].nunique().reset_index()
        all_courses.columns = ['Curso', 'Respondentes Únicos']
        all_courses['%'] = (all_courses['Respondentes Únicos'] / df['respondent_id'].nunique() * 100).round(2)
        st.dataframe(all_courses, use_container_width=True)

def show_entrepreneurship_analysis(df, tech_to_label):
    """Análise de empreendedorismo"""
    st.markdown("## 🚀 Empreendedorismo")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Conceitos de Empreendedorismo")
        
        conceito_cols = {
            'Abrir Negócio': next((col for col in df.columns if 'abrir o próprio negócio' in col.lower()), None),
            'Impacto Social': next((col for col in df.columns if 'fazer algo bom para a sociedade' in col.lower()), None),
            'Melhorar Ambiente': next((col for col in df.columns if 'melhorar o ambiente' in col.lower()), None)
        }
        
        conceito_data = {}
        for label, col in conceito_cols.items():
            if col:
                count = df.groupby(col)['respondent_id'].nunique().get(1, 0)  # Assumindo 1 como resposta positiva
                if count > 0:
                    conceito_data[label] = count
        
        if conceito_data:
            fig = create_bar_chart_distinct(df_temp, 'conceito', "Conceitos de Empreendedorismo", '#e74c3c')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Dados não encontrados")
    
    with col2:
        st.subheader("Fundadores/Sócios")
        
        fundador_col = next((col for col in ['socio_ou_fundador', 'Você é sócio(a) ou fundador(a) de alguma empresa?Response']
                           if col in df.columns), None)
        
        if fundador_col:
            fig = create_bar_chart_distinct(df, fundador_col, "Fundadores/Sócios", '#3498db')
            st.plotly_chart(fig, use_container_width=True)
            
            total_resp = df['respondent_id'].nunique()
            total_fund = df[df[fundador_col] == 'Sim']['respondent_id'].nunique()
            pct = (total_fund / total_resp * 100)
            st.metric("Percentual de Fundadores", f"{pct:.1f}%")
        else:
            st.info("Coluna de fundador não encontrada")

def show_professors_analysis(df, tech_to_label):
    """Análise dos professores"""
    st.markdown("## 👨‍🏫 Avaliação dos Professores")
    
    prof_data = {}
    patterns = {
        'Inconformismo': ['inconformismo', 'transformá-la'],
        'Visão': ['visão para oportunidades'],
        'Inovação': ['pensamento inovador', 'criativo'],
        'Coragem': ['coragem para tomar riscos'],
        'Curiosidade': ['curiosidade'],
        'Comunicação': ['comunicação', 'sociabilidade'],
        'Planejamento': ['planejamento de atividades'],
        'Apoio': ['apoio a iniciativas']
    }
    
    for label, keywords in patterns.items():
        for col in df.columns:
            if 'PROFESSORES' in col.upper() and any(kw.lower() in col.lower() for kw in keywords):
                valores = pd.to_numeric(df[col], errors='coerce')
                media = valores.mean()
                if not pd.isna(media) and media > 0:
                    prof_data[label] = media
                break
    
    if prof_data:
        fig = create_bar_chart_distinct(pd.DataFrame({'caracteristica': list(prof_data.keys()),
                                                     'valor': list(prof_data.values())}),
                                      'caracteristica', "Avaliação dos Professores", '#9b59b6')
        st.plotly_chart(fig, use_container_width=True)
        
        media_geral = np.mean(list(prof_data.values()))
        st.metric("Média Geral", f"{media_geral:.2f}")
    else:
        st.warning("⚠️ Dados não encontrados")

def show_infrastructure_analysis(df, tech_to_label):
    """Análise de infraestrutura"""
    st.markdown("## 🏢 Infraestrutura")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Infraestrutura Geral")
        
        infra_data = {}
        infra_keywords = {
            'Biblioteca': 'biblioteca',
            'Labs Informática': ['laboratórios de informática', 'labs informática'],
            'Labs Pesquisa': ['laboratórios de pesquisa', 'experimentação'],
            'Espaços Convivência': ['espaços', 'convivência'],
            'Restaurante': 'restaurante'
        }
        
        for label, keywords in infra_keywords.items():
            keywords = [keywords] if isinstance(keywords, str) else keywords
            for col in df.columns:
                if any(kw.lower() in col.lower() for kw in keywords):
                    valores = pd.to_numeric(df[col], errors='coerce')
                    media = valores.mean()
                    if not pd.isna(media) and media > 0:
                        infra_data[label] = media
                    break
        
        if infra_data:
            fig = create_bar_chart_distinct(pd.DataFrame({'local': list(infra_data.keys()),
                                                        'avaliacao': list(infra_data.values())}),
                                          'local', "Avaliação da Infraestrutura", '#16a085')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Dados não encontrados")
    
    with col2:
        st.subheader("Acessibilidade (PCD)")
        
        acess_data = {}
        acess_keywords = {
            'Calçadas': 'calçadas',
            'Vias Acesso': ['vias de acesso', 'edificações'],
            'Rotas Internas': 'rota acessível',
            'Sanitários': 'sanitários',
            'Elevadores': ['elevadores', 'rampas']
        }
        
        for label, keywords in acess_keywords.items():
            keywords = [keywords] if isinstance(keywords, str) else keywords
            for col in df.columns:
                if any(kw.lower() in col.lower() for kw in keywords):
                    valores = pd.to_numeric(df[col], errors='coerce')
                    media = valores.mean()
                    if not pd.isna(media) and media > 0:
                        acess_data[label] = media
                    break
        
        if acess_data:
            fig = create_bar_chart_distinct(pd.DataFrame({'item': list(acess_data.keys()),
                                                        'avaliacao': list(acess_data.values())}),
                                          'item', "Avaliação de Acessibilidade", '#27ae60')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Dados não encontrados")

def process_data(df):
    """Processa dados mantendo contagem de respondentes únicos"""
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

def main():
    # Header
    st.markdown('<h1 class="main-header">📊 Dashboard CEFET-MG</h1>', unsafe_allow_html=True)
    st.markdown("### Pesquisa sobre Empreendedorismo e Educação Superior")
    st.markdown("---")
    
    # Carregar mapeamento
    col_to_tech, tech_to_label, tech_to_class = load_column_mapping()
    
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
        
        with st.spinner('🔄 Aplicando mapeamento de colunas...'):
            df = apply_mapping(df, col_to_tech)
        
        with st.spinner('⚙️ Processando dados...'):
            df_processed, stats = process_data(df)
        
        if df_processed is None:
            st.stop()
        
        st.success(f"✅ {stats['total_linhas']:,} respostas de {stats['total_unicos']:,} respondentes carregadas!")
        
        if stats['respostas_multiplas'] > 0:
            st.info(f"📋 {stats['respostas_multiplas']:,} respostas múltiplas (válidas) detectadas")
        
        tabs = st.tabs([
            "📊 Geral",
            "👥 Perfil",
            "🎓 Cursos",
            "🚀 Empreendedorismo",
            "👨‍🏫 Professores",
            "🏢 Infraestrutura"
        ])
        
        with tabs[0]:
            show_kpis(df_processed, stats, tech_to_label)
            with st.expander("🔍 Ver dados brutos (100 primeiras linhas)"):
                st.dataframe(df_processed.head(100), use_container_width=True)
        
        with tabs[1]:
            show_profile_analysis(df_processed, tech_to_label)
        
        with tabs[2]:
            show_courses_analysis(df_processed, tech_to_label)
        
        with tabs[3]:
            show_entrepreneurship_analysis(df_processed, tech_to_label)
        
        with tabs[4]:
            show_professors_analysis(df_processed, tech_to_label)
        
        with tabs[5]:
            show_infrastructure_analysis(df_processed, tech_to_label)
        
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
