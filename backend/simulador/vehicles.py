"""Catalogo simplificado de veiculos e seus limites de OBC (on-board charger).

O gargalo de uma sessao de carregamento AC e o veiculo, nao o carregador: um carro com OBC
de 7,4 kW num GW22K carrega a 7,4 kW. Ver skill `integracao-sems-simulador`, secao 4.

TODO(datasheet): valores de OBC e capacidade de bateria sao aproximacoes de mercado para fins
de simulacao/demo - confirmar contra ficha tecnica oficial de cada veiculo antes de usar em
material de orcamento entregue ao cliente.
"""

import random
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class VehicleProfile:
    name: str
    obc_max_kw: Decimal
    battery_capacity_kwh: Decimal


VEHICLE_CATALOG: tuple[VehicleProfile, ...] = (
    VehicleProfile("Nissan Leaf", Decimal("6.6"), Decimal("40.0")),
    VehicleProfile("Chevrolet Bolt EV", Decimal("7.4"), Decimal("60.0")),
    VehicleProfile("BYD Dolphin", Decimal("7.0"), Decimal("44.9")),
    VehicleProfile("Renault Kwid E-Tech", Decimal("6.6"), Decimal("26.8")),
    VehicleProfile("BYD Song Plus", Decimal("11.0"), Decimal("71.8")),
    VehicleProfile("Volvo XC40 Recharge", Decimal("11.0"), Decimal("78.0")),
)


def pick_vehicle(rng: random.Random) -> VehicleProfile:
    return rng.choice(VEHICLE_CATALOG)
