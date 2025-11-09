# models/schemas.py
from pydantic import BaseModel
from typing import Union, Optional

"""
Este arquivo define a "forma" dos dados que nossa API espera.
(Todas as classes Pydantic que estavam no main.py)
"""

class CheckinContext(BaseModel):
    contexto: Optional[str] = "Pessoal" 
    area: Optional[str] = "Saúde Mental" 
    sentimento: Union[float, int] 

class DrilldownRequest(BaseModel):
    topico_selecionado: str

class CheckinFinal(BaseModel):
    contexto: Optional[str] = "Pessoal"
    area: Optional[str] = "Saúde Mental"
    sentimento: Union[float, int]
    topicos_selecionados: list[str]
    diario_texto: str

class GeminiResponse(BaseModel):
    """Modelo para o JSON que esperamos do Gemini no final"""
    insight: str = "N/A"
    acao: str = "N/A"
    sentimento_texto: str = "N/A"
    temas: list[str] = []
    resumo: str = "N/A"