import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from io import BytesIO

# Configuração da página
st.set_page_config(
    page_title="Dashboard CEFET/MG - Pesquisa Empreendedorismo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .section-header {
        font-size: 1.8rem;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 3px solid #1f77b4;
        padding-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)


def processar_dados(df):
    """Processa e limpa os dados do DataFrame"""
    # Remover duplicatas baseado no respondent_id
    df_unique = df.drop_duplicates(subset=['respondent_id'], keep='first')
    
    # Estatísticas de duplicação
    total_linhas = len(df)
    total_unicos = len(df_unique)
    linhas_duplicadas = total_linhas - total_unicos
    
    return df_unique, {
        'total_linhas': total_linhas,
        'total_unicos': total_unicos,
        'linhas_duplicadas': linhas_duplicadas,
        'pct_duplicacao': (linhas_duplicadas / total_linhas * 100) if total_linhas > 0 else 0
    }


def criar_metricas_gerais(df, stats):
    """Cria as métricas gerais do dashboard"""
    st.markdown('<h2 class="section-header">📊 Visão Geral</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total de Respondentes", f"{stats['total_unicos']:,}")
    
    with col2:
        idade_media = df['IDADE'].mean()
        st.metric("Idade Média", f"{idade_media:.1f} anos")
    
    with col3:
        total_alunos = len(df[df['VOCE É'] == 'SOU ALUNO(A) DE GRADUAÇÃO.'])
        pct_alunos = (total_alunos / stats['total_unicos'] * 100)
        st.metric("Alunos Atuais", f"{pct_alunos:.1f}%", f"{total_alunos:,} alunos")
    
    with col4:
        total_fundadores = len(df[df['Você é sócio(a) ou fundador(a) de alguma empresa?Response'] == 'Sim'])
        pct_fundadores = (total_fundadores / stats['total_unicos'] * 100)
        st.metric("Fundadores/Sócios", f"{pct_fundadores:.1f}%", f"{total_fundadores:,} pessoas")
    
    with col5:
        total_cursos = df['CURSO DE GRADUAÇÃO OF'].nunique()
        st.metric("Cursos Diferentes", f"{total_cursos}")


def criar_analise_perfil(df):
    """Cria análise do perfil dos respondentes"""
    st.markdown('<h2 class="section-header">👥 Perfil dos Respondentes</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de distribuição por perfil
        perfil_counts = df['VOCE É'].value_counts()
        fig_perfil = px.pie(
            values=perfil_counts.values,
            names=perfil_counts.index,
            title='Distribuição por Perfil',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_perfil.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_perfil, use_container_width=True)
    
    with col2:
        # Gráfico de distribuição por faixa etária
        df['Faixa Etária'] = pd.cut(
            df['IDADE'],
            bins=[0, 19, 25, 30, 100],
            labels=['Até 19 anos', '20-25 anos', '26-30 anos', 'Acima de 30 anos']
        )
        faixa_counts = df['Faixa Etária'].value_counts().sort_index()
        fig_idade = px.bar(
            x=faixa_counts.index,
            y=faixa_counts.values,
            title='Distribuição por Faixa Etária',
            labels={'x': 'Faixa Etária', 'y': 'Quantidade'},
            color=faixa_counts.values,
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_idade, use_container_width=True)


def criar_analise_cursos(df):
    """Cria análise de distribuição por cursos"""
    st.markdown('<h2 class="section-header">🎓 Distribuição por Cursos</h2>', unsafe_allow_html=True)
    
    # Top 15 cursos
    curso_counts = df['CURSO DE GRADUAÇÃO OF'].value_counts().head(15)
    
    fig_cursos = px.bar(
        x=curso_counts.values,
        y=curso_counts.index,
        orientation='h',
        title='Top 15 Cursos com Mais Respondentes',
        labels={'x': 'Quantidade de Respondentes', 'y': 'Curso'},
        color=curso_counts.values,
        color_continuous_scale='Viridis'
    )
    fig_cursos.update_layout(height=600, showlegend=False)
    st.plotly_chart(fig_cursos, use_container_width=True)
    
    # Tabela com todos os cursos
    with st.expander("Ver todos os cursos"):
        curso_df = df['CURSO DE GRADUAÇÃO OF'].value_counts().reset_index()
        curso_df.columns = ['Curso', 'Quantidade']
        curso_df['Percentual'] = (curso_df['Quantidade'] / len(df) * 100).round(2)
        st.dataframe(curso_df, use_container_width=True)


def criar_analise_empreendedorismo(df):
    """Cria análise sobre empreendedorismo"""
    st.markdown('<h2 class="section-header">🚀 Empreendedorismo</h2>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    # Conceitos de empreendedorismo
    conceitos = {
        'Abrir Negócio': 'O que você entende como empreendedorismo?Empreendedorismo é abrir o próprio negócio (empresa)',
        'Fazer Bem Social': 'O que você entende como empreendedorismo?Empreendedorismo é fazer algo bom para a sociedade',
        'Melhorar Ambiente': 'O que você entende como empreendedorismo?Empreendedorismo é melhorar o ambiente no qual estou inserido'
    }
    
    conceitos_data = []
    for nome, coluna in conceitos.items():
        if coluna in df.columns:
            count = df[coluna].notna().sum()
            conceitos_data.append({'Conceito': nome, 'Quantidade': count})
    
    if conceitos_data:
        conceitos_df = pd.DataFrame(conceitos_data)
        fig_conceitos = px.bar(
            conceitos_df,
            x='Conceito',
            y='Quantidade',
            title='Conceitos de Empreendedorismo',
            color='Quantidade',
            color_continuous_scale='Sunset'
        )
        st.plotly_chart(fig_conceitos, use_container_width=True)
    
    # Participação em projetos
    col1, col2 = st.columns(2)
    
    with col1:
        if '"Considero que, durante a graduação, EU contribui para o crescimento de um ou mais projetos na Instituição de Ensino Superior."Response' in df.columns:
            contribuiu_col = '"Considero que, durante a graduação, EU contribui para o crescimento de um ou mais projetos na Instituição de Ensino Superior."Response'
            contribuiu = df[contribuiu_col].value_counts()
            fig_contribuiu = px.pie(
                values=contribuiu.values,
                names=contribuiu.index,
                title='Contribuição para Projetos na IES'
            )
            st.plotly_chart(fig_contribuiu, use_container_width=True)
    
    with col2:
        if 'Você é sócio(a) ou fundador(a) de alguma empresa?Response' in df.columns:
            fundador = df['Você é sócio(a) ou fundador(a) de alguma empresa?Response'].value_counts()
            fig_fundador = px.pie(
                values=fundador.values,
                names=fundador.index,
                title='Sócios/Fundadores de Empresas',
                color_discrete_sequence=['#2ecc71', '#e74c3c']
            )
            st.plotly_chart(fig_fundador, use_container_width=True)


def criar_analise_professores(df):
    """Cria análise sobre características dos professores"""
    st.markdown('<h2 class="section-header">👨‍🏫 Avaliação dos Professores</h2>', unsafe_allow_html=True)
    
    # Características dos professores
    caracteristicas_prof = {
        'Inconformismo': 'O quanto as seguintes características estão presentes nos(as) PROFESSORES(AS) da minha Instituição de Ensino Superior?Caso não saiba avaliar alguma delas, marcar a opção "Não observado"Inconformismo com a realidade e disposição para transformá-la',
        'Visão Oportunidades': 'O quanto as seguintes características estão presentes nos(as) PROFESSORES(AS) da minha Instituição de Ensino Superior?Caso não saiba avaliar alguma delas, marcar a opção "Não observado"Visão para oportunidades',
        'Pensamento Inovador': 'O quanto as seguintes características estão presentes nos(as) PROFESSORES(AS) da minha Instituição de Ensino Superior?Caso não saiba avaliar alguma delas, marcar a opção "Não observado"Pensamento inovador e criativo',
        'Coragem para Riscos': 'O quanto as seguintes características estão presentes nos(as) PROFESSORES(AS) da minha Instituição de Ensino Superior?Caso não saiba avaliar alguma delas, marcar a opção "Não observado"Coragem para tomar riscos',
        'Curiosidade': 'O quanto as seguintes características estão presentes nos(as) PROFESSORES(AS) da minha Instituição de Ensino Superior?Caso não saiba avaliar alguma delas, marcar a opção "Não observado"Curiosidade',
        'Comunicação': 'O quanto as seguintes características estão presentes nos(as) PROFESSORES(AS) da minha Instituição de Ensino Superior?Caso não saiba avaliar alguma delas, marcar a opção "Não observado"Facilidade de comunicação das ideias e sociabilidade',
        'Planejamento': 'O quanto as seguintes características estão presentes nos(as) PROFESSORES(AS) da minha Instituição de Ensino Superior?Caso não saiba avaliar alguma delas, marcar a opção "Não observado"Planejamento de atividades',
        'Apoio Iniciativas': 'O quanto as seguintes características estão presentes nos(as) PROFESSORES(AS) da minha Instituição de Ensino Superior?Caso não saiba avaliar alguma delas, marcar a opção "Não observado"Apoio a iniciativas empreendedoras'
    }
    
    caracteristicas_data = []
    for nome, coluna in caracteristicas_prof.items():
        if coluna in df.columns:
            # Assumindo valores numéricos (ajustar conforme necessário)
            media = pd.to_numeric(df[coluna], errors='coerce').mean()
            caracteristicas_data.append({'Característica': nome, 'Média': media})
    
    if caracteristicas_data:
        caract_df = pd.DataFrame(caracteristicas_data).sort_values('Média', ascending=True)
        fig_prof = px.bar(
            caract_df,
            x='Média',
            y='Característica',
            orientation='h',
            title='Características Empreendedoras dos Professores (Média)',
            color='Média',
            color_continuous_scale='RdYlGn',
            range_color=[0, 5]
        )
        fig_prof.update_layout(height=500)
        st.plotly_chart(fig_prof, use_container_width=True)
    else:
        st.info("As colunas de características dos professores precisam ser convertidas para valores numéricos.")


def criar_analise_infraestrutura(df):
    """Cria análise sobre infraestrutura"""
    st.markdown('<h2 class="section-header">🏢 Infraestrutura</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Infraestrutura Geral")
        infra_geral = {
            'Biblioteca': 'Como você avalia a qualidade da infraestrutura oferecida pela sua Instituição de Ensino Superior?Caso não saiba avaliar algum deles (seja por desconhecer ou por não ter experienciado ensino presencial), marcar a opção "Não observado"Biblioteca',
            'Lab Informática': 'Como você avalia a qualidade da infraestrutura oferecida pela sua Instituição de Ensino Superior?Caso não saiba avaliar algum deles (seja por desconhecer ou por não ter experienciado ensino presencial), marcar a opção "Não observado"Laboratórios de informática',
            'Lab Pesquisa': 'Como você avalia a qualidade da infraestrutura oferecida pela sua Instituição de Ensino Superior?Caso não saiba avaliar algum deles (seja por desconhecer ou por não ter experienciado ensino presencial), marcar a opção "Não observado"Laboratórios de pesquisa e experimentação',
            'Espaços Convivência': 'Como você avalia a qualidade da infraestrutura oferecida pela sua Instituição de Ensino Superior?Caso não saiba avaliar algum deles (seja por desconhecer ou por não ter experienciado ensino presencial), marcar a opção "Não observado"Espaços abertos ou de convivência'
        }
        
        infra_data = []
        for nome, coluna in infra_geral.items():
            if coluna in df.columns:
                media = pd.to_numeric(df[coluna], errors='coerce').mean()
                infra_data.append({'Item': nome, 'Média': media})
        
        if infra_data:
            infra_df = pd.DataFrame(infra_data)
            fig_infra = px.bar(
                infra_df,
                x='Item',
                y='Média',
                title='Avaliação da Infraestrutura',
                color='Média',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_infra, use_container_width=True)
    
    with col2:
        st.subheader("Acessibilidade (PCD)")
        infra_pcd = {
            'Calçadas': 'Como você avalia a qualidade da infraestrutura destinada à pessoas com deficiência na sua Instituição de Ensino Superior?Caso não saiba avaliar algum deles (seja por desconhecer ou por não ter experienciado ensino presencial), marcar a opção "Não observado"Calçadas e vias de passeios acessíveis',
            'Vias Acesso': 'Como você avalia a qualidade da infraestrutura destinada à pessoas com deficiência na sua Instituição de Ensino Superior?Caso não saiba avaliar algum deles (seja por desconhecer ou por não ter experienciado ensino presencial), marcar a opção "Não observado"Vias de acesso às edificações acessíveis',
            'Sanitários': 'Como você avalia a qualidade da infraestrutura destinada à pessoas com deficiência na sua Instituição de Ensino Superior?Caso não saiba avaliar algum deles (seja por desconhecer ou por não ter experienciado ensino presencial), marcar a opção "Não observado"Sanitários acessíveis',
            'Elevadores': 'Como você avalia a qualidade da infraestrutura destinada à pessoas com deficiência na sua Instituição de Ensino Superior?Caso não saiba avaliar algum deles (seja por desconhecer ou por não ter experienciado ensino presencial), marcar a opção "Não observado"Elevadores e rampas acessíveis'
        }
        
        pcd_data = []
        for nome, coluna in infra_pcd.items():
            if coluna in df.columns:
                media = pd.to_numeric(df[coluna], errors='coerce').mean()
                pcd_data.append({'Item': nome, 'Média': media})
        
        if pcd_data:
            pcd_df = pd.DataFrame(pcd_data)
            fig_pcd = px.bar(
                pcd_df,
                x='Item',
                y='Média',
                title='Avaliação de Acessibilidade',
                color='Média',
                color_continuous_scale='Greens'
            )
            st.plotly_chart(fig_pcd, use_container_width=True)


def main():
    """Função principal do aplicativo"""
    
    # Header
    st.markdown('<h1 class="main-header">📊 Dashboard CEFET/MG - Pesquisa Empreendedorismo</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/200x80/1f77b4/ffffff?text=CEFET-MG", use_container_width=True)
        st.markdown("### 📁 Upload de Dados")
        st.markdown("Faça upload do arquivo Excel com os dados da pesquisa.")
        
        uploaded_file = st.file_uploader(
            "Selecione o arquivo Excel",
            type=['xlsx', 'xls'],
            help="Arquivo deve conter a coluna 'respondent_id' como identificador único"
        )
        
        st.markdown("---")
        st.markdown("### ℹ️ Sobre")
        st.info(
            "Este dashboard analisa os dados da pesquisa sobre empreendedorismo "
            "e educação superior no CEFET/MG. **MVP v1.0**"
        )
    
    # Processamento dos dados
    if uploaded_file is not None:
        try:
            # Mostrar spinner enquanto carrega
            with st.spinner('Carregando e processando dados...'):
                # Ler arquivo Excel
                df = pd.read_excel(uploaded_file)
                
                # Verificar se tem a coluna respondent_id
                if 'respondent_id' not in df.columns:
                    st.error("❌ O arquivo deve conter a coluna 'respondent_id'")
                    return
                
                # Processar dados
                df_processed, stats = processar_dados(df)
                
                st.success(f"✅ Arquivo carregado com sucesso! {stats['total_unicos']:,} respondentes únicos encontrados.")
            
            # Mostrar alerta de duplicação se houver
            if stats['linhas_duplicadas'] > 0:
                st.warning(
                    f"⚠️ Foram encontradas e removidas {stats['linhas_duplicadas']:,} linhas duplicadas "
                    f"({stats['pct_duplicacao']:.2f}% do total)"
                )
            
            # Criar tabs para organizar o conteúdo
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📊 Visão Geral",
                "👥 Perfil",
                "🚀 Empreendedorismo",
                "👨‍🏫 Professores",
                "🏢 Infraestrutura"
            ])
            
            with tab1:
                criar_metricas_gerais(df_processed, stats)
                criar_analise_cursos(df_processed)
            
            with tab2:
                criar_analise_perfil(df_processed)
            
            with tab3:
                criar_analise_empreendedorismo(df_processed)
            
            with tab4:
                criar_analise_professores(df_processed)
            
            with tab5:
                criar_analise_infraestrutura(df_processed)
            
            # Botão para download dos dados processados
            st.markdown("---")
            st.markdown("### 💾 Download dos Dados Processados")
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_processed.to_excel(writer, index=False, sheet_name='Dados_Limpos')
            
            st.download_button(
                label="📥 Baixar dados processados (Excel)",
                data=output.getvalue(),
                file_name="dados_cefet_processados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            st.error(f"❌ Erro ao processar o arquivo: {str(e)}")
            st.exception(e)
    
    else:
        # Tela inicial
        st.info("👆 Faça upload do arquivo Excel no menu lateral para começar a análise.")
        
        st.markdown("### 📋 Requisitos do Arquivo")
        st.markdown("""
        - Formato: Excel (.xlsx ou .xls)
        - Deve conter a coluna **respondent_id** como identificador único
        - Estrutura baseada na pesquisa de empreendedorismo CEFET/MG
        """)
        
        st.markdown("### 📊 Funcionalidades")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **Análises Disponíveis:**
            - ✅ Visão geral com KPIs principais
            - ✅ Perfil dos respondentes
            - ✅ Distribuição por cursos
            - ✅ Análise de empreendedorismo
            """)
        
        with col2:
            st.markdown("""
            **Recursos:**
            - ✅ Remoção automática de duplicatas
            - ✅ Visualizações interativas
            - ✅ Download de dados processados
            - ✅ Interface responsiva
            """)


if __name__ == "__main__":
    main()
