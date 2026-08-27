from decimal import Decimal

import pytest

from app.services.pricing import calculate_session_amount


def test_sem_promocao_sem_desconto_sem_franquia():
    result = calculate_session_amount(
        energy_kwh=Decimal("10.000"),
        tariff_rate_per_kwh=Decimal("1.5000"),
    )

    assert result.gross_amount == Decimal("15.0000")
    assert result.final_amount == Decimal("15.0000")
    assert result.promo_kwh_deducted == Decimal("0.000")
    assert result.franquia_kwh_used == Decimal("0.000")


def test_promocao_e_desconto_aplicados_na_ordem_correta_nao_acumulam_sobre_bruto():
    # 6 kWh em 60 min, 30 min gratis (metade da sessao -> metade da energia), 15% de plano.
    result = calculate_session_amount(
        energy_kwh=Decimal("6.000"),
        tariff_rate_per_kwh=Decimal("2.0000"),
        session_duration_minutes=Decimal("60"),
        free_minutes=30,
        plan_discount_pct=Decimal("15"),
    )

    assert result.gross_amount == Decimal("12.0000")
    assert result.promo_kwh_deducted == Decimal("3.000")
    assert result.billed_kwh_after_promo == Decimal("3.000")
    # 3 kWh restantes * 2.00 * 0.85 = 5.10 - desconto nunca incide sobre o bruto (12*0.85=10.20)
    assert result.final_amount == Decimal("5.1000")


def test_franquia_abatida_em_kwh_antes_de_virar_dinheiro():
    result = calculate_session_amount(
        energy_kwh=Decimal("6.000"),
        tariff_rate_per_kwh=Decimal("2.0000"),
        session_duration_minutes=Decimal("60"),
        free_minutes=30,
        plan_discount_pct=Decimal("15"),
        franquia_kwh_available=Decimal("1.000"),
    )

    assert result.franquia_kwh_used == Decimal("1.000")
    assert result.billed_kwh_final == Decimal("2.000")
    # 2 kWh faturados * (2.00 * 0.85) = 3.40
    assert result.final_amount == Decimal("3.4000")


def test_franquia_excedida_cobra_o_excedente_com_desconto_do_plano():
    result = calculate_session_amount(
        energy_kwh=Decimal("10.000"),
        tariff_rate_per_kwh=Decimal("1.0000"),
        plan_discount_pct=Decimal("15"),
        franquia_kwh_available=Decimal("6.000"),
    )

    assert result.franquia_kwh_used == Decimal("6.000")
    assert result.billed_kwh_final == Decimal("4.000")
    # excedente de 4 kWh * (1.00 * 0.85) = 3.40
    assert result.final_amount == Decimal("3.4000")


def test_franquia_maior_que_consumo_zera_a_sessao_sem_ficar_negativo():
    result = calculate_session_amount(
        energy_kwh=Decimal("2.000"),
        tariff_rate_per_kwh=Decimal("1.0000"),
        franquia_kwh_available=Decimal("10.000"),
    )

    assert result.franquia_kwh_used == Decimal("2.000")
    assert result.billed_kwh_final == Decimal("0.000")
    assert result.final_amount == Decimal("0.0000")


def test_promocao_nunca_deduz_mais_energia_do_que_a_consumida():
    # 30 min gratis numa sessao de so 10 min -> nao pode "criar" energia negativa.
    result = calculate_session_amount(
        energy_kwh=Decimal("2.000"),
        tariff_rate_per_kwh=Decimal("1.0000"),
        session_duration_minutes=Decimal("10"),
        free_minutes=30,
    )

    assert result.promo_kwh_deducted == Decimal("2.000")
    assert result.billed_kwh_after_promo == Decimal("0.000")
    assert result.final_amount == Decimal("0.0000")


def test_free_minutes_sem_duracao_nao_aplica_promocao():
    result = calculate_session_amount(
        energy_kwh=Decimal("5.000"),
        tariff_rate_per_kwh=Decimal("1.0000"),
        free_minutes=15,
    )

    assert result.promo_kwh_deducted == Decimal("0.000")
    assert result.free_minutes_applied == 0
    assert result.final_amount == Decimal("5.0000")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"energy_kwh": Decimal("-1"), "tariff_rate_per_kwh": Decimal("1")},
        {"energy_kwh": Decimal("1"), "tariff_rate_per_kwh": Decimal("-1")},
        {"energy_kwh": Decimal("1"), "tariff_rate_per_kwh": Decimal("1"), "free_minutes": -5},
        {
            "energy_kwh": Decimal("1"),
            "tariff_rate_per_kwh": Decimal("1"),
            "plan_discount_pct": Decimal("101"),
        },
        {
            "energy_kwh": Decimal("1"),
            "tariff_rate_per_kwh": Decimal("1"),
            "franquia_kwh_available": Decimal("-1"),
        },
    ],
)
def test_entradas_invalidas_levantam_value_error(kwargs):
    with pytest.raises(ValueError):
        calculate_session_amount(**kwargs)
