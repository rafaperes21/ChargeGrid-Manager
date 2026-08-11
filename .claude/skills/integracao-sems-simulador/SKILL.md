---
name: integracao-sems-simulador
description: Contrato de dados do SEMS+ (modelo Pull), serviço de polling e simulador de hardware que gera curvas P(t) realistas de carregamento. Use ao implementar o polling, o cliente SEMS+, o simulador do HCA G2 ou qualquer coisa que consuma leituras de potência dos carregadores.
---

# Integração SEMS+ e simulador de hardware

## 1. Por que existe um simulador

O HCA G2 não expõe API pública e o SEMS+ é **Pull-only**. Não há webhook, não há push.
O backend precisa perguntar periodicamente. Para desenvolvimento e demo, o simulador ocupa
o lugar do SEMS+ **atrás do mesmo contrato** — trocar um pelo outro é mudar
`SEMS_SOURCE=simulator|real` no `.env`, nada mais.

Se você se pegar escrevendo código que só funciona com o simulador, parou de simular.

## 2. Contrato — `ChargerReading`

Toda fonte de dados devolve uma lista disto:

```python
class ChargerReading(BaseModel):
    charger_serial: str        # identificador do HCA G2 no SEMS+
    timestamp: datetime        # UTC, hora DA LEITURA no dispositivo, não do fetch
    power_kw: Decimal          # potência instantânea
    status: ChargerStatus      # available | charging | error | offline
    total_energy_kwh: Decimal  # acumulador do dispositivo (monotônico)
    error_code: str | None
```

`timestamp` é a chave de idempotência. O polling repete leituras; processar duas vezes a mesma
leitura não pode duplicar energia.

## 3. Serviço de polling

- Intervalo: 1–5 min, configurável (`POLL_INTERVAL_SECONDS`, default 60).
- Roda como task assíncrona no startup do FastAPI (dev) ou worker separado (produção).
- Tolerância a falha: SEMS+ fora do ar não derruba a API. Loga, incrementa contador de falhas,
  tenta de novo com backoff. Após N falhas consecutivas, marca os carregadores como `offline`
  e alerta o dashboard.
- Persiste **toda** leitura em `charger_readings` (série temporal). É a matéria-prima do
  módulo de IA — não descarte, não agregue na ingestão.

Integração de energia entre leituras, por trapézio:

```
Δenergia_kwh = (P_anterior + P_atual) / 2 × Δt_horas
```

Multiplicar a última potência pelo intervalo inteiro superfatura o cliente na rampa de subida
e subfatura na descida. Use trapézio.

## 4. Curva P(t) do simulador

Uma sessão real de carregamento AC não é potência constante. O perfil, seguindo a curva da
atividade 5:

| Fase | SoC | Comportamento |
|---|---|---|
| Rampa | 0–2 min | sobe de 0 até a potência negociada |
| Platô | até ~80 % | potência ~constante = min(P_carregador, P_máx_do_OBC_do_veículo) |
| Taper | 80–100 % | decai aproximadamente linear até ~10 % da nominal |
| Fim | 100 % | cai a 0, status volta a `available` |

Sobre o platô, adicione ruído gaussiano de ±2 % — dado limpo demais entrega que é simulado e,
pior, faz o detector de anomalias da §IA aprender um padrão que não existe no mundo real.

O gargalo é o **veículo**, não o carregador: um carro com OBC de 7,4 kW num GW22K carrega a
7,4 kW. O simulador precisa modelar isso, senão as estimativas de tempo do portal do cliente
ficam otimistas demais.

## 5. Cenários que o simulador precisa saber gerar

Sem estes, não há como testar metade do produto:

- **Dia típico** por tipo de estabelecimento (shopping tem pico noturno e de fim de semana;
  empresa tem pico às 8h e platô o dia todo).
- **Horário de pico com todos os pontos ocupados** — para exercitar a fila.
- **Falha de equipamento**: consumo zerado por horas com carro plugado → alimenta a detecção
  de anomalias.
- **Pico anormal** de consumo → o outro lado da detecção de anomalias.
- **Histórico retroativo** de 60–90 dias, para o Prophet/LSTM ter o que treinar no dia 1.
  Sem isso o módulo de IA não tem demo.

Semente fixa (`--seed`) para reprodutibilidade. Uma demo que gera números diferentes a cada
execução é impossível de ensaiar.

## 6. Quando a API real aparecer

Implemente `SemsClient` como interface com duas realizações, `SimulatedSemsClient` e
`RealSemsClient`, escolhidas por config. O resto do sistema depende só da interface.
Autenticação, rate limit e paginação do SEMS+ real são desconhecidos — isole essas
preocupações dentro do `RealSemsClient`.
