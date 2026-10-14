"""Despacho de energia do estabelecimento - Sprint 4 (Fase 1, solar + bateria).

Funcao pura, sem banco nem HTTP: dado o que os carregadores estao consumindo agora, o que o
inversor solar esta gerando e o estado da bateria, decide de onde vem cada kW, na ordem
**solar -> bateria -> rede**, respeitando o limite contratado com a distribuidora
(`Establishment.power_limit_kw`).

Regras (e o porque de cada uma):
- Solar primeiro: energia gerada no local e a mais barata e a unica 100% renovavel.
- Sobra de solar carrega a bateria (ate a potencia maxima de carga e ate 100% de SoC); o que
  sobrar depois disso e excedente (`solar_surplus_kw` - injetado na rede ou consumido por
  outras cargas do predio; o ChargeGrid-Manager nao controla esse destino).
- Bateria cobre o deficit que o solar nao cobriu, limitada pela potencia maxima de descarga e
  pela energia acima do SoC minimo (`min_soc_pct` protege a vida util da bateria).
- Rede cobre o resto, ate `grid_limit_kw`. Se mesmo assim faltar, o que falta vira
  `unserved_kw` - no fluxo ao vivo isso nao deveria acontecer, porque o controle de demanda
  (`services/demand_control.py`) ja limitou os carregadores ao disponivel antes de eles puxarem.
- A bateria NUNCA carrega pela rede: o objetivo e deslocar energia solar, nao arbitragem.

Perdas: toda a perda de ida-e-volta da bateria e aplicada na carga (`energia armazenada =
potencia de carga x dt x eficiencia`); a descarga entrega o que sai do SoC. Simplificacao
documentada - o total de perdas no ciclo completo fica o mesmo.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_KW = Decimal("0.001")
_ZERO = Decimal("0")
_HUNDRED = Decimal("100")


def _q(value: Decimal) -> Decimal:
    return value.quantize(_KW, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class BatterySpec:
    """Parametros fisicos da bateria - vem do `EnergyAsset` do tipo `battery`."""

    capacity_kwh: Decimal
    max_charge_kw: Decimal
    max_discharge_kw: Decimal
    min_soc_pct: Decimal
    round_trip_efficiency_pct: Decimal

    @property
    def efficiency(self) -> Decimal:
        return self.round_trip_efficiency_pct / _HUNDRED

    @property
    def min_energy_kwh(self) -> Decimal:
        return self.capacity_kwh * self.min_soc_pct / _HUNDRED


def max_discharge_kw(spec: BatterySpec, soc_pct: Decimal, dt_h: Decimal) -> Decimal:
    """Maior potencia que a bateria consegue entregar por `dt_h` sem cair abaixo do SoC
    minimo. Usado tambem pelo controle de demanda para saber quanto a bateria soma ao
    disponivel antes de os carregadores puxarem."""
    if dt_h <= 0:
        return _ZERO
    stored_kwh = spec.capacity_kwh * soc_pct / _HUNDRED
    usable_kwh = max(_ZERO, stored_kwh - spec.min_energy_kwh)
    return _q(min(spec.max_discharge_kw, usable_kwh / dt_h))


def max_charge_kw(spec: BatterySpec, soc_pct: Decimal, dt_h: Decimal) -> Decimal:
    """Maior potencia de carga aceita por `dt_h` sem passar de 100% (ja descontando perda)."""
    if dt_h <= 0 or spec.efficiency <= 0:
        return _ZERO
    stored_kwh = spec.capacity_kwh * soc_pct / _HUNDRED
    room_kwh = max(_ZERO, spec.capacity_kwh - stored_kwh)
    return _q(min(spec.max_charge_kw, room_kwh / (dt_h * spec.efficiency)))


@dataclass(frozen=True)
class DispatchResult:
    load_kw: Decimal
    solar_kw: Decimal
    solar_to_load_kw: Decimal
    battery_to_load_kw: Decimal
    grid_to_load_kw: Decimal
    solar_to_battery_kw: Decimal
    solar_surplus_kw: Decimal
    unserved_kw: Decimal
    soc_before_pct: Decimal | None
    soc_after_pct: Decimal | None

    @property
    def battery_kw(self) -> Decimal:
        """Potencia liquida da bateria com sinal: positivo = descarregando (entregando),
        negativo = carregando. Convencao igual a dos inversores hibridos no SEMS+."""
        return self.battery_to_load_kw - self.solar_to_battery_kw

    @property
    def renewable_kw(self) -> Decimal:
        """Parcela da carga atendida por fonte renovavel local. A bateria so carrega com
        solar (nunca pela rede), entao o que sai dela tambem e renovavel."""
        return self.solar_to_load_kw + self.battery_to_load_kw


def dispatch(
    load_kw: Decimal,
    solar_kw: Decimal,
    battery: BatterySpec | None,
    soc_pct: Decimal | None,
    grid_limit_kw: Decimal | None,
    dt_h: Decimal,
) -> DispatchResult:
    """Decide de onde vem cada kW da carga dos carregadores.

    `battery=None` (estabelecimento sem bateria) e `solar_kw=0` (sem inversor, ou noite)
    sao casos validos. `grid_limit_kw=None` significa rede sem limite - usado so pelo
    cenario A e pelo backfill historico, onde a carga ja aconteceu e precisa ser coberta.
    """
    load_kw = max(_ZERO, load_kw)
    solar_kw = max(_ZERO, solar_kw)

    solar_to_load = min(solar_kw, load_kw)
    deficit = load_kw - solar_to_load
    solar_left = solar_kw - solar_to_load

    battery_to_load = _ZERO
    solar_to_battery = _ZERO
    soc_after = soc_pct
    if battery is not None and soc_pct is not None:
        if deficit > 0:
            battery_to_load = min(deficit, max_discharge_kw(battery, soc_pct, dt_h))
            deficit -= battery_to_load
        elif solar_left > 0:
            solar_to_battery = min(solar_left, max_charge_kw(battery, soc_pct, dt_h))
            solar_left -= solar_to_battery

        stored = battery.capacity_kwh * soc_pct / _HUNDRED
        stored += solar_to_battery * dt_h * battery.efficiency
        stored -= battery_to_load * dt_h
        stored = min(battery.capacity_kwh, max(_ZERO, stored))
        soc_after = (stored / battery.capacity_kwh * _HUNDRED).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    if grid_limit_kw is None:
        grid_to_load = deficit
    else:
        grid_to_load = min(deficit, max(_ZERO, grid_limit_kw))
    unserved = deficit - grid_to_load

    return DispatchResult(
        load_kw=_q(load_kw),
        solar_kw=_q(solar_kw),
        solar_to_load_kw=_q(solar_to_load),
        battery_to_load_kw=_q(battery_to_load),
        grid_to_load_kw=_q(grid_to_load),
        solar_to_battery_kw=_q(solar_to_battery),
        solar_surplus_kw=_q(solar_left),
        unserved_kw=_q(unserved),
        soc_before_pct=soc_pct,
        soc_after_pct=soc_after,
    )
