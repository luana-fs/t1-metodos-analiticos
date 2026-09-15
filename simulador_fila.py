# =============================================================================
# Simulador de Redes de Filas - Metodos Analiticos de Simulacao
# Modulo 6: filas em tandem / rede de filas com topologia configuravel
# =============================================================================

import heapq

# ---------------------------------------------------------------------------
# ETAPA 1: Gerador de Números Pseudoaleatórios (Método Congruente Linear)
# ---------------------------------------------------------------------------
# Parâmetros do gerador congruente linear: X(n+1) = (a * X(n) + c) % M
a = 1103515245
c = 12345
M = 2**31  # 2147483648
previous = 42  # semente inicial (seed)
count = 0       # quantidade de números pseudoaleatórios ainda disponíveis


def NextRandom():
    """
    Gera um número pseudoaleatório normalizado entre 0 e 1
    usando o Método Congruente Linear.
    Armazena o último valor gerado para a próxima chamada.
    """
    global previous, count
    previous = ((a * previous) + c) % M
    count -= 1  # decrementa o contador de números disponíveis
    return previous / M


def tempo_entre(minimo, maximo):
    """
    Gera um tempo aleatório no intervalo [minimo, maximo)
    usando o gerador de números pseudoaleatórios.
    Usa fórmula U(A, B) = A + [(B-A) * U(0,1)]
    """
    return minimo + ((maximo - minimo) * NextRandom())


# ---------------------------------------------------------------------------
# ETAPA 2: Estruturas do Simulador - Fila, Evento e Escalonador
# ---------------------------------------------------------------------------
#
# A rede de filas é descrita por uma LISTA de filas (ver classe Fila). Cada
# fila é identificada pelo seu índice nessa lista. A "sintaxe" usada para
# descrever a topologia da rede e o roteamento entre as filas é a lista
# `roteamento` de cada fila: pares (probabilidade, indice_da_fila_destino).
# A probabilidade que sobra (1 - soma das probabilidades) é a chance do
# cliente sair da rede ao terminar o atendimento naquela fila. Isso permite
# descrever qualquer topologia (tandem, paralela, com realimentação etc.)
# sem alterar o motor de simulação — só a configuração de cada cenário.
# ---------------------------------------------------------------------------

# Tipos de evento
TIPO_CHEGADA = "CHEGADA"     # chegada externa de um cliente na rede
TIPO_SAIDA = "SAIDA"         # fim de atendimento em uma fila
TIPO_PASSAGEM = "PASSAGEM"   # cliente roteado de uma fila para outra


class Fila:
    """
    Representa uma fila (nó) dentro da rede de filas.

    - servidores: número de servidores (c)
    - capacidade: capacidade máxima de clientes (K), incluindo os em atendimento
    - ch_min / ch_max: intervalo de tempo entre chegadas EXTERNAS (None se a
      fila não recebe clientes de fora da rede, apenas de outras filas)
    - at_min / at_max: intervalo de tempo de atendimento desta fila
    - roteamento: lista de tuplas (probabilidade, indice_fila_destino) que
      define, ao final do atendimento, para onde é enviado o cliente. A
      probabilidade restante (1 - soma das probabilidades) representa a
      saída do cliente do sistema.
    """

    def __init__(self, nome, servidores, capacidade,
                 ch_min=None, ch_max=None, at_min=None, at_max=None,
                 roteamento=None):
        self.nome = nome
        self.servidores = servidores
        self.capacidade = capacidade
        self.ch_min = ch_min
        self.ch_max = ch_max
        self.at_min = at_min
        self.at_max = at_max
        self.roteamento = roteamento or []

        # Estado dinâmico da fila
        self.clientes = 0
        self.perdas = 0
        self.atendidos = 0  # nº de atendimentos concluídos (para a vazão)
        self.times = [0.0] * (capacidade + 1)

    def tem_chegada_externa(self):
        return self.ch_min is not None


class Evento:
    """
    Representa um evento do escalonador: possui um tipo (chegada, saída ou
    passagem), o tempo em que deve ocorrer e a fila à qual se refere.
    Implementa __lt__ (equivalente ao compareTo em Java) para que o
    escalonador baseado em heap mantenha a ordem correta pelo tempo.
    """

    def __init__(self, tempo, tipo, fila_idx):
        self.tempo = tempo
        self.tipo = tipo
        self.fila_idx = fila_idx

    def __lt__(self, other):
        return self.tempo < other.tempo


class Escalonador:
    """Fila de prioridade de eventos, ordenada pelo tempo de ocorrência."""

    def __init__(self):
        self._heap = []

    def agenda(self, tempo, tipo, fila_idx):
        heapq.heappush(self._heap, Evento(tempo, tipo, fila_idx))

    def proximo(self):
        if not self._heap:
            return None
        return heapq.heappop(self._heap)

    def __len__(self):
        return len(self._heap)

    def maior_tempo(self):
        return max(e.tempo for e in self._heap)


# Variáveis globais da simulação (rede de filas)
tempo_global = 0.0
filas = []               # lista de objetos Fila que compõem a rede
escalonador = None       # objeto Escalonador


def init_simulacao(filas_config, seed=42, num_randoms=100000):
    """
    Inicializa a rede de filas e o escalonador a partir de uma lista de
    configurações de fila (dicionários, um por nó da rede) e uma semente
    para o gerador. O índice de cada dicionário na lista define o índice
    usado em `roteamento` para apontar para aquela fila.
    """
    global tempo_global, filas, escalonador, previous, count

    tempo_global = 0.0
    filas = [Fila(**cfg) for cfg in filas_config]
    escalonador = Escalonador()
    previous = seed
    count = num_randoms


def agenda_evento(tempo, tipo, fila_idx):
    escalonador.agenda(tempo, tipo, fila_idx)


def proximo_evento():
    return escalonador.proximo()


def contabiliza_tempo(tempo_evento):
    """
    Acumula, para TODAS as filas da rede, o tempo que cada uma permaneceu
    no seu estado atual antes de o tempo global avançar para o instante do
    próximo evento (AcumulaTempo generalizado para múltiplas filas).
    """
    global tempo_global
    dt = tempo_evento - tempo_global
    for fila in filas:
        if 0 <= fila.clientes <= fila.capacidade:
            fila.times[fila.clientes] += dt
    tempo_global = tempo_evento


# ---------------------------------------------------------------------------
# ETAPA 3: Procedimentos CHEGADA, SAIDA e PASSAGEM
# ---------------------------------------------------------------------------

def _entra_na_fila(fila_idx):
    """
    Procedimento comum a CHEGADA e PASSAGEM: tenta inserir o cliente na
    fila indicada, agendando o fim de seu atendimento caso haja servidor
    livre, ou contabilizando perda caso a fila esteja cheia.
    """
    fila = filas[fila_idx]
    if fila.clientes < fila.capacidade:
        fila.clientes += 1
        if fila.clientes <= fila.servidores:
            tempo_saida = tempo_global + tempo_entre(fila.at_min, fila.at_max)
            agenda_evento(tempo_saida, TIPO_SAIDA, fila_idx)
    else:
        fila.perdas += 1


def _decide_roteamento(fila):
    """
    Sorteia, usando um número pseudoaleatório, o destino de um cliente que
    acabou de ser atendido em `fila`. Retorna o índice da fila de destino,
    ou None caso o cliente saia do sistema. Quando a fila tem um único
    destino com probabilidade 1.0 (caso das filas em tandem), o resultado
    é sempre aquele destino, sem depender do valor sorteado.
    """
    if not fila.roteamento:
        return None
    r = NextRandom()
    acumulado = 0.0
    for probabilidade, destino in fila.roteamento:
        acumulado += probabilidade
        if r < acumulado:
            return destino
    return None  # probabilidade restante: cliente sai do sistema


def CHEGADA(fila_idx, tempo_evento):
    """Chegada externa de um cliente na fila `fila_idx`."""
    contabiliza_tempo(tempo_evento)
    fila = filas[fila_idx]

    _entra_na_fila(fila_idx)

    if count > 0:
        tempo_chegada = tempo_global + tempo_entre(fila.ch_min, fila.ch_max)
        agenda_evento(tempo_chegada, TIPO_CHEGADA, fila_idx)


def SAIDA(fila_idx, tempo_evento):
    """Fim de atendimento de um cliente na fila `fila_idx`."""
    contabiliza_tempo(tempo_evento)
    fila = filas[fila_idx]

    fila.clientes -= 1
    fila.atendidos += 1

    # Se ainda há clientes esperando para serem atendidos
    if fila.clientes >= fila.servidores:
        tempo_saida = tempo_global + tempo_entre(fila.at_min, fila.at_max)
        agenda_evento(tempo_saida, TIPO_SAIDA, fila_idx)

    # Roteia o cliente que terminou o atendimento para a próxima fila
    # da rede (evento de PASSAGEM) ou o cliente sai do sistema.
    destino_idx = _decide_roteamento(fila)
    if destino_idx is not None:
        agenda_evento(tempo_global, TIPO_PASSAGEM, destino_idx)


def PASSAGEM(fila_idx, tempo_evento):
    """Chegada de um cliente vindo de outra fila da rede (roteamento interno)."""
    contabiliza_tempo(tempo_evento)
    _entra_na_fila(fila_idx)


# ---------------------------------------------------------------------------
# ETAPA 4 e 5: Cálculo e exibição de resultados
# ---------------------------------------------------------------------------

def calcular_resultados(fila, tempo_total):
    """Calcula probabilidades e índices de desempenho de uma fila da rede."""
    probs = []
    for i in range(fila.capacidade + 1):
        probs.append(fila.times[i] / tempo_total if tempo_total > 0 else 0)

    populacao_media = sum(i * probs[i] for i in range(fila.capacidade + 1))

    if fila.servidores == 1:
        utilizacao = 1.0 - probs[0]
    else:
        utilizacao = sum((min(i, fila.servidores) / fila.servidores) * probs[i]
                         for i in range(fila.capacidade + 1))

    # Vazão empírica: nº de atendimentos concluídos / tempo total.
    # Funciona tanto para filas com chegada externa quanto para filas que
    # só recebem clientes roteados internamente pela rede (como a Fila 2
    # em um sistema tandem, que não tem chegada externa própria).
    vazao = fila.atendidos / tempo_total if tempo_total > 0 else 0

    tempo_resposta = populacao_media / vazao if vazao > 0 else 0

    return {
        "tempo_total": tempo_total,
        "perdas": fila.perdas,
        "atendidos": fila.atendidos,
        "times": list(fila.times),
        "probs": probs,
        "populacao_media": populacao_media,
        "utilizacao": utilizacao,
        "vazao": vazao,
        "tempo_resposta": tempo_resposta,
    }


def exibir_resultados(nome_fila, resultados):
    """Exibe a distribuição de probabilidade e os índices de desempenho de uma fila."""
    print("=" * 60)
    print(f"  Resultados da Simulação: {nome_fila}")
    print("=" * 60)

    print(f"\nTempo total de simulação: {resultados['tempo_total']:.4f}")
    print(f"Clientes perdidos (fila cheia): {resultados['perdas']}")
    print(f"Clientes atendidos: {resultados['atendidos']}")
    print()

    print("Estado | Tempo Acumulado |  Probabilidade")
    print("-" * 45)
    for i in range(len(resultados['probs'])):
        prob = resultados['probs'][i]
        tempo = resultados['times'][i]
        print(f"  {i:>3}  | {tempo:>14.4f}  |  {prob:.6f} ({prob*100:.2f}%)")

    print()
    print("-" * 45)
    print("Índices de Desempenho:")
    print("-" * 45)
    print(f"  População média (E[N]):    {resultados['populacao_media']:.4f} clientes")
    print(f"  Utilização:                {resultados['utilizacao']:.4f} ({resultados['utilizacao']*100:.2f}%)")
    print(f"  Vazão (throughput):        {resultados['vazao']:.4f} clientes/unidade de tempo")
    print(f"  Tempo de resposta (E[W]):  {resultados['tempo_resposta']:.4f} unidades de tempo")
    prob_perda = resultados['probs'][-1]
    print(f"  Prob. de perda P(K={len(resultados['probs'])-1}):   {prob_perda:.6f} ({prob_perda*100:.2f}%)")
    print("=" * 60)
    print()


# ---------------------------------------------------------------------------
# Execução de uma simulação completa da rede de filas
# ---------------------------------------------------------------------------

def executar_simulacao(filas_config, eventos_iniciais, seed,
                       num_randoms=100000, warmup_randoms=0):
    """
    Executa uma simulação completa de uma rede de filas.

    - filas_config: lista de dicionários com os parâmetros de cada Fila
      (ver classe Fila). O índice de cada dicionário na lista define o
      índice da fila usado em `roteamento` e em `eventos_iniciais`.
    - eventos_iniciais: lista de tuplas (fila_idx, tempo) com as chegadas
      externas iniciais a agendar antes do início do laço principal.
    - warmup_randoms: quantidade de aleatórios usados na fase de
      aquecimento (warm-up); os tempos acumulados dessa fase são
      descartados ao final para eliminar o efeito do estado inicial.

    Retorna uma lista de dicionários de resultados, um por fila da rede,
    na mesma ordem de `filas_config`.
    """
    total_randoms = num_randoms + warmup_randoms
    init_simulacao(filas_config, seed, total_randoms)

    for fila_idx, tempo in eventos_iniciais:
        agenda_evento(tempo, TIPO_CHEGADA, fila_idx)

    def processa_evento(evento):
        if evento.tipo == TIPO_CHEGADA:
            CHEGADA(evento.fila_idx, evento.tempo)
        elif evento.tipo == TIPO_SAIDA:
            SAIDA(evento.fila_idx, evento.tempo)
        elif evento.tipo == TIPO_PASSAGEM:
            PASSAGEM(evento.fila_idx, evento.tempo)

    # ---------------------------------------------------------------------
    # WARM-UP (Aquecimento): roda normalmente, mas descarta os tempos
    # acumulados ao final, mantendo apenas o estado atual das filas.
    # ---------------------------------------------------------------------
    if warmup_randoms > 0:
        limite_warmup = num_randoms  # count vai de total até 0
        while count > limite_warmup:
            evento = proximo_evento()
            if evento is None:
                break
            processa_evento(evento)
        for fila in filas:
            fila.times = [0.0] * (fila.capacidade + 1)
            fila.perdas = 0
            fila.atendidos = 0

    # Loop principal: fase de coleta de dados
    while count > 0:
        evento = proximo_evento()
        if evento is None:
            break
        processa_evento(evento)

    # Contabiliza o tempo restante no último estado de cada fila
    if len(escalonador) > 0:
        contabiliza_tempo(escalonador.maior_tempo())

    # O warm-up zera os tempos acumulados (mas não o relógio da simulação),
    # então a soma dos tempos acumulados de uma fila já corresponde ao
    # tempo "total" da fase de coleta, excluindo o período de warm-up.
    tempo_total_coleta = sum(filas[0].times) if filas else 0.0

    return [calcular_resultados(fila, tempo_total_coleta) for fila in filas]


# ---------------------------------------------------------------------------
# LOTES MÉDIOS (Mean Batches) e INTERVALOS DE CONFIANÇA
# ---------------------------------------------------------------------------

def executar_lotes(filas_config, eventos_iniciais, sementes,
                   num_randoms=100000, warmup_randoms=0):
    """
    Executa a simulação da rede várias vezes (uma por semente) e retorna,
    para cada lote, a lista de resultados por fila.
    """
    resultados_lotes = []
    for semente in sementes:
        resultado = executar_simulacao(filas_config, eventos_iniciais, semente,
                                       num_randoms, warmup_randoms)
        resultados_lotes.append(resultado)
    return resultados_lotes


T_STUDENT_95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    25: 2.060, 29: 2.045, 30: 2.042
}


def obter_t_student(gl):
    if gl in T_STUDENT_95:
        return T_STUDENT_95[gl]
    if gl > 30:
        return 1.96
    chaves = sorted(T_STUDENT_95.keys())
    for i in range(len(chaves) - 1):
        if chaves[i] <= gl < chaves[i + 1]:
            return T_STUDENT_95[chaves[i]]
    return 1.96


def calcular_intervalo_confianca(valores):
    n = len(valores)
    if n < 2:
        media = valores[0] if n == 1 else 0
        return media, 0, media, media

    media = sum(valores) / n
    variancia = sum((x - media) ** 2 for x in valores) / (n - 1)
    desvio_padrao = variancia ** 0.5

    t = obter_t_student(n - 1)
    margem = t * (desvio_padrao / (n ** 0.5))

    return media, margem, media - margem, media + margem


def exibir_resultados_lotes(nome_fila, resultados_lotes_fila, cap):
    """resultados_lotes_fila: lista com o dicionário de resultados de UMA fila por lote."""
    num_lotes = len(resultados_lotes_fila)

    print("=" * 70)
    print(f"  Resultados com Lotes Médios: {nome_fila}")
    print(f"  Número de lotes: {num_lotes}")
    print("=" * 70)

    print("\nEstado |  Prob. Média  |      IC 95%")
    print("-" * 55)
    for i in range(cap + 1):
        probs_estado = [r['probs'][i] for r in resultados_lotes_fila]
        media, margem, li, ls = calcular_intervalo_confianca(probs_estado)
        print(f"  {i:>3}  |  {media:.6f}   |  [{li:.6f} ; {ls:.6f}]")

    print()
    print("-" * 55)
    print("Índices de Desempenho (média dos lotes com IC 95%):")
    print("-" * 55)

    for chave, rotulo, fmt in [
        ("populacao_media", "E[N]  ", "{:.4f}"),
        ("utilizacao", "Util  ", "{:.4f}"),
        ("vazao", "Vazão ", "{:.4f}"),
        ("tempo_resposta", "E[W]  ", "{:.4f}"),
        ("perdas", "Perdas", "{:.1f}"),
    ]:
        vals = [r[chave] for r in resultados_lotes_fila]
        media, margem, li, ls = calcular_intervalo_confianca(vals)
        print(f"  {rotulo}: {fmt.format(media)}  [{fmt.format(li)} ; {fmt.format(ls)}]")

    print("=" * 70)
    print()


# ---------------------------------------------------------------------------
# MAIN: Execução da Simulação
# ---------------------------------------------------------------------------

def main():
    SEMENTES = [
        42, 137, 256, 1024, 7777, 12345, 31415, 65537, 99991, 100003,
        54321, 11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888, 98765,
        13579, 24680, 36912, 48024, 50000, 61111, 72222, 83333, 94444, 10007
    ]  # 30 sementes para 30 replicações
    NUM_RANDOMS = 100000
    WARMUP_RANDOMS = 5000

    # =====================================================================
    # MÓDULO 6: filas em tandem (rede de filas)
    #
    # Fila 1 - G/G/2/3, chegadas externas [1,5], atendimento [4,5]
    # Fila 2 - G/G/1/5, sem chegada externa, atendimento [1,3]
    # 100% dos clientes que saem da Fila 1 vão para a Fila 2; ao saírem da
    # Fila 2, vão embora do sistema.
    #
    # A topologia da rede é descrita abaixo por meio da lista `filas_tandem`
    # (uma entrada por fila) e do campo `roteamento` de cada fila, que
    # informa a probabilidade de um cliente atendido ali ser enviado para
    # outra fila da lista. Para simular uma topologia diferente, basta
    # alterar essa lista de configuração — o motor de simulação (funções
    # CHEGADA/SAIDA/PASSAGEM) não precisa mudar.
    # =====================================================================

    filas_tandem = [
        dict(nome="Fila 1 (G/G/2/3)", servidores=2, capacidade=3,
             ch_min=1.0, ch_max=5.0, at_min=4.0, at_max=5.0,
             roteamento=[(1.0, 1)]),  # 100% dos atendidos vão para a Fila 2
        dict(nome="Fila 2 (G/G/1/5)", servidores=1, capacidade=5,
             at_min=1.0, at_max=3.0,
             roteamento=[]),  # sai do sistema após atendimento
    ]
    eventos_iniciais_tandem = [(0, 2.5)]  # primeiro cliente chega na Fila 1 em t=2.5

    print("\n>>> Simulação Filas em Tandem - Execução única <<<\n")
    resultado_tandem = executar_simulacao(filas_tandem, eventos_iniciais_tandem,
                                          seed=42, num_randoms=NUM_RANDOMS)
    for fila_cfg, resultado in zip(filas_tandem, resultado_tandem):
        exibir_resultados(fila_cfg["nome"], resultado)

    print(">>> Simulação Filas em Tandem - Lotes médios (com warm-up) <<<\n")
    lotes_tandem = executar_lotes(filas_tandem, eventos_iniciais_tandem,
                                  SEMENTES, NUM_RANDOMS, WARMUP_RANDOMS)
    for idx, fila_cfg in enumerate(filas_tandem):
        exibir_resultados_lotes(fila_cfg["nome"],
                                [lote[idx] for lote in lotes_tandem],
                                fila_cfg["capacidade"])


if __name__ == "__main__":
    main()
