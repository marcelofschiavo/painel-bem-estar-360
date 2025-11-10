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
                if row and row[0] == username and row[1] == password:
                    print(f"Login bem-sucedido para: {username}")
                    return True # Encontrou
            
            print(f"Login falhou para: {username}")
            return False # Não encontrou
        
        except Exception as e:
            print(f"Erro ao ler lista de usuários: {e}")
            return False
            
    # --- NOVA FUNÇÃO DE CRIAR USUÁRIO ---
    def create_user(self, username, password):
        """Cria um novo usuário se ele não existir."""
        if not self.users_sheet:
            return False, "Erro: Aba de usuários não conectada."
        if not username or not password or len(username) < 3 or len(password) < 3:
            return False, "Usuário e senha devem ter pelo menos 3 caracteres."
        
        try:
            users_list = self.users_sheet.get_all_values()[1:] # Pula cabeçalho
            for row in users_list:
                if row and row[0] == username: # Checa se a linha não está vazia e o usuário existe
                    print(f"Tentativa de criar usuário existente: {username}")
                    return False, "Esse nome de usuário já existe. Tente outro."
            
            # Usuário não existe, vamos criar
            self.users_sheet.append_row([username, password])
            print(f"Novo usuário criado: {username}")
            return True, "Usuário criado com sucesso! Agora você pode fazer o login."
        except Exception as e:
            print(f"Erro ao criar usuário: {e}")
            return False, f"Erro no servidor ao tentar criar usuário: {e}"

    # --- FUNÇÃO ATUALIZADA ---
    def write_checkin(self, checkin: CheckinFinal, gemini_data: GeminiResponse, paciente_id: str):
        """Prepara e escreve a linha final na planilha (sem 'contexto')."""
        if not self.checkins_sheet:
            raise Exception("Aba de check-ins não conectada.")

        try:
            agora = datetime.now().isoformat()
            topicos_str = ", ".join(checkin.topicos_selecionados)
            temas_gemini_str = ", ".join(gemini_data.temas)

            # --- LINHA ATUALIZADA (11 colunas) ---
            nova_linha = [
                agora,                     # A
                checkin.area,              # B
                checkin.sentimento,        # C
                topicos_str,               # D
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

    # --- NOVA FUNÇÃO DE LEITURA ---
    def get_all_checkin_data(self):
        """Busca todos os registros de check-in."""
        if not self.checkins_sheet:
            print("Erro: Aba de check-ins não conectada.")
            return None, []
        try:
            all_data = self.checkins_sheet.get_all_values()
            if not all_data or len(all_data) < 2: # Se não tiver nem cabeçalho e 1 linha
                return None, []
            headers = all_data[0]
            rows = all_data[1:]
            return headers, rows
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
            if len(all_data) < 2: return False # Nada para apagar
            
            # Encontra o índice da coluna de ID (deve ser a 11ª coluna, índice 10)
            id_col_index = 10 
            
            # Procura de baixo para cima
            for i in range(len(all_data) - 1, 0, -1):
                if len(all_data[i]) > id_col_index and all_data[i][id_col_index] == paciente_id:
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