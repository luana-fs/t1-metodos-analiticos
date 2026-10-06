# Simulador T1 — versão Python

Conversão e adaptação do Java fornecido pelo grupo, conforme a imagem do T1.
Requer Python 3.9 ou superior e PyYAML. Não requer Java.

## Executar

Extraia o ZIP e abra um terminal na pasta extraída:

```bash
python -m pip install -r requirements.txt
python simulador_fila.py
```

Para escolher o modelo e salvar os resultados:

```bash
python simulador_fila.py modelo_t1.yml --saida resultados.txt --json resultados.json
```

No Windows, se necessário, substitua `python` por `py`.

## Modelo entregue

- Q1: 1 servidor, capacidade ilimitada, chegadas uniformes entre 2 e 4 minutos, serviço uniforme entre 1 e 2 minutos.
- Q2: 2 servidores, capacidade total 5, serviço uniforme entre 4 e 6 minutos.
- Q3: 2 servidores, capacidade total 10, serviço uniforme entre 5 e 15 minutos.
- Q1 envia 20% para Q2 e 80% para Q3.
- Q2 envia 30% para Q1, 50% para Q3 e 20% para fora.
- Q3 envia 70% para Q2 e 30% para fora.
- Filas inicialmente vazias; primeira chegada externa a Q1 em 2,0 minutos.
- Uma execução com semente 42 e exatamente 100.000 aleatórios; sem aquecimento.

## Entrada YAML

Aceita a marcação !PARAMETERS e os campos do exemplo da disciplina:
arrivals, queues, network, seeds, rndnumbersPerSeed e rndnumbers.
A ausência de capacity (ou null) representa capacidade ilimitada.
O restante das probabilidades de cada origem representa saída da rede.
A ordem das rotas em network define os intervalos usados no sorteio.
Pode-se adicionar filas, ligações, ciclos e fontes externas sem editar o motor.
Se seeds existir, rndnumbers é ignorado. Cada semente produz uma execução independente.
Sem seeds, a lista rndnumbers é utilizada na ordem informada, e seu tamanho define o orçamento.
As entradas de arrivals iniciam as fontes de chegadas externas.

## Conversão e correções

A estrutura preserva filas, eventos em fila de prioridade, tempos acumulados antes das mudanças de estado e roteamento probabilístico.
Foi reproduzido em Python o algoritmo java.util.Random.nextDouble, usando seed 42.
Um nextDouble conta como um aleatório, apesar das duas atualizações internas do gerador.
Os resultados NÃO são iguais ao Java enviado, pois houve correções:

1. Q1 -> Q2: 0,2 e Q1 -> Q3: 0,8, conforme a imagem.
2. Apenas a primeira chegada é pré-agendada; não há segunda cadeia externa duplicada.
3. Chegadas internas são eventos separados e não geram novas chegadas externas.
4. Q1 é realmente ilimitada, sem limite artificial de 1.000 clientes.
5. Ao esgotar aleatórios, não se inventa duração zero nem se força saída do cliente.
6. O relógio não avança além do instante do último sorteio.
7. Estados de probabilidade zero também são exibidos nas filas finitas.
8. A configuração foi retirada do código e colocada no YAML.

## Convenções de reprodução

- Ao chegar, sorteia-se primeiro o atendimento (quando há servidor livre), depois a próxima chegada externa.
- Ao sair, sorteia-se primeiro o novo atendimento na origem (se há espera), depois o destino.
- Toda conclusão consome um sorteio de roteamento, como no Java, inclusive com destino determinístico.
- Em empate temporal, saídas têm prioridade; demais empates seguem a ordem de agendamento.
- Transferências são eventos internos no mesmo instante, com trânsito zero.
- A ação associada ao último sorteio é registrada e a execução para imediatamente, sem processar outro evento, mesmo no mesmo instante. Clientes/eventos pendentes não são drenados.
- Todos os tempos são em minutos. A capacidade inclui espera e atendimento.
- As probabilidades dos estados são tempo no estado / tempo global.
- Fila ilimitada: são exibidos os estados até o máximo alcançado; demais estados têm tempo zero nesta execução.

Essas convenções são explícitas para comparação. Uma mesma semente em outro gerador ou outra ordem de sorteios não garante resultados iguais. Ainda é necessário comparar com o simulador do módulo 3, idealmente com uma lista comum de aleatórios e as mesmas convenções.

## Resultados incluídos

resultados.txt e resultados.json foram gerados por esta versão com modelo_t1.yml.
Tempo global: 50665,746894 minutos. Perdas: Q1=0, Q2=8, Q3=11505.
Esses valores pertencem à execução identificada, não são um gabarito universal.
O modelo Word não foi preenchido neste pacote.

## Testes

```bash
python -m unittest -v
```

Cobrem sequência conhecida do gerador Java, parada com um sorteio, orçamentos de 1 a 79 e 100.000, soma dos tempos/probabilidades, limites de capacidade, retorno sem gerar fonte externa, lista explícita e reprodução da execução.
