import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import re

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
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .section-header {
        font-size: 1.3rem;
        color: #2c3e50;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 0.5rem;
    }
    
    @media (min-width: 768px) {
        .main-header {
            font-size: 2.5rem;
        }
        .section-header {
            font-size: 1.8rem;
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
    return df.rename(columns=cols_to_rename)

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
    """Remove duplicatas e retorna estatísticas"""
    if df is None:
        return None, None
        
    if 'respondent_id' not in df.columns:
        st.error("❌ Coluna 'respondent_id' não encontrada!")
        st.info(f"Colunas disponíveis: {', '.join(df.columns[:5])}...")
        return None, None
    
    df_unique = df.drop_duplicates(subset=['respondent_id'], keep='first')
    
    stats = {
        'total_linhas': len(df),
        'total_unicos': len(df_unique),
        'duplicadas': len(df) - len(df_unique)
    }
    
    return df_unique, stats

# ===== Visualizações =====
def show_kpis(df, stats, tech_to_label):
    """Mostra KPIs principais"""
    st.markdown('<h2 class="section-header">📊 Visão Geral</h2>', unsafe_allow_html=True)
    
    cols = st.columns(4)
    
    with cols[0]:
        st.metric("📝 Total Respondentes", f"{stats['total_unicos']:,}")
    
    with cols[1]:
        idade_col = 'idade' if 'idade' in df.columns else None
        if idade_col and idade_col in df.columns:
            media_idade = df[idade_col].mean()
            st.metric("👤 Idade Média", f"{media_idade:.1f} anos")
        else:
            st.metric("👤 Idade Média", "N/A")
    
    with cols[2]:
        voce_col = 'voce_e' if 'voce_e' in df.columns else None
        if voce_col:
            total_alunos = df[voce_col].str.contains('ALUNO', case=False, na=False).sum()
            pct = (total_alunos / stats['total_unicos'] * 100)
            st.metric("🎓 Alunos Atuais", f"{pct:.1f}%")
        else:
            st.metric("🎓 Alunos Atuais", "N/A")
    
    with cols[3]:
        fundador_col = 'socio_ou_fundador' if 'socio_ou_fundador' in df.columns else None
        if fundador_col:
            total_fundadores = (df[fundador_col] == 'Sim').sum()
            pct = (total_fundadores / stats['total_unicos'] * 100)
            st.metric("🚀 Fundadores", f"{pct:.1f}%")
        else:
            st.metric("🚀 Fundadores", "N/A")

def show_profile_analysis(df, tech_to_label):
    """Análise de perfil dos respondentes"""
    st.markdown('<h2 class="section-header">👥 Perfil dos Respondentes</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Distribuição por Perfil")
        voce_col = 'voce_e' if 'voce_e' in df.columns else None
        if voce_col:
            perfil_counts = df[voce_col].value_counts()
            st.bar_chart(perfil_counts)
            
            with st.expander("Ver detalhes"):
                perfil_df = perfil_counts.reset_index()
                perfil_df.columns = ['Perfil', 'Quantidade']
                perfil_df['%'] = (perfil_df['Quantidade'] / perfil_df['Quantidade'].sum() * 100).round(2)
                st.dataframe(perfil_df, use_container_width=True)
        else:
            st.info("Coluna de perfil não encontrada")
    
    with col2:
        st.subheader("Distribuição por Idade")
        idade_col = 'idade' if 'idade' in df.columns else None
        if idade_col:
            df_temp = df.copy()
            df_temp['faixa_etaria'] = pd.cut(
                df_temp[idade_col],
                bins=[0, 19, 25, 30, 100],
                labels=['Até 19', '20-25', '26-30', 'Acima de 30']
            )
            faixa_counts = df_temp['faixa_etaria'].value_counts().sort_index()
            st.bar_chart(faixa_counts)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Mínima", f"{df[idade_col].min():.0f}")
            with col_b:
                st.metric("Máxima", f"{df[idade_col].max():.0f}")
        else:
            st.info("Coluna de idade não encontrada")

def show_courses_analysis(df, tech_to_label):
    """Análise de cursos"""
    st.markdown('<h2 class="section-header">🎓 Análise de Cursos</h2>', unsafe_allow_html=True)
    
    curso_col = 'curso_graduacao' if 'curso_graduacao' in df.columns else None
    
    if not curso_col:
        st.info("Coluna de curso não encontrada")
        return
    
    curso_counts = df[curso_col].value_counts().head(15)
    
    st.subheader("Top 15 Cursos")
    st.bar_chart(curso_counts)
    
    with st.expander("Ver todos os cursos"):
        all_courses = df[curso_col].value_counts().reset_index()
        all_courses.columns = ['Curso', 'Quantidade']
        all_courses['%'] = (all_courses['Quantidade'] / len(df) * 100).round(2)
        st.dataframe(all_courses, use_container_width=True)

def show_entrepreneurship_analysis(df, tech_to_label):
    """Análise de empreendedorismo"""
    st.markdown('<h2 class="section-header">🚀 Empreendedorismo</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Conceitos de Empreendedorismo")
        conceitos = {
            'conceito_empreendedorismo_abrir_negocio': 'Abrir negócio',
            'conceito_empreendedorismo_impacto_social': 'Impacto social',
            'conceito_empreendedorismo_melhorar_ambiente': 'Melhorar ambiente'
        }
        
        conceito_data = {}
        for col, label in conceitos.items():
            if col in df.columns:
                count = df[col].notna().sum()
                conceito_data[label] = count
        
        if conceito_data:
            st.bar_chart(conceito_data)
    
    with col2:
        st.subheader("Fundadores/Sócios")
        fundador_col = 'socio_ou_fundador' if 'socio_ou_fundador' in df.columns else None
        if fundador_col:
            fundador_counts = df[fundador_col].value_counts()
            st.bar_chart(fundador_counts)
            
            if 'Sim' in fundador_counts.index:
                pct = (fundador_counts['Sim'] / len(df) * 100)
                st.metric("Percentual de Fundadores", f"{pct:.1f}%")
        else:
            st.info("Dados não disponíveis")

def show_professors_analysis(df, tech_to_label):
    """Análise dos professores"""
    st.markdown('<h2 class="section-header">👨‍🏫 Avaliação dos Professores</h2>', unsafe_allow_html=True)
    
    prof_cols = {
        'professores_inconformismo_transformacao': 'Inconformismo',
        'professores_visao_oportunidades': 'Visão',
        'professores_pensamento_inovador_criativo': 'Inovação',
        'professores_coragem_riscos': 'Coragem',
        'professores_curiosidade': 'Curiosidade',
        'professores_comunicacao_sociabilidade': 'Comunicação',
        'professores_planejamento_atividades': 'Planejamento',
        'professores_apoio_iniciativas': 'Apoio'
    }
    
    prof_data = {}
    for col, label in prof_cols.items():
        if col in df.columns:
            valores = pd.to_numeric(df[col], errors='coerce')
            media = valores.mean()
            if not pd.isna(media):
                prof_data[label] = media
    
    if prof_data:
        st.subheader("Características Empreendedoras")
        st.bar_chart(prof_data)
        
        media_geral = np.mean(list(prof_data.values()))
        st.metric("Média Geral", f"{media_geral:.2f}")
    else:
        st.info("Dados não disponíveis")

def show_infrastructure_analysis(df, tech_to_label):
    """Análise de infraestrutura"""
    st.markdown('<h2 class="section-header">🏢 Infraestrutura</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Infraestrutura Geral")
        infra_cols = {
            'infraestrutura_biblioteca': 'Biblioteca',
            'infraestrutura_labs_informatica': 'Labs Informática',
            'infraestrutura_labs_pesquisa_exper': 'Labs Pesquisa',
            'infraestrutura_espacos_convivencia': 'Espaços Convivência',
            'infraestrutura_restaurante': 'Restaurante'
        }
        
        infra_data = {}
        for col, label in infra_cols.items():
            if col in df.columns:
                valores = pd.to_numeric(df[col], errors='coerce')
                media = valores.mean()
                if not pd.isna(media):
                    infra_data[label] = media
        
        if infra_data:
            st.bar_chart(infra_data)
        else:
            st.info("Dados não disponíveis")
    
    with col2:
        st.subheader("Acessibilidade (PCD)")
        acess_cols = {
            'acessibilidade_calcadas_vias': 'Calçadas',
            'acessibilidade_vias_acesso_edificacoes': 'Vias Acesso',
            'acessibilidade_rota_interna': 'Rotas Internas',
            'acessibilidade_sanitarios': 'Sanitários',
            'acessibilidade_elevadores_rampas': 'Elevadores'
        }
        
        acess_data = {}
        for col, label in acess_cols.items():
            if col in df.columns:
                valores = pd.to_numeric(df[col], errors='coerce')
                media = valores.mean()
                if not pd.isna(media):
                    acess_data[label] = media
        
        if acess_data:
            st.bar_chart(acess_data)
        else:
            st.info("Dados não disponíveis")

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
            github_path = st.text_input(
                "Caminho no GitHub",
                value="JOAO-cefet-main/Dados CEFET_MG  Sem dados pessoais 2  Copia.xlsx",
                help="Caminho relativo no repositório"
            )
        
        # Opção 2: Upload manual
        st.markdown("**OU**")
        uploaded_file = st.file_uploader(
            "📤 Upload arquivo Excel",
            type=['xlsx', 'xls'],
            help="Arquivo deve conter a coluna 'respondent_id'"
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
                source_info = f"📦 Arquivo do GitHub: {github_path}"
        else:
            st.error(f"❌ Arquivo não encontrado: {github_path}")
            st.info("💡 Verifique se o caminho está correto ou faça upload manual.")
    
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
        
        # Processar
        with st.spinner('⚙️ Removendo duplicatas...'):
            df_processed, stats = process_data(df)
        
        if df_processed is None:
            st.stop()
        
        st.success(f"✅ {stats['total_unicos']:,} respondentes carregados!")
        
        if stats['duplicadas'] > 0:
            st.warning(f"⚠️ {stats['duplicadas']:,} duplicatas removidas")
        
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
        # Tela inicial
        st.info("👆 Configure a fonte de dados no menu lateral")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📋 Opções")
            st.markdown("""
            **Opção 1: Arquivo do GitHub** ✅
            - Marque "Usar arquivo do GitHub"
            - Configure o caminho correto
            
            **Opção 2: Upload Manual** 📤
            - Desmarque "Usar arquivo do GitHub"
            - Faça upload do arquivo .xlsx
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
