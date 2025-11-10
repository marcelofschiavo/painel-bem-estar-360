# services/ai_service.py (Versão Leve)
import os
import json
# from transformers import pipeline # <-- REMOVIDO
import google.generativeai as genai
from models.schemas import CheckinContext, DrilldownRequest, CheckinFinal, GeminiResponse
from fastapi import UploadFile

"""
(Atualizado) 
1. REMOVIDO o Whisper (transformers) para deixar o app mais leve.
"""

class AIService:
    def __init__(self):
        print("Carregando serviços de IA...")
        # self.transcriber = self._load_whisper() # <-- REMOVIDO
        self.transcriber = None # Apenas para garantir que não quebre
        self.gemini_model = self._load_gemini()

    def _load_whisper(self):
        # --- FUNÇÃO REMOVIDA ---
        pass

    def _load_gemini(self):
        # (Sem mudanças)
        try:
            GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
            if not GOOGLE_API_KEY:
                raise ValueError("Variável de ambiente GOOGLE_API_KEY não definida.")
            genai.configure(api_key=GOOGLE_API_KEY)
            generation_config = {"temperature": 0.8, "response_mime_type": "application/json"} 
            model = genai.GenerativeModel(
                model_name="gemini-flash-latest", 
                generation_config=generation_config
            )
            print("Modelo Gemini (flash-latest) configurado com sucesso.")
            return model
        except Exception as e:
            print(f"Erro ao configurar o Gemini: {e}")
            return None

    async def get_suggestions(self, contexto: CheckinContext):
        # (Sem mudanças)
        if not self.gemini_model: raise Exception("Modelo Gemini não carregado.")
        sentimento_desc = "muito positivo"
        if contexto.sentimento <= 2: sentimento_desc = "extremamente negativo"
        elif contexto.sentimento <= 3: sentimento_desc = "negativo"
        prompt = f"""
        Contexto: O usuário está fazendo um check-in de bem-estar.
        - Área da Vida: {contexto.area}
        - Sentimento (1-5): {contexto.sentimento} (indica sentimento {sentimento_desc}).
        Gere 4 "gatilhos prováveis" que podem ter causado esse sentimento.
        Seja muito breve e direto (máximo 10 palavras por item, idealmente 5-7).
        Retorne APENAS um objeto JSON válido no formato:
        {{"sugestoes": ["item curto 1", "item curto 2", "item curto 3", "item curto 4"]}}
        """
        try:
            response = await self.gemini_model.generate_content_async(prompt)
            json_data = json.loads(response.text)
            print(f"Sugestões do Gemini: {json_data.get('sugestoes', [])}")
            return json_data
        except Exception as e:
            print(f"Erro ao chamar Gemini (Nível 1): {e}")
            return {"sugestoes": ["Fale sobre seu dia", "O que mais te marcou hoje?"]}

    async def get_drilldown_questions(self, request: DrilldownRequest):
        # (Sem mudanças)
        if not self.gemini_model: raise Exception("Modelo Gemini não carregado.")
        prompt = f"""
        Contexto: O usuário selecionou o tópico: "{request.topico_selecionado}"
        Gere 4 perguntas-chave curtas para investigar este tópico.
        Para cada pergunta, inclua 2-3 exemplos de respostas curtas entre parênteses.
        Retorne APENAS um objeto JSON válido no formato:
        {{"perguntas": ["Pergunta 1? (ex: sim, não)", "Pergunta 2? (ex: hoje, ontem)", "Pergunta 3? (ex: raiva, tristeza)", "Pergunta 4? (ex: sim, um pouco, não)"]}}
        """
        try:
            response = await self.gemini_model.generate_content_async(prompt)
            json_data = json.loads(response.text)
            print(f"Perguntas-Chave do Gemini: {json_data.get('perguntas', [])}")
            return json_data
        except Exception as e:
            print(f"Erro ao chamar Gemini (Nível 2): {e}")
            return {"perguntas": ["Pode detalhar mais?", "Como você se sentiu?"]}

    async def transcribe_audio(self, file: UploadFile):
        # --- FUNÇÃO ATUALIZADA (Placeholder) ---
        print("A função de transcrição de áudio foi desativada.")
        return {"transcricao": "[Áudio desativado]"}

    async def process_final_checkin(self, checkin_data: CheckinFinal, diario_para_analise: str) -> GeminiResponse:
        # (Sem mudanças)
        if not self.gemini_model: raise Exception("Modelo Gemini não carregado.")
        if not diario_para_analise: 
            return GeminiResponse(
                insight="Seu check-in de sentimento foi salvo.",
                acao="Na próxima vez, tente escrever um diário para receber mais insights."
            )
        prompt_final = f"""
        Contexto Psicológico:
        Um usuário registrou um diário sobre a área "{checkin_data.area}" com nota {checkin_data.sentimento}/5.
        Diário: "{diario_para_analise}" 
        Analise o diário e retorne APENAS um objeto JSON válido com 5 chaves:
        1. "insight": (String) 1 frase empática que valide o sentimento. Não dê conselhos.
        2. "acao": (String) 1 ação concreta e imediata (máx 2 frases) baseada no diário.
        3. "sentimento_texto": (String) Uma única palavra que descreva a emoção principal (ex: "Frustração").
        4. "temas": (Lista de Strings) Uma lista com 2 ou 3 temas principais (ex: ["Conflito", "Prazo"]).
        5. "resumo": (String) Um resumo de 2 frases para uma psicóloga.
        """
        try:
            response = await self.gemini_model.generate_content_async(prompt_final)
            json_data = json.loads(response.text)
            gemini_response = GeminiResponse(**json_data)
            print(f"Análise Final do Gemini: {gemini_response.model_dump_json(indent=2)}")
            return gemini_response
        except Exception as e:
            print(f"Erro ao gerar análise final do Gemini: {e}")
            return GeminiResponse(
                insight="Houve um erro ao analisar seu diário.",
                acao="Tente novamente mais tarde."
            )

    async def get_sugestao_recado_psicologa(self, ultimo_diario_paciente: str, rascunho_psicologa: str):
        # (Sem mudanças)
        if not self.gemini_model:
            raise Exception("Modelo Gemini não carregado.")
        if not ultimo_diario_paciente:
            return {"recado": "O paciente não deixou um diário para este registro."}
        prompt = f"""
        Contexto: Você é uma psicóloga (TCC). Um paciente enviou o seguinte registro de diário:
        ---
        [DIÁRIO DO PACIENTE]:
        {ultimo_diario_paciente}
        ---
        Você começou a escrever um rascunho de resposta (ou o campo está vazio):
        ---
        [SEU RASCUNHO]:
        {rascunho_psicologa}
        ---
        Sua tarefa é usar AMBOS os textos como contexto. Gere uma mensagem empática e completa. 
        Se o rascunho já tiver um bom começo, continue a partir dele. 
        Se o rascunho estiver vazio, apenas responda ao diário do paciente.
        Retorne APENAS um objeto JSON válido no formato:
        {{"recado": "Sua mensagem sugerida (ou completada) aqui."}}
        """
        try:
            response = await self.gemini_model.generate_content_async(prompt)
            json_data = json.loads(response.text)
            print(f"Sugestão de Recado: {json_data.get('recado', 'N/A')}")
            return json_data
        except Exception as e:
            print(f"Erro ao gerar sugestão de recado: {e}")
            return {"recado": f"Erro ao gerar sugestão: {e}"}

# Cria uma instância única
ai_service = AIService()