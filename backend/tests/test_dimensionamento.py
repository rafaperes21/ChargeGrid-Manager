from decimal import Decimal

from app.models.enums import ChargerModel
from app.services import dimensionamento


def test_monofasico_sempre_recomenda_gw7k():
    assert dimensionamento.select_model("monofasico", Decimal("100")) == ChargerModel.gw7k


def test_trifasico_recomenda_gw22k_com_carga_suficiente_para_dois_pontos():
    model = dimensionamento.select_model("trifasico", Decimal("44"))
    assert model == ChargerModel.gw22k


def test_trifasico_empate_favorece_gw11k():
    model = dimensionamento.select_model("trifasico", Decimal("43.99"))
    assert model == ChargerModel.gw11k


def test_max_chargers_caso_normal():
    qty = dimensionamento.max_chargers(
        available_power_kw=Decimal("40"),
        model=ChargerModel.gw11k,
        establishment_type="estacionamento",
        parking_spots=8,
    )
    # usable = 40*0.8=32; max_by_power = floor(32 / (11*0.7)) = floor(4.15) = 4
    assert qty == 4


def test_max_chargers_limitado_pelas_vagas_fisicas():
    qty = dimensionamento.max_chargers(
        available_power_kw=Decimal("400"),
        model=ChargerModel.gw11k,
        establishment_type="estacionamento",
        parking_spots=2,
    )
    assert qty == 2


def test_max_chargers_zero_quando_carga_insuficiente():
    qty = dimensionamento.max_chargers(
        available_power_kw=Decimal("3"),
        model=ChargerModel.gw11k,
        establishment_type="empresa",
        parking_spots=8,
    )
    assert qty == 0


def test_min_power_required_preenchido_quando_max_chargers_e_zero():
    min_power = dimensionamento.min_power_required_kw(ChargerModel.gw11k, "empresa")
    # nominal(11) * fator(0.85) / margem(0.80) = 11.6875
    assert min_power == Decimal("11.69")


def test_estimate_budget_sempre_sob_consulta_enquanto_unit_price_e_none():
    budget = dimensionamento.estimate_budget(
        ChargerModel.gw11k, 4, "estacionamento", Decimal("1.20")
    )
    assert budget["capex"] is None
    assert budget["payback_months"] is None
    assert budget["note"] is not None and "sob consulta" in budget["note"].lower()
