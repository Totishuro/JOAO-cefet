# 🚀 Guia Rápido de Deploy - Streamlit Cloud

## 📝 Passo a Passo Completo

### 1️⃣ Preparar o Repositório GitHub

#### a) Criar repositório no GitHub
1. Acesse [github.com](https://github.com)
2. Clique em **"New repository"**
3. Nome sugerido: `dashboard-cefet-empreendedorismo`
4. Descrição: `Dashboard interativo para análise de pesquisa sobre empreendedorismo - CEFET/MG`
5. Selecione **"Public"** (necessário para Streamlit Cloud gratuito)
6. Marque **"Add a README file"**
7. Clique em **"Create repository"**

#### b) Adicionar arquivos ao repositório

**Opção 1: Via interface web do GitHub**
1. Clique em **"Add file"** → **"Create new file"**
2. Cole o conteúdo de cada arquivo:
   - `streamlit_app.py`
   - `requirements.txt`
   - `.gitignore`
3. Commit cada arquivo

**Opção 2: Via linha de comando**
```bash
# Clone o repositório
git clone https://github.com/seu-usuario/dashboard-cefet-empreendedorismo.git
cd dashboard-cefet-empreendedorismo

# Adicione os arquivos
# (Cole o conteúdo dos arquivos que forneci)

# Commit e push
git add .
git commit -m "Initial commit: MVP v1.0"
git push origin main
```

---

### 2️⃣ Deploy no Streamlit Cloud

#### a) Acessar Streamlit Cloud
1. Acesse [share.streamlit.io](https://share.streamlit.io)
2. Clique em **"Sign in"**
3. Escolha **"Continue with GitHub"**
4. Autorize o Streamlit a acessar seu GitHub

#### b) Criar novo app
1. Clique em **"New app"**
2. Preencha os campos:
   - **Repository**: `seu-usuario/dashboard-cefet-empreendedorismo`
   - **Branch**: `main`
   - **Main file path**: `streamlit_app.py`
   - **App URL** (opcional): escolha um nome customizado
     - Exemplo: `cefet-dashboard`
     - URL final: `cefet-dashboard.streamlit.app`

#### c) Deploy
1. Clique em **"Deploy!"**
2. Aguarde 2-5 minutos para o deploy completar
3. O app iniciará automaticamente

---

### 3️⃣ Verificar o Deploy

#### Sinais de sucesso ✅
- Status: **"Your app is running"**
- Pode acessar a URL: `https://seu-app.streamlit.app`
- Interface carrega sem erros

#### Possíveis erros ❌

**Erro: Module not found**
- **Causa**: Falta biblioteca no `requirements.txt`
- **Solução**: Adicione a biblioteca faltante e faça commit

**Erro: File not found**
- **Causa**: Nome do arquivo principal errado
- **Solução**: Verifique que o arquivo é `streamlit_app.py` (exatamente)

**Erro: Build failed**
- **Causa**: Erro de sintaxe no código
- **Solução**: Verifique os logs e corrija o erro

---

### 4️⃣ Testar o App

1. **Acesse a URL** do seu app
2. **Faça upload** de um arquivo Excel de teste
3. **Verifique** se todas as abas funcionam
4. **Teste** o download dos dados processados

---

### 5️⃣ Configurações Avançadas (Opcional)

#### Secrets (dados sensíveis)
Se precisar de senhas ou tokens:

1. No Streamlit Cloud, vá em **"Settings"** → **"Secrets"**
2. Adicione em formato TOML:
```toml
[database]
user = "seu_usuario"
password = "sua_senha"
```

3. No código, acesse com:
```python
import streamlit as st
user = st.secrets["database"]["user"]
```

#### Recursos do servidor
- **Free tier**: 1 GB RAM, 1 CPU
- Se precisar mais: upgrade para **Pro** ($20/mês)

---

### 6️⃣ Atualizar o App

Sempre que fizer mudanças no código:

```bash
git add .
git commit -m "Descrição das mudanças"
git push origin main
```

O Streamlit Cloud detecta automaticamente e **redeploya** em ~2 minutos.

---

### 7️⃣ Gerenciar o App

#### Ver logs
1. No dashboard do Streamlit Cloud
2. Clique no seu app
3. Clique em **"Manage app"** → **"Logs"**

#### Reiniciar app
1. **"Manage app"** → **"Reboot app"**

#### Desligar app temporariamente
1. **"Settings"** → **"Sleep app"**

#### Deletar app
1. **"Settings"** → **"Delete app"**

---

## 🔧 Troubleshooting

### App muito lento
- Reduza o tamanho dos dados
- Otimize processamento com `@st.cache_data`
- Considere upgrade para Pro

### Timeout ao carregar dados grandes
Adicione no início do código:
```python
import streamlit as st
st.set_page_config(
    page_title="Dashboard",
    layout="wide"
)
```

### Erro de memória
- Arquivo muito grande
- Reduza dados ou faça pré-processamento
- Upgrade para Pro

---

## 📱 Compartilhar o App

Seu app estará publicamente acessível em:
```
https://seu-app-name.streamlit.app
```

Compartilhe esse link com:
- ✅ Colegas de trabalho
- ✅ Stakeholders
- ✅ Estudantes
- ✅ Qualquer pessoa com internet

---

## 🎉 Pronto!

Seu dashboard está no ar! 🚀

**URL do app**: `https://[seu-app].streamlit.app`

Para dúvidas, consulte a [documentação oficial](https://docs.streamlit.io/streamlit-community-cloud).
