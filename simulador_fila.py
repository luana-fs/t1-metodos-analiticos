# =============================================================================
# Simulador de Filas - Métodos Analíticos de Simulação
# =============================================================================

# ---------------------------------------------------------------------------
# ETAPA 1: Gerador de Números Pseudoaleatórios (Método Congruente Linear)
# ---------------------------------------------------------------------------
# Parâmetros do gerador congruente linear: X(n+1) = (a * X(n) + c) % M
a = 1103515245
c = 12345
M = 2**31  # 2147483648
previous = 42  # semente inicial (seed)

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


# ---------------------------------------------------------------------------
# ETAPA 2 e 3: Estruturas do Simulador
# ---------------------------------------------------------------------------

# Tipos de evento
TIPO_CHEGADA = "CHEGADA"
TIPO_PASSAGEM = "PASSAGEM"  # PA: passagem de cliente da fila 1 para fila 2
TIPO_SAIDA = "SAIDA"

# Variáveis globais da simulação (SISTEMA TANDEM)
tempo_global = 0.0       # tempo atual da simulação
fila1 = 0                # número de clientes na fila 1 (inclui os em atendimento)
fila2 = 0                # número de clientes na fila 2 (inclui os em atendimento)
servidores1 = 1          # número de servidores na fila 1
servidores2 = 1          # número de servidores na fila 2
capacidade1 = 5          # capacidade máxima da fila 1 (K1)
capacidade2 = 5          # capacidade máxima da fila 2 (K2)
count = 100000           # quantidade de números pseudoaleatórios a usar
perdas = 0               # clientes perdidos (fila 1 cheia)

# Intervalos de tempo (distribuição uniforme)
chegada_min = 3.0
chegada_max = 5.0
atendimento_min = 4.0
atendimento_max = 5.0

# Escalonador de eventos (lista de tuplas: (tempo, tipo))
escalonador = []

# Tempos acumulados por estado de cada fila
# times1[i] = tempo total em que a fila 1 esteve com i clientes
# times2[i] = tempo total em que a fila 2 esteve com i clientes
times1 = []
times2 = []


def init_simulacao(serv1, cap1, serv2, cap2, ch_min, ch_max, at_min, at_max, seed=42, num_randoms=100000):
    """Inicializa todas as variáveis globais para uma nova simulação TANDEM.
    
    Args:
        serv1, cap1: servidores e capacidade da fila 1
        serv2, cap2: servidores e capacidade da fila 2
        ch_min, ch_max: intervalo de tempo entre chegadas
        at_min, at_max: intervalo de tempo de atendimento
        seed: semente do gerador pseudoaleatório
        num_randoms: quantidade de números pseudoaleatórios a usar
    """
    global tempo_global, fila1, fila2, servidores1, servidores2, capacidade1, capacidade2
    global count, perdas, chegada_min, chegada_max, atendimento_min, atendimento_max
    global escalonador, times1, times2, previous

    tempo_global = 0.0
    fila1 = 0
    fila2 = 0
    servidores1 = serv1
    servidores2 = serv2
    capacidade1 = cap1
    capacidade2 = cap2
    count = num_randoms
    perdas = 0
    chegada_min = ch_min
    chegada_max = ch_max
    atendimento_min = at_min
    atendimento_max = at_max
    previous = seed
    escalonador = []
    times1 = [0.0] * (capacidade1 + 1)
    times2 = [0.0] * (capacidade2 + 1)


def tempo_entre(minimo, maximo):
    """
    Gera um tempo aleatório no intervalo [minimo, maximo)
    usando o gerador de números pseudoaleatórios.
    Usa fórmula U(A, B) = A + [(B-A) * U(0,1)]
    """
    return minimo + ((maximo - minimo) * NextRandom())


def agenda_evento(tempo, tipo):
    """Agenda um evento no escalonador."""
    escalonador.append((tempo, tipo))


def proximo_evento():
    """
    Remove e retorna o próximo evento do escalonador
    (o evento com menor tempo agendado).
    """
    if not escalonador:
        return None
    # Encontra o evento com menor tempo
    idx_min = 0
    for i in range(1, len(escalonador)):
        if escalonador[i][0] < escalonador[idx_min][0]:
            idx_min = i
    evento = escalonador.pop(idx_min)
    return evento


def contabiliza_tempo(tempo_evento):
    """
    Acumula o tempo que cada fila permaneceu no estado atual
    antes de mudar para o próximo estado. Aplica a contabilização
    para AMBAS as filas do sistema TANDEM.
    """
    global tempo_global
    dt = tempo_evento - tempo_global
    # Acumula tempo para fila 1 (se o estado é válido)
    if 0 <= fila1 <= capacidade1:
        times1[fila1] += dt
    # Acumula tempo para fila 2 (se o estado é válido)
    if 0 <= fila2 <= capacidade2:
        times2[fila2] += dt
    tempo_global = tempo_evento


# ---------------------------------------------------------------------------
# ETAPA 3: Procedimentos CHEGADA, PASSAGEM e SAIDA
# ---------------------------------------------------------------------------

def CHEGADA(tempo_evento):
    """
    Procedimento que simula a chegada de um cliente na fila 1 (sistema TANDEM).
    - Contabiliza o tempo no estado atual de ambas as filas
    - Se a fila 1 não estiver cheia, adiciona o cliente
    - Se houver servidor livre na fila 1, agenda uma PASSAGEM (PA) para fila 2
    - Sempre agenda a próxima chegada
    
    Nota: No sistema TANDEM, a saída da fila 1 é uma passagem para fila 2,
    não uma saída do sistema.
    """
    global fila1, perdas

    contabiliza_tempo(tempo_evento)

    # Verifica capacidade e variáveis de controle da FILA 1
    if fila1 < capacidade1:
        fila1 += 1
        # Se houver servidor livre na fila 1, agenda passagem (PA) para fila 2
        # Condição: fila1 <= servidores1
        if fila1 <= servidores1:
            tempo_passagem = tempo_global + tempo_entre(atendimento_min, atendimento_max)
            agenda_evento(tempo_passagem, TIPO_PASSAGEM)
    else:
        # Fila 1 cheia: cliente perdido
        perdas += 1

    # Agenda próxima chegada
    if count > 0:
        tempo_chegada = tempo_global + tempo_entre(chegada_min, chegada_max)
        agenda_evento(tempo_chegada, TIPO_CHEGADA)


def SAIDA(tempo_evento):
    """
    Procedimento que simula a saída de um cliente da fila 2 (sistema TANDEM).
    - Contabiliza o tempo no estado atual
    - Remove o cliente da fila 2 (saída do sistema)
    - Se ainda houver clientes esperando na fila 2, agenda nova saída
    
    Utiliza variáveis de controle da FILA 2: fila2, servidores2
    """
    global fila2

    contabiliza_tempo(tempo_evento)

    fila2 -= 1

    # Se ainda há clientes esperando para serem atendidos na fila 2
    # Condição: fila2 >= servidores2
    if fila2 >= servidores2:
        tempo_saida = tempo_global + tempo_entre(atendimento_min, atendimento_max)
        agenda_evento(tempo_saida, TIPO_SAIDA)


# Função PASSAGEM: Passagem de cliente entre fila 1 e fila 2
def PASSAGEM(tempo_evento):
    """
    Procedimento que simula a passagem de um cliente da fila 1 para fila 2 (SISTEMA TANDEM).
    
    Este procedimento é uma combinação de:
    - SAÍDA da fila 1 (termina atendimento em fila 1)
    - CHEGADA na fila 2 (inicia fila em fila 2)
    
    Processo:
    1. Contabiliza o tempo no estado atual de AMBAS as filas
    2. Remove cliente de fila 1 (fila1--)
    3. Se há clientes esperando em fila 1, agenda próxima PASSAGEM (PA)
    4. Tenta adicionar cliente em fila 2:
       - Se fila 2 não está cheia, adiciona e verifica servidor livre para agendar SAÍDA (SA)
       - Se fila 2 está cheia, cliente é perdido
    
    Nota: Usa variáveis de controle da FILA 1 quando remove cliente (fila1, servidores1)
          Usa variáveis de controle da FILA 2 quando adiciona cliente (fila2, servidores2, capacidade2)
    """
    global fila1, fila2, perdas

    # Etapa 1: Contabiliza tempo em AMBAS as filas
    contabiliza_tempo(tempo_evento)

    # Etapa 2: Remove cliente de fila 1 (saída de fila 1)
    fila1 -= 1

    # Etapa 3: Se há clientes esperando em fila 1, agenda próxima passagem
    # Condição: fila1 >= servidores1 (há clientes em espera que podem usar servidor)
    if fila1 >= servidores1:
        tempo_passagem = tempo_global + tempo_entre(atendimento_min, atendimento_max)
        agenda_evento(tempo_passagem, TIPO_PASSAGEM)

    # Etapa 4: Tenta adicionar cliente em fila 2 (chegada em fila 2)
    # Verifica capacidade da FILA 2
    if fila2 < capacidade2:
        # Fila 2 não está cheia: adiciona cliente
        fila2 += 1
        # Se houver servidor livre em fila 2, agenda saída do sistema
        # Condição: fila2 <= servidores2
        if fila2 <= servidores2:
            tempo_saida = tempo_global + tempo_entre(atendimento_min, atendimento_max)
            agenda_evento(tempo_saida, TIPO_SAIDA)
    else:
        # Fila 2 está cheia: cliente é perdido
        perdas += 1


# ---------------------------------------------------------------------------
# ETAPA 4 e 5: Exibição de resultados
# ---------------------------------------------------------------------------

def calcular_resultados_fila(times_fila, capacidade_fila, num_servidores, nome_fila="Fila"):
    """
    Calcula e retorna os resultados de uma execução da simulação para uma fila específica.
    
    Args:
        times_fila: array de tempos acumulados para cada estado da fila
        capacidade_fila: capacidade máxima da fila (K)
        num_servidores: número de servidores nesta fila
        nome_fila: nome descritivo da fila (para logs)
        
    Retorna um dicionário com probabilidades, tempos e índices de desempenho.
    """
    tempo_total = sum(times_fila)

    # Distribuição de probabilidade: tempo acumulado / tempo global
    probs = []
    for i in range(capacidade_fila + 1):
        probs.append(times_fila[i] / tempo_total if tempo_total > 0 else 0)

    # População média (E[N]): soma de i * P(i) para i = 0..K
    populacao_media = sum(i * probs[i] for i in range(capacidade_fila + 1))

    # Utilização: 1 - P(0) para 1 servidor; para c servidores: soma de min(i,c)/c * P(i)
    if num_servidores == 1:
        utilizacao = 1.0 - probs[0]
    else:
        utilizacao = sum((min(i, num_servidores) / num_servidores) * probs[i]
                         for i in range(capacidade_fila + 1))

    # Vazão (throughput): lambda_efetivo = lambda * (1 - P(K))
    # lambda = 1 / E[tempo_entre_chegadas] = 2 / (chegada_min + chegada_max)
    lambda_chegada = 2.0 / (chegada_min + chegada_max)
    vazao = lambda_chegada * (1.0 - probs[capacidade_fila])

    # Tempo de resposta médio (Little: E[N] = vazão * E[W])
    tempo_resposta = populacao_media / vazao if vazao > 0 else 0

    return {
        "tempo_total": tempo_total,
        "perdas": perdas,
        "times": list(times_fila),
        "probs": probs,
        "populacao_media": populacao_media,
        "utilizacao": utilizacao,
        "vazao": vazao,
        "tempo_resposta": tempo_resposta,
    }


# Mantém função anterior para compatibilidade (DEPRECATED)
def calcular_resultados():
    """
    DEPRECATED: Use calcular_resultados_fila() ao invés.
    Calcula resultados para a fila 2 (saída do sistema TANDEM).
    """
    return calcular_resultados_fila(times2, capacidade2, servidores2, "Fila 2")


def exibir_resultados(nome_fila, resultados):
    """
    Exibe a distribuição de probabilidade dos estados da fila
    e os índices de desempenho de uma única execução.
    """
    print("=" * 60)
    print(f"  Resultados da Simulação: {nome_fila}")
    print("=" * 60)

    print(f"\nTempo total de simulação: {resultados['tempo_total']:.4f}")
    print(f"Clientes perdidos (fila cheia): {resultados['perdas']}")
    print()

    # Distribuição de probabilidade dos estados
    print("Estado | Tempo Acumulado |  Probabilidade")
    print("-" * 45)
    for i in range(len(resultados['probs'])):
        prob = resultados['probs'][i]
        tempo = resultados['times'][i]
        print(f"  {i:>3}  | {tempo:>14.4f}  |  {prob:.6f} ({prob*100:.2f}%)")

    # ETAPA 5: Índices de desempenho
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
# Função auxiliar: executa uma simulação completa e retorna os resultados
# ---------------------------------------------------------------------------

def executar_simulacao(serv1, cap1, serv2, cap2, ch_min, ch_max, at_min, at_max, seed,
                       num_randoms=100000, warmup_randoms=0):
    """
    Executa uma simulação completa TANDEM com os parâmetros dados e retorna os resultados.
    
    Args:
        serv1, cap1: número de servidores e capacidade da fila 1
        serv2, cap2: número de servidores e capacidade da fila 2
        ch_min, ch_max: intervalo de tempo entre chegadas
        at_min, at_max: intervalo de tempo de atendimento
        seed: semente do gerador pseudoaleatório
        num_randoms: quantidade de números pseudoaleatórios a usar
        warmup_randoms: quantidade de aleatórios usados na fase de aquecimento (warm-up).
                       Durante o warm-up, a simulação roda normalmente mas os tempos acumulados são
                       descartados ao final dessa fase, eliminando o efeito do estado inicial.
    """
    global perdas
    total_randoms = num_randoms + warmup_randoms
    init_simulacao(serv1, cap1, serv2, cap2, ch_min, ch_max, at_min, at_max, seed, total_randoms)

    # Primeira chegada no tempo fixo 3.0 (conforme especificação)
    agenda_evento(3.0, TIPO_CHEGADA)

    # ---------------------------------------------------------------------------
    # WARM-UP (Aquecimento)
    # Descarta os primeiros eventos para eliminar o efeito do estado inicial.
    # A simulação roda normalmente, mas ao final do warm-up os tempos acumulados
    # são zerados, mantendo apenas o estado atual de ambas as filas como ponto de partida
    # para a fase de coleta de dados (análise estacionária).
    # ---------------------------------------------------------------------------
    if warmup_randoms > 0:
        limite_warmup = num_randoms  # count vai de total até 0; warm-up acaba quando count == num_randoms
        while count > limite_warmup:
            evento = proximo_evento()
            if evento is None:
                break
            tempo_evento, tipo_evento = evento
            if tipo_evento == TIPO_CHEGADA:
                CHEGADA(tempo_evento)
            elif tipo_evento == TIPO_PASSAGEM:
                PASSAGEM(tempo_evento)
            elif tipo_evento == TIPO_SAIDA:
                SAIDA(tempo_evento)
        # Descarta os tempos acumulados durante o warm-up e reseta contadores
        times1[:] = [0.0] * (cap1 + 1)
        times2[:] = [0.0] * (cap2 + 1)
        perdas_antes = perdas  # guarda para não contar perdas do warm-up

    # Loop principal: fase de coleta de dados (análise estacionária)
    # Critério de parada: utilização dos aleatórios restantes (num_randoms)
    while count > 0:
        evento = proximo_evento()
        if evento is None:
            break
        tempo_evento, tipo_evento = evento
        if tipo_evento == TIPO_CHEGADA:
            CHEGADA(tempo_evento)
        elif tipo_evento == TIPO_PASSAGEM:
            PASSAGEM(tempo_evento)
        elif tipo_evento == TIPO_SAIDA:
            SAIDA(tempo_evento)

    # Contabiliza o tempo restante no último estado
    if escalonador:
        ultimo_tempo = max(e[0] for e in escalonador)
        contabiliza_tempo(ultimo_tempo)

    # Desconta as perdas do warm-up (se houve)
    if warmup_randoms > 0:
        perdas = perdas - perdas_antes

    # Verificação: soma dos tempos acumulados deve ser consistente
    soma_tempos1 = sum(times1)
    soma_tempos2 = sum(times2)
    # Verifica que nenhum tempo é negativo (integridade dos dados)
    for i in range(cap1 + 1):
        assert times1[i] >= 0, f"Tempo negativo no estado {i} da fila 1: {times1[i]}"
    for i in range(cap2 + 1):
        assert times2[i] >= 0, f"Tempo negativo no estado {i} da fila 2: {times2[i]}"

    # Retorna resultados de ambas as filas
    return {
        "fila1": calcular_resultados_fila(times1, cap1, serv1, "Fila 1"),
        "fila2": calcular_resultados_fila(times2, cap2, serv2, "Fila 2"),
        "perdas_totais": perdas,
    }


# ---------------------------------------------------------------------------
# LOTES MÉDIOS (Mean Batches)
# Executa a simulação múltiplas vezes com sementes diferentes para reduzir
# o efeito da variabilidade dos resultados. Não se assume o resultado de
# um modelo dado apenas uma única execução; faz-se um conjunto de execuções
# e calcula-se a média entre os resultados, mitigando possíveis simulações
# com resultados discrepantes.
# ---------------------------------------------------------------------------

def executar_lotes(serv1, cap1, serv2, cap2, ch_min, ch_max, at_min, at_max,
                   sementes, num_randoms=100000, warmup_randoms=0):
    """
    Executa a simulação TANDEM várias vezes (uma por semente) e coleta
    os resultados de cada lote para análise estatística.
    O warm-up é aplicado em cada lote para descartar o período transiente.
    
    Args:
        serv1, cap1: número de servidores e capacidade da fila 1
        serv2, cap2: número de servidores e capacidade da fila 2
        ch_min, ch_max: intervalo de tempo entre chegadas
        at_min, at_max: intervalo de tempo de atendimento
        sementes: lista de sementes para cada lote
        num_randoms: quantidade de números pseudoaleatórios por lote
        warmup_randoms: quantidade de aleatórios usados no warm-up
    """
    resultados_lotes = []
    for semente in sementes:
        resultado = executar_simulacao(serv1, cap1, serv2, cap2, ch_min, ch_max,
                                       at_min, at_max, semente,
                                       num_randoms, warmup_randoms)
        resultados_lotes.append(resultado)
    return resultados_lotes


# ---------------------------------------------------------------------------
# INTERVALOS DE CONFIANÇA
# Utiliza-se testes estatísticos para analisar a qualidade do resultado
# da simulação. Calcula-se o intervalo de confiança de 95% para avaliar
# quantitativamente a precisão dos resultados obtidos pelos lotes médios.
# Fórmula: IC = média ± t * (desvio_padrão / sqrt(n))
# onde t é o valor crítico da distribuição t-Student para 95% de confiança.
# ---------------------------------------------------------------------------

# Tabela t-Student bicaudal 95% para graus de liberdade (n-1) de 1 a 30
T_STUDENT_95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    25: 2.060, 29: 2.045, 30: 2.042
}

def obter_t_student(gl):
    """Retorna o valor t-Student para o grau de liberdade mais próximo."""
    if gl in T_STUDENT_95:
        return T_STUDENT_95[gl]
    # Para gl > 30, usa aproximação de 1.96 (distribuição normal)
    if gl > 30:
        return 1.96
    # Busca o valor mais próximo na tabela
    chaves = sorted(T_STUDENT_95.keys())
    for i in range(len(chaves) - 1):
        if chaves[i] <= gl < chaves[i + 1]:
            return T_STUDENT_95[chaves[i]]
    return 1.96


def calcular_intervalo_confianca(valores):
    """
    Calcula a média e o intervalo de confiança de 95% para uma lista de valores.
    Retorna (média, margem_de_erro, limite_inferior, limite_superior).
    """
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


def exibir_resultados_lotes(nome_fila, resultados_lotes, cap):
    """
    Exibe os resultados consolidados de múltiplos lotes:
    média das probabilidades por estado e intervalos de confiança
    dos índices de desempenho.
    """
    num_lotes = len(resultados_lotes)

    print("=" * 70)
    print(f"  Resultados com Lotes Médios: {nome_fila}")
    print(f"  Número de lotes: {num_lotes}")
    print("=" * 70)

    # --- Média das probabilidades por estado ---
    print("\nEstado |  Prob. Média  |      IC 95%")
    print("-" * 55)
    for i in range(cap + 1):
        probs_estado = [r['probs'][i] for r in resultados_lotes]
        media, margem, li, ls = calcular_intervalo_confianca(probs_estado)
        print(f"  {i:>3}  |  {media:.6f}   |  [{li:.6f} ; {ls:.6f}]")

    # --- Índices de desempenho com IC 95% ---
    print()
    print("-" * 55)
    print("Índices de Desempenho (média dos lotes com IC 95%):")
    print("-" * 55)

    # População média
    vals = [r['populacao_media'] for r in resultados_lotes]
    media, margem, li, ls = calcular_intervalo_confianca(vals)
    print(f"  E[N]:  {media:.4f}  [{li:.4f} ; {ls:.4f}]")

    # Utilização
    vals = [r['utilizacao'] for r in resultados_lotes]
    media, margem, li, ls = calcular_intervalo_confianca(vals)
    print(f"  Util:  {media:.4f}  [{li:.4f} ; {ls:.4f}]")

    # Vazão
    vals = [r['vazao'] for r in resultados_lotes]
    media, margem, li, ls = calcular_intervalo_confianca(vals)
    print(f"  Vazão: {media:.4f}  [{li:.4f} ; {ls:.4f}]")

    # Tempo de resposta
    vals = [r['tempo_resposta'] for r in resultados_lotes]
    media, margem, li, ls = calcular_intervalo_confianca(vals)
    print(f"  E[W]:  {media:.4f}  [{li:.4f} ; {ls:.4f}]")

    # Perdas
    vals = [r['perdas'] for r in resultados_lotes]
    media, margem, li, ls = calcular_intervalo_confianca(vals)
    print(f"  Perdas: {media:.1f}  [{li:.1f} ; {ls:.1f}]")

    print("=" * 70)
    print()


# ---------------------------------------------------------------------------
# MAIN: Execução da Simulação
# ---------------------------------------------------------------------------

def main():
    # Sementes para os lotes médios (mean batches)
    # Usa-se sementes diferentes para cada lote (20-30 replicações conforme
    # recomendação), garantindo independência entre as execuções e
    # reduzindo a variabilidade dos resultados
    SEMENTES = [
        42, 137, 256, 1024, 7777, 12345, 31415, 65537, 99991, 100003,
        54321, 11111, 22222, 33333, 44444, 55555, 66666, 77777, 88888, 98765,
        13579, 24680, 36912, 48024, 50000, 61111, 72222, 83333, 94444, 10007
    ]  # 30 sementes para 30 replicações
    NUM_RANDOMS = 100000
    # WARM-UP: descarta os primeiros 5000 aleatórios para eliminar
    # o efeito do estado inicial (transiente -> estacionário)
    WARMUP_RANDOMS = 5000

    # =====================================================================
    # SISTEMA TANDEM: Duas filas interligadas em série
    # Fila 1 (entrada): G/G/2/4 - chegadas [3,5], atendimento [5,6]
    # Fila 2 (saída):   G/G/3/5 - chegadas de PA, atendimento [2,4]
    # =====================================================================

    # --- Execução única (semente padrão) ---
    print("\n>>> Simulação TANDEM (G/G/2/4 → G/G/3/5) - Execução única <<<\n")
    resultado_tandem = executar_simulacao(
        serv1=2, cap1=4,  # Fila 1: 2 servidores, capacidade 4
        serv2=3, cap2=5,  # Fila 2: 3 servidores, capacidade 5
        ch_min=3.0, ch_max=5.0,    # Intervalo de chegadas externas
        at_min=4.0, at_max=5.0,    # Intervalo de atendimento (ambas filas)
        seed=42, num_randoms=NUM_RANDOMS
    )
    
    # Exibir resultados de FILA 1
    exibir_resultados("FILA 1 (Entrada - G/G/2/4)", resultado_tandem["fila1"])
    print()
    
    # Exibir resultados de FILA 2
    exibir_resultados("FILA 2 (Saída - G/G/3/5)", resultado_tandem["fila2"])
    print()
    
    # Análise de Correlação
    print("=" * 60)
    print("  ANÁLISE DE CORRELAÇÃO TANDEM")
    print("=" * 60)
    print(f"Perdas totais (ambas filas): {resultado_tandem['perdas_totais']}")
    print(f"Vazão entrada (Fila 1):      {resultado_tandem['fila1']['vazao']:.4f} clientes/min")
    print(f"Vazão saída (Fila 2):        {resultado_tandem['fila2']['vazao']:.4f} clientes/min")
    print(f"Diferença de vazão:          {abs(resultado_tandem['fila1']['vazao'] - resultado_tandem['fila2']['vazao']):.6f}")
    print(f"E[N] Fila 1:                 {resultado_tandem['fila1']['populacao_media']:.4f} clientes")
    print(f"E[N] Fila 2:                 {resultado_tandem['fila2']['populacao_media']:.4f} clientes")
    print(f"E[N] Total:                  {resultado_tandem['fila1']['populacao_media'] + resultado_tandem['fila2']['populacao_media']:.4f} clientes")
    print("=" * 60)
    print()
    print("Intervalo entre chegadas: [3, 5] minutos")
    print("Intervalo de atendimento: [4, 5] minutos (ambas filas)\n")

    # --- Lotes médios (mean batches) com intervalos de confiança ---
    # Reduz o efeito da variabilidade executando múltiplas vezes (30 lotes)
    # com descarte de warm-up para análise estacionária
    print(">>> Simulação TANDEM (G/G/2/4 → G/G/3/5) - Lotes médios (com warm-up) <<<\n")
    lotes_tandem = executar_lotes(
        serv1=2, cap1=4,  # Fila 1: 2 servidores, capacidade 4
        serv2=3, cap2=5,  # Fila 2: 3 servidores, capacidade 5
        ch_min=3.0, ch_max=5.0,    # Intervalo de chegadas
        at_min=4.0, at_max=5.0,    # Intervalo de atendimento
        sementes=SEMENTES, num_randoms=NUM_RANDOMS,
        warmup_randoms=WARMUP_RANDOMS
    )
    
    # Exibir resultados de FILA 1
    exibir_resultados_lotes("FILA 1 (Entrada - G/G/2/4)", [r["fila1"] for r in lotes_tandem], cap=4)
    print()
    
    # Exibir resultados de FILA 2
    exibir_resultados_lotes("FILA 2 (Saída - G/G/3/5)", [r["fila2"] for r in lotes_tandem], cap=5)
    print()
    
    # Análise de Correlação entre Lotes
    print("=" * 70)
    print("  ANÁLISE DE CORRELAÇÃO TANDEM (LOTES MÉDIOS)")
    print("=" * 70)
    
    # Extrair dados de correlação
    vazoes_fila1 = [r["fila1"]["vazao"] for r in lotes_tandem]
    vazoes_fila2 = [r["fila2"]["vazao"] for r in lotes_tandem]
    poblacao_fila1 = [r["fila1"]["populacao_media"] for r in lotes_tandem]
    poblacao_fila2 = [r["fila2"]["populacao_media"] for r in lotes_tandem]
    
    # Calcular médias e correlação
    media_vazao1, margem_v1, li_v1, ls_v1 = calcular_intervalo_confianca(vazoes_fila1)
    media_vazao2, margem_v2, li_v2, ls_v2 = calcular_intervalo_confianca(vazoes_fila2)
    media_pop1, margem_p1, li_p1, ls_p1 = calcular_intervalo_confianca(poblacao_fila1)
    media_pop2, margem_p2, li_p2, ls_p2 = calcular_intervalo_confianca(poblacao_fila2)
    
    # Correlação entre vazões
    dif_vazoes = [vazoes_fila1[i] - vazoes_fila2[i] for i in range(len(vazoes_fila1))]
    media_dif_vazao, _, li_dif, ls_dif = calcular_intervalo_confianca(dif_vazoes)
    
    print(f"\nVazão Fila 1:         {media_vazao1:.6f}  [{li_v1:.6f} ; {ls_v1:.6f}]")
    print(f"Vazão Fila 2:         {media_vazao2:.6f}  [{li_v2:.6f} ; {ls_v2:.6f}]")
    print(f"Diferença de Vazão:   {media_dif_vazao:.6f}  [{li_dif:.6f} ; {ls_dif:.6f}]")
    print(f"  → Filas sincronizadas: {'SIM ✅' if li_dif <= 0 <= ls_dif else 'NÃO ⚠️'}")
    
    print(f"\nPopulação Fila 1:     {media_pop1:.4f}  [{li_p1:.4f} ; {ls_p1:.4f}]")
    print(f"População Fila 2:     {media_pop2:.4f}  [{li_p2:.4f} ; {ls_p2:.4f}]")
    print(f"População Total:      {media_pop1 + media_pop2:.4f}  [{li_p1 + li_p2:.4f} ; {ls_p1 + ls_p2:.4f}]")
    
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
