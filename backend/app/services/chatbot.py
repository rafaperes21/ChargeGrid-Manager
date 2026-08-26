"""Chatbot do proprietario (M7 minimo) - LLM local via Ollama, sem chave de API externa.

So duas ferramentas tem dado real hoje: status dos carregadores (M1) e previsao de demanda
(microservico `ia`). `get_active_sessions`, `get_revenue_summary` e `calculate_sizing` da
skill `chatbots-gemini` dependem de M3/M6, que nao existem - fora de escopo.

Regra de seguranca da skill: o escopo de dados vem do estabelecimento ja autenticado/validado
pela API (`get_owned_establishment`), nunca de um argumento que o modelo preenche - por isso
as ferramentas abaixo fecham `establishment` por closure e nao expoem nenhum id ao LLM.
"""

import httpx
import requests
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_ollama import ChatOllama
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.charger import Charger
from app.models.establishment import Establishment
from app.schemas.chatbot import ChatMessageIn, ChatResponse

SYSTEM_PROMPT = """Voce e o assistente tecnico do ChargeGrid-Manager para o dono do
estabelecimento. Tom direto, tecnico, como um colega de engenharia - sem emoji.

Voce so tem DUAS ferramentas disponiveis hoje: status dos carregadores e previsao de demanda.
Nao existe ferramenta de sessoes ativas, receita ou dimensionamento de instalacao ainda - se
perguntarem sobre isso, diga claramente que essa informacao nao esta disponivel no momento,
nao invente um numero.

Nunca invente dado. Se uma ferramenta falhar ou nao tiver informacao suficiente, diga isso
com todas as letras em vez de estimar."""

MAX_TOOL_ITERATIONS = 4
HISTORY_WINDOW = 10


def _describe_chargers(db: Session, establishment: Establishment) -> str:
    chargers = (
        db.query(Charger)
        .filter(Charger.establishment_id == establishment.id)
        .order_by(Charger.spot_label)
        .all()
    )
    if not chargers:
        return "Nenhum carregador cadastrado neste estabelecimento."

    lines = [
        f"{charger.spot_label} ({charger.sems_serial}): {charger.status.value}, "
        f"nominal {charger.nominal_power_kw} kW"
        for charger in chargers
    ]
    return "\n".join(lines)


def _describe_demand_forecast(establishment: Establishment, settings: Settings) -> str:
    url = f"{settings.ia_service_url}/forecast/establishments/{establishment.id}/demand"
    try:
        response = requests.get(url, params={"horizon_hours": 48}, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return (
            "Nao consegui consultar a previsao de demanda agora - o servico de IA pode estar "
            "fora do ar."
        )

    data = response.json()
    if data["status"] == "insufficient_data":
        return (
            "Ainda nao ha historico suficiente (minimo de 4 semanas) para gerar previsao de "
            "demanda."
        )

    lines = [f"Previsao de demanda - modelo {data.get('model_version')}."]
    peak_labels = data.get("peak_labels") or []
    if peak_labels:
        lines.append("Picos esperados: " + "; ".join(peak_labels) + ".")
    if data.get("fallback_used"):
        lines.append(
            "Aviso: o modelo principal falhou - isto e uma media historica simples, nao a "
            "previsao real do Prophet."
        )
    backtest = data.get("backtest")
    if backtest:
        mae = backtest["overall_mae"]
        lines.append(f"Erro medio do modelo (MAE) no backtest: {mae:.2f} kWh/h.")
    return "\n".join(lines)


def build_tools(
    db: Session, establishment: Establishment, settings: Settings
) -> list[StructuredTool]:
    def get_charger_status() -> str:
        return _describe_chargers(db, establishment)

    def get_demand_forecast() -> str:
        return _describe_demand_forecast(establishment, settings)

    return [
        StructuredTool.from_function(
            func=get_charger_status,
            name="get_charger_status",
            description=(
                "Devolve o status atual (livre, carregando, problema, reservado, offline) de "
                "cada carregador do estabelecimento."
            ),
        ),
        StructuredTool.from_function(
            func=get_demand_forecast,
            name="get_demand_forecast",
            description=(
                "Devolve a previsao de demanda das proximas 48h: picos esperados e qualidade "
                "do modelo."
            ),
        ),
    ]


def run_chat(
    db: Session,
    establishment: Establishment,
    message: str,
    history: list[ChatMessageIn],
    settings: Settings,
) -> ChatResponse:
    tools = build_tools(db, establishment, settings)
    tools_by_name = {tool.name: tool for tool in tools}
    model_with_tools = ChatOllama(
        model=settings.ollama_model, base_url=settings.ollama_base_url, temperature=0
    ).bind_tools(tools)

    messages: list = [SystemMessage(content=SYSTEM_PROMPT)]
    for entry in history[-HISTORY_WINDOW:]:
        if entry.role == "user":
            messages.append(HumanMessage(content=entry.content))
        else:
            messages.append(AIMessage(content=entry.content))
    messages.append(HumanMessage(content=message))

    tools_used: list[str] = []
    try:
        for _ in range(MAX_TOOL_ITERATIONS):
            response = model_with_tools.invoke(messages)
            messages.append(response)
            if not response.tool_calls:
                return ChatResponse(reply=response.content, tools_used=tools_used)

            for call in response.tool_calls:
                tool = tools_by_name.get(call["name"])
                result = (
                    tool.invoke(call["args"])
                    if tool
                    else f"Ferramenta '{call['name']}' nao existe."
                )
                tools_used.append(call["name"])
                messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
    except httpx.ConnectError:
        return ChatResponse(
            reply="Nao consegui falar com o assistente agora - confira se o Ollama esta rodando.",
            tools_used=tools_used,
        )

    return ChatResponse(
        reply="Nao consegui concluir a resposta em tempo habil - tente reformular a pergunta.",
        tools_used=tools_used,
    )
