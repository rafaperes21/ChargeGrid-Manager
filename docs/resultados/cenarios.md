# Resultados quantitativos - cenarios A vs B

> **Dados simulados/sinteticos - nao sao medicoes de um eletroposto real.** Gerado por `backend/scripts/cenarios.py` (`--seed 42 --date 2026-10-14`). Rodar de novo com os mesmos parametros reproduz esta tabela exatamente.

| Metrica | A - sem o sistema | B - com o sistema (autoconsumo) | B - reserva para a ponta | B com tarifa convencional* |
|---|---:|---:|---:|---:|
| Energia entregue aos veiculos (kWh) | 305,956 | 305,956 | 305,956 | 305,956 |
| Pico de potencia na rede (kW) | 35,600 | 35,600 | 33,936 | 35,600 |
| Pico de carga dos carregadores (kW) | 35,600 | 35,600 | 35,600 | 35,600 |
| Energia comprada da rede (kWh) | 305,956 | 236,192 | 239,665 | 236,192 |
| Custo de energia da rede (R$, sem impostos) | 241,52 | 255,44 | 242,02 | 186,45 |
| Energia renovavel local na recarga (%) | 0,0 | 22,8 | 21,7 | 22,8 |
| kWh evitados da rede (vs. A) | 0,000 | 69,764 | 66,291 | 69,764 |
| CO2 da energia da rede (kg) | 14,105 | 10,888 | 11,049 | 10,888 |
| CO2 evitado (kg, vs. A) | 0,000 | 3,216 | 3,056 | 3,216 |
| Geracao solar total (kWh) | 0,000 | 70,031 | 70,031 | 70,031 |
| Excedente solar nao usado (kWh) | 0,000 | 0,000 | 1,816 | 0,000 |
| Tempo medio de recarga (min) | 305,9 | 305,9 | 305,9 | 305,9 |
| Sessoes concluidas | 11 | 11 | 11 | 11 |
| Sessoes nao concluidas | 0 | 0 | 0 | 0 |

\* Linha informativa: o sistema B pagando a tarifa do cenario A, para separar o efeito de solar/bateria/controle de demanda do efeito da troca de modalidade tarifaria.

Modos da bateria: **autoconsumo** (default) descarrega sempre que o solar nao cobre a carga; **reserva para a ponta** (opcao do proprietario) guarda a energia solar e so descarrega na ponta da distribuidora (17h30-20h30) ou para segurar o limite contratado.

## Sensibilidade - 30 dias de demanda sorteados (seeds 1 a 30)

Um dia so e fragil: a ordem de chegada dos carros muda bastante o resultado. Mesma comparacao A x B, mesma configuracao, um dia de demanda diferente por seed.

| Metrica | Media A | Media B (autoconsumo) | Media B (reserva) | Dias B melhor que A | Dias B reserva melhor que A |
|---|---:|---:|---:|---:|---:|
| Pico de potencia na rede (kW) | 31,80 | 29,64 | 29,75 | 18 de 30 | 18 de 30 |
| Energia comprada da rede (kWh) | 339,17 | 268,80 | 273,07 | 30 de 30 | 30 de 30 |
| Custo de energia da rede (R$, sem impostos) | 267,73 | 253,26 | 241,05 | 25 de 30 | 28 de 30 |
| Energia renovavel local na recarga (%) | 0,00 | 21,71 | 20,25 | 30 de 30 | 30 de 30 |
| CO2 evitado (kg, vs. A) | 0,00 | 3,24 | 3,05 | 30 de 30 | 30 de 30 |

## Premissas e fontes

- Dia util 2026-10-14; 4 carregadores de 11 kW; limite contratado 40 kW (cenario B); FV 20 kWp e bateria 20 kWh / 10 kW, SoC minimo 10% e eficiencia 90% (premissas de simulacao, iguais ao seed da demo).
- A: tarifa convencional B3 (R$ 0,78938/kWh). B: Tarifa Branca B3 (ponta R$ 1,55911, intermediario R$ 1,03179, fora de ponta R$ 0,68501 por kWh). Fonte: ANEEL REH 3.596/2026 (Enel SP), subgrupo B3, TUSD+TE sem impostos e sem bandeira.
- Fator de emissao: 0,0461 kg CO2/kWh - MCTI/SIRENE - fator medio anual do SIN de 2025 (inventarios corporativos), planilha Inventario_2026_janago.xlsx.
- Mesmo dia de demanda nos dois cenarios; a demanda NAO reage ao preco (sem dado de elasticidade). Bateria comeca no SoC minimo; excedente solar sem credito (SCEE nao modelado); valores sem impostos e sem bandeira tarifaria.
