---
title: Painel de Bem-Estar 360
emoji: 🧠
colorFrom: blue
colorTo: green
sdk: gradio
app_file: app.py
pinned: false
---

# 🧠 Painel de Bem-Estar 360°

[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue)](https://huggingface.co/spaces/marcelofschiavo/painel-bem-estar-360)

Um aplicativo de check-in de saúde mental guiado por IA, projetado para facilitar o diálogo entre pacientes e terapeutas, transformando registros diários em dados estruturados.

![Screenshot do Painel de Bem-Estar 360°](https://caminho/para/sua/imagem.png)
*(Substitua este link por um screenshot que você subiu para o GitHub)*

---

## 🎯 O Projeto

O "Painel de Bem-Estar 360°" é uma ferramenta de *journaling* inteligente. O objetivo é criar uma ponte de dados entre as sessões de terapia, ajudando o paciente a registrar seus sentimentos e eventos de forma guiada e fornecendo à psicóloga dados ricos e pré-analisados.

Ele resolve a "síndrome da página em branco" ao usar uma IA (Gemini) para fazer perguntas investigativas com base no sentimento do usuário. Todos os dados são salvos em um Google Sheets, prontos para serem conectados a uma ferramenta de BI (como o Tableau) para análise de tendências.

---

## ✨ Principais Funcionalidades

* **Fluxo de Check-in Guiado:** A interface reage ao input do usuário. Ao definir um sentimento e área da vida (ex: Carreira, nota 2/10), a IA sugere tópicos prováveis ("Conflito com gestor?", "Sobrecarga?").
* **Investigação (Drill-Down):** Ao selecionar um tópico, a IA gera perguntas-chave para aprofundar a reflexão (ex: "Foi na frente de colegas?", "É a primeira vez?").
* **Input Multimodal (Texto e Voz):** O usuário pode digitar seu diário ou usar o microfone. As falas são transcritas usando o modelo **Whisper** da OpenAI.
* **Análise Pós-Registro (Gemini):** Após o envio, o diário é analisado por uma chamada única ao Google Gemini, que gera:
    * **Insight Rápido:** Uma frase empática de validação para o usuário.
    * **Ação Proposta:** Uma pequena ação imediata que o usuário pode tomar.
    * **Sentimento do Texto:** A emoção principal detectada (ex: "Angústia", "Frustração").
    * **Temas Principais:** Uma lista de 2-3 temas (ex: "Luto", "Conflito").
    * **Resumo para Psicóloga:** Um resumo de 2 frases focado nos fatos e sentimentos.
* **Transparência Total:** O usuário vê exatamente quais dados e análises serão salvos e enviados à sua psicóloga.
* **Persistência de Dados:** Todos os 11 pontos de dados (incluindo timestamp e todas as análises da IA) são salvos em uma nova linha no **Google Sheets**.

---

## 🛠️ Arquitetura e Tecnologias

Este projeto foi refatorado para ser um aplicativo **Gradio autônomo**, otimizado para deploy no Hugging Face Spaces e uso eficiente de memória (resolvendo problemas de `CUDA out of memory`).

* **Frontend (UI):** [Gradio](https://www.gradio.app/) (`app.py`)
* **Estrutura de Código:** Lógica de negócios desacoplada em `services/` e modelos de dados em `models/`.
* **IA (Transcrição de Áudio):** [Hugging Face Transformers](https://huggingface.co/docs/transformers/index) (`pipeline`) rodando o modelo `openai/whisper-tiny`.
* **IA (Lógica Generativa):** [Google Gemini](https://ai.google.dev/) (`gemini-flash-latest`) para toda a análise de texto (sugestões, perguntas, insights, ações, resumo e temas).
* **Banco de Dados:** [Google Sheets](https://www.google.com/sheets/about/) (controlado via `gspread`).
* **Deploy:** [Hugging Face Spaces](https://huggingface.co/spaces) (SDK do Gradio).

---

## 🚀 Como Executar Localmente

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/marcelofschiavo/painel-bem-estar-360.git](https://github.com/marcelofschiavo/painel-bem-estar-360.git)
    cd painel-bem-estar-360
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as dependências Python:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Instale o FFmpeg (necessário para o Whisper):**
    * **Linux (Ubuntu/Debian):** `sudo apt-get install ffmpeg`
    * **Mac (Homebrew):** `brew install ffmpeg`
    * **Windows:** Instale via `choco install ffmpeg` ou [baixe o binário](https://ffmpeg.org/download.html) e adicione ao PATH.

5.  **Configure seus Segredos (Environment Variables):**
    * Veja a seção abaixo. Você **precisa** configurar suas chaves de API.

6.  **Rode o aplicativo:**
    ```bash
    python app.py
    ```

---

## 🤫 Configuração de Segredos

O aplicativo precisa de duas chaves secretas para funcionar. Ao rodar localmente, você deve "exportá-las" no seu terminal.

```bash
# 1. Sua chave de API do Google Gemini
export GOOGLE_API_KEY="AIzaSy..."

# 2. O CONTEÚDO do seu arquivo credentials.json do Google Sheets
# (Abra o arquivo, copie tudo e cole como uma string única)
export GOOGLE_SHEETS_CREDENTIALS='{"type": "service_account", "project_id": "...", ...}'