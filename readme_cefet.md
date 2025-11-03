# 📊 Dashboard CEFET/MG - Pesquisa Empreendedorismo

Dashboard interativo para análise de dados da pesquisa sobre empreendedorismo e educação superior no CEFET/MG.

## 🚀 Funcionalidades (MVP v1.0)

### ✅ Implementado
- **Upload de Dados**: Interface para upload de arquivos Excel
- **Processamento Automático**: Remoção de duplicatas baseado em `respondent_id`
- **Visão Geral**: KPIs principais e métricas gerais
- **Análise de Perfil**: Distribuição por idade, perfil e faixa etária
- **Análise de Cursos**: Top cursos e distribuição completa
- **Análise de Empreendedorismo**: Conceitos, projetos e fundadores
- **Avaliação de Professores**: Características empreendedoras
- **Infraestrutura**: Avaliação geral e acessibilidade
- **Download**: Exportação de dados processados

## 📋 Requisitos

- Python 3.8+
- Arquivo Excel com coluna `respondent_id` obrigatória

## 🛠️ Instalação Local

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/dashboard-cefet.git
cd dashboard-cefet
```

### 2. Crie um ambiente virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Execute o aplicativo
```bash
streamlit run streamlit_app.py
```

O aplicativo abrirá automaticamente no navegador em `http://localhost:8501`

## ☁️ Deploy no Streamlit Cloud

### 1. Conecte seu GitHub
- Acesse [share.streamlit.io](https://share.streamlit.io)
- Faça login com sua conta GitHub
- Clique em "New app"

### 2. Configure o deploy
- **Repository**: Selecione o repositório do projeto
- **Branch**: `main` (ou sua branch principal)
- **Main file path**: `streamlit_app.py`

### 3. Deploy
- Clique em "Deploy!"
- Aguarde alguns minutos para o deploy completar
- Seu app estará disponível em: `https://seu-app.streamlit.app`

## 📁 Estrutura do Projeto

```
dashboard-cefet/
│
├── streamlit_app.py      # Aplicação principal
├── requirements.txt      # Dependências Python
├── README.md            # Documentação
└── .gitignore           # Arquivos ignorados pelo Git
```

## 🎯 Como Usar

1. **Acesse o dashboard** (local ou na nuvem)
2. **Faça upload** do arquivo Excel no menu lateral
3. **Navegue** pelas abas para ver diferentes análises:
   - 📊 Visão Geral
   - 👥 Perfil
   - 🚀 Empreendedorismo
   - 👨‍🏫 Professores
   - 🏢 Infraestrutura
4. **Baixe** os dados processados se necessário

## 📊 Estrutura dos Dados

O arquivo Excel deve conter as seguintes colunas principais:

### Obrigatórias
- `respondent_id`: Identificador único do respondente

### Recomendadas
- `VOCE É`: Perfil do respondente (Aluno/Egresso)
- `IDADE`: Idade do respondente
- `CURSO DE GRADUAÇÃO OF`: Curso do respondente
- `Você é sócio(a) ou fundador(a) de alguma empresa?Response`: Informação sobre empreendedorismo
- Colunas de avaliação de professores
- Colunas de avaliação de infraestrutura

## 🔄 Próximas Versões

### MVP v2.0 (Planejado)
- [ ] Filtros interativos por curso e período
- [ ] Análise temporal (evolução ao longo dos anos)
- [ ] Comparações entre cursos
- [ ] Análise de texto (feedbacks)
- [ ] Exportação de relatórios em PDF
- [ ] Dashboard administrativo

### MVP v3.0 (Planejado)
- [ ] Machine Learning para predições
- [ ] Análise de sentimentos
- [ ] Recomendações baseadas em IA
- [ ] Integração com banco de dados

## 🐛 Problemas Conhecidos

- Colunas com nomes muito longos podem causar problemas de visualização
- Valores não numéricos em campos de avaliação precisam ser convertidos manualmente

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT.

## 👨‍💻 Autor

Desenvolvido para análise de dados da pesquisa CEFET/MG

## 📧 Contato

Para dúvidas ou sugestões, abra uma issue no GitHub.

---

**Versão**: 1.0.0 (MVP)  
**Data**: Novembro 2024
