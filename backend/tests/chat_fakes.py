"""Modelo de chat falso para os testes dos assistentes - o CI nao tem Ollama.

Recebe um roteiro de respostas: string = resposta em texto (transmitida palavra a palavra);
lista de (nome, args) = pedido de ferramentas. Guarda as mensagens recebidas em cada chamada,
para o teste conferir o que o modelo "viu" (prompt, resultado das ferramentas)."""

import json

from langchain_core.messages import AIMessageChunk


class _BoundFake:
    def __init__(self, parent):
        self.parent = parent

    def stream(self, messages):
        return self.parent._stream(messages, "tools")


class FakeChatModel:
    """`modes` registra se cada chamada foi com ferramentas (`tools`) ou sem (`plain`)."""

    def __init__(self, script):
        self.script = list(script)
        self.calls: list[list] = []
        self.modes: list[str] = []
        self.bound_tools: list = []

    def bind_tools(self, tools):
        self.bound_tools = list(tools)
        return _BoundFake(self)

    def stream(self, messages):
        return self._stream(messages, "plain")

    def _stream(self, messages, mode):
        self.calls.append(list(messages))
        self.modes.append(mode)
        step = self.script.pop(0)
        if isinstance(step, str):
            words = step.split(" ")
            for i, word in enumerate(words):
                yield AIMessageChunk(content=word if i == 0 else " " + word)
            return
        yield AIMessageChunk(
            content="",
            tool_call_chunks=[
                {"name": name, "args": json.dumps(args), "id": f"call-{i}", "index": i}
                for i, (name, args) in enumerate(step)
            ],
        )

    @property
    def tool_names(self):
        return [tool.name for tool in self.bound_tools]


class FailingChatModel:
    def bind_tools(self, tools):
        return self

    def stream(self, messages):
        raise ConnectionError("ollama fora do ar")
        yield  # pragma: no cover


def factory_for(model):
    return lambda settings: model
