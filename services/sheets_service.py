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
            
            # Abre o arquivo de planilha inteiro
            spreadsheet = client.open_by_key(SHEET_ID)
            
            # --- MUDANÇA AQUI: Abre as duas abas ---
            self.checkins_sheet = spreadsheet.worksheet("Checkins") # Aba onde salvamos os dados
            self.users_sheet = spreadsheet.worksheet("Usuarios")   # Aba onde lemos os logins
            
            print(f"Google Sheet (Checkins, Usuarios) conectado com sucesso.")
            
        except Exception as e:
            print(f"Erro Crítico ao conectar ao Google Sheets: {e}")
            self.checkins_sheet = None
            self.users_sheet = None

    # --- NOVA FUNÇÃO ---
    def check_user(self, username, password):
        """Verifica se o usuário e senha existem na aba 'Usuarios'."""
        if not self.users_sheet:
            print("Erro: Aba de usuários não conectada.")
            return False
        
        try:
            # Pega todos os valores da planilha de usuários, exceto o cabeçalho
            users_list = self.users_sheet.get_all_values()[1:] 
            
            for row in users_list:
                # Coluna A (row[0]) é username, Coluna B (row[1]) é password
                if row[0] == username and row[1] == password:
                    print(f"Login bem-sucedido para: {username}")
                    return True # Encontrou
            
            print(f"Login falhou para: {username}")
            return False # Não encontrou
        
        except Exception as e:
            print(f"Erro ao ler lista de usuários: {e}")
            return False

    # --- FUNÇÃO ATUALIZADA ---
    def write_checkin(self, checkin: CheckinFinal, gemini_data: GeminiResponse, paciente_id: str):
        """Prepara e escreve a linha final na planilha (com ID do paciente)."""
        if not self.checkins_sheet:
            print("Erro: Aba de check-ins não conectada. Dados não salvos.")
            raise Exception("Aba de check-ins não conectada.")

        try:
            agora = datetime.now().isoformat()
            topicos_str = ", ".join(checkin.topicos_selecionados)
            temas_gemini_str = ", ".join(gemini_data.temas)

            # (A ordem das colunas é a mesma de antes)
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
                paciente_id # Coluna L
            ]
            
            self.checkins_sheet.append_row(nova_linha)
            print(f"Dados de '{paciente_id}' salvos no Google Sheets com sucesso.")
            
        except Exception as e:
            print(f"Erro ao escrever no Google Sheets: {e}")
            raise

# Cria uma instância única
sheets_service = SheetsService()