# app.py (com Dropdown de 12 itens e Botão de Descartar)
import gradio as gr
import os
import time
from services.ai_service import ai_service
from services.sheets_service import sheets_service
from models.schemas import CheckinContext, DrilldownRequest, CheckinFinal, GeminiResponse
from fastapi import UploadFile # (Simulação)
import pandas as pd # Importa o pandas para o DataFrame

# --- Lista de Áreas (NOVO) ---
# Esta é a nova lista de 12 itens para o dropdown
areas_de_vida = [
    # Relacionamentos
    "Social: Amizades, convívio, conexões.",
    "Amoroso: Parceria, afeto, intimidade.",
    "Família: Harmonia, diálogo, vínculos.",
    # Profissional
    "Financeiro: Renda, controle, poupança.",
    "Realização: Propósito, satisfação, reconhecimento.",
    "Acadêmica: Estudo, aprendizado, evolução.",
    # Qualidade de vida
    "Hobbies: Prazer, diversão, lazer.",
    "Espiritualidade: Conexão, paz, propósito.",
    "Plenitude: Gratidão, felicidade, contentamento.",
    # Pessoal
    "Emoções: Gestão, sentimentos, equilíbrio.",
    "Cognitiva: Foco, memória, clareza.",
    "Física: Energia, saúde, disposição."
]

# --- Funções de Lógica ---

def fn_login(username, password):
    # (Sem mudanças)
    if not username or not password:
        return None, gr.update(visible=False), gr.update(value="Usuário ou senha não podem estar em branco.", visible=True), gr.update(), gr.update(visible=False)
    login_valido = sheets_service.check_user(username, password)
    if login_valido:
        return username, gr.update(visible=True), gr.update(value="", visible=False), gr.update(selected=1), gr.update(visible=True)
    else:
        return None, gr.update(visible=False), gr.update(value="Login falhou. Verifique seu usuário e senha.", visible=True), gr.update(), gr.update(visible=False)

async def fn_get_suggestions(contexto_bool, area, sentimento_float):
    # (Sem mudanças)
    try:
        contexto_str = "Profissional" if contexto_bool else "Pessoal"
        contexto_data = CheckinContext(contexto=contexto_str, area=area, sentimento=sentimento_float)
        response_data = await ai_service.get_suggestions(contexto_data)
        sugestoes = response_data.get("sugestoes", [])
        return gr.update(choices=sugestoes, visible=True)
    except Exception as e:
        print(f"Erro ao chamar ai_service.get_suggestions: {e}")
        return gr.update(visible=False)

async def fn_get_drilldown(topicos_selecionados):
    # (Sem mudanças)
    if not topicos_selecionados:
        return gr.update(visible=False), gr.update(label="Meu Diário"), gr.update(value=None)
    primeiro_topico = topicos_selecionados[0]
    try:
        request_data = DrilldownRequest(topico_selecionado=primeiro_topico)
        response_data = await ai_service.get_drilldown_questions(request_data)
        perguntas = response_data.get("perguntas", [])
        markdown_text = "### Pontos-chave para detalhar:\n" + "\n".join(f"* {p}" for p in perguntas)
        return gr.update(visible=True), gr.update(label=f"Sobre: '{primeiro_topico}'"), gr.update(value=markdown_text)
    except Exception as e:
        print(f"Erro ao chamar ai_service.get_drilldown_questions: {e}")
        return gr.update(visible=False), gr.update(label="Meu Diário"), gr.update(value=None)

async def fn_transcribe(audio_filepath, diaro_atual):
    # (Sem alterações)
    if audio_filepath is None: return diaro_atual
    try:
        class SimulaUploadFile:
            def __init__(self, filepath):
                self.filename = os.path.basename(filepath); self.file = open(filepath, 'rb')
            async def read(self): return self.file.read()
            def close(self): self.file.close()
        audio_file = SimulaUploadFile(audio_filepath)
        response_data = await ai_service.transcribe_audio(audio_file)
        audio_file.close() 
        transcricao = response_data.get("transcricao", ""); novo_texto = f"{diaro_atual}\n{transcricao}".strip()
        return novo_texto
    except Exception as e:
        return diaro_atual

# --- FUNÇÃO ATUALIZADA ---
async def fn_submit_checkin(paciente_id_do_state, contexto_bool, area, sentimento_float, topicos, diaro_texto):
    """Nível Final: Orquestra os serviços de IA e Sheets. Agora mostra botão de descartar."""
    
    if not paciente_id_do_state:
        # Mostra feedback de erro, esconde botão de descartar
        return gr.update(value="### ❌ Erro: Usuário não autenticado.", visible=True), gr.update(visible=False)
        
    try:
        contexto_str = "Profissional" if contexto_bool else "Pessoal"
        checkin_data = CheckinFinal(contexto=contexto_str, area=area, sentimento=sentimento_float,
                                    topicos_selecionados=topicos, diario_texto=diaro_texto)
        
        gemini_data = await ai_service.process_final_checkin(checkin_data)
        sheets_service.write_checkin(checkin_data, gemini_data, paciente_id_do_state)
        
        msg = f"Check-in de {paciente_id_do_state} salvo com sucesso!"
        insight = gemini_data.insight
        acao = gemini_data.acao
        
        feedback = f"""
        ### ✅ {msg}
        **Insight Rápido:** {insight}
        **Uma Pequena Ação para Agora:** {acao}
        
        ---
        **Dados de Transparência (enviados à sua psicóloga):**
        * **Sentimento Detectado no Texto:** {gemini_data.sentimento_texto}
        * **Temas Principais:** {", ".join(gemini_data.temas)}
        * **Resumo:** {gemini_data.resumo}
        """
        # Mostra o feedback E o novo botão de descartar
        return gr.update(value=feedback, visible=True), gr.update(visible=True)
    
    except Exception as e:
        print(f"Erro no fn_submit_checkin: {e}")
        return gr.update(value=f"Erro ao processar o check-in: {e}", visible=True), gr.update(visible=False)

# --- FUNÇÃO ATUALIZADA ---
def fn_delete_last_record(paciente_id_do_state):
    """Chamado quando o usuário clica em 'Descartar'."""
    sheets_service.delete_last_record(paciente_id_do_state)
    
    # Esconde o botão e atualiza a mensagem de feedback
    return gr.update(visible=False), gr.update(value="### ✅ Registro descartado com sucesso.", visible=True)

# --- FUNÇÃO REMOVIDA ---
# fn_keep_record() não é mais necessária

def fn_load_history(paciente_id_do_state):
    """Carrega o histórico do Google Sheets para o DataFrame."""
    # (Sem mudanças)
    headers, history = sheets_service.get_history(paciente_id_do_state)
    if not history:
        return gr.update(value=None), gr.update(value="Nenhum histórico encontrado.", visible=True)
    
    col_indices = [
        headers.index('timestamp'), headers.index('area'), 
        headers.index('sentimento'), headers.index('sentimento_texto'), 
        headers.index('temas_gemini'), headers.index('diario_texto')
    ]
    display_headers = [headers[i] for i in col_indices]
    display_data = [[row[i] for i in col_indices] for row in history]
    df = pd.DataFrame(display_data, columns=display_headers)
    
    return gr.update(value=df, visible=True), gr.update(visible=False)


# --- Interface Gráfica (Gradio Blocks) ---
with gr.Blocks(theme=gr.themes.Default()) as app: 
    
    state_user = gr.State(None)
    gr.Markdown("# 🧠 Painel de Bem-Estar 360°")
    
    with gr.Tabs() as tabs:
        
        # --- ABA 1: LOGIN (Padrão) ---
        with gr.Tab("Login", id=0) as login_tab:
            # (Sem mudanças)
            gr.Markdown("Por favor, faça o login para continuar.")
            in_login_username = gr.Textbox(label="Usuário", placeholder="Ex: marcelo")
            in_login_password = gr.Textbox(label="Senha", type="password", placeholder="Ex: senha123")
            btn_login = gr.Button("Entrar")
            out_login_message = gr.Markdown(visible=False, value="", elem_classes=["error"])

        # --- ABA 2: CHECK-IN (Começa Oculta) ---
        with gr.Tab("Check-in", id=1, visible=False) as checkin_tab:
            
            gr.Markdown("Faça seu check-in diário. A IA irá te guiar.")
            with gr.Row():
                with gr.Column(scale=1):
                    in_contexto = gr.Checkbox(label="Check-in Profissional?", info="Deixe desmarcado para Pessoal", value=False)
                    
                    # --- MUDANÇA AQUI: Nova lista de áreas ---
                    in_area = gr.Dropdown(
                        choices=areas_de_vida, # Usa a nova lista definida no topo
                        label="Sobre qual área?", 
                        value=areas_de_vida[9] # Padrão = "Emoções"
                    )
                    
                    in_sentimento = gr.Slider(
                        1, 10, step=1, label="Como você avalia essa área HOJE? (1=Péssimo, 10=Ótimo)", value=5)
                
                with gr.Column(scale=2):
                    out_sugestoes = gr.CheckboxGroup(label="O que aconteceu? (IA Nível 1)", visible=False)

            with gr.Row(visible=False) as components_n3:
                with gr.Column(scale=2):
                    in_diario_texto = gr.Textbox(label="Meu Diário", lines=8, placeholder="Descreva o que aconteceu ou...", visible=True)
                    in_diario_audio = gr.Audio(sources=["microphone"], type="filepath", label="...grave seu diário por voz.", visible=True)
                with gr.Column(scale=1, min_width=200):
                    out_perguntas_chave = gr.Markdown("### Pontos-chave para detalhar:")

            btn_submit = gr.Button("Registrar Check-in")
            out_feedback = gr.Markdown(visible=False)
            
            # --- MUDANÇA AQUI: Botão de Descartar ---
            btn_discard = gr.Button(
                "Prefiro descartar este registro/não enviar para a psicóloga", 
                variant="secondary", # Cinza, menos proeminente
                visible=False
            )

        # --- ABA 3: HISTÓRICO (Sem mudanças) ---
        with gr.Tab("Meu Histórico", id=2, visible=False) as history_tab:
            gr.Markdown("Veja seus registros anteriores. Os mais recentes aparecem primeiro.")
            btn_load_history = gr.Button("Carregar meu histórico")
            out_history_message = gr.Markdown(visible=False)
            out_history_df = gr.DataFrame(label="Seus Registros", visible=False, wrap=True)

    # --- Conexões (Event Listeners) ---
    
    # Conexão de Login (Sem mudanças)
    btn_login.click(
        fn=fn_login,
        inputs=[in_login_username, in_login_password],
        outputs=[state_user, checkin_tab, out_login_message, tabs, history_tab]
    )
    
    # Conexões do Check-in (Sem mudanças)
    in_sentimento.release(
        fn=fn_get_suggestions,
        inputs=[in_contexto, in_area, in_sentimento],
        outputs=[out_sugestoes]
    )
    out_sugestoes.select(
        fn=fn_get_drilldown,
        inputs=[out_sugestoes],
        outputs=[components_n3, in_diario_texto, out_perguntas_chave]
    )
    in_diario_audio.stop_recording(
        fn=fn_transcribe,
        inputs=[in_diario_audio, in_diario_texto],
        outputs=[in_diario_texto]
    )

    # --- MUDANÇA AQUI: Saída do btn_submit ---
    btn_submit.click(
        fn=fn_submit_checkin,
        inputs=[state_user, in_contexto, in_area, in_sentimento, out_sugestoes, in_diario_texto],
        outputs=[out_feedback, btn_discard] # Mostra o feedback E o botão de descartar
    )
    
    # --- MUDANÇA AQUI: Nova conexão do btn_discard ---
    btn_discard.click(
        fn=fn_delete_last_record,
        inputs=[state_user],
        outputs=[btn_discard, out_feedback] # Esconde o botão e atualiza o feedback
    )
    
    # Conexão da Aba de Histórico (Sem mudanças)
    btn_load_history.click(
        fn=fn_load_history,
        inputs=[state_user],
        outputs=[out_history_df, out_history_message]
    )

if __name__ == "__main__":
    app.launch(debug=True)