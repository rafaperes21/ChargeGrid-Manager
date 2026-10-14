"""Barreira de seguranca dos assistentes (Sprint 4, M7) - roda ANTES do LLM.

Relato de fogo, fumaca, faisca, choque ou cheiro de queimado recebe resposta FIXA, escrita
aqui, nunca gerada pelo modelo (skill `chatbots-gemini`): um LLM pode "diagnosticar" o
problema ou sugerir que a pessoa mexa no equipamento, e em emergencia eletrica isso e
perigoso. O modelo nem e chamado nesses casos.

A deteccao e por palavra-chave, de proposito ampla: um falso positivo custa uma mensagem de
seguranca a mais; um falso negativo pode custar uma pessoa encostando num carregador
energizado.
"""

import re
import unicodedata

_EMERGENCY_PATTERNS = [
    r"\bfogo\b",
    r"\bincendio",
    r"\bchamas?\b",
    r"\bfumac",
    r"\bfumega",
    r"\bfaisc",
    r"\bcentelh",
    r"\bchoque",
    r"\beletrocut",
    r"\bqueimad",
    r"\bqueimando\b",
    r"\bexplo",
    r"\bcurto[\s-]?circuito",
    r"\bderretend",
]
_EMERGENCY_RE = re.compile("|".join(_EMERGENCY_PATTERNS))

OWNER_EMERGENCY_REPLY = (
    "ATENÇÃO — possível emergência elétrica. Siga estes passos agora:\n"
    "1. Se houver fogo ou fumaça, afaste todas as pessoas e ligue 193 (Corpo de Bombeiros).\n"
    "2. Só desligue o disjuntor do circuito dos carregadores se puder fazer isso sem se "
    "aproximar do equipamento afetado. Não use água em equipamento energizado.\n"
    "3. Não toque no carregador, no cabo nem no veículo conectado.\n"
    "4. Não religue o circuito antes de uma inspeção por eletricista habilitado "
    "(NBR 5410 / NBR 17019) e acione a assistência técnica GoodWe.\n"
    "Esta é uma resposta fixa de segurança — o assistente não faz diagnóstico de emergência."
)

CUSTOMER_EMERGENCY_REPLY = (
    "Atenção, sua segurança vem primeiro:\n"
    "1. Pare de usar o carregador e não toque no equipamento, no cabo nem no carro.\n"
    "2. Afaste-se e avise agora o responsável pelo local.\n"
    "3. Se houver fogo ou fumaça, ligue 193 (Corpo de Bombeiros).\n"
    "Esta é uma resposta automática de segurança."
)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def is_emergency(message: str) -> bool:
    return _EMERGENCY_RE.search(_normalize(message)) is not None
