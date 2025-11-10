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
            
            spreadsheet = client.open_by_key(SHEET_ID)
            self.checkins_sheet = spreadsheet.worksheet("Checkins")
            self.users_sheet = spreadsheet.worksheet("Usuarios")
            
            print(f"Google Sheet (Checkins, Usuarios) conectado com sucesso.")
            
        except Exception as e:
            print(f"Erro Crítico ao conectar ao Google Sheets: {e}")
            self.checkins_sheet = None
            self.users_sheet = None

    def check_user(self, username, password):
        # (Sem mudanças nesta função)
        if not self.users_sheet: return False
        try:
            users_list = self.users_sheet.get_all_values()[1:] 
            for row in users_list:
                if row[0] == username and row[1] == password:
                    print(f"Login bem-sucedido para: {username}")
                    return True
            print(f"Login falhou para: {username}")
            return False
        except Exception as e:
            print(f"Erro ao ler lista de usuários: {e}")
            return False

    def write_checkin(self, checkin: CheckinFinal, gemini_data: GeminiResponse, paciente_id: str):
        # (Sem mudanças nesta função)
        if not self.checkins_sheet:
            raise Exception("Aba de check-ins não conectada.")
        try:
            agora = datetime.now().isoformat()
            topicos_str = ", ".join(checkin.topicos_selecionados)
            temas_gemini_str = ", ".join(gemini_data.temas)
            nova_linha = [
                agora, checkin.contexto, checkin.area, checkin.sentimento,
                topicos_str, checkin.diario_texto, gemini_data.insight,
                gemini_data.acao, gemini_data.sentimento_texto,
                temas_gemini_str, gemini_data.resumo, paciente_id
            ]
            self.checkins_sheet.append_row(nova_linha)
            print(f"Dados de '{paciente_id}' salvos no Google Sheets com sucesso.")
        except Exception as e:
            print(f"Erro ao escrever no Google Sheets: {e}")
            raise

    # --- NOVA FUNÇÃO DE LEITURA ---
    def get_history(self, paciente_id: str):
        """Busca os últimos 20 registros de um paciente."""
        if not self.checkins_sheet:
            print("Erro: Aba de check-ins não conectada.")
            return None, []
        
        try:
            all_data = self.checkins_sheet.get_all_values()
            if not all_data:
                return None, []
                
            headers = all_data[0]
            # Filtra os dados pelo ID do paciente (coluna L, índice 11)
            # e pega os últimos 20 registros
            user_history = [row for row in all_data[1:] if row[11] == paciente_id]
            user_history.reverse() # Mostra os mais recentes primeiro
            return headers, user_history[:20]
        
        except Exception as e:
            print(f"Erro ao ler o histórico: {e}")
            return None, []

    # --- NOVA FUNÇÃO DE EXCLUSÃO ---
    def delete_last_record(self, paciente_id: str):
        """Encontra e apaga a última linha que corresponde ao ID do paciente."""
        if not self.checkins_sheet:
            print("Erro: Aba de check-ins não conectada.")
            return False
            
        try:
            all_data = self.checkins_sheet.get_all_values()
            # Procura de baixo para cima
            for i in range(len(all_data) - 1, 0, -1):
                if all_data[i][11] == paciente_id:
                    # Encontrou a linha! (O índice do GSheets é 1-based)
                    row_to_delete = i + 1
                    self.checkins_sheet.delete_rows(row_to_delete)
                    print(f"Registro da linha {row_to_delete} ({paciente_id}) apagado.")
                    return True
            print(f"Nenhum registro encontrado para apagar para {paciente_id}")
            return False
        except Exception as e:
            print(f"Erro ao apagar o registro: {e}")
            return False

# Cria uma instância única
sheets_service = SheetsService()