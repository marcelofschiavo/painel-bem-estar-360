# services/sheets_service.py
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from models.schemas import CheckinFinal, GeminiResponse
import os
import json

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"]
SHEET_ID = "1QhiPEx0z-_vnKgcGhr05ie1KucDjGkPXm4HBb0UKdGw" 
GOOGLE_SHEETS_CREDS_SECRET_NAME = "GOOGLE_SHEETS_CREDENTIALS"

class SheetsService:
    def __init__(self):
        # (Sem mudanças)
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
        # (Sem mudanças)
        if not self.users_sheet: return False
        try:
            users_list = self.users_sheet.get_all_values()[1:] 
            for row in users_list:
                if row and row[0] == username and row[1] == password:
                    return True
            return False
        except Exception as e:
            return False
            
    def create_user(self, username, password):
        # (Sem mudanças)
        if not self.users_sheet:
            return False, "Erro: Aba de usuários não conectada."
        if not username or not password or len(username) < 3 or len(password) < 3:
            return False, "Usuário e senha devem ter pelo menos 3 caracteres."
        try:
            users_list = self.users_sheet.get_all_values()[1:]
            for row in users_list:
                if row and row[0] == username:
                    return False, "Esse nome de usuário já existe. Tente outro."
            self.users_sheet.append_row([username, password])
            return True, "Usuário criado com sucesso! Agora você pode fazer o login."
        except Exception as e:
            return False, f"Erro no servidor ao tentar criar usuário: {e}"

    # --- FUNÇÃO ATUALIZADA ---
    def write_checkin(self, checkin: CheckinFinal, gemini_data: GeminiResponse, paciente_id: str):
        """Prepara e escreve a linha final na planilha (voltamos a 11 colunas)."""
        if not self.checkins_sheet:
            raise Exception("Aba de check-ins não conectada.")

        try:
            agora = datetime.now().isoformat()
            topicos_str = ", ".join(checkin.topicos_selecionados) # O 'outro_topico' estará aqui
            temas_gemini_str = ", ".join(gemini_data.temas)

            # --- MUDANÇA AQUI: Voltamos para 11 colunas ---
            nova_linha = [
                agora,                     # A
                checkin.area,              # B
                checkin.sentimento,        # C
                topicos_str,               # D (Agora inclui o tópico escrito)
                checkin.diario_texto,      # E
                gemini_data.insight,       # F
                gemini_data.acao,          # G
                gemini_data.sentimento_texto, # H
                temas_gemini_str,          # I
                gemini_data.resumo,        # J
                paciente_id                # K
            ]
            
            self.checkins_sheet.append_row(nova_linha)
            print(f"Dados de '{paciente_id}' salvos no Google Sheets com sucesso.")
            
        except Exception as e:
            print(f"Erro ao escrever no Google Sheets: {e}")
            raise

    def get_all_checkin_data(self):
        # (Sem mudanças)
        if not self.checkins_sheet:
            return None, []
        try:
            all_data = self.checkins_sheet.get_all_values()
            if not all_data or len(all_data) < 2:
                return None, []
            headers = all_data[0]
            rows = all_data[1:]
            return headers, rows
        except Exception as e:
            print(f"Erro ao ler o histórico: {e}")
            return None, []

    # --- FUNÇÃO ATUALIZADA ---
    def delete_last_record(self, paciente_id: str):
        """Encontra e apaga a última linha que corresponde ao ID do paciente."""
        if not self.checkins_sheet:
            return False
            
        try:
            all_data = self.checkins_sheet.get_all_values()
            if len(all_data) < 2: return False
            
            # --- MUDANÇA AQUI: ID do paciente agora é a 11ª coluna (índice 10) ---
            id_col_index = 10 
            
            for i in range(len(all_data) - 1, 0, -1):
                if len(all_data[i]) > id_col_index and all_data[i][id_col_index] == paciente_id:
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