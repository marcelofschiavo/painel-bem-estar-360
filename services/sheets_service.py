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
        self.checkins_sheet = None
        self.users_sheet = None
        self.recados_sheet = None # <-- NOVO
        self.psicologas_list = []
        self.all_users_data = [] 
        
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
            self.recados_sheet = spreadsheet.worksheet("Recados") # <-- NOVO
            
            self.all_users_data = self.users_sheet.get_all_values()
            
            if len(self.all_users_data) > 1:
                self.psicologas_list = [row[0] for row in self.all_users_data[1:] if len(row) > 2 and row[2] == "Psicóloga"]
            
            print(f"Google Sheet (Checkins, Usuarios, Recados) conectado. {len(self.psicologas_list)} psicólogas carregadas.")
            
        except Exception as e:
            print(f"Erro Crítico ao conectar ao Google Sheets: {e}")

    def get_psicologas_list_for_signup(self):
        # (Sem mudanças)
        if not self.psicologas_list:
            return ["Nenhuma psicóloga encontrada"]
        return self.psicologas_list

    def get_pacientes_da_psicologa(self, psicologa_username: str):
        # (Sem mudanças)
        if not self.all_users_data:
            return ["Nenhum paciente encontrado"]
        pacientes = []
        try:
            for row in self.all_users_data[1:]:
                if len(row) > 3 and row[2] == "Paciente" and row[3] == psicologa_username:
                    pacientes.append(row[0])
            if not pacientes:
                return ["Nenhum paciente vinculado a você"]
            return pacientes
        except Exception as e:
            print(f"Erro ao buscar pacientes: {e}")
            return [f"Erro ao buscar pacientes: {e}"]

    def check_user(self, username, password):
        # (Sem mudanças)
        if not self.all_users_data:
            return False, None, None
        try:
            users_list = self.all_users_data[1:] 
            for row in users_list:
                if row and len(row) > 3 and row[0] == username and row[1] == password:
                    role = row[2] 
                    psicologa_associada = row[3] if role == "Paciente" else None
                    return True, role, psicologa_associada
            print(f"Login falhou para: {username}")
            return False, None, None
        except Exception as e:
            print(f"Erro ao ler lista de usuários: {e}")
            return False, None, None

    def create_user(self, username, password, psicologa_selecionada):
        # --- MUDANÇA (Request 1): Texto de sucesso ---
        if not self.users_sheet:
            return False, "Erro: Aba de usuários não conectada."
        if not username or not password or len(username) < 3 or len(password) < 3:
            return False, "Usuário e senha devem ter pelo menos 3 caracteres."
        if not psicologa_selecionada or psicologa_selecionada == "Nenhuma psicóloga encontrada":
            return False, "Por favor, selecione uma psicóloga da lista."
        try:
            users_list = self.all_users_data[1:]
            for row in users_list:
                if row and row[0] == username:
                    return False, "Esse nome de usuário já existe. Tente outro."
            novo_usuario = [username, password, "Paciente", psicologa_selecionada]
            self.users_sheet.append_row(novo_usuario)
            self.all_users_data.append(novo_usuario) 
            print(f"Novo usuário 'Paciente' criado: {username}, vinculado a {psicologa_selecionada}")
            
            # --- MUDANÇA (Request 1) ---
            return True, f"Paciente de usuário '{username}' criado com sucesso! Agora você pode fazer o login."
        except Exception as e:
            print(f"Erro ao criar usuário: {e}")
            return False, f"Erro no servidor ao tentar criar usuário: {e}"

    def write_checkin(self, checkin: CheckinFinal, gemini_data: GeminiResponse, paciente_id: str, psicologa_id: str, compartilhado: bool):
        # (Sem mudanças)
        if not self.checkins_sheet:
            raise Exception("Aba de check-ins não conectada.")
        try:
            agora = datetime.now().isoformat()
            topicos_str = ", ".join(checkin.topicos_selecionados)
            temas_gemini_str = ", ".join(gemini_data.temas)
            nova_linha = [
                agora, checkin.area, checkin.sentimento, topicos_str,
                checkin.diario_texto, gemini_data.insight, gemini_data.acao,
                gemini_data.sentimento_texto, temas_gemini_str,
                gemini_data.resumo, paciente_id, psicologa_id, compartilhado
            ]
            self.checkins_sheet.append_row(nova_linha)
            print(f"Dados de '{paciente_id}' (Psic: {psicologa_id}) salvos. Compartilhado: {compartilhado}")
        except Exception as e:
            print(f"Erro ao escrever no Google Sheets: {e}")
            raise

    def get_all_checkin_data(self):
        # (Sem mudanças)
        if not self.checkins_sheet: return None, []
        try:
            all_data = self.checkins_sheet.get_all_values()
            if not all_data or len(all_data) < 2: return None, []
            headers = all_data[0]; rows = all_data[1:]
            return headers, rows
        except Exception as e:
            print(f"Erro ao ler o histórico: {e}"); return None, []

    # --- NOVA FUNÇÃO ---
    def get_ultimo_diario_paciente(self, paciente_id: str):
        """Busca o último diário COMPARTILHADO de um paciente."""
        if not self.checkins_sheet: return None, "Erro: Aba de check-ins não conectada."
        try:
            headers, all_rows = self.get_all_checkin_data()
            if not headers: return None, "Nenhum dado encontrado."
            
            id_col = headers.index('paciente_id')
            share_col = headers.index('compartilhado')
            diario_col = headers.index('diario_texto')
            topicos_col = headers.index('topicos_selecionados')

            # Procura de baixo para cima (mais recentes)
            for row in reversed(all_rows):
                if len(row) > id_col and row[id_col] == paciente_id and str(row[share_col]).upper() == 'TRUE':
                    # Encontrou o último registro compartilhado
                    topicos = row[topicos_col]
                    diario = row[diario_col]
                    # Retorna um diário combinado para a IA
                    return f"Tópicos: {topicos}\n\nDiário: {diario}", f"Último diário (compartilhado) de {paciente_id} carregado."
            
            return None, f"Nenhum diário compartilhado encontrado para {paciente_id}."
        except Exception as e:
            print(f"Erro ao buscar último diário: {e}")
            return None, f"Erro ao buscar diário: {e}"

    # --- NOVA FUNÇÃO ---
    def send_recado(self, psicologa_id, paciente_id, mensagem):
        """Salva um novo recado na aba 'Recados'."""
        if not self.recados_sheet:
            return False, "Erro: Aba de recados não conectada."
        try:
            nova_linha = [
                datetime.now().isoformat(), # timestamp
                psicologa_id,
                paciente_id,
                mensagem
            ]
            self.recados_sheet.append_row(nova_linha)
            print(f"Recado de {psicologa_id} para {paciente_id} salvo.")
            return True, "Recado enviado com sucesso."
        except Exception as e:
            print(f"Erro ao enviar recado: {e}")
            return False, f"Erro ao enviar recado: {e}"

    # --- NOVA FUNÇÃO ---
    def get_recados_paciente(self, paciente_id: str):
        """Busca todos os recados para um paciente."""
        if not self.recados_sheet: return None, []
        try:
            all_data = self.recados_sheet.get_all_values()
            if len(all_data) < 2: return None, []
            
            headers = all_data[0] # timestamp, psicologa_id, paciente_id, mensagem_texto
            recados = [row for row in all_data[1:] if len(row) > 2 and row[2] == paciente_id]
            recados.reverse() # Mais recentes primeiro
            
            return headers, recados[:20] # Retorna os últimos 20
        except Exception as e:
            print(f"Erro ao ler recados: {e}")
            return None, []

    def delete_last_record(self, paciente_id: str):
        # (Sem mudanças)
        if not self.checkins_sheet: return False
        try:
            all_data = self.checkins_sheet.get_all_values()
            if len(all_data) < 2: return False
            id_col_index = 10 
            for i in range(len(all_data) - 1, 0, -1):
                if len(all_data[i]) > id_col_index and all_data[i][id_col_index] == paciente_id:
                    row_to_delete = i + 1
                    self.checkins_sheet.delete_rows(row_to_delete)
                    print(f"Registro da linha {row_to_delete} ({paciente_id}) apagado.")
                    return True
            return False
        except Exception as e:
            print(f"Erro ao apagar o registro: {e}"); return False

# Cria uma instância única
sheets_service = SheetsService()