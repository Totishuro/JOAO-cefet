import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import requests
import io
from datetime import datetime

# ===== Configuração =====
st.set_page_config(
    page_title="Dashboard CEFET-MG",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Definir configurações base dos gráficos
def get_base_graph_config():
    return {
        'plot_bgcolor': 'rgba(0,0,0,0)',  # Fundo transparente
        'paper_bgcolor': 'rgba(0,0,0,0)',  # Fundo do papel transparente
        'font': {
            'color': 'white',  # Fonte branca
            'size': 12
        },
        'xaxis': {
            'gridcolor': 'rgba(255,255,255,0.1)',
            'linecolor': 'rgba(255,255,255,0.2)',
            'tickfont': {'color': 'white'}
        },
        'yaxis': {
            'gridcolor': 'rgba(255,255,255,0.1)',
            'linecolor': 'rgba(255,255,255,0.2)',
            'tickfont': {'color': 'white'}
        }
    }

# CSS para mobile responsivo e tema
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

    /* Tema escuro para melhor contraste */
    .reportview-container {
        background: #0e1117;
    }
    
    .sidebar .sidebar-content {
        background: #262730;
    }
</style>
""", unsafe_allow_html=True)

# ===== Funções Utilitárias =====
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
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return '<br>'.join(lines)

def debug_column_search(df, section_name, patterns):
    """Função auxiliar para debug de colunas não encontradas"""
    st.error(f"⚠️ Dados não encontrados para: {section_name}")
    
    matching_cols = []
    for col in df.columns:
        for pattern in patterns:
            if pattern.lower() in col.lower():
                matching_cols.append({
                    'coluna': col,
                    'valores_unicos': df[col].unique().tolist()[:5],
                    'nulos': df[col].isnull().sum()
                })
    
    if matching_cols:
        st.write("Colunas encontradas:")
        for col_info in matching_cols:
            st.write(f"- {col_info['coluna']}")
            st.write(f"  Primeiros valores: {col_info['valores_unicos']}")
            st.write(f"  Valores nulos: {col_info['nulos']}")
    else:
        st.write("Nenhuma coluna encontrada com os padrões buscados")

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
def create_horizontal_bar_chart(df, categoria_col, valor_col, title, color='#3498db'):
    """Cria gráfico de barras horizontal com quebra de linha nos rótulos"""
    df = df.copy()
    df[categoria_col] = df[categoria_col].apply(break_text)
    
    fig = go.Figure(data=[
        go.Bar(
            y=df[categoria_col],
            x=df[valor_col],
            orientation='h',
            marker_color=color,
            text=df[valor_col],
            textposition='outside',
            textfont={'color': 'white'}
        )
    ])
    
    fig.update_layout(
        **get_base_graph_config(),
        title=title,
        height=max(300, len(df) * 30),
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False
    )
    
    return fig

def create_vertical_bar_chart(df, categoria_col, valor_col, title, color='#3498db'):
    """Cria gráfico de barras vertical com quebra de linha nos rótulos"""
    df = df.copy()
    df[categoria_col] = df[categoria_col].apply(break_text)
    
    fig = go.Figure(data=[
        go.Bar(
            x=df[categoria_col],
            y=df[valor_col],
            marker_color=color,
            text=df[valor_col],
            textposition='outside',
            textfont={'color': 'white'}
        )
    ])
    
    fig.update_layout(
        **get_base_graph_config(),
        title=title,
        height=400,
        margin=dict(l=20, r=20, t=40, b=100),
        showlegend=False,
        xaxis_tickangle=-45
    )
    
    return fig

# ===== Funções de Análise =====
def show_kpis(df):
    """Mostra KPIs principais"""
    st.markdown("## 📊 Visão Geral")
    
    cols = st.columns(2)
    
    with cols[0]:
        total_respondentes = df['respondent_id'].nunique()
        st.metric("📝 Total de Respondentes", f"{total_respondentes:,}")
    
    with cols[1]:
        idade_col = next((col for col in ['idade', 'IDADE'] if col in df.columns), None)
        if idade_col:
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
        voce_col = next((col for col in ['voce_e', 'VOCE É'] if col in df.columns), None)
        if voce_col:
            counts = df.groupby(voce_col)['respondent_id'].nunique().reset_index()
            counts.columns = ['Perfil', 'Contagem']
            fig = create_vertical_bar_chart(counts, 'Perfil', 'Contagem', "", '#667eea')
            st.plotly_chart(fig, use_container_width=True)
        else:
            debug_column_search(df, "Perfil", ['voce_e', 'VOCE É'])
    
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
            counts = df_temp.groupby('faixa_etaria')['respondent_id'].nunique().reset_index()
            counts.columns = ['Faixa', 'Contagem']
            fig = create_vertical_bar_chart(counts, 'Faixa', 'Contagem', "", '#764ba2')
            st.plotly_chart(fig, use_container_width=True)
        else:
            debug_column_search(df, "Idade", ['idade', 'IDADE'])

def show_courses_analysis(df):
    """Análise de cursos"""
    st.markdown("## 🎓 Análise de Cursos")
    
    curso_col = next((col for col in ['curso_graduacao', 'CURSO DE GRADUAÇÃO OF', 'curso'] 
                     if col in df.columns), None)
    if curso_col:
        counts = df.groupby(curso_col)['respondent_id'].nunique().reset_index()
        counts.columns = ['Curso', 'Contagem']
        counts = counts.sort_values('Contagem', ascending=True).tail(15)
        
        fig = create_horizontal_bar_chart(counts, 'Curso', 'Contagem', "Top 15 Cursos", '#2ecc71')
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Ver todos os cursos"):
            all_courses = df.groupby(curso_col)['respondent_id'].nunique().reset_index()
            all_courses.columns = ['Curso', 'Respondentes Únicos']
            all_courses['%'] = (all_courses['Respondentes Únicos'] / 
                              df['respondent_id'].nunique() * 100).round(2)
            st.dataframe(all_courses.sort_values('Respondentes Únicos', ascending=False),
                        use_container_width=True)
    else:
        debug_column_search(df, "Cursos", ['curso', 'graduacao'])

def show_entrepreneurship_analysis(df):
    """Análise de empreendedorismo"""
    st.markdown("## 🚀 Empreendedorismo")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Conceitos de Empreendedorismo")
        
        conceito_patterns = [
            ('Negócio', ['negócio', 'empresa', 'empreender']),
            ('Social', ['social', 'sociedade', 'comunidade']),
            ('Inovação', ['inovação', 'inovar', 'criar']),
            ('Ambiente', ['ambiente', 'meio', 'sustentável'])
        ]
        
        conceito_data = {}
        for label, patterns in conceito_patterns:
            for col in df.columns:
                if 'empreend' in col.lower() and any(p in col.lower() for p in patterns):
                    count = df[df[col] == 1]['respondent_id'].nunique()
                    if count > 0:
                        conceito_data[label] = count
                    break
        
        if conceito_data:
            df_conceitos = pd.DataFrame(list(conceito_data.items()), 
                                      columns=['Conceito', 'Contagem'])
            fig = create_vertical_bar_chart(df_conceitos, 'Conceito', 'Contagem', 
                                          "", '#e74c3c')
            st.plotly_chart(fig, use_container_width=True)
        else:
            debug_column_search(df, "Conceitos de Empreendedorismo", ['empreend'])
    
    with col2:
        st.subheader("Fundadores/Sócios")
        fundador_col = next((col for col in [
            'socio_ou_fundador',
            'Você é sócio(a) ou fundador(a) de alguma empresa?Response'
        ] if col in df.columns), None)
        
        if fundador_col:
            counts = df.groupby(fundador_col)['respondent_id'].nunique().reset_index()
            counts.columns = ['Resposta', 'Contagem']
            
            fig = create_horizontal_bar_chart(counts, 'Resposta', 'Contagem', 
                                            "", '#3498db')
            st.plotly_chart(fig, use_container_width=True)
            
            total_resp = df['respondent_id'].nunique()
            total_fund = df[df[fundador_col] == 'Sim']['respondent_id'].nunique()
            pct = (total_fund / total_resp * 100)
            st.metric("Percentual de Fundadores", f"{pct:.1f}%")
        else:
            debug_column_search(df, "Fundadores", ['socio', 'fundador'])

def show_professors_analysis(df):
    """Análise dos professores"""
    st.markdown("## 👨‍🏫 Avaliação dos Professores")
    
    prof_patterns = {
        'Inconformismo': ['inconformismo', 'transformá-la'],
        'Visão': ['visão para oportunidades'],
        'Inovação': ['pensamento inovador', 'criativo'],
        'Coragem': ['coragem para tomar riscos'],
        'Curiosidade': ['curiosidade'],
        'Comunicação': ['comunicação', 'sociabilidade'],
        'Planejamento': ['planejamento de atividades'],
        'Apoio': ['apoio a iniciativas']
    }
    
    prof_data = {}
    for label, keywords in prof_patterns.items():
        for col in df.columns:
            if 'PROFESSOR' in col.upper() and any(kw.lower() in col.lower() for kw in keywords):
                valores = pd.to_numeric(df[col], errors='coerce')
                media = valores.mean()
                if not pd.isna(media) and media > 0:
                    prof_data[label] = media
                break
    
    if prof_data:
        df_prof = pd.DataFrame(list(prof_data.items()), columns=['Característica', 'Média'])
        fig = create_horizontal_bar_chart(df_prof, 'Característica', 'Média', 
                                        "", '#9b59b6')
        st.plotly_chart(fig, use_container_width=True)
        
        media_geral = np.mean(list(prof_data.values()))
        st.metric("Média Geral", f"{media_geral:.2f}")
    else:
        debug_column_search(df, "Professores", ['PROFESSOR', 'DOCENTE'])

def show_infrastructure_analysis(df):
    """Análise de infraestrutura"""
    st.markdown("## 🏢 Infraestrutura")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Infraestrutura Geral")
        
        infra_keywords = {
            'Biblioteca': ['biblioteca'],
            'Labs Informática': ['laboratórios de informática', 'labs informática'],
            'Labs Pesquisa': ['laboratórios de pesquisa', 'experimentação'],
            'Espaços': ['espaços', 'convivência'],
            'Restaurante': ['restaurante']
        }
        
        infra_data = {}
        for label, keywords in infra_keywords.items():
            for col in df.columns:
                if any(kw.lower() in col.lower() for kw in keywords):
                    valores = pd.to_numeric(df[col], errors='coerce')
                    media = valores.mean()
                    if not pd.isna(media) and media > 0:
                        infra_data[label] = media
                    break
        
        if infra_data:
            df_infra = pd.DataFrame(list(infra_data.items()), 
                                  columns=['Local', 'Avaliação'])
            fig = create_horizontal_bar_chart(df_infra, 'Local', 'Avaliação', 
                                            "", '#16a085')
            st.plotly_chart(fig, use_container_width=True)
        else:
            debug_column_search(df, "Infraestrutura", ['infraestrutura', 'biblioteca'])
    
    with col2:
        st.subheader("Acessibilidade (PCD)")
        
        acess_keywords = {
            'Calçadas': ['calçadas'],
            'Vias Acesso': ['vias de acesso', 'edificações'],
            'Rotas': ['rota acessível'],
            'Sanitários': ['sanitários'],
            'Elevadores': ['elevadores', 'rampas']
        }
        
        acess_data = {}
        for label, keywords in acess_keywords.items():
            for col in df.columns:
                if any(kw.lower() in col.lower() for kw in keywords):
                    valores = pd.to_numeric(df[col], errors='coerce')
                    media = valores.mean()
                    if not pd.isna(media) and media > 0:
                        acess_data[label] = media
                    break
        
        if acess_data:
            df_acess = pd.DataFrame(list(acess_data.items()), 
                                  columns=['Item', 'Avaliação'])
            fig = create_horizontal_bar_chart(df_acess, 'Item', 'Avaliação', 
                                            "", '#27ae60')
            st.plotly_chart(fig, use_container_width=True)
        else:
            debug_column_search(df, "Acessibilidade", ['acessibilidade', 'pcd'])

def process_data(df):
    """Processa dados mantendo contagem de respondentes únicos"""
    if df is None:
        return None
        
    if 'respondent_id' not in df.columns:
        st.error("❌ Coluna 'respondent_id' não encontrada!")
        st.info(f"Colunas disponíveis: {', '.join(df.columns[:10])}...")
        return None
    
    return df

# ===== MAIN =====
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
        
        # Data e hora atual
        now = datetime.utcnow()
        st.markdown(f"**Última atualização:** {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
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
            df_processed = process_data(df)
        
        if df_processed is None:
            st.stop()
        
        st.success(f"✅ {df_processed['respondent_id'].nunique():,} respondentes únicos carregados!")
        
        tabs = st.tabs([
            "📊 Geral",
            "👥 Perfil",
            "🎓 Cursos",
            "🚀 Empreendedorismo",
            "👨‍🏫 Professores",
            "🏢 Infraestrutura"
        ])
        
        with tabs[0]:
            show_kpis(df_processed)
            with st.expander("🔍 Ver dados brutos (100 primeiras linhas)"):
                st.dataframe(df_processed.head(100), use_container_width=True)
        
        with tabs[1]:
            show_profile_analysis(df_processed)
        
        with tabs[2]:
            show_courses_analysis(df_processed)
        
        with tabs[3]:
            show_entrepreneurship_analysis(df_processed)
        
        with tabs[4]:
            show_professors_analysis(df_processed)
        
        with tabs[5]:
            show_infrastructure_analysis(df_processed)
        
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
