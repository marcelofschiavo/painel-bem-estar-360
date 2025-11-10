# models/schemas.py
from pydantic import BaseModel
from typing import Union, Optional

class CheckinContext(BaseModel):
    area: Optional[str] = "Emoções: Gestão, sentimentos, equilíbrio." 
    sentimento: Union[float, int] 

class DrilldownRequest(BaseModel):
    topico_selecionado: str

class CheckinFinal(BaseModel):
    area: Optional[str] = "Emoções: Gestão, sentimentos, equilíbrio."
    sentimento: Union[float, int]
    topicos_selecionados: list[str]
    diario_texto: Optional[str] = ""
    # O campo 'outro_topico' foi removido daqui

class GeminiResponse(BaseModel):
    insight: str = "N/A"
    acao: str = "N/A"
    sentimento_texto: str = "N/A"
    temas: list[str] = []
    resumo: str = "N/A"