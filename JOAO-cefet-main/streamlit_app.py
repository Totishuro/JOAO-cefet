import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

# ===== Configuração =====
st.set_page_config(
    page_title="Dashboard CEFET-MG",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS para mobile responsivo
st.markdown("""
<style>
    .main-header {
        font-size: 1.5rem;
        color: #1f77b4;
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
</style>
""", unsafe_allow_html=True)

# ===== Funções de Mapeamento =====
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
    
    # Debug: mostrar quais colunas foram mapeadas
    mapped_count = len(cols_to_rename)
    st.sidebar.success(f"✅ {mapped_count} colunas mapeadas")
    
    return df_renamed

# ===== Funções de Processamento =====
@st.cache_data(show_spinner=False)
def load_excel(file_or_path):
    """Carrega arquivo Excel"""
    try:
        df = pd.read_excel(file_or_path, engine='openpyxl')
        return df
    except Exception as e:
        st.error(f"❌ Erro ao ler arquivo: {str(e)}")
        return None

def process_data(df):
    """Processa dados SEM remover duplicatas (respostas múltiplas são válidas)"""
    if df is None:
        return None, None
        
    if 'respondent_id' not in df.columns:
        st.error("❌ Coluna 'respondent_id' não encontrada!")
        st.info(f"Colunas disponíveis: {', '.join(df.columns[:10])}...")
        return None, None
    
    # IMPORTANTE: NÃO remover duplicatas - são respostas múltiplas válidas!
    total_respostas = len(df)
    total_respondentes_unicos = df['respondent_id'].nunique()
    
    stats = {
        'total_linhas': total_respostas,
        'total_unicos': total_respondentes_unicos,
        'respostas_multiplas': total_respostas - total_respondentes_unicos
    }
    
    return df, stats  # Retorna o DataFrame COMPLETO

# ===== Funções de Plotagem =====
def break_long_text(text, max_length=20):
    """Quebra texto longo em múltiplas linhas"""
    if not isinstance(text, str):
        text = str(text)
    
    if len(text) <= max_length:
        return text
    
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= max_length:
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

def create_horizontal_bar_chart(data_dict, title, color='#1f77b4', max_items=15):
    """Cria gráfico de barras HORIZONTAL (melhor para textos longos)"""
    if not data_dict:
        return None
    
    df_plot = pd.DataFrame(list(data_dict.items()), columns=['Categoria', 'Valor'])
    df_plot = df_plot.sort_values('Valor', ascending=True).tail(max_items)  # Top items
    
    fig = go.Figure(data=[
        go.Bar(
            y=df_plot['Categoria'],
            x=df_plot['Valor'],
            orientation='h',
            marker_color=color,
            text=df_plot['Valor'],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Quantidade: %{x}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title=title,
        xaxis_title="Quantidade",
        yaxis_title="",
        height=max(400, len(df_plot) * 30),  # Altura dinâmica
        xaxis=dict(
            rangemode='tozero',
            gridcolor='lightgray'
        ),
        margin=dict(l=200, r=30, t=60, b=60),  # Margem esquerda para nomes longos
        plot_bgcolor='white',
        hovermode='y unified'
    )
    
    fig.update_yaxes(
        showgrid=False,
        showline=True,
        linewidth=1,
        linecolor='black',
        tickmode='linear'
    )
    
    return fig

def create_bar_chart(data_dict, title, color='#1f77b4'):
    """Cria gráfico de barras com Plotly e quebra de linha nos rótulos"""
    if not data_dict:
        return None
    
    df_plot = pd.DataFrame(list(data_dict.items()), columns=['Categoria', 'Valor'])
    
    # Quebrar textos longos em múltiplas linhas
    df_plot['Categoria_Original'] = df_plot['Categoria']
    df_plot['Categoria'] = df_plot['Categoria'].apply(break_long_text)
    
    fig = go.Figure(data=[
        go.Bar(
            x=df_plot['Categoria'],
            y=df_plot['Valor'],
            marker_color=color,
            text=df_plot['Valor'],
            textposition='outside',
            hovertemplate='<b>%{customdata}</b><br>Quantidade: %{y}<extra></extra>',
            customdata=df_plot['Categoria_Original']
        )
    ])
    
    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title="Quantidade",
        xaxis_tickangle=0,  # Sem inclinação quando tem quebra de linha
        height=450,
        yaxis=dict(
            rangemode='tozero',  # Não mostrar valores negativos
            gridcolor='lightgray'
        ),
        margin=dict(b=120, l=60, r=30, t=60),  # Margem maior embaixo
        plot_bgcolor='white',
        hovermode='x unified'
    )
    
    fig.update_xaxes(
        showgrid=False,
        showline=True,
        linewidth=1,
        linecolor='black'
    )
    
    return fig

# ===== Visualizações =====
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
        idade_col = 'idade' if 'idade' in df.columns else 'IDADE'
        if idade_col in df.columns:
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
        voce_col = 'voce_e' if 'voce_e' in df.columns else 'VOCE É'
        if voce_col in df.columns:
            perfil_counts = df[voce_col].value_counts()
            fig = create_bar_chart(perfil_counts.to_dict(), "Perfil dos Respondentes", '#667eea')
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Coluna de perfil não encontrada. Procurado: {voce_col}")
    
    with col2:
        st.subheader("Distribuição por Idade")
        idade_col = 'idade' if 'idade' in df.columns else 'IDADE'
        if idade_col in df.columns:
            df_temp = df.copy()
            df_temp[idade_col] = pd.to_numeric(df_temp[idade_col], errors='coerce')
            df_temp['faixa_etaria'] = pd.cut(
                df_temp[idade_col],
                bins=[0, 19, 25, 30, 100],
                labels=['Até 19', '20-25', '26-30', 'Acima de 30']
            )
            faixa_counts = df_temp['faixa_etaria'].value_counts().sort_index()
            fig = create_bar_chart(faixa_counts.to_dict(), "Faixa Etária", '#764ba2')
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Coluna de idade não encontrada. Procurado: {idade_col}")

def show_courses_analysis(df, tech_to_label):
    """Análise de cursos"""
    st.markdown("## 🎓 Análise de Cursos")
    
    # Tentar encontrar coluna de curso
    curso_col = None
    possible_names = ['curso_graduacao', 'CURSO DE GRADUAÇÃO OF', 'curso']
    for name in possible_names:
        if name in df.columns:
            curso_col = name
            break
    
    if not curso_col:
        st.info(f"Coluna de curso não encontrada. Colunas disponíveis: {', '.join(df.columns[:10])}...")
        return
    
    curso_counts = df[curso_col].value_counts().head(15)
    
    st.subheader("Top 15 Cursos")
    # Usar gráfico HORIZONTAL para nomes de cursos longos
    fig = create_horizontal_bar_chart(curso_counts.to_dict(), "Cursos com Mais Respondentes", '#2ecc71', max_items=15)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("Ver todos os cursos"):
        all_courses = df[curso_col].value_counts().reset_index()
        all_courses.columns = ['Curso', 'Quantidade']
        all_courses['%'] = (all_courses['Quantidade'] / len(df) * 100).round(2)
        st.dataframe(all_courses, use_container_width=True)

def show_entrepreneurship_analysis(df, tech_to_label):
    """Análise de empreendedorismo"""
    st.markdown("## 🚀 Empreendedorismo")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Conceitos de Empreendedorismo")
        
        # Buscar colunas de conceito (originais e mapeadas)
        conceito_cols = {}
        
        # Padrão original
        for col in df.columns:
            if 'O que você entende como empreendedorismo' in col:
                if 'abrir o próprio negócio' in col.lower():
                    conceito_cols['Abrir Negócio'] = col
                elif 'fazer algo bom para a sociedade' in col.lower():
                    conceito_cols['Impacto Social'] = col
                elif 'melhorar o ambiente' in col.lower():
                    conceito_cols['Melhorar Ambiente'] = col
        
        # Padrão mapeado
        if 'conceito_empreendedorismo_abrir_negocio' in df.columns:
            conceito_cols['Abrir Negócio'] = 'conceito_empreendedorismo_abrir_negocio'
        if 'conceito_empreendedorismo_impacto_social' in df.columns:
            conceito_cols['Impacto Social'] = 'conceito_empreendedorismo_impacto_social'
        if 'conceito_empreendedorismo_melhorar_ambiente' in df.columns:
            conceito_cols['Melhorar Ambiente'] = 'conceito_empreendedorismo_melhorar_ambiente'
        
        conceito_data = {}
        for label, col in conceito_cols.items():
            # Contar valores não nulos (incluindo strings)
            count = df[col].notna().sum()
            if count > 0:
                conceito_data[label] = count
        
        if conceito_data:
            fig = create_bar_chart(conceito_data, "Conceitos de Empreendedorismo", '#e74c3c')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Dados não encontrados. Colunas procuradas: conceitos de empreendedorismo")
    
    with col2:
        st.subheader("Fundadores/Sócios")
        
        # Buscar coluna de fundador
        fundador_col = None
        possible_names = ['socio_ou_fundador', 'Você é sócio(a) ou fundador(a) de alguma empresa?Response']
        for name in possible_names:
            if name in df.columns:
                fundador_col = name
                break
        
        if fundador_col:
            fundador_counts = df[fundador_col].value_counts()
            fig = create_bar_chart(fundador_counts.to_dict(), "Fundadores/Sócios", '#3498db')
            st.plotly_chart(fig, use_container_width=True)
            
            if 'Sim' in fundador_counts.index:
                pct = (fundador_counts['Sim'] / len(df) * 100)
                st.metric("Percentual de Fundadores", f"{pct:.1f}%")
        else:
            st.info("Coluna de fundador não encontrada")

def show_professors_analysis(df, tech_to_label):
    """Análise dos professores"""
    st.markdown("## 👨‍🏫 Avaliação dos Professores")
    
    # Buscar colunas de características dos professores
    prof_data = {}
    
    # Padrões de busca
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
            if 'PROFESSORES' in col:
                if any(keyword.lower() in col.lower() for keyword in keywords):
                    valores = pd.to_numeric(df[col], errors='coerce')
                    media = valores.mean()
                    if not pd.isna(media) and media > 0:
                        prof_data[label] = media
                    break
    
    if prof_data:
        st.subheader("Características Empreendedoras")
        fig = create_bar_chart(prof_data, "Avaliação Média dos Professores", '#9b59b6')
        st.plotly_chart(fig, use_container_width=True)
        
        media_geral = np.mean(list(prof_data.values()))
        st.metric("Média Geral", f"{media_geral:.2f}")
    else:
        st.warning("⚠️ Dados não encontrados. Verifique se as colunas de avaliação dos professores estão no arquivo.")
        with st.expander("Debug: Colunas que contêm 'PROFESSORES'"):
            prof_cols = [col for col in df.columns if 'PROFESSOR' in col.upper()]
            if prof_cols:
                st.write(prof_cols[:5])
            else:
                st.write("Nenhuma coluna encontrada")

def show_infrastructure_analysis(df, tech_to_label):
    """Análise de infraestrutura"""
    st.markdown("## 🏢 Infraestrutura")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Infraestrutura Geral")
        
        # Buscar colunas de infraestrutura
        infra_data = {}
        infra_keywords = {
            'Biblioteca': 'biblioteca',
            'Labs Informática': ['laboratórios de informática', 'labs informática'],
            'Labs Pesquisa': ['laboratórios de pesquisa', 'experimentação'],
            'Espaços Convivência': ['espaços', 'convivência'],
            'Restaurante': 'restaurante'
        }
        
        for label, keywords in infra_keywords.items():
            if isinstance(keywords, str):
                keywords = [keywords]
            
            for col in df.columns:
                if 'infraestrutura' in col.lower() or 'Como você avalia a qualidade da infraestrutura' in col:
                    if any(kw.lower() in col.lower() for kw in keywords):
                        valores = pd.to_numeric(df[col], errors='coerce')
                        media = valores.mean()
                        if not pd.isna(media) and media > 0:
                            infra_data[label] = media
                        break
        
        if infra_data:
            fig = create_bar_chart(infra_data, "Avaliação da Infraestrutura", '#16a085')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Dados não encontrados")
    
    with col2:
        st.subheader("Acessibilidade (PCD)")
        
        # Buscar colunas de acessibilidade
        acess_data = {}
        acess_keywords = {
            'Calçadas': 'calçadas',
            'Vias Acesso': ['vias de acesso', 'edificações'],
            'Rotas Internas': 'rota acessível',
            'Sanitários': 'sanitários',
            'Elevadores': ['elevadores', 'rampas']
        }
        
        for label, keywords in acess_keywords.items():
            if isinstance(keywords, str):
                keywords = [keywords]
            
            for col in df.columns:
                if 'deficiência' in col.lower() or 'acessibilidade' in col.lower():
                    if any(kw.lower() in col.lower() for kw in keywords):
                        valores = pd.to_numeric(df[col], errors='coerce')
                        media = valores.mean()
                        if not pd.isna(media) and media > 0:
                            acess_data[label] = media
                        break
        
        if acess_data:
            fig = create_bar_chart(acess_data, "Avaliação de Acessibilidade", '#27ae60')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Dados não encontrados")

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
            github_paths = [
                "JOAO-cefet-main/data/dados_cefet.xlsx",
                "JOAO-cefet-main/Dados CEFET_MG  Sem dados pessoais 2  Copia.xlsx",
                "data/dados_cefet.xlsx"
            ]
            
            github_path = st.selectbox(
                "Selecione o arquivo",
                github_paths,
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
    
    # Tentar carregar do GitHub
    if use_github and not uploaded_file:
        github_file = Path(github_path)
        if github_file.exists():
            with st.spinner('📥 Carregando arquivo do GitHub...'):
                df = load_excel(str(github_file))
                source_info = f"📦 Arquivo: {github_path}"
        else:
            st.error(f"❌ Arquivo não encontrado: {github_path}")
            st.info("💡 Tente outro arquivo ou faça upload manual.")
    
    # Se upload manual
    if uploaded_file:
        with st.spinner('📥 Processando upload...'):
            df = load_excel(uploaded_file)
            source_info = f"📤 Upload: {uploaded_file.name}"
    
    if df is not None:
        st.success(source_info)
        
        # Aplicar mapeamento
        with st.spinner('🔄 Aplicando mapeamento de colunas...'):
            df = apply_mapping(df, col_to_tech)
        
        # Processar (SEM remover duplicatas!)
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
