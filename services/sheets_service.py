# services/sheets_service.py
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from models.schemas import CheckinFinal, GeminiResponse
import os
import json

# ... (Configurações de SCOPES, SHEET_ID, etc. - Sem mudanças) ...
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file"
]
SHEET_ID = "1QhiPEx0z-_vnKgcGhr05ie1KucDjGkPXm4HBb0UKdGw" 
GOOGLE_SHEETS_CREDS_SECRET_NAME = "GOOGLE_SHEETS_CREDENTIALS"

class SheetsService:
    def __init__(self):
        try:
            creds_json_str = os.getenv(GOOGLE_SHEETS_CREDS_SECRET_NAME)
            if not creds_json_str:
                raise ValueError(f"Secret '{GOOGLE_SHEETS_CREDS_SECRET_NAME}' não encontrado.")
            creds_dict = json.loads(creds_json_str)
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            client = gspread.authorize(creds)
            self.sheet = client.open_by_key(SHEET_ID).sheet1
            print(f"Google Sheet (ID: {SHEET_ID[:10]}...) conectado com sucesso.")
        except Exception as e:
            print(f"Erro Crítico ao conectar ao Google Sheets: {e}")
            self.sheet = None

    # --- FUNÇÃO ATUALIZADA ---
    def write_checkin(self, checkin: CheckinFinal, gemini_data: GeminiResponse, paciente_id: str):
        """Prepara e escreve a linha final na planilha (com ID do paciente)."""
        if not self.sheet:
            print("Erro: Planilha não conectada. Dados não salvos.")
            raise Exception("Planilha não conectada.")

        try:
            agora = datetime.now().isoformat()
            topicos_str = ", ".join(checkin.topicos_selecionados)
            temas_gemini_str = ", ".join(gemini_data.temas)

            # --- LINHA ATUALIZADA (12 COLUNAS) ---
            nova_linha = [
                agora,                     # A
                checkin.contexto,          # B
                checkin.area,              # C
                checkin.sentimento,        # D
                topicos_str,               # E
                checkin.diario_texto,      # F
                gemini_data.insight,       # G
                gemini_data.acao,          # H
                gemini_data.sentimento_texto, # I
                temas_gemini_str,          # J
                gemini_data.resumo,        # K
                paciente_id                # L (NOVO)
            ]
            
            self.sheet.append_row(nova_linha)
            print(f"Dados de '{paciente_id}' salvos no Google Sheets com sucesso.")
            
        except Exception as e:
            print(f"Erro ao escrever no Google Sheets: {e}")
            raise

# Cria uma instância única
sheets_service = SheetsService()