"""Copia dos enums do backend (`backend/app/models/enums.py`) usados pelas tabelas que a IA
le. `ia` e `backend` sao servicos deployados separadamente (Railway), cada um com seu proprio
requirements/venv - nao ha import cruzado entre os dois codebases. Os VALORES abaixo precisam
ficar em sincronia manual com o backend: sao o mesmo tipo ENUM do Postgres."""

import enum


class ChargerStatus(str, enum.Enum):
    livre = "livre"
    carregando = "carregando"
    problema = "problema"
    reservado = "reservado"
    offline = "offline"


class ChargerModel(str, enum.Enum):
    gw7k = "GW7K"
    gw11k = "GW11K"
    gw22k = "GW22K"
