# app.py (com Abas de Login)
import gradio as gr
import os
import time
from services.ai_service import ai_service
from services.sheets_service import sheets_service
from models.schemas import CheckinContext, DrilldownRequest, CheckinFinal, GeminiResponse
from fastapi import UploadFile # (Simulação)

# --- Funções de Lógica ---

# --- NOVA FUNÇÃO DE LOGIN ---
def fn_login(username, password):
    """Verifica o login contra o Google Sheets."""
    if not username or not password:
        return None, gr.update(visible=False), gr.update(value="Usuário ou senha não podem estar em branco.", visible=True), gr.update()
        
    login_valido = sheets_service.check_user(username, password)
    
    if login_valido:
        # Sucesso!
        # 1. Salva o username no 'state'
        # 2. Mostra a aba 'Check-in'
        # 3. Limpa a mensagem de erro
        # 4. Muda o foco do usuário para a Aba de Check-in (ID 1)
        return username, gr.update(visible=True), gr.update(value="", visible=False), gr.update(selected=1)
    else:
        # Falha!
        # 1. Não salva nada no 'state'
        # 2. Mantém a aba 'Check-in' oculta
        # 3. Mostra mensagem de erro
        # 4. Mantém o foco na aba Login
        return None, gr.update(visible=False), gr.update(value="Login falhou. Verifique seu usuário e senha.", visible=True), gr.update()


async def fn_get_suggestions(contexto_bool, area, sentimento_float):
    # (Sem alterações)
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
    # (Sem alterações)
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
    # (Sem alterações - código de simulação omitido para encurtar)
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
    """Nível Final: Orquestra os serviços de IA e Sheets."""
    
    # Validação (o ID agora vem do state, não de um campo de texto)
    if not paciente_id_do_state:
        return gr.update(value="### ❌ Erro: Usuário não autenticado. Por favor, faça o login novamente.", visible=True)
        
    try:
        contexto_str = "Profissional" if contexto_bool else "Pessoal"
        
        checkin_data = CheckinFinal(
            contexto=contexto_str,
            area=area,
            sentimento=sentimento_float,
            topicos_selecionados=topicos,
            diario_texto=diaro_texto
        )
        
        gemini_data = await ai_service.process_final_checkin(checkin_data)
        
        # Passa o ID do state para o serviço de planilhas
        sheets_service.write_checkin(checkin_data, gemini_data, paciente_id_do_state)
        
        msg = f"Check-in de {paciente_id_do_state} salvo com sucesso!"
        insight = gemini_data.insight
        acao = gemini_data.acao
        # ... (resto da formatação do feedback) ...
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
        return gr.update(value=feedback, visible=True)
    
    except Exception as e:
        print(f"Erro no fn_submit_checkin: {e}")
        return gr.update(value=f"Erro ao processar o check-in: {e}", visible=True)

# --- Interface Gráfica (Gradio Blocks) ---
with gr.Blocks(theme=gr.themes.Default()) as app: 
    
    # --- MUDANÇA AQUI: Variável de Memória ---
    state_user = gr.State(None) # Guarda o nome do usuário logado

    gr.Markdown("# 🧠 Painel de Bem-Estar 360°")
    
    # --- MUDANÇA AQUI: Estrutura de Abas ---
    with gr.Tabs() as tabs:
        
        # --- ABA 1: LOGIN (Padrão) ---
        with gr.Tab("Login", id=0) as login_tab:
            gr.Markdown("Por favor, faça o login para continuar.")
            in_login_username = gr.Textbox(label="Usuário", placeholder="Ex: marcelo")
            in_login_password = gr.Textbox(label="Senha", type="password", placeholder="Ex: senha123")
            btn_login = gr.Button("Entrar")
            out_login_message = gr.Markdown(visible=False, value="", elem_classes=["error"]) # Para mensagens de erro

        # --- ABA 2: CHECK-IN (Começa Oculta) ---
        with gr.Tab("Check-in", id=1, visible=False) as checkin_tab:
            
            # --- TODO O CÓDIGO ANTIGO DO APP VAI AQUI DENTRO ---
            gr.Markdown("Faça seu check-in diário. A IA irá te guiar.")
            
            with gr.Row():
                with gr.Column(scale=1):
                    in_contexto = gr.Checkbox(
                        label="Check-in Profissional?", 
                        info="Deixe desmarcado para Pessoal",
                        value=False 
                    )
                    in_area = gr.Dropdown(
                        ["Saúde Mental", "Saúde Física", "Relacionamentos", "Carreira", "Finanças", "Lazer", "Outro"], 
                        label="Sobre qual área?",
                        value="Saúde Mental"
                    )
                    in_sentimento = gr.Slider(
                        1, 10, step=1, label="Como você avalia essa área HOJE? (1=Péssimo, 10=Ótimo)", value=5
                    )
                
                with gr.Column(scale=2):
                    out_sugestoes = gr.CheckboxGroup(
                        label="O que aconteceu? (IA Nível 1)", 
                        visible=False
                    )

            with gr.Row(visible=False) as components_n3:
                with gr.Column(scale=2):
                    in_diario_texto = gr.Textbox(
                        label="Meu Diário", 
                        lines=8, 
                        placeholder="Descreva o que aconteceu ou...",
                        visible=True
                    )
                    in_diario_audio = gr.Audio(
                        sources=["microphone"], 
                        type="filepath", 
                        label="...grave seu diário por voz.",
                        visible=True
                    )
                with gr.Column(scale=1, min_width=200):
                    out_perguntas_chave = gr.Markdown("### Pontos-chave para detalhar:")

            btn_submit = gr.Button("Registrar Check-in")
            out_feedback = gr.Markdown(visible=False)
            # --- FIM DO CÓDIGO ANTIGO ---

    # --- Conexões (Event Listeners) ---
    
    # --- NOVA CONEXÃO DE LOGIN ---
    btn_login.click(
        fn=fn_login,
        inputs=[in_login_username, in_login_password],
        outputs=[
            state_user,         # Salva o usuário na memória (state)
            checkin_tab,        # Mostra a aba de check-in
            out_login_message,  # Mostra a mensagem de erro (se houver)
            tabs                # Muda o foco para a aba de check-in
        ]
    )
    
    # --- Conexões antigas (sem mudanças, exceto no submit) ---
    in_sentimento.release(
        fn=fn_get_suggestions,
        inputs=[in_contexto, in_area, in_sentimento],
        outputs=[out_sugestoes]
    )

    out_sugestoes.select(
        fn=fn_get_drilldown,
        inputs=[out_sugestoes],
        outputs=[
            components_n3,      
            in_diario_texto,    
            out_perguntas_chave 
        ]
    )
    
    in_diario_audio.stop_recording(
        fn=fn_transcribe,
        inputs=[in_diario_audio, in_diario_texto],
        outputs=[in_diario_texto]
    )

    # --- MUDANÇA AQUI: Pega o 'state_user' como input ---
    btn_submit.click(
        fn=fn_submit_checkin,
        inputs=[
            state_user, # Pega o ID da memória (state)
            in_contexto, 
            in_area, 
            in_sentimento, 
            out_sugestoes, 
            in_diario_texto
        ],
        outputs=[out_feedback]
    )

# --- Lançar a Aplicação ---
if __name__ == "__main__":
    app.launch(debug=True)