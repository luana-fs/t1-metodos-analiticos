# t1-metodos-analiticos

# Simulador de Redes de Filas - Metodos Analiticos de Simulacao

Simulador de eventos discretos para uma **rede de filas** (Modulo 6 - filas
em tandem), utilizando o Metodo Congruente Linear para geracao de numeros
pseudoaleatorios. O motor de simulacao e generico: qualquer topologia de
rede (tandem, com bifurcacoes, com realimentacao etc.) e descrita apenas
por configuracao, sem alterar o codigo dos procedimentos de evento.

## Requisitos

- Python 3.x

## Como rodar

```bash
python simulador_fila.py
```

O `main()` executa a simulacao da rede de filas em tandem exigida na
entrega do Modulo 6:

- **Fila 1** - G/G/2/3 (2 servidores, capacidade 3), chegadas externas no
  intervalo [1,5], atendimento no intervalo [4,5]
- **Fila 2** - G/G/1/5 (1 servidor, capacidade 5), sem chegada externa,
  atendimento no intervalo [1,3]

A Fila 2 nao recebe clientes de fora da rede: 100% dos clientes atendidos
na Fila 1 sao roteados para a Fila 2 (filas em tandem/linha); ao terminarem
o atendimento na Fila 2, os clientes saem do sistema.

Ambas as filas partem vazias, o primeiro cliente chega na Fila 1 no tempo
2,5, e a simulacao roda ate consumir 100.000 numeros aleatorios.

A simulacao e reportada de duas formas, uma para cada fila:

1. **Execucao unica** (semente 42): distribuicao de probabilidade dos
   estados, tempos acumulados por estado, numero de clientes perdidos
   (fila cheia) e atendidos, alem dos indices de desempenho (populacao
   media, utilizacao, vazao e tempo de resposta).
2. **Lotes medios** (30 replicacoes com sementes diferentes e 5.000
   aleatorios de warm-up descartados por lote): media de cada metrica com
   intervalo de confianca de 95%, para reduzir o efeito da variabilidade
   de uma unica execucao.

O tempo global da simulacao (mesmo para as duas filas, pois compartilham o
mesmo relogio) aparece no bloco "Tempo total de simulacao" de cada fila.

## Estrutura do simulador: rede de filas com topologia configuravel

O simulador nao esta amarrado a duas filas fixas em tandem — o motor de
simulacao trabalha com uma **lista de filas** e um **roteamento por fila**,
o que permite descrever qualquer topologia de rede:

- `Fila`: classe com as propriedades de cada no da rede — servidores,
  capacidade, intervalo de chegada externa (`ch_min`/`ch_max`, `None` se a
  fila so recebe clientes roteados de outra fila), intervalo de
  atendimento (`at_min`/`at_max`), estado atual, tempos acumulados por
  estado, perdas e atendimentos concluidos.
- `roteamento`: lista de pares `(probabilidade, indice_da_fila_destino)`
  associada a cada fila, que define para onde vai um cliente ao terminar o
  atendimento nela. A probabilidade que sobra (1 - soma das
  probabilidades) representa a saida do cliente do sistema. E essa lista
  que define a "sintaxe" da topologia da rede (quem manda cliente pra
  quem, e com que probabilidade) — no cenario do Modulo 6, a Fila 1 tem
  `roteamento=[(1.0, indice_da_fila_2)]` (100% para a Fila 2) e a Fila 2
  tem `roteamento=[]` (sai do sistema).
- `Evento` / `Escalonador`: classes que representam o evento (tipo + tempo
  + fila) e o escalonador de eventos, implementado com uma fila de
  prioridade (`heapq`) ordenada pelo tempo do evento.
- Tipos de evento: `CHEGADA` (chegada externa de cliente na rede), `SAIDA`
  (fim de atendimento em uma fila, que dispara o roteamento para a proxima
  fila ou a saida do sistema) e `PASSAGEM` (chegada de um cliente vindo de
  outra fila da rede).
- `contabiliza_tempo` (equivalente ao `AcumulaTempo` do pseudocodigo do
  modulo) atualiza os tempos acumulados de **todas** as filas da rede a
  cada evento, nao apenas da fila diretamente afetada.

Para simular uma topologia diferente (mais filas, roteamento
probabilistico, realimentacao etc.), basta descrever cada fila em uma
lista de dicionarios (parametros da classe `Fila`) e informar, via
`roteamento`, os indices das filas de destino com suas probabilidades —
veja o exemplo em `main()`, em `simulador_fila.py`. O motor de simulacao
(`executar_simulacao`, `CHEGADA`, `SAIDA`, `PASSAGEM`) nao precisa ser
alterado para isso.

