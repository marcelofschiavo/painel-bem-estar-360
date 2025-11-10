# services/ai_service.py
import os
import json
from transformers import pipeline
import google.generativeai as genai
from models.schemas import CheckinContext, DrilldownRequest, CheckinFinal, GeminiResponse
from fastapi import UploadFile

"""
(Atualizado) 
1. Whisper -> Small
2. Prompts de Gemini atualizados (sem contexto, sugestões mais curtas)
"""

class AIService:
    def __init__(self):
        print("Carregando serviços de IA...")
        self.transcriber = self._load_whisper()
        self.gemini_model = self._load_gemini()

    def _load_whisper(self):
        try:
            print("Carregando modelo de transcrição (Whisper)...")
            # --- MUDANÇA AQUI: tiny -> small ---
            model = pipeline("automatic-speech-recognition", model="openai/whisper-small")
            print("Modelo de transcrição (small) carregado.")
            return model
        except Exception as e:
            print(f"Erro ao carregar Whisper: {e}")
            return None

    def _load_gemini(self):
        # (Sem mudanças aqui)
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
        """Gera as sugestões de Nível 1 (sem contexto)."""
        if not self.gemini_model:
            raise Exception("Modelo Gemini não carregado.")
        
        sentimento_desc = "muito positivo"
        if contexto.sentimento <= 3: sentimento_desc = "extremamente negativo"
        elif contexto.sentimento <= 6: sentimento_desc = "negativo/neutro"

        # --- MUDANÇA AQUI: Prompt atualizado ---
        prompt = f"""
        Contexto: O usuário está fazendo um check-in de bem-estar.
        - Área da Vida: {contexto.area}
        - Sentimento (1-10): {contexto.sentimento} (indica sentimento {sentimento_desc}).

        Gere 4 "gatilhos prováveis" que podem ter causado esse sentimento.
        Seja muito breve e direto (máximo 10 palavras por item).
        
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
        Tópico: "{request.topico_selecionado}"
        Gere 4 perguntas-chave curtas para investigar este tópico.
        Retorne APENAS um objeto JSON válido no formato:
        {{"perguntas": ["Pergunta 1?", "Pergunta 2?", "Pergunta 3?", "Pergunta 4?"]}}
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
        # (Sem mudanças)
        if not self.transcriber: raise Exception("Modelo Whisper não carregado.")
        audio_bytes = await file.read()
        try:
            resultado = self.transcriber(audio_bytes)
            transcricao = resultado.get("text", "").strip().strip('"')
            print(f"Transcrição concluída: {transcricao}")
            return {"transcricao": transcricao}
        except Exception as e:
            print(f"Erro na transcrição: {e}")
            return {"transcricao": "[Erro ao processar áudio]"}

    async def process_final_checkin(self, checkin: CheckinFinal) -> GeminiResponse:
        """Roda a análise final do Gemini (sem contexto)."""
        if not self.gemini_model:
            raise Exception("Modelo Gemini não carregado.")
        
        if not checkin.diario_texto:
            return GeminiResponse(
                insight="Seu check-in de sentimento foi salvo.",
                acao="Na próxima vez, tente escrever um diário ou gravar um áudio para receber mais insights."
            )

        # --- MUDANÇA AQUI: Prompt atualizado ---
        prompt_final = f"""
        Contexto Psicológico:
        Um usuário registrou um diário sobre a área "{checkin.area}" com nota {checkin.sentimento}/10.
        Diário: "{checkin.diario_texto}"

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

# Cria uma instância única para ser usada pelo FastAPI
ai_service = AIService()