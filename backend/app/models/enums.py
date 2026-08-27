import enum


class UserRole(str, enum.Enum):
    owner = "owner"
    customer = "customer"


class ChargerModel(str, enum.Enum):
    gw7k = "GW7K"
    gw11k = "GW11K"
    gw22k = "GW22K"


class ChargerStatus(str, enum.Enum):
    livre = "livre"
    carregando = "carregando"
    problema = "problema"
    reservado = "reservado"
    offline = "offline"


class PlanKind(str, enum.Enum):
    avulso = "avulso"
    mensal = "mensal"
    trimestral = "trimestral"


class ChargingSessionStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    finished = "finished"
    error = "error"
