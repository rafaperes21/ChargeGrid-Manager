"""Loop de agente compartilhado pelos dois assistentes (Sprint 4, M7).

Compartilha so a MECANICA (chamar o modelo, executar ferramentas, transmitir tokens) - prompt
e ferramentas sao de cada assistente e nunca se misturam (`services/chatbot.py` para o
proprietario, `services/chatbot_customer.py` para o cliente). Regras que valem para os dois:

- Barreira de emergencia antes do modelo (`chatbot_safety`).
- Falha do modelo vira mensagem honesta de indisponibilidade, nunca resposta inventada.
- Janela de historico limitada (`HISTORY_WINDOW` mensagens).
- Log de depuracao com tamanho da pergunta e ferramentas chamadas - sem o texto da pergunta,
  que pode ter dado pessoal.

`model_factory` existe para os testes injetarem um modelo falso: o CI nao tem Ollama.
"""

import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langchain_ollama import ChatOllama
from ollama import ResponseError

from app.core.config import Settings
from app.schemas.chatbot import ChatMessageIn, ChatResponse
from app.services.chatbot_safety import is_emergency

logger = logging.getLogger(__name__)

HISTORY_WINDOW = 10

_NOTHING_CONSULTED = " Nenhuma informação foi consultada."


def unavailable_reply(error: Exception, settings: Settings) -> str:
    """Resposta honesta quando o modelo falha - nomeando a causa. Antes era sempre "confira se
    o Ollama está rodando", inclusive quando o Ollama estava no ar e so faltava baixar o modelo."""
    if isinstance(error, httpx.ConnectError | ConnectionError):
        return (
            f"Não consegui conectar ao Ollama em {settings.ollama_base_url} — confira se ele está "
            "rodando (`ollama serve` ou o serviço do sistema)." + _NOTHING_CONSULTED
        )
    if isinstance(error, ResponseError) and error.status_code == 404:
        return (
            f"O modelo {settings.ollama_model} não está instalado no Ollama — rode "
            f"`ollama pull {settings.ollama_model}`." + _NOTHING_CONSULTED
        )
    return (
        "O assistente teve um erro inesperado ao consultar o modelo — veja o log do backend."
        + _NOTHING_CONSULTED
    )


ModelFactory = Callable[[Settings], BaseChatModel]


def default_model_factory(settings: Settings) -> BaseChatModel:
    return ChatOllama(model=settings.ollama_model, base_url=settings.ollama_base_url, temperature=0)


@dataclass(frozen=True)
class Assistant:
    """Identidade de um assistente: nome (para log), prompt, ferramentas e resposta fixa de
    emergencia. Montado por requisicao, com as ferramentas ja presas ao usuario/estabelecimento
    autenticado."""

    name: str
    system_prompt: str
    tools: list[StructuredTool]
    emergency_reply: str


def _build_messages(assistant: Assistant, message: str, history: list[ChatMessageIn]) -> list:
    messages: list = [SystemMessage(content=assistant.system_prompt)]
    for entry in history[-HISTORY_WINDOW:]:
        cls = HumanMessage if entry.role == "user" else AIMessage
        messages.append(cls(content=entry.content))
    messages.append(HumanMessage(content=message))
    return messages


def _run_tools(assistant: Assistant, response: AIMessage, used: list[str]) -> list[str]:
    """Executa as ferramentas pedidas (chamadas identicas repetidas na mesma resposta rodam
    uma vez so) e devolve o texto de cada resultado."""
    tools_by_name = {tool.name: tool for tool in assistant.tools}
    results: list[str] = []
    seen: set[str] = set()
    for call in response.tool_calls:
        key = f"{call['name']}:{sorted(call['args'].items())}"
        if key in seen:
            continue
        seen.add(key)
        tool = tools_by_name.get(call["name"])
        try:
            result = (
                tool.invoke(call["args"]) if tool else f"Ferramenta '{call['name']}' nao existe."
            )
        except Exception:  # ferramenta quebrada nao derruba a conversa nem vira chute
            logger.exception("Ferramenta %s falhou", call["name"])
            result = "Nao consegui consultar essa informacao agora."
        used.append(call["name"])
        results.append(f"[{call['name']}] {result}")
    return results


def _answer_messages(
    assistant: Assistant, message: str, history: list[ChatMessageIn], results: list[str]
) -> list:
    """Mensagens do passo final: a pergunta com os dados consultados em TEXTO, sem mensagens
    de ferramenta. No teste ao vivo com llama3.1:8b (Ollama), devolver os resultados como
    `ToolMessage` fazia o modelo re-chamar a mesma ferramenta em loop ou responder "essas sao
    as informacoes" sem repetir nenhum numero; com os dados no texto ele responde com eles."""
    messages = _build_messages(assistant, message, history)[:-1]
    data = "\n".join(f"- {r}" for r in results)
    messages.append(
        HumanMessage(
            content=(
                f"{message}\n\nDados consultados agora nas ferramentas do sistema (use so estes "
                f"numeros; quem perguntou nao viu estes dados, entao repita os valores):\n{data}"
                "\n\nSe alguma parte da pergunta nao esta coberta por estes dados, diga que nao "
                "consultou essa parte - nao deduza nem complete por conta propria."
            )
        )
    )
    return messages


def _log(assistant: Assistant, message: str, used: list[str], outcome: str) -> None:
    logger.info(
        "chatbot=%s msg_len=%d tools=%s outcome=%s", assistant.name, len(message), used, outcome
    )


def _stream_text(model, messages) -> Iterator[tuple]:
    """Transmite texto enquanto o modelo nao esta pedindo ferramenta: `("token", pedaco)` a
    cada pedaco e, por ultimo, `("end", texto_completo, mensagem_agregada_ou_None)`."""
    aggregated = None
    text = ""
    for chunk in model.stream(messages):
        aggregated = chunk if aggregated is None else aggregated + chunk
        piece = chunk.content if isinstance(chunk.content, str) else ""
        # ruido tipo "vou consultar..." antes de um tool call nao vai pra tela
        if piece and not aggregated.tool_call_chunks:
            text += piece
            yield ("token", piece)
    yield ("end", text, aggregated)


def stream_agent(
    assistant: Assistant,
    message: str,
    history: list[ChatMessageIn],
    settings: Settings,
    model_factory: ModelFactory | None = None,
) -> Iterator[dict]:
    """Eventos da resposta, na ordem: `tool` (ferramenta chamada), `token` (pedaco de texto) e
    um `done` final com a resposta inteira e as ferramentas usadas.

    Duas etapas: (1) o modelo COM ferramentas decide o que consultar - pode pedir varias de
    uma vez; (2) se consultou algo, o modelo SEM ferramentas escreve a resposta a partir dos
    dados (ver `_answer_messages`). Sem encadeamento de ferramentas (consultar B dependendo
    do resultado de A): as ferramentas daqui sao independentes, e cada rodada a mais custa
    ~30 s num LLM local em CPU.
    """
    used: list[str] = []
    if is_emergency(message):
        _log(assistant, message, used, "emergency")
        yield {"type": "token", "text": assistant.emergency_reply}
        yield {"type": "done", "reply": assistant.emergency_reply, "tools_used": used}
        return

    try:
        base_model = (model_factory or default_model_factory)(settings)
        model_with_tools = base_model.bind_tools(assistant.tools)

        text, decision = "", None
        for event in _stream_text(model_with_tools, _build_messages(assistant, message, history)):
            if event[0] == "token":
                yield {"type": "token", "text": event[1]}
            else:
                _, text, decision = event
        if decision is None or not decision.tool_calls:
            _log(assistant, message, used, "ok")
            reply = text or (str(decision.content) if decision else "")
            yield {"type": "done", "reply": reply, "tools_used": used}
            return

        results = _run_tools(assistant, decision, used)
        for name in used:
            yield {"type": "tool", "name": name}

        text = ""
        for event in _stream_text(
            base_model, _answer_messages(assistant, message, history, results)
        ):
            if event[0] == "token":
                yield {"type": "token", "text": event[1]}
            else:
                text = event[1]
        _log(assistant, message, used, "ok")
        yield {"type": "done", "reply": text, "tools_used": used}
    except Exception as error:
        logger.exception("Falha ao consultar o modelo do assistente %s", assistant.name)
        _log(assistant, message, used, "unavailable")
        reply = unavailable_reply(error, settings)
        yield {"type": "token", "text": reply}
        yield {"type": "done", "reply": reply, "tools_used": used}


def run_agent(
    assistant: Assistant,
    message: str,
    history: list[ChatMessageIn],
    settings: Settings,
    model_factory: ModelFactory | None = None,
) -> ChatResponse:
    """Versao sem streaming - consome o mesmo gerador, para os dois caminhos nunca divergirem."""
    final = None
    for event in stream_agent(assistant, message, history, settings, model_factory):
        if event["type"] == "done":
            final = event
    return ChatResponse(reply=final["reply"], tools_used=final["tools_used"])
