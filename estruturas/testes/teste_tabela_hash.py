import unittest

from estruturas.tabela_hash import TabelaHash


class TesteTabelaHash(unittest.TestCase):
    def test_insercao_busca_e_atualizacao(self):
        tabela = TabelaHash(capacidade=5)
        self.assertTrue(tabela.esta_vazia())
        self.assertEqual(tabela.quantidade(), 0)

        tabela.inserir(10, {"nome": "Ana", "prioridade": "alta", "horario": "08:15"})
        self.assertFalse(tabela.esta_vazia())
        self.assertEqual(tabela.quantidade(), 1)
        self.assertEqual(tabela.buscar(10)["nome"], "Ana")

        # Atualiza registro do mesmo ID sem duplicar quantidade
        tabela.inserir(10, {"nome": "Ana Souza", "prioridade": "emergencia", "horario": "08:15"})
        self.assertEqual(tabela.quantidade(), 1)
        self.assertEqual(tabela.buscar(10)["nome"], "Ana Souza")
        self.assertTrue(tabela.validar())

    def test_colisao_encadeamento_e_remocao(self):
        # Com capacidade 5, IDs 1 e 6 caem no mesmo bucket (1 % 5 == 1 e 6 % 5 == 1)
        tabela = TabelaHash(capacidade=5)
        tabela.inserir(1, {"nome": "Carlos", "prioridade": "media", "horario": "09:00"})
        tabela.inserir(6, {"nome": "Beatriz", "prioridade": "baixa", "horario": "09:10"})

        self.assertEqual(tabela.quantidade(), 2)
        self.assertEqual(tabela.total_colisoes, 1)
        self.assertEqual(tabela.buscar(1)["nome"], "Carlos")
        self.assertEqual(tabela.buscar(6)["nome"], "Beatriz")

        self.assertTrue(tabela.remover(1))
        self.assertIsNone(tabela.buscar(1))
        self.assertEqual(tabela.buscar(6)["nome"], "Beatriz")
        self.assertEqual(tabela.quantidade(), 1)
        self.assertFalse(tabela.remover(999))
        self.assertTrue(tabela.validar())

    def test_redimensionamento_acima_de_75_porcento(self):
        tabela = TabelaHash(capacidade=4)
        # 3 de 4 = 0.75 (não passa de 0.75); o 4º novo registro ultrapassa 0.75 e dispara rehash
        tabela.inserir(1, {"nome": "P1", "prioridade": "baixa", "horario": "10:00"})
        tabela.inserir(2, {"nome": "P2", "prioridade": "media", "horario": "10:05"})
        tabela.inserir(3, {"nome": "P3", "prioridade": "alta", "horario": "10:10"})
        self.assertEqual(tabela.capacidade, 4)

        tabela.inserir(4, {"nome": "P4", "prioridade": "emergencia", "horario": "10:15"})
        self.assertEqual(tabela.capacidade, 8)
        self.assertEqual(tabela.quantidade(), 4)
        self.assertEqual(tabela.buscar(1)["nome"], "P1")
        self.assertEqual(tabela.buscar(4)["nome"], "P4")
        self.assertTrue(tabela.validar())

    def test_entradas_invalidas(self):
        tabela = TabelaHash(capacidade=5)
        with self.assertRaises(ValueError):
            tabela.inserir(0, {"nome": "Invalido"})
        with self.assertRaises(ValueError):
            tabela.inserir(-2, {"nome": "Invalido"})
        with self.assertRaises(ValueError):
            tabela.inserir(5, None)


if __name__ == "__main__":
    unittest.main()
