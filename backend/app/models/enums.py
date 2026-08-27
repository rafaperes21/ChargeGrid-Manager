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


class ReservationStatus(str, enum.Enum):
    pending = "pending"
    fulfilled = "fulfilled"
    cancelled = "cancelled"
    no_show = "no_show"


class PaymentMethod(str, enum.Enum):
    """Declarativo (M3, Tarefa 4.2/4.3): registra a escolha, nunca processa pagamento de
    verdade - sem gateway, sem PCI, sem simulacao de latencia. Fora de escopo do desafio."""

    pix = "pix"
    cartao_credito = "cartao_credito"
    cartao_debito = "cartao_debito"
    carteira_do_app = "carteira_do_app"
