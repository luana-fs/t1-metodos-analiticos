"""Conversão do simulador Java para Python, com configuração externa YAML.

Cada nextDouble equivale a um aleatório (duas atualizações internas do LCG).
O último sorteio é aplicado, mas nenhum novo evento é processado após o limite.
"""
import argparse
import heapq
import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


class JavaRandom:
    """Algoritmo de java.util.Random.nextDouble, sem dependência de Java."""
    def __init__(self, seed):
        self.state = (seed ^ 0x5DEECE66D) & ((1 << 48) - 1)

    def bits(self, n):
        self.state = (self.state * 0x5DEECE66D + 11) & ((1 << 48) - 1)
        return self.state >> (48 - n)

    def random(self):
        return ((self.bits(26) << 27) + self.bits(27)) / (1 << 53)


class LimiteAtingido(Exception):
    pass


class Aleatorios:
    def __init__(self, limite, seed=42, valores=None):
        self.limite = limite
        self.usados = 0
        self.gerador = JavaRandom(seed)
        self.valores = valores

    def proximo(self):
        if self.usados >= self.limite:
            raise LimiteAtingido
        r = (self.valores[self.usados] if self.valores is not None
             else self.gerador.random())
        self.usados += 1
        return r

    def verificar_fim(self):
        if self.usados >= self.limite:
            raise LimiteAtingido


@dataclass
class Fila:
    nome: str
    servidores: int
    capacidade: object
    servico: tuple
    chegada: object = None
    rotas: list = field(default_factory=list)
    clientes: int = 0
    perdas: int = 0
    tempos: dict = field(default_factory=lambda: defaultdict(float))
    max_clientes: int = 0


def carregar_modelo(caminho):
    try:
        import yaml
    except ImportError as exc:
        raise ValueError('Instale a dependência: python -m pip install -r requirements.txt') from exc
    class Loader(yaml.SafeLoader):
        pass
    Loader.add_constructor('!PARAMETERS', lambda loader, node: loader.construct_mapping(node, deep=True))
    with open(caminho, encoding='utf-8-sig') as arquivo:
        modelo = yaml.load(arquivo, Loader=Loader)
    validar(modelo)
    return modelo


def numero(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def validar(m):
    if not isinstance(m, dict) or not isinstance(m.get('queues'), dict) or not m['queues']:
        raise ValueError('Defina queues com ao menos uma fila.')
    for nome, q in m['queues'].items():
        s, k = q.get('servers'), q.get('capacity')
        if type(s) is not int or s < 1:
            raise ValueError(f'{nome}: servers deve ser inteiro positivo.')
        if k is not None and (type(k) is not int or k < s):
            raise ValueError(f'{nome}: capacity deve ser inteiro >= servers ou omitida.')
        for baixo, alto in [('minService', 'maxService'), ('minArrival', 'maxArrival')]:
            if baixo == 'minService' or baixo in q or alto in q:
                a, b = q.get(baixo), q.get(alto)
                if not numero(a) or not numero(b) or not 0 < a <= b:
                    raise ValueError(f'{nome}: intervalo inválido para {baixo}/{alto}.')
    if not isinstance(m.get('arrivals'), dict) or not m['arrivals']:
        raise ValueError('Defina ao menos uma chegada inicial em arrivals.')
    for nome, tempo in m['arrivals'].items():
        if nome not in m['queues'] or not numero(tempo) or tempo < 0:
            raise ValueError('Chegada inicial inválida.')
        if 'minArrival' not in m['queues'][nome]:
            raise ValueError(f'{nome}: faltam intervalos para chegadas externas.')
    somas = defaultdict(float)
    for r in m.get('network', []):
        if r.get('source') not in m['queues'] or r.get('target') not in m['queues']:
            raise ValueError('Rota com origem/destino inexistente.')
        p = r.get('probability')
        if not numero(p) or not 0 <= p <= 1:
            raise ValueError('Probabilidade inválida.')
        somas[r['source']] += p
    if any(p > 1 + 1e-12 for p in somas.values()):
        raise ValueError('Probabilidades de saída somam mais de 1.')
    if 'seeds' in m:
        if not isinstance(m['seeds'], list) or not m['seeds'] or any(type(s) is not int for s in m['seeds']):
            raise ValueError('seeds deve conter inteiros.')
        n = m.get('rndnumbersPerSeed')
        if type(n) is not int or n <= 0:
            raise ValueError('rndnumbersPerSeed deve ser inteiro positivo.')
    else:
        valores = m.get('rndnumbers')
        if not isinstance(valores, list) or not valores or any(not numero(x) or not 0 <= x < 1 for x in valores):
            raise ValueError('Defina seeds e rndnumbersPerSeed ou uma lista rndnumbers em [0,1).')


class Simulador:
    def __init__(self, modelo, seed=42, valores=None):
        validar(modelo)
        self.filas = {}
        for nome, q in modelo['queues'].items():
            chegada = (q['minArrival'], q['maxArrival']) if 'minArrival' in q else None
            self.filas[nome] = Fila(nome, q['servers'], q.get('capacity'),
                                     (q['minService'], q['maxService']), chegada)
        for r in modelo.get('network', []):
            self.filas[r['source']].rotas.append((r['target'], r['probability']))
        limite = len(valores) if valores is not None else modelo['rndnumbersPerSeed']
        self.rng = Aleatorios(limite, seed, valores)
        self.seed = None if valores is not None else seed
        self.tempo = 0.0
        self.eventos = []
        self.sequencia = 0
        self.chegadas_externas = 0
        for nome, tempo in modelo['arrivals'].items():
            self.agendar(tempo, 'EXTERNA', nome)

    def agendar(self, tempo, tipo, nome):
        # Saídas primeiro em empate; depois ordem de agendamento.
        self.sequencia += 1
        heapq.heappush(self.eventos, (tempo, 0 if tipo == 'SAIDA' else 1,
                                    self.sequencia, tipo, nome))

    def agendar_sorteado(self, intervalo, tipo, nome):
        a, b = intervalo
        duracao = a + (b - a) * self.rng.proximo()
        self.agendar(self.tempo + duracao, tipo, nome)
        self.rng.verificar_fim()

    def entrar(self, fila):
        if fila.capacidade is not None and fila.clientes >= fila.capacidade:
            fila.perdas += 1
            return
        fila.clientes += 1
        fila.max_clientes = max(fila.max_clientes, fila.clientes)
        if fila.clientes <= fila.servidores:
            self.agendar_sorteado(fila.servico, 'SAIDA', fila.nome)

    def sair(self, fila):
        fila.clientes -= 1
        if fila.clientes >= fila.servidores:
            self.agendar_sorteado(fila.servico, 'SAIDA', fila.nome)
        # Como no Java, toda conclusão sorteia o roteamento, inclusive saída certa.
        r = self.rng.proximo()
        acumulado = 0.0
        for destino, prob in fila.rotas:
            acumulado += prob
            if r < acumulado:
                self.agendar(self.tempo, 'INTERNA', destino)
                break
        self.rng.verificar_fim()

    def executar(self):
        try:
            while self.eventos and self.rng.usados < self.rng.limite:
                tempo, _, _, tipo, nome = heapq.heappop(self.eventos)
                dt = tempo - self.tempo
                for fila in self.filas.values():
                    fila.tempos[fila.clientes] += dt
                self.tempo = tempo
                fila = self.filas[nome]
                if tipo == 'SAIDA':
                    self.sair(fila)
                else:
                    if tipo == 'EXTERNA':
                        self.chegadas_externas += 1
                    self.entrar(fila)
                    if tipo == 'EXTERNA':
                        self.agendar_sorteado(fila.chegada, 'EXTERNA', nome)
        except LimiteAtingido:
            pass
        resultados = {}
        for nome, fila in self.filas.items():
            maior = fila.capacidade if fila.capacidade is not None else fila.max_clientes
            estados = [{'estado': i, 'tempo': fila.tempos[i],
                        'probabilidade': fila.tempos[i] / self.tempo if self.tempo else 0.0}
                       for i in range(maior + 1)]
            resultados[nome] = {'perdas': fila.perdas, 'estados': estados}
        return {'semente': self.seed, 'gerador': 'java.util.Random.nextDouble' if self.seed is not None else 'lista',
                'aleatorios_usados': self.rng.usados, 'limite': self.rng.limite,
                'tempo_global': self.tempo, 'chegadas_externas': self.chegadas_externas,
                'motivo_parada': 'limite de aleatorios' if self.rng.usados == self.rng.limite else 'agenda vazia',
                'filas': resultados}


def formatar(r):
    linhas = [f"Semente: {r['semente']} | Gerador: {r['gerador']}",
              f"Aleatórios usados: {r['aleatorios_usados']}",
              f"Tempo global: {r['tempo_global']:.6f} minutos",
              f"Parada: {r['motivo_parada']}"]
    for nome, fila in r['filas'].items():
        linhas += ['', f"{nome} — Clientes perdidos: {fila['perdas']}",
                   'Estado | Tempo acumulado (min) | Probabilidade (%)']
        for e in fila['estados']:
            linhas.append(f"{e['estado']:>6} | {e['tempo']:>21.6f} | {100 * e['probabilidade']:>17.6f}")
    return '\n'.join(linhas)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modelo', nargs='?', default=str(Path(__file__).with_name('modelo_t1.yml')))
    parser.add_argument('--saida', help='Arquivo TXT com os resultados')
    parser.add_argument('--json', dest='json_path', help='Arquivo JSON com os resultados')
    args = parser.parse_args()
    try:
        m = carregar_modelo(args.modelo)
        if 'seeds' in m:
            resultados = [Simulador(m, seed=s).executar() for s in m['seeds']]
        else:
            resultados = [Simulador(m, valores=m['rndnumbers']).executar()]
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Erro: {exc}\n')
    texto = '\n\n'.join(formatar(r) for r in resultados)
    print(texto)
    if args.saida:
        Path(args.saida).write_text(texto + '\n', encoding='utf-8')
    if args.json_path:
        Path(args.json_path).write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
