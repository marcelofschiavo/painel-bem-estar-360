# services/sheets_service.py
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from models.schemas import CheckinFinal, GeminiResponse
import os  # NOVO
import json # NOVO

"""
Este arquivo lida APENAS com a conexão e escrita no Google Sheets.
VERSÃO ATUALIZADA PARA LER 'SECRETS' DO HUGGING FACE.
"""

# Configurações
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]
# O ID da sua planilha (que já estava no código)
SHEET_ID = "1QhiPEx0z-_vnKgcGhr05ie1KucDjGkPXm4HBb0UKdGw" 

# NOVO: Nome da variável de ambiente que vamos criar no HFS
GOOGLE_SHEETS_CREDS_SECRET_NAME = "GOOGLE_SHEETS_CREDENTIALS"

class SheetsService:
    def __init__(self):
        try:
            # --- LÓGICA DE AUTENTICAÇÃO ATUALIZADA ---
            # 1. Pega o CONTEÚDO do credentials.json a partir do "Secret"
            creds_json_str = os.getenv(GOOGLE_SHEETS_CREDS_SECRET_NAME)
            if not creds_json_str:
                raise ValueError(f"Secret '{GOOGLE_SHEETS_CREDS_SECRET_NAME}' não encontrado.")
            
            # 2. Converte a string JSON em um dicionário
            creds_dict = json.loads(creds_json_str)
            
            # 3. Autoriza usando o dicionário (em vez do arquivo)
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            client = gspread.authorize(creds)
            # --- FIM DA ATUALIZAÇÃO ---
            
            self.sheet = client.open_by_key(SHEET_ID).sheet1
            print(f"Google Sheet (ID: {SHEET_ID[:10]}...) conectado com sucesso.")
            
        except Exception as e:
            print(f"Erro Crítico ao conectar ao Google Sheets: {e}")
            self.sheet = None

    def write_checkin(self, checkin: CheckinFinal, gemini_data: GeminiResponse):
        """Prepara e escreve a linha final na planilha."""
        if not self.sheet:
            print("Erro: Planilha não conectada. Dados não salvos.")
            raise Exception("Planilha não conectada.")

        try:
            agora = datetime.now().isoformat()
            topicos_str = ", ".join(checkin.topicos_selecionados)
            temas_gemini_str = ", ".join(gemini_data.temas)

            nova_linha = [
                agora,
                checkin.contexto,
                checkin.area,
                checkin.sentimento,
                topicos_str,
                checkin.diario_texto,
                gemini_data.insight,
                gemini_data.acao,
                gemini_data.sentimento_texto,
                temas_gemini_str,
                gemini_data.resumo,
            ]
            
            self.sheet.append_row(nova_linha)
            print("Dados salvos no Google Sheets com sucesso.")
            
        except Exception as e:
            print(f"Erro ao escrever no Google Sheets: {e}")
            raise

# Cria uma instância única
sheets_service = SheetsService()