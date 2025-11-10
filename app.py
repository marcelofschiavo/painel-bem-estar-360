# app.py (com Autenticação)
import gradio as gr
import os
from services.ai_service import ai_service
from services.sheets_service import sheets_service
from models.schemas import CheckinContext, DrilldownRequest, CheckinFinal, GeminiResponse
from fastapi import UploadFile # (Simulação)

API_URL = "http://127.0.0.1:8000" # (Não usado, mas mantido por consistência)

# --- Funções de Lógica ---

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
    # (Sem alterações)
    if audio_filepath is None:
        return diaro_atual
    # ... (código de simulação do UploadFile) ...
    # (Omitido para encurtar)
    return diaro_atual

# --- FUNÇÃO ATUALIZADA ---
async def fn_submit_checkin(paciente_id, contexto_bool, area, sentimento_float, topicos, diaro_texto):
    """Nível Final: Orquestra os serviços de IA e Sheets."""
    
    # Validação simples
    if not paciente_id:
        return gr.update(value="### ❌ Erro: Por favor, insira seu ID de Paciente.", visible=True)
        
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
        
        # --- MUDANÇA AQUI: Passa o ID para o serviço ---
        sheets_service.write_checkin(checkin_data, gemini_data, paciente_id)
        
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
with gr.Blocks(theme=gr.themes.Default()) as app: 
    
    gr.Markdown("# 🧠 Painel de Bem-Estar 360°")
    gr.Markdown("Faça seu check-in diário. A IA irá te guiar.")

    # --- MUDANÇA AQUI: CAMPO DE ID DO PACIENTE ---
    with gr.Row():
        in_paciente_id = gr.Textbox(
            label="Seu Nome ou ID de Paciente", 
            placeholder="Ex: 'Ana Silva' ou 'Paciente_001'",
            max_lines=1
        )

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

    # --- Conexões (Event Listeners) ---

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

    # --- MUDANÇA AQUI: Adiciona 'in_paciente_id' aos inputs ---
    btn_submit.click(
        fn=fn_submit_checkin,
        inputs=[
            in_paciente_id, # NOVO INPUT
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