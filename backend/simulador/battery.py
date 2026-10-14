"""Bateria simulada - Sprint 4 (Fase 1). Faz o papel do BMS/inversor hibrido GoodWe que, na
planta real, executaria o setpoint de carga/descarga e reportaria o SoC ao SEMS+.

Quem DECIDE quanto carregar/descarregar e o backend (`app/services/energy_dispatch.py`); aqui
so a fisica: aplicar o setpoint vigente durante o tempo que passou e atualizar o SoC, com a
mesma convencao de perdas do despacho (perda inteira na carga), para o SoC reportado bater com
o que o despacho previu.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.services.energy_dispatch import BatterySpec

_HUNDRED = Decimal("100")


@dataclass
class SimulatedBattery:
    spec: BatterySpec
    soc_pct: Decimal
    # positivo = descarregando, negativo = carregando (mesma convencao do SEMS+)
    setpoint_kw: Decimal = Decimal("0")

    def advance(self, dt_h: Decimal) -> Decimal:
        """Aplica o setpoint vigente por `dt_h` horas e devolve o SoC novo (%)."""
        if dt_h <= 0:
            return self.soc_pct
        before = self.spec.capacity_kwh * self.soc_pct / _HUNDRED
        if self.setpoint_kw >= 0:
            # o BMS corta a descarga no SoC minimo (ou onde ja estava, se comecou abaixo)
            floor = min(before, self.spec.min_energy_kwh)
            stored = max(floor, before - self.setpoint_kw * dt_h)
        else:
            stored = min(
                self.spec.capacity_kwh, before + -self.setpoint_kw * dt_h * self.spec.efficiency
            )
        self.soc_pct = (stored / self.spec.capacity_kwh * _HUNDRED).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return self.soc_pct
