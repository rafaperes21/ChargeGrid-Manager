"""Script de cenarios A vs B (Sprint 4, Fase 3) - dados simulados."""

from datetime import date
from decimal import Decimal

import pytest

from scripts.cenarios import (
    TARIFF_WHITE,
    Config,
    _kwh,
    build_demand,
    run,
    sensitivity,
    simulate,
    tariff_post,
    to_csv,
    to_markdown,
)
from simulador.solar import LOCAL_TZ

CFG = Config(day=date(2026, 10, 14))


def test_same_seed_same_output_byte_for_byte():
    first, _ = run(CFG)
    second, _ = run(CFG)
    assert to_csv(first) == to_csv(second)
    assert to_markdown(first, CFG) == to_markdown(second, CFG)


def test_both_scenarios_serve_the_same_demand():
    table, _ = run(CFG)
    assert table["A"]["energia_entregue_kwh"] == table["B"]["energia_entregue_kwh"]
    assert table["A"]["sessoes_nao_concluidas"] == table["B"]["sessoes_nao_concluidas"] == 0


def test_scenario_b_never_exceeds_contracted_limit():
    # 8 carregadores forcam a carga acima de 40 kW - o controle de demanda tem que segurar
    cfg = Config(day=date(2026, 10, 14), chargers=8, seed=3)
    arrivals = build_demand(cfg)
    a = simulate(cfg, arrivals, with_system=False)
    b = simulate(cfg, arrivals, with_system=True)
    assert max(m.grid_kw for m in a.minutes) > cfg.grid_limit_kw  # sem controle, estoura
    assert max(m.grid_kw for m in b.minutes) <= cfg.grid_limit_kw
    # carga sai do despacho arredondada em 0,001 kW; o pedido nao e arredondado
    assert all(m.load_kw <= m.requested_kw + Decimal("0.001") for m in b.minutes)
    assert any(m.load_kw < m.requested_kw - 1 for m in b.minutes)  # houve limitacao de fato


def test_energy_balance_every_minute():
    _, results = run(CFG)
    for m in results["B"].minutes:
        assert m.solar_to_load_kw + m.battery_to_load_kw + m.grid_kw == m.load_kw


def test_scenario_a_is_all_grid():
    _, results = run(CFG)
    a = results["A"].minutes
    assert _kwh(a, "grid_kw") == _kwh(a, "load_kw")
    assert _kwh(a, "solar_kw") == 0


def test_co2_uses_mcti_factor():
    table, _ = run(CFG)
    avoided = table["B"]["kwh_evitados_rede"]
    assert table["B"]["co2_evitado_kg"] == (avoided * Decimal("0.0461")).quantize(
        Decimal("0.001")
    )


@pytest.mark.parametrize(
    ("hhmm", "post"),
    [("17:29", "intermediario"), ("17:30", "ponta"), ("20:29", "ponta"),
     ("20:30", "intermediario"), ("21:30", "fora_ponta"), ("16:29", "fora_ponta")],
)
def test_enel_sp_tariff_posts(hhmm, post):
    from datetime import datetime, time

    hour, minute = map(int, hhmm.split(":"))
    at = datetime.combine(date(2026, 10, 14), time(hour, minute), tzinfo=LOCAL_TZ)
    assert tariff_post(at) == post
    assert post in TARIFF_WHITE


def test_sensitivity_counts_days():
    summary = sensitivity(CFG, range(1, 4))
    assert summary["energia_rede_kwh"]["dias"] == 3
    assert 0 <= summary["custo_energia_rs"]["dias_B_melhor"] <= 3
