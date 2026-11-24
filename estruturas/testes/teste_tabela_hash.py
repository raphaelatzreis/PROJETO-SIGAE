import unittest
from estruturas.tabela_hash import TabelaHash


class TestTabelaHash(unittest.TestCase):
    def test_insercao_e_busca(self):
        tabela = TabelaHash(capacidade=11)
        paciente = {"nome": "Ana", "prioridade": "alta", "horario": "08:30"}
        tabela.inserir(101, paciente)

        self.assertEqual(tabela.quantidade(), 1)
        self.assertTrue(tabela.existe(101))
        self.assertFalse(tabela.existe(999))
        self.assertEqual(tabela.buscar(101), paciente)
        self.assertIsNone(tabela.buscar(999))

    def test_atualizacao_mesmo_id_e_colisoes(self):
        tabela = TabelaHash(capacidade=11)
        tabela.inserir(1, {"nome": "P1", "prioridade": "baixa", "horario": "09:00"})
        tabela.inserir(12, {"nome": "P12", "prioridade": "media", "horario": "09:10"})

        self.assertEqual(tabela.total_colisoes, 1)
        self.assertEqual(len(tabela.inspecionar_bucket(1)), 2)

        tabela.inserir(1, {"nome": "P1 Atualizado", "prioridade": "emergencia", "horario": "09:15"})
        self.assertEqual(tabela.quantidade(), 2)
        self.assertEqual(tabela.buscar(1)["nome"], "P1 Atualizado")

    def test_remocao_e_limpeza(self):
        tabela = TabelaHash(capacidade=11)
        tabela.inserir(5, {"nome": "P5", "prioridade": "media", "horario": "10:00"})
        tabela.inserir(16, {"nome": "P16", "prioridade": "alta", "horario": "10:05"})

        self.assertTrue(tabela.remover(5))
        self.assertFalse(tabela.remover(5))
        self.assertFalse(tabela.existe(5))
        self.assertTrue(tabela.existe(16))
        self.assertEqual(len(tabela.listar_pacientes()), 1)

        tabela.limpar()
        self.assertTrue(tabela.esta_vazia())
        self.assertEqual(tabela.quantidade(), 0)
        self.assertEqual(tabela.total_colisoes, 0)

    def test_redimensionamento_acima_de_75_porcento(self):
        tabela = TabelaHash(capacidade=4)
        for i in range(1, 5):
            tabela.inserir(i, {"nome": f"P{i}", "prioridade": "baixa", "horario": "11:00"})
        self.assertEqual(tabela.capacidade, 4)

        tabela.inserir(5, {"nome": "P5", "prioridade": "emergencia", "horario": "11:05"})
        self.assertEqual(tabela.capacidade, 8)
        self.assertEqual(tabela.quantidade(), 5)
        self.assertEqual(tabela.ocupacao_percentual(), 62.5)
        self.assertTrue(tabela.validar())
        self.assertTrue(tabela.resumo()["integra"])

    def test_entradas_invalidas_e_casos_de_borda(self):
        with self.assertRaises(ValueError):
            TabelaHash(capacidade=0)

        with self.assertRaises(ValueError):
            TabelaHash(capacidade=-5)

        tabela = TabelaHash(capacidade=7)
        self.assertFalse(tabela.remover(1))
        self.assertIsNone(tabela.buscar(1))

        with self.assertRaises(ValueError):
            tabela.inserir(0, {"nome": "Inválido"})

        with self.assertRaises(ValueError):
            tabela.inserir(-2, {"nome": "Inválido"})

        with self.assertRaises(ValueError):
            tabela.inserir(True, {"nome": "Bool não é ID"})

        with self.assertRaises(ValueError):
            tabela.inserir(1, None)

        self.assertTrue(tabela.validar())

    def test_estresse_colisoes_e_remocao_reinsercao(self):
        tabela = TabelaHash(capacidade=10)
        ids_colisao = [10 * k + 3 for k in range(1, 7)]

        for pid in ids_colisao:
            tabela.inserir(pid, {"nome": f"Paciente {pid}", "prioridade": "alta", "horario": "09:00"})

        self.assertEqual(tabela.quantidade(), len(ids_colisao))
        self.assertGreater(tabela.total_colisoes, 0)
        self.assertTrue(tabela.validar())

        for pid in ids_colisao[::2]:
            self.assertTrue(tabela.remover(pid))
            self.assertFalse(tabela.existe(pid))

        for pid in ids_colisao[::2]:
            tabela.inserir(pid, {"nome": f"Paciente {pid} Reinserido", "prioridade": "emergencia", "horario": "09:30"})
            self.assertTrue(tabela.existe(pid))
            self.assertEqual(tabela.buscar(pid)["nome"], f"Paciente {pid} Reinserido")

        self.assertEqual(tabela.quantidade(), len(ids_colisao))
        self.assertTrue(tabela.validar())

    def test_estresse_insercao_e_multiplos_rehashes(self):
        tabela = TabelaHash(capacidade=8)
        total = 2000

        for i in range(1, total + 1):
            tabela.inserir(i, {"nome": f"Paciente {i}", "prioridade": "media", "horario": "08:00"})

        self.assertEqual(tabela.quantidade(), total)
        self.assertGreater(tabela.capacidade, 8)
        self.assertLessEqual(tabela.ocupacao(), tabela.FATOR_CARGA_MAXIMO + 0.5)
        self.assertTrue(tabela.validar())

        for i in range(1, total + 1):
            self.assertEqual(tabela.buscar(i)["nome"], f"Paciente {i}")

    def test_estresse_operacoes_mistas_em_ondas(self):
        tabela = TabelaHash(capacidade=7)
        ativos = {}

        for onda in range(5):
            inicio = onda * 400 + 1
            fim = inicio + 400

            for pid in range(inicio, fim):
                dados = {"nome": f"Paciente {pid}", "prioridade": "media", "onda": onda}
                tabela.inserir(pid, dados)
                ativos[pid] = dados

            for pid in range(inicio, fim):
                if pid % 2 == 0:
                    novos_dados = {"nome": f"Paciente {pid} Atualizado", "prioridade": "emergencia", "onda": onda}
                    tabela.inserir(pid, novos_dados)
                    ativos[pid] = novos_dados

            for pid in range(inicio, fim):
                if pid % 3 == 0:
                    self.assertTrue(tabela.remover(pid))
                    ativos.pop(pid)
                    self.assertFalse(tabela.remover(pid))

            self.assertEqual(tabela.quantidade(), len(ativos))
            self.assertTrue(tabela.validar())

        for pid, esperado in ativos.items():
            encontrado = tabela.buscar(pid)
            self.assertIsNotNone(encontrado)
            self.assertEqual(encontrado["nome"], esperado["nome"])
            self.assertEqual(encontrado["prioridade"], esperado["prioridade"])

        self.assertEqual(len(tabela.listar_pacientes()), len(ativos))
        self.assertTrue(tabela.resumo()["integra"])

