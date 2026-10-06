import copy
import unittest
from pathlib import Path
from simulador_fila import JavaRandom, Simulador, carregar_modelo


class TestSimulador(unittest.TestCase):
    def setUp(self):
        self.modelo = carregar_modelo(Path(__file__).with_name('modelo_t1.yml'))

    def test_java_random_seed_42(self):
        rng = JavaRandom(42)
        self.assertEqual([rng.random() for _ in range(3)],
                         [0.7275636800328681, 0.6832234717598454, 0.30871945533265976])

    def test_parada_no_primeiro_sorteio(self):
        self.modelo['rndnumbersPerSeed'] = 1
        r = Simulador(self.modelo).executar()
        self.assertEqual(r['tempo_global'], 2.0)
        self.assertEqual(r['aleatorios_usados'], 1)
        for f in r['filas'].values():
            self.assertEqual(f['estados'][0]['tempo'], 2.0)

    def test_orcamentos_e_estatisticas(self):
        for n in list(range(1, 80)) + [100000]:
            self.modelo['rndnumbersPerSeed'] = n
            s = Simulador(self.modelo)
            r = s.executar()
            self.assertEqual(r['aleatorios_usados'], n)
            for nome, f in r['filas'].items():
                self.assertAlmostEqual(sum(e['tempo'] for e in f['estados']), r['tempo_global'], places=6)
                self.assertAlmostEqual(sum(e['probabilidade'] for e in f['estados']), 1.0)
                self.assertTrue(all(e['tempo'] >= 0 for e in f['estados']))
                fila = s.filas[nome]
                self.assertGreaterEqual(fila.clientes, 0)
                if fila.capacidade is not None:
                    self.assertLessEqual(fila.max_clientes, fila.capacidade)
            self.assertEqual(r['filas']['Q1']['perdas'], 0)
            # Uma única sequência externa, sempre com intervalo >= 2 minutos.
            self.assertLessEqual(r['chegadas_externas'], int((r['tempo_global'] - 2) / 2) + 1)

    def test_retorno_nao_cria_chegada_externa(self):
        m = {'queues': {'Q1': {'servers': 1, 'minService': 1, 'maxService': 1,
                              'minArrival': 100, 'maxArrival': 100}},
             'arrivals': {'Q1': 2}, 'network': [{'source': 'Q1', 'target': 'Q1', 'probability': 1}],
             'seeds': [42], 'rndnumbersPerSeed': 20}
        r = Simulador(m).executar()
        self.assertLess(r['tempo_global'], 102)
        self.assertEqual(r['chegadas_externas'], 1)

    def test_lista_aleatorios(self):
        m = copy.deepcopy(self.modelo)
        del m['seeds']
        m['rndnumbers'] = [0.0, 0.5]
        r = Simulador(m, valores=m['rndnumbers']).executar()
        self.assertEqual(r['aleatorios_usados'], 2)
        self.assertEqual(r['tempo_global'], 2.0)

    def test_reprodutibilidade(self):
        self.assertEqual(Simulador(self.modelo).executar(), Simulador(self.modelo).executar())


if __name__ == '__main__':
    unittest.main()
