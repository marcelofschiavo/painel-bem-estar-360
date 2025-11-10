# models/schemas.py
from pydantic import BaseModel
from typing import Union, Optional

"""
(Atualizado) Remove 'contexto' das classes.
"""

class CheckinContext(BaseModel):
    # contexto: Optional[str] = "Pessoal"  <-- REMOVIDO
    area: Optional[str] = "Emoções: Gestão, sentimentos, equilíbrio." 
    sentimento: Union[float, int] 

class DrilldownRequest(BaseModel):
    topico_selecionado: str

class CheckinFinal(BaseModel):
    # contexto: Optional[str] = "Pessoal" <-- REMOVIDO
    area: Optional[str] = "Emoções: Gestão, sentimentos, equilíbrio."
    sentimento: Union[float, int]
    topicos_selecionados: list[str]
    diario_texto: Optional[str] = ""

class GeminiResponse(BaseModel):
    insight: str = "N/A"
    acao: str = "N/A"
    sentimento_texto: str = "N/A"
    temas: list[str] = []
    resumo: str = "N/A"