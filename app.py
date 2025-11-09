# app.py (O antigo gradio_app.py)
import gradio as gr

# Importa os serviços que o main.py costumava chamar
from services.ai_service import ai_service
from services.sheets_service import sheets_service
from models.schemas import CheckinContext, DrilldownRequest, CheckinFinal, GeminiResponse
from fastapi import UploadFile # Necessário para o Whisper

"""
Este é o nosso aplicativo principal e único.
Ele contém a UI (Gradio) e chama os 'services' diretamente.
"""

# --- Funções de Lógica (Agora chamando 'services' diretamente) ---

# As funções do Gradio precisam ser 'async' agora
async def fn_get_suggestions(contexto_str, area, sentimento_float):
    """Nível 1: Busca sugestões no AI Service."""
    try:
        # Cria o objeto Pydantic que o serviço espera
        contexto_data = CheckinContext(
            contexto=contexto_str, 
            area=area, 
            sentimento=sentimento_float
        )
        # Chama o serviço diretamente
        response_data = await ai_service.get_suggestions(contexto_data)
        sugestoes = response_data.get("sugestoes", [])
        return gr.update(choices=sugestoes, visible=True)
    except Exception as e:
        print(f"Erro ao chamar ai_service.get_suggestions: {e}")
        return gr.update(visible=False)

async def fn_get_drilldown(topicos_selecionados):
    """Nível 2: Busca perguntas-chave no AI Service."""
    if not topicos_selecionados:
        return gr.update(visible=False), gr.update(visible=False), gr.update(value="", visible=False)
    
    primeiro_topico = topicos_selecionados[0]
    
    try:
        request_data = DrilldownRequest(topico_selecionado=primeiro_topico)
        response_data = await ai_service.get_drilldown_questions(request_data)
        
        perguntas = response_data.get("perguntas", [])
        markdown_text = "### Pontos-chave para detalhar:\n" + "\n".join(f"* {p}" for p in perguntas)
        
        diario_inicial = f"Sobre '{primeiro_topico}': "
        return gr.update(visible=True, value=markdown_text), gr.update(value=diario_inicial, visible=True), gr.update(visible=True)
    except Exception as e:
        print(f"Erro ao chamar ai_service.get_drilldown_questions: {e}")
        return gr.update(visible=False), gr.update(value="", visible=False), gr.update(visible=False)

async def fn_transcribe(audio_filepath, diaro_atual):
    """Nível 3: Envia áudio para o AI Service."""
    if audio_filepath is None:
        return diaro_atual
    try:
        # Para o AI Service funcionar, precisamos simular um UploadFile
        # Esta é a parte mais "chata" da fusão
        class SimulaUploadFile:
            def __init__(self, filepath):
                self.filename = os.path.basename(filepath)
                self.file = open(filepath, 'rb')
            async def read(self):
                return self.file.read()
            def close(self):
                self.file.close()

        audio_file = SimulaUploadFile(audio_filepath)
        response_data = await ai_service.transcribe_audio(audio_file)
        audio_file.close() # Fecha o arquivo
        
        transcricao = response_data.get("transcricao", "")
        novo_texto = f"{diaro_atual}\n{transcricao}".strip()
        return novo_texto
    except Exception as e:
        print(f"Erro ao chamar ai_service.transcribe_audio: {e}")
        return diaro_atual

async def fn_submit_checkin(contexto_str, area, sentimento_float, topicos, diaro_texto):
    """Nível Final: Orquestra os serviços de IA e Sheets."""
    try:
        checkin_data = CheckinFinal(
            contexto=contexto_str,
            area=area,
            sentimento=sentimento_float,
            topicos_selecionados=topicos,
            diario_texto=diaro_texto
        )
        
        # 1. Roda toda a análise de IA
        gemini_data = await ai_service.process_final_checkin(checkin_data)
        
        # 2. Salva os dados no Google Sheets
        sheets_service.write_checkin(checkin_data, gemini_data)
        
        # 3. Formata o feedback
        msg = "Seu check-in foi salvo com sucesso!"
        insight = gemini_data.insight
        acao = gemini_data.acao
        sentimento_txt = gemini_data.sentimento_texto
        temas_txt = ", ".join(gemini_data.temas)
        resumo_txt = gemini_data.resumo
            
        feedback = f"""
        ### ✅ {msg}
        
        **Insight Rápido:**
        {insight}
        
        **Uma Pequena Ação para Agora:**
        {acao}
        
        ---
        **Dados de Transparência (enviados à sua psicóloga):**
        * **Sentimento Detectado no Texto:** {sentimento_txt}
        * **Temas Principais:** {temas_txt}
        * **Resumo:** {resumo_txt}
        """
        return gr.update(value=feedback, visible=True)
    
    except Exception as e:
        print(f"Erro no fn_submit_checkin: {e}")
        return gr.update(value=f"Erro ao processar o check-in: {e}", visible=True)

# --- Interface Gráfica (Gradio Blocks) ---
with gr.Blocks(theme=gr.themes.Soft()) as app: 
    
    gr.Markdown("# 🧠 Painel de Bem-Estar 360°")
    gr.Markdown("Faça seu check-in diário. A IA irá te guiar.")

    # Layout simples (base)
    with gr.Row():
        with gr.Column(scale=1):
            in_contexto = gr.Radio(
                ["Pessoal", "Profissional"], 
                label="Qual o contexto?",
                value="Pessoal"
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
            out_perguntas_chave = gr.Markdown(visible=False) 

    with gr.Row():
        in_diario_texto = gr.Textbox(
            lines=5, 
            label="Meu Diário",
            placeholder="Seu diário aparecerá aqui...",
            visible=False 
        )

    with gr.Row():
        in_diario_audio = gr.Audio(
            sources=["microphone"], 
            type="filepath", 
            label="Grave seu diário por voz (Opcional)",
            visible=False 
        )

    btn_submit = gr.Button("Registrar Check-in")
    out_feedback = gr.Markdown(visible=False)

    # --- Conexões (Event Listeners) ---
    # (As funções agora são 'async' mas o Gradio lida com isso)
    in_sentimento.release(
        fn=fn_get_suggestions,
        inputs=[in_contexto, in_area, in_sentimento],
        outputs=[out_sugestoes]
    )

    out_sugestoes.select(
        fn=fn_get_drilldown,
        inputs=[out_sugestoes],
        outputs=[
            out_perguntas_chave, 
            in_diario_texto,    
            in_diario_audio
        ]
    )
    
    in_diario_audio.stop_recording(
        fn=fn_transcribe,
        inputs=[in_diario_audio, in_diario_texto],
        outputs=[in_diario_texto]
    )

    btn_submit.click(
        fn=fn_submit_checkin,
        inputs=[in_contexto, in_area, in_sentimento, out_sugestoes, in_diario_texto],
        outputs=[out_feedback]
    )

# --- Lançar a Aplicação ---
if __name__ == "__main__":
    app.launch(debug=True)