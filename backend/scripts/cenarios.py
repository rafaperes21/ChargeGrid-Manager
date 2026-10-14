"""Cenarios quantitativos A vs B - Sprint 4, Fase 3. DADOS SIMULADOS/SINTETICOS.

Simula o MESMO dia de demanda de recarga (mesmas chegadas, mesmos veiculos, mesmos SoC) em:

- A - sem o sistema: sem controle de demanda, sem solar/bateria, tarifa convencional da
  distribuidora (preco unico por kWh). Tudo vem da rede, sem limite.
- B - com o sistema: controle de demanda (`services/demand_control.allocate_power`),
  despacho solar -> bateria -> rede (`services/energy_dispatch.dispatch`) e tarifa horaria
  (Tarifa Branca) da distribuidora - as MESMAS funcoes que o polling usa ao vivo.
- B (tarifa convencional) - linha informativa: o sistema B pagando a tarifa do A, para separar
  o efeito de solar/bateria/controle do efeito da escolha de tarifa.

Uso (de dentro de `backend/`):

    python -m scripts.cenarios                 # defaults = Estacionamento Central da demo
    python -m scripts.cenarios --seed 7 --date 2026-10-15 --out ../docs

Mesmo `--seed` e mesmos parametros -> mesma saida, byte a byte (CSV/MD).

FONTES DOS NUMEROS QUE NAO SAO PREMISSA DE SIMULACAO (consultadas em 14/10/2026)
- Fator de emissao da rede: MCTI/SIRENE, "Fator medio - Inventarios corporativos", planilha
  Inventario_2026_janago.xlsx, aba "inventario-todos": fator medio ANUAL de 2025 = 0,0461
  tCO2/MWh (= 0,0461 kg/kWh), ultimo ano completo publicado.
  https://www.gov.br/mcti/pt-br/acompanhe-o-mcti/cgcl/paginas/fator-medio-inventarios-corporativos
- Tarifas: ANEEL, Resolucao Homologatoria n. 3.596/2026 (Enel SP, vigencia 04/07/2026 a
  03/07/2027), Tabela 2, subgrupo B3, tarifas de aplicacao (TUSD + TE, R$/MWh, sem impostos
  e sem bandeira):
    convencional 472,42 + 316,96 = 789,38
    branca ponta 1.076,66 + 482,45 = 1.559,11 | intermediario 729,88 + 301,91 = 1.031,79 |
    fora de ponta 383,10 + 301,91 = 685,01
  https://www.enel.com.br/content/dam/enel-br/megamenu/para-voc%C3%AA/REH%203596.2026%20Enel%20SP.pdf
- Postos tarifarios da Enel SP: ponta 17h30-20h30; intermediario 16h30-17h30 e 20h30-21h30;
  fora de ponta no restante - https://www.enel.com.br/pt-saopaulo/tarifa-branca.html
  (o script so aceita dia util: a regra de fim de semana nao foi conferida em fonte).

PREMISSAS DE SIMULACAO (nao sao medicao): 4 carregadores de 11 kW, limite contratado de 40 kW,
arranjo FV de 20 kWp e bateria de 20 kWh (os mesmos do seed da demo), perfil de chegadas
"estacionamento" e catalogo de veiculos do simulador, curva solar de `simulador/solar.py`.
Simplificacoes: passo de 1 min; sem a rampa de 2 min nem o ruido da curva P(t) (iguais nos
dois cenarios, nao mudam a comparacao); bateria comeca no SoC minimo (nao entra energia
"de graca" de ontem); excedente solar sem credito de compensacao (SCEE nao modelado); a
demanda dos clientes NAO muda com o preco (sem dado de elasticidade, nao inventamos um).
"""

import argparse
import csv
import io
import random
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from app.services.demand_control import allocate_power
from app.services.energy_dispatch import BatterySpec, dispatch, max_discharge_kw
from simulador.profiles import PROFILE_BY_KIND, sessions_for_day
from simulador.solar import LOCAL_TZ, SolarParams, solar_power_kw
from simulador.vehicles import VehicleProfile, pick_vehicle

D = Decimal

GRID_EMISSION_FACTOR_KG_PER_KWH = D("0.0461")  # MCTI, fator medio anual 2025 (ver docstring)
EMISSION_FACTOR_SOURCE = (
    "MCTI/SIRENE - fator medio anual do SIN de 2025 (inventarios corporativos), "
    "planilha Inventario_2026_janago.xlsx"
)
TARIFF_SOURCE = "ANEEL REH 3.596/2026 (Enel SP), subgrupo B3, TUSD+TE sem impostos e sem bandeira"
TARIFF_CONVENTIONAL = D("0.78938")  # R$/kWh
TARIFF_WHITE = {"ponta": D("1.55911"), "intermediario": D("1.03179"), "fora_ponta": D("0.68501")}

PEAK = (time(17, 30), time(20, 30))
INTERMEDIATE = ((time(16, 30), time(17, 30)), (time(20, 30), time(21, 30)))

TAPER_START_SOC = D("0.80")
TAPER_END_PCT_OF_NOMINAL = D("0.10")
STEP = timedelta(minutes=1)
DT_H = D(1) / D(60)
MAX_HORIZON = timedelta(hours=36)
SYNTHETIC_NOTICE = "Dados simulados/sinteticos - nao sao medicoes de um eletroposto real."


def tariff_post(at: datetime) -> str:
    local = at.astimezone(LOCAL_TZ).time()
    if PEAK[0] <= local < PEAK[1]:
        return "ponta"
    if any(start <= local < end for start, end in INTERMEDIATE):
        return "intermediario"
    return "fora_ponta"


@dataclass(frozen=True)
class Config:
    day: date
    seed: int = 42
    chargers: int = 4
    charger_kw: D = D("11")
    grid_limit_kw: D = D("40")
    pv_kwp: D = D("20")
    battery: BatterySpec = field(
        default_factory=lambda: BatterySpec(
            capacity_kwh=D("20"),
            max_charge_kw=D("10"),
            max_discharge_kw=D("10"),
            min_soc_pct=D("10"),
            round_trip_efficiency_pct=D("90"),
        )
    )
    emission_factor: D = GRID_EMISSION_FACTOR_KG_PER_KWH


@dataclass(frozen=True)
class Arrival:
    charger: int
    at: datetime
    vehicle: VehicleProfile
    initial_soc: D
    target_soc: D


def build_demand(cfg: Config) -> list[Arrival]:
    """O dia de demanda, sorteado UMA vez e reaproveitado pelos dois cenarios."""
    rng = random.Random(cfg.seed)
    profile = PROFILE_BY_KIND["estacionamento"]
    arrivals = []
    for charger in range(cfg.chargers):
        for local_time in sessions_for_day(profile, cfg.day, rng):
            arrivals.append(
                Arrival(
                    charger=charger,
                    at=datetime.combine(cfg.day, local_time, tzinfo=LOCAL_TZ),
                    vehicle=pick_vehicle(rng),
                    initial_soc=D(str(round(rng.uniform(0.15, 0.60), 3))),
                    target_soc=D(str(round(rng.uniform(0.80, 1.0), 3))),
                )
            )
    return sorted(arrivals, key=lambda a: (a.at, a.charger))


def requested_kw(soc: D, vehicle: VehicleProfile, nominal_kw: D) -> D:
    """Mesma forma da curva do simulador (`simulador/curve_engine.py`), mas indexada pelo SoC
    em vez do tempo: plato = min(carregador, OBC) ate 80%, depois cai linear ate 10% da
    nominal em 100%. Indexar por SoC e o que faz um carro limitado demorar mais."""
    plateau = min(nominal_kw, vehicle.obc_max_kw)
    if soc < TAPER_START_SOC:
        return plateau
    floor = nominal_kw * TAPER_END_PCT_OF_NOMINAL
    progress = (soc - TAPER_START_SOC) / (D(1) - TAPER_START_SOC)
    return max(floor, plateau - (plateau - floor) * progress)


@dataclass
class Minute:
    at: datetime
    requested_kw: D
    load_kw: D
    solar_kw: D
    solar_to_load_kw: D
    battery_to_load_kw: D
    grid_kw: D
    solar_surplus_kw: D
    battery_soc_pct: D | None
    post: str


@dataclass
class Result:
    name: str
    minutes: list[Minute]
    session_minutes: list[int]
    unfinished: int


def simulate(cfg: Config, arrivals: list[Arrival], with_system: bool) -> Result:
    start = datetime.combine(cfg.day, time.min, tzinfo=LOCAL_TZ)
    pending = {c: [a for a in arrivals if a.charger == c] for c in range(cfg.chargers)}
    active: dict[int, dict] = {}
    durations: list[int] = []
    soc = cfg.battery.min_soc_pct if with_system else None
    solar_params = SolarParams(peak_kwp=cfg.pv_kwp)
    minutes: list[Minute] = []

    t = start
    while t < start + MAX_HORIZON:
        for charger, queue in pending.items():
            if charger not in active and queue and queue[0].at <= t:
                arrival = queue.pop(0)
                active[charger] = {"arrival": arrival, "soc": arrival.initial_soc, "since": t}
        if not active and not any(pending.values()) and t >= start + timedelta(days=1):
            break

        requested = {
            c: requested_kw(s["soc"], s["arrival"].vehicle, cfg.charger_kw)
            for c, s in active.items()
        }
        solar = solar_power_kw("GW-INV-CENARIO", t, solar_params) if with_system else D("0")
        if with_system:
            available = cfg.grid_limit_kw + solar + max_discharge_kw(cfg.battery, soc, DT_H)
            caps = allocate_power(requested, available)
        else:
            caps = requested
        delivered = {c: min(requested[c], caps[c]) for c in requested}
        load = sum(delivered.values(), D("0"))

        result = dispatch(
            load_kw=load,
            solar_kw=solar,
            battery=cfg.battery if with_system else None,
            soc_pct=soc,
            grid_limit_kw=cfg.grid_limit_kw if with_system else None,
            dt_h=DT_H,
        )
        minutes.append(
            Minute(
                at=t,
                requested_kw=sum(requested.values(), D("0")),
                load_kw=result.load_kw,
                solar_kw=result.solar_kw,
                solar_to_load_kw=result.solar_to_load_kw,
                battery_to_load_kw=result.battery_to_load_kw,
                grid_kw=result.grid_to_load_kw,
                solar_surplus_kw=result.solar_surplus_kw,
                battery_soc_pct=soc,
                post=tariff_post(t),
            )
        )
        soc = result.soc_after_pct

        for charger, power in delivered.items():
            session = active[charger]
            capacity = session["arrival"].vehicle.battery_capacity_kwh
            session["soc"] += power * DT_H / capacity
            if session["soc"] >= session["arrival"].target_soc:
                durations.append(int((t + STEP - session["arrival"].at).total_seconds() // 60))
                del active[charger]
        t += STEP

    return Result(
        name="",
        minutes=minutes,
        session_minutes=durations,
        unfinished=len(active) + sum(len(q) for q in pending.values()),
    )


def _kwh(minutes: list[Minute], attr: str) -> D:
    return sum((getattr(m, attr) for m in minutes), D("0")) * DT_H


def _money(value: D) -> D:
    return value.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def _q(value: D, places: str = "0.001") -> D:
    return value.quantize(D(places), rounding=ROUND_HALF_UP)


def energy_cost(minutes: list[Minute], tariff: Callable[[str], D]) -> D:
    return sum((m.grid_kw * DT_H * tariff(m.post) for m in minutes), D("0"))


def metrics(result: Result, baseline_grid_kwh: D, cfg: Config, tariff) -> dict[str, D]:
    m = result.minutes
    load = _kwh(m, "load_kw")
    grid = _kwh(m, "grid_kw")
    renewable = _kwh(m, "solar_to_load_kw") + _kwh(m, "battery_to_load_kw")
    avoided = baseline_grid_kwh - grid
    share = renewable / load * 100 if load > 0 else D("0")
    mean_minutes = (
        D(sum(result.session_minutes)) / len(result.session_minutes)
        if result.session_minutes
        else D("0")
    )
    return {
        "energia_entregue_kwh": _q(load),
        "pico_rede_kw": _q(max(x.grid_kw for x in m)),
        "pico_carga_kw": _q(max(x.load_kw for x in m)),
        "energia_rede_kwh": _q(grid),
        "custo_energia_rs": _money(energy_cost(m, tariff)),
        "renovavel_pct": _q(share, "0.1"),
        "kwh_evitados_rede": _q(avoided),
        "co2_rede_kg": _q(grid * cfg.emission_factor),
        "co2_evitado_kg": _q(avoided * cfg.emission_factor),
        "solar_gerado_kwh": _q(_kwh(m, "solar_kw")),
        "excedente_solar_kwh": _q(_kwh(m, "solar_surplus_kw")),
        "tempo_medio_recarga_min": _q(mean_minutes, "0.1"),
        "sessoes_concluidas": D(len(result.session_minutes)),
        "sessoes_nao_concluidas": D(result.unfinished),
    }


METRIC_LABELS = {
    "energia_entregue_kwh": "Energia entregue aos veiculos (kWh)",
    "pico_rede_kw": "Pico de potencia na rede (kW)",
    "pico_carga_kw": "Pico de carga dos carregadores (kW)",
    "energia_rede_kwh": "Energia comprada da rede (kWh)",
    "custo_energia_rs": "Custo de energia da rede (R$, sem impostos)",
    "renovavel_pct": "Energia renovavel local na recarga (%)",
    "kwh_evitados_rede": "kWh evitados da rede (vs. A)",
    "co2_rede_kg": "CO2 da energia da rede (kg)",
    "co2_evitado_kg": "CO2 evitado (kg, vs. A)",
    "solar_gerado_kwh": "Geracao solar total (kWh)",
    "excedente_solar_kwh": "Excedente solar nao usado (kWh)",
    "tempo_medio_recarga_min": "Tempo medio de recarga (min)",
    "sessoes_concluidas": "Sessoes concluidas",
    "sessoes_nao_concluidas": "Sessoes nao concluidas",
}
SCENARIOS = ("A", "B", "B_tarifa_convencional")


def run(cfg: Config) -> tuple[dict[str, dict[str, D]], dict[str, Result]]:
    arrivals = build_demand(cfg)
    a = simulate(cfg, arrivals, with_system=False)
    b = simulate(cfg, arrivals, with_system=True)
    baseline = _kwh(a.minutes, "grid_kw")
    table = {
        "A": metrics(a, baseline, cfg, lambda post: TARIFF_CONVENTIONAL),
        "B": metrics(b, baseline, cfg, lambda post: TARIFF_WHITE[post]),
        "B_tarifa_convencional": metrics(b, baseline, cfg, lambda post: TARIFF_CONVENTIONAL),
    }
    return table, {"A": a, "B": b}


SENSITIVITY_KEYS = (
    "pico_rede_kw",
    "energia_rede_kwh",
    "custo_energia_rs",
    "renovavel_pct",
    "co2_evitado_kg",
)
# metricas em que "menor e melhor" (para contar em quantos dias B ganhou de A)
_LOWER_IS_BETTER = {"pico_rede_kw", "energia_rede_kwh", "custo_energia_rs"}


def sensitivity(cfg: Config, seeds: range) -> dict[str, dict[str, D]]:
    """Mesmo A vs B em varios dias de demanda sorteados (um por seed): um dia so e fragil
    demais para virar conclusao - a ordem de chegada muda muito o resultado de custo."""
    rows = [run(replace(cfg, seed=seed))[0] for seed in seeds]
    summary = {}
    for key in SENSITIVITY_KEYS:
        a = [r["A"][key] for r in rows]
        b = [r["B"][key] for r in rows]
        if key == "co2_evitado_kg":
            wins = sum(1 for value in b if value > 0)
        elif key == "renovavel_pct":
            wins = sum(1 for va, vb in zip(a, b, strict=True) if vb > va)
        else:
            wins = sum(1 for va, vb in zip(a, b, strict=True) if vb < va)
        summary[key] = {
            "media_A": _q(sum(a, D("0")) / len(a), "0.01"),
            "media_B": _q(sum(b, D("0")) / len(b), "0.01"),
            "min_B": min(b),
            "max_B": max(b),
            "dias_B_melhor": D(wins),
            "dias": D(len(rows)),
        }
    return summary


def to_csv(table: dict[str, dict[str, D]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["# " + SYNTHETIC_NOTICE])
    writer.writerow(["metrica", "descricao", *SCENARIOS])
    for key, label in METRIC_LABELS.items():
        writer.writerow([key, label, *(str(table[s][key]) for s in SCENARIOS)])
    return buffer.getvalue()


def _br(value: D) -> str:
    text = f"{value:,}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def sensitivity_to_csv(summary: dict[str, dict[str, D]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["# " + SYNTHETIC_NOTICE])
    columns = ["media_A", "media_B", "min_B", "max_B", "dias_B_melhor", "dias"]
    writer.writerow(["metrica", *columns])
    for key, values in summary.items():
        writer.writerow([key, *(str(values[c]) for c in columns)])
    return buffer.getvalue()


def to_markdown(
    table: dict[str, dict[str, D]], cfg: Config, summary: dict[str, dict[str, D]] | None = None,
    seeds: range | None = None,
) -> str:
    lines = [
        "# Resultados quantitativos - cenarios A vs B",
        "",
        f"> **{SYNTHETIC_NOTICE}** Gerado por `backend/scripts/cenarios.py` "
        f"(`--seed {cfg.seed} --date {cfg.day.isoformat()}`). Rodar de novo com os mesmos "
        "parametros reproduz esta tabela exatamente.",
        "",
        "| Metrica | A - sem o sistema | B - com o sistema | B com tarifa convencional* |",
        "|---|---:|---:|---:|",
    ]
    for key, label in METRIC_LABELS.items():
        values = " | ".join(_br(table[s][key]) for s in SCENARIOS)
        lines.append(f"| {label} | {values} |")
    lines += [
        "",
        "\\* Linha informativa: o sistema B pagando a tarifa do cenario A, para separar o efeito "
        "de solar/bateria/controle de demanda do efeito da troca de modalidade tarifaria.",
        "",
    ]
    if summary is not None and seeds is not None:
        lines += [
            f"## Sensibilidade - {len(seeds)} dias de demanda sorteados "
            f"(seeds {seeds.start} a {seeds.stop - 1})",
            "",
            "Um dia so e fragil: a ordem de chegada dos carros muda bastante o resultado. Mesma "
            "comparacao A x B, mesma configuracao, um dia de demanda diferente por seed.",
            "",
            "| Metrica | Media A | Media B | B min | B max | Dias em que B foi melhor |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for key, v in summary.items():
            lines.append(
                f"| {METRIC_LABELS[key]} | {_br(v['media_A'])} | {_br(v['media_B'])} | "
                f"{_br(v['min_B'])} | {_br(v['max_B'])} | "
                f"{v['dias_B_melhor']} de {v['dias']} |"
            )
        lines.append("")
    lines += [
        "## Premissas e fontes",
        "",
        f"- Dia util {cfg.day.isoformat()}; {cfg.chargers} carregadores de {cfg.charger_kw} kW; "
        f"limite contratado {cfg.grid_limit_kw} kW (cenario B); FV {cfg.pv_kwp} kWp e bateria "
        f"{cfg.battery.capacity_kwh} kWh / {cfg.battery.max_discharge_kw} kW, SoC minimo "
        f"{cfg.battery.min_soc_pct}% e eficiencia {cfg.battery.round_trip_efficiency_pct}% "
        "(premissas de simulacao, iguais ao seed da demo).",
        "- A: tarifa convencional B3 (R$ 0,78938/kWh). B: Tarifa Branca B3 (ponta R$ 1,55911, "
        "intermediario R$ 1,03179, fora de ponta R$ 0,68501 por kWh). Fonte: "
        f"{TARIFF_SOURCE}.",
        f"- Fator de emissao: {_br(cfg.emission_factor)} kg CO2/kWh - {EMISSION_FACTOR_SOURCE}.",
        "- Mesmo dia de demanda nos dois cenarios; a demanda NAO reage ao preco (sem dado de "
        "elasticidade). Bateria comeca no SoC minimo; excedente solar sem credito (SCEE nao "
        "modelado); valores sem impostos e sem bandeira tarifaria.",
        "",
    ]
    return "\n".join(lines)


def render_charts(results: dict[str, Result], table, cfg: Config, out_dir: Path) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # paleta validada (skill dataviz, validate_palette.js): passa CVD/contraste em claro
    colors = {"load": "#7c3aed", "solar": "#d97706", "battery": "#0f9b8e", "grid": "#3b6bc4"}
    ink, muted = "#2a2732", "#726d7d"
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.edgecolor": muted,
            "axes.labelcolor": ink,
            "xtick.color": muted,
            "ytick.color": muted,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    start = datetime.combine(cfg.day, time.min, tzinfo=LOCAL_TZ)

    def hours(minutes):
        return [(m.at - start).total_seconds() / 3600 for m in minutes]

    paths = []

    # 1. potencia ao longo do dia
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=150)
    a, b = results["A"].minutes, results["B"].minutes
    ax.plot(hours(a), [float(m.grid_kw) for m in a], color=muted, lw=1.6,
            label="A - rede (= carga, sem controle)")
    ax.plot(hours(b), [float(m.grid_kw) for m in b], color=colors["grid"], lw=2,
            label="B - rede")
    ax.plot(hours(b), [float(m.solar_kw) for m in b], color=colors["solar"], lw=1.6, ls="--",
            label="B - geracao solar")
    ax.axhline(float(cfg.grid_limit_kw), color="#dc2626", lw=1.2, ls=":",
               label=f"limite contratado ({cfg.grid_limit_kw} kW)")
    ax.set_xlim(0, max(24, hours(a)[-1], hours(b)[-1]))
    ax.set_xticks(range(0, 25, 3), [f"{h:02d}h" for h in range(0, 25, 3)])
    ax.set_ylabel("kW")
    ax.set_title("Potencia ao longo do dia - A sem o sistema x B com o sistema", loc="left",
                 color=ink)
    ax.grid(axis="y", color="#eae6f2")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.text(0.01, 0.01, SYNTHETIC_NOTICE, fontsize=8, color=muted)
    path = out_dir / "cenarios_potencia_dia.png"
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, metadata={"Software": None})
    plt.close(fig)
    paths.append(path)

    # 2. energia por fonte (barras empilhadas horizontais)
    fig, ax = plt.subplots(figsize=(10, 3.2), dpi=150)
    labels = ["A - sem o sistema", "B - com o sistema"]
    parts = [
        ("Solar -> carga", "solar_to_load_kw", colors["solar"]),
        ("Bateria -> carga", "battery_to_load_kw", colors["battery"]),
        ("Rede -> carga", "grid_kw", colors["grid"]),
    ]
    lefts = [0.0, 0.0]
    for label, attr, color in parts:
        values = [float(_kwh(results[s].minutes, attr)) for s in ("A", "B")]
        bars = ax.barh(labels, values, left=lefts, color=color, label=label,
                       edgecolor="white", linewidth=2, height=0.55)
        for bar, value in zip(bars, values, strict=True):
            if value >= 8:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height() / 2,
                        f"{value:.0f} kWh", ha="center", va="center", color="white", fontsize=9)
        lefts = [x + v for x, v in zip(lefts, values, strict=True)]
    ax.invert_yaxis()
    ax.set_xlabel("kWh entregues aos veiculos no dia")
    ax.set_title("De onde veio a energia das recargas", loc="left", color=ink)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="lower right", bbox_to_anchor=(1, 1.02))
    ax.grid(axis="x", color="#eae6f2")
    fig.text(0.01, 0.01, SYNTHETIC_NOTICE, fontsize=8, color=muted)
    path = out_dir / "cenarios_energia_por_fonte.png"
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, metadata={"Software": None})
    plt.close(fig)
    paths.append(path)

    # 3. comparativo de metricas - um eixo por metrica (nunca eixo duplo)
    panels = [
        ("pico_rede_kw", "Pico na rede (kW)"),
        ("custo_energia_rs", "Custo de energia (R$)"),
        ("renovavel_pct", "Renovavel (%)"),
        ("co2_rede_kg", "CO2 da rede (kg)"),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.4), dpi=150)
    for ax, (key, title) in zip(axes, panels, strict=True):
        values = [float(table["A"][key]), float(table["B"][key])]
        bars = ax.bar(["A", "B"], values, color=[muted, colors["load"]], width=0.6)
        for bar, value in zip(bars, values, strict=True):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), _br(D(str(value))),
                    ha="center", va="bottom", fontsize=9, color=ink)
        ax.set_title(title, fontsize=10, color=ink)
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)
        ax.margins(y=0.18)
    fig.suptitle("A sem o sistema x B com o sistema", x=0.01, ha="left", color=ink)
    fig.text(0.01, 0.01, SYNTHETIC_NOTICE, fontsize=8, color=muted)
    path = out_dir / "cenarios_comparativo.png"
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(path, metadata={"Software": None})
    plt.close(fig)
    paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Cenarios A vs B (dados simulados).")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--date", type=date.fromisoformat, default=date(2026, 10, 14))
    parser.add_argument("--chargers", type=int, default=4)
    parser.add_argument("--grid-limit-kw", type=D, default=D("40"))
    parser.add_argument("--pv-kwp", type=D, default=D("20"))
    parser.add_argument(
        "--grid-emission-factor",
        type=D,
        default=GRID_EMISSION_FACTOR_KG_PER_KWH,
        help="kg CO2/kWh da rede (default: MCTI, fator medio anual 2025)",
    )
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[2] / "docs")
    parser.add_argument("--no-charts", action="store_true")
    parser.add_argument(
        "--sensitivity-days", type=int, default=30,
        help="quantos dias (seeds 1..N) na analise de sensibilidade; 0 desliga",
    )
    args = parser.parse_args()
    if args.date.weekday() >= 5:
        parser.error("use um dia util - os postos tarifarios de fim de semana nao foram "
                     "conferidos em fonte")

    cfg = Config(
        day=args.date,
        seed=args.seed,
        chargers=args.chargers,
        grid_limit_kw=args.grid_limit_kw,
        pv_kwp=args.pv_kwp,
        emission_factor=args.grid_emission_factor,
    )
    table, results = run(cfg)
    seeds = range(1, args.sensitivity_days + 1)
    summary = sensitivity(cfg, seeds) if args.sensitivity_days > 0 else None
    results_dir = args.out / "resultados"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "cenarios.csv").write_text(to_csv(table), encoding="utf-8")
    if summary is not None:
        (results_dir / "cenarios_sensibilidade.csv").write_text(
            sensitivity_to_csv(summary), encoding="utf-8"
        )
    markdown = to_markdown(table, cfg, summary, seeds if summary is not None else None)
    (results_dir / "cenarios.md").write_text(markdown, encoding="utf-8")
    print(markdown)
    if not args.no_charts:
        for path in render_charts(results, table, cfg, args.out / "img"):
            print(f"grafico: {path}")


if __name__ == "__main__":
    main()
