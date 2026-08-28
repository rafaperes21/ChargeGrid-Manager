"""Capacidade real (aproximada) de bateria dos modelos de veiculo ja cadastrados na base de
demonstracao - especificacao publica de cada fabricante (mercado brasileiro quando
aplicavel), nao inventada. So usada pra estimar % de bateria e tempo restante de carga na
sessao do cliente.

M5-portal-cliente.md documentava "% estimado da bateria, tempo estimado restante" como
bloqueado por "sem cadastro de modelo de veiculo" - o campo `User.vehicle_model` (texto
livre) ja existia, so faltava esse mapeamento pra capacidade em kWh.

Estimativa, nunca fato: assume que o veiculo comecou a sessao vazio (0%) - unico jeito de
estimar sem telemetria real da bateria do carro (o sistema nao tem acesso a isso, so a
energia que o carregador entregou). Por isso a UI sempre rotula como "estimado"."""

from decimal import ROUND_HALF_UP, Decimal

# kWh utilizavel aproximado por modelo - especificacao publica do fabricante. Varia por
# versao/ano/mercado; e uma estimativa de referencia, nao o valor exato do carro do cliente.
VEHICLE_BATTERY_KWH: dict[str, Decimal] = {
    "BYD Dolphin": Decimal("44.900"),
    "BYD Dolphin Mini": Decimal("30.008"),
    "GWM Ora 03": Decimal("48.000"),
    "Volvo EX30": Decimal("51.000"),
    "Renault Kwid E-Tech": Decimal("26.800"),
}

_MAX_BATTERY_PCT = Decimal("100")


def estimate_battery_status(
    *,
    vehicle_model: str | None,
    energy_kwh: Decimal | None,
    current_power_kw: Decimal | None,
) -> tuple[Decimal | None, int | None]:
    """Devolve (percentual estimado de bateria, minutos estimados restantes).

    `(None, None)` quando o modelo nao esta no catalogo (nao da pra estimar sem capacidade
    conhecida) - nunca um numero generico/medio inventado. Minutos restantes tambem fica
    `None` sem potencia atual > 0 (carregador ainda nao esta entregando energia de verdade,
    ou a sessao ja nao esta ativa)."""
    capacity = VEHICLE_BATTERY_KWH.get(vehicle_model) if vehicle_model else None
    if capacity is None or capacity <= 0:
        return None, None

    delivered = energy_kwh or Decimal("0.000")
    battery_pct = min(_MAX_BATTERY_PCT, (delivered / capacity) * Decimal("100")).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )

    remaining_minutes = None
    if current_power_kw and current_power_kw > 0:
        remaining_kwh = max(Decimal("0.000"), capacity - delivered)
        remaining_minutes = int(
            (remaining_kwh / current_power_kw * 60).to_integral_value(rounding=ROUND_HALF_UP)
        )

    return battery_pct, remaining_minutes
