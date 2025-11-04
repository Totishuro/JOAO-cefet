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
    /* Mobile First */
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
    
    /* Tablet e Desktop */
    @media (min-width: 768px) {
        .main-header {
            font-size: 2.5rem;
        }
        .section-header {
            font-size: 1.8rem;
        }
    }
    
    /* Melhorias de acessibilidade */
    .stButton>button {
        width: 100%;
    }
    
    /* Tabelas responsivas */
    .dataframe {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# ===== Funções de Mapeamento =====
def load_column_mapping():
    """Carrega o mapeamento de colunas do CSV"""
    csv_path = Path("columns_classification.csv")
    
    if csv_path.exists():
        mapping_df = pd.read_csv(csv_path)
        
        # Criar dicionários de mapeamento
        col_to_tech = dict(zip(mapping_df['coluna_original'], mapping_df['nome_tecnico']))
        tech_to_label = dict(zip(mapping_df['nome_tecnico'], mapping_df['rotulo_publico']))
        tech_to_class = dict(zip(mapping_df['nome_tecnico'], mapping_df['classe']))
        
        return col_to_tech, tech_to_label, tech_to_class
    else:
        st.warning("⚠️ Arquivo columns_classification.csv não encontrado. Usando nomes originais.")
        return {}, {}, {}

def apply_mapping(df, col_to_tech):
    """Aplica o mapeamento de colunas ao DataFrame"""
    if not col_to_tech:
        return df
    
    # Renomear apenas colunas que existem no mapping
    cols_to_rename = {orig: tech for orig, tech in col_to_tech.items() if orig in df.columns}
    return df.rename(columns=cols_to_rename)

# ===== Funções de Processamento =====
@st.cache_data(show_spinner=False)
def load_excel(file):
    """Carrega arquivo Excel"""
    return pd.read_excel(file, engine='openpyxl')

def process_data(df):
    """Remove duplicatas e retorna estatísticas"""
    if 'respondent_id' not in df.columns:
        st.error("❌ Coluna 'respondent_id' não encontrada!")
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
    
    # Adaptar layout para mobile
    if st.session_state.get('mobile_view', False):
        cols = st.columns(2)
    else:
        cols = st.columns(4)
    
    with cols[0]:
        st.metric("📝 Total Respondentes", f"{stats['total_unicos']:,}")
    
    with cols[1]:
        # Buscar coluna de idade
        idade_col = 'idade' if 'idade' in df.columns else None
        if idade_col and idade_col in df.columns:
            media_idade = df[idade_col].mean()
            st.metric("👤 Idade Média", f"{media_idade:.1f} anos")
        else:
            st.metric("👤 Idade Média", "N/A")
    
    if len(cols) > 2:
        with cols[2]:
            # Alunos atuais
            voce_col = 'voce_e' if 'voce_e' in df.columns else None
            if voce_col:
                total_alunos = df[voce_col].str.contains('ALUNO', case=False, na=False).sum()
                pct = (total_alunos / stats['total_unicos'] * 100)
                st.metric("🎓 Alunos Atuais", f"{pct:.1f}%")
            else:
                st.metric("🎓 Alunos Atuais", "N/A")
        
        with cols[3]:
            # Fundadores
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
            
            # Tabela detalhada
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
            # Criar faixas etárias
            df_temp = df.copy()
            df_temp['faixa_etaria'] = pd.cut(
                df_temp[idade_col],
                bins=[0, 19, 25, 30, 100],
                labels=['Até 19', '20-25', '26-30', 'Acima de 30']
            )
            faixa_counts = df_temp['faixa_etaria'].value_counts().sort_index()
            st.bar_chart(faixa_counts)
            
            # Estatísticas
            st.metric("Mínima", f"{df[idade_col].min():.0f}")
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
    
    # Top 15 cursos
    curso_counts = df[curso_col].value_counts().head(15)
    
    st.subheader("Top 15 Cursos")
    st.bar_chart(curso_counts)
    
    # Tabela completa
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
            
            # Percentual
            if 'Sim' in fundador_counts.index:
                pct = (fundador_counts['Sim'] / len(df) * 100)
                st.metric("Percentual de Fundadores", f"{pct:.1f}%")
        else:
            st.info("Dados não disponíveis")
    
    # Contribuição para projetos
    st.subheader("Contribuição para Projetos")
    contrib_col = 'contribuiu_crescimento_projetos' if 'contribuiu_crescimento_projetos' in df.columns else None
    if contrib_col:
        contrib_counts = df[contrib_col].value_counts()
        st.bar_chart(contrib_counts)
    else:
        st.info("Dados não disponíveis")

def show_professors_analysis(df, tech_to_label):
    """Análise dos professores"""
    st.markdown('<h2 class="section-header">👨‍🏫 Avaliação dos Professores</h2>', unsafe_allow_html=True)
    
    # Características dos professores
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
            # Converter para numérico e calcular média
            valores = pd.to_numeric(df[col], errors='coerce')
            media = valores.mean()
            if not pd.isna(media):
                prof_data[label] = media
    
    if prof_data:
        st.subheader("Características Empreendedoras")
        st.bar_chart(prof_data)
        
        # Média geral
        media_geral = np.mean(list(prof_data.values()))
        st.metric("Média Geral", f"{media_geral:.2f}")
    else:
        st.info("Dados não disponíveis")
    
    # Experiência e acessibilidade
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Experiência no Mercado")
        exp_col = 'professores_experiencia_mercado' if 'professores_experiencia_mercado' in df.columns else None
        if exp_col:
            exp_counts = df[exp_col].value_counts()
            st.bar_chart(exp_counts)
    
    with col2:
        st.subheader("Acessibilidade para Apoiar")
        acess_col = 'professores_acessiveis_apoiar_iniciativas' if 'professores_acessiveis_apoiar_iniciativas' in df.columns else None
        if acess_col:
            acess_counts = df[acess_col].value_counts()
            st.bar_chart(acess_counts)

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
    
    # Internet
    st.subheader("Qualidade da Internet")
    internet_cols = {
        'internet_disponibilidade_acesso': 'Disponibilidade',
        'internet_velocidade_wifi': 'Velocidade WiFi'
    }
    
    internet_data = {}
    for col, label in internet_cols.items():
        if col in df.columns:
            valores = pd.to_numeric(df[col], errors='coerce')
            media = valores.mean()
            if not pd.isna(media):
                internet_data[label] = media
    
    if internet_data:
        st.bar_chart(internet_data)
    else:
        st.info("Dados não disponíveis")

def show_retention_analysis(df, tech_to_label):
    """Análise de permanência e evasão"""
    st.markdown('<h2 class="section-header">📌 Permanência e Evasão</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Motivos de Permanência")
        perm_col = 'permanencia_motivos' if 'permanencia_motivos' in df.columns else None
        if perm_col and df[perm_col].notna().sum() > 0:
            # Contar menções
            all_motivos = df[perm_col].dropna().str.split(',').explode()
            motivos_counts = all_motivos.value_counts().head(10)
            st.bar_chart(motivos_counts)
        else:
            st.info("Dados não disponíveis")
    
    with col2:
        st.subheader("Motivos de Evasão")
        evasao_col = 'evasao_motivos' if 'evasao_motivos' in df.columns else None
        if evasao_col and df[evasao_col].notna().sum() > 0:
            all_evasao = df[evasao_col].dropna().str.split(',').explode()
            evasao_counts = all_evasao.value_counts().head(10)
            st.bar_chart(evasao_counts)
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
        st.markdown("### 📁 Upload de Dados")
        uploaded_file = st.file_uploader(
            "Selecione o arquivo Excel",
            type=['xlsx', 'xls'],
            help="Arquivo deve conter a coluna 'respondent_id'"
        )
        
        # Detectar visualização mobile
        if st.checkbox("📱 Modo Mobile", value=False):
            st.session_state['mobile_view'] = True
        else:
            st.session_state['mobile_view'] = False
        
        st.markdown("---")
        st.markdown("### ℹ️ Sobre")
        st.info("Dashboard MVP v1.0 - CEFET/MG")
    
    # Processar dados
    if uploaded_file:
        try:
            with st.spinner('📥 Carregando dados...'):
                df = load_excel(uploaded_file)
                
                # Aplicar mapeamento
                df = apply_mapping(df, col_to_tech)
                
                # Processar
                df_processed, stats = process_data(df)
                
                if df_processed is None:
                    return
                
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
                "🏢 Infraestrutura",
                "📌 Permanência"
            ])
            
            with tabs[0]:
                show_kpis(df_processed, stats, tech_to_label)
                with st.expander("🔍 Ver dados brutos"):
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
            
            with tabs[6]:
                show_retention_analysis(df_processed, tech_to_label)
            
            # Download
            st.markdown("---")
            st.markdown("### 💾 Download")
            csv = df_processed.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Baixar dados processados (CSV)",
                csv,
                "dados_cefet_processados.csv",
                "text/csv"
            )
            
        except Exception as e:
            st.error(f"❌ Erro: {str(e)}")
            st.exception(e)
    
    else:
        # Tela inicial
        st.info("👆 Faça upload do arquivo Excel no menu lateral")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📋 Requisitos")
            st.markdown("""
            - Formato Excel (.xlsx)
            - Coluna `respondent_id` obrigatória
            - Arquivo `columns_classification.csv` na raiz
            """)
        
        with col2:
            st.markdown("### 📊 Análises")
            st.markdown("""
            - Perfil dos respondentes
            - Cursos e distribuições
            - Empreendedorismo
            - Avaliação de professores
            - Infraestrutura e acessibilidade
            - Permanência e evasão
            """)

if __name__ == "__main__":
    main()
