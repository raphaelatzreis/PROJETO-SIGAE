
import unittest

from estruturas.tabela_hash import TabelaHash


class TesteTabelaHash(unittest.TestCase):

    def setUp(self):
        self.tabela = TabelaHash()

    def test_criar_tabela_vazia(self):
        self.assertEqual(self.tabela.capacidade, 11)
        self.assertEqual(self.tabela.quantidade(), 0)
        self.assertTrue(self.tabela.esta_vazia())
        self.assertEqual(self.tabela.ocupacao(), 0)
        self.assertEqual(self.tabela.ocupacao_percentual(), 0)
        self.assertTrue(self.tabela.validar())

    def test_impedir_capacidade_invalida(self):
        for capacidade in [0, -1, -10]:
            with self.subTest(capacidade=capacidade):
                with self.assertRaises(ValueError):
                    TabelaHash(capacidade)

    def test_impedir_ids_invalidos(self):
        ids_invalidos = [0, -1, -10, True, False, 1.5, "10", None]

        for id_paciente in ids_invalidos:
            with self.subTest(id=id_paciente):
                with self.assertRaises(ValueError):
                    self.tabela.inserir(id_paciente, "Paciente")

                with self.assertRaises(ValueError):
                    self.tabela.buscar(id_paciente)

                with self.assertRaises(ValueError):
                    self.tabela.remover(id_paciente)

                with self.assertRaises(ValueError):
                    self.tabela.existe(id_paciente)

                with self.assertRaises(ValueError):
                    self.tabela.inspecionar_bucket(id_paciente)

    def test_inserir_e_buscar_paciente(self):
        paciente = {"nome": "Ana", "prioridade": 2}

        resultado = self.tabela.inserir(101, paciente)

        self.assertIs(resultado, paciente)
        self.assertIs(self.tabela.buscar(101), paciente)
        self.assertTrue(self.tabela.existe(101))
        self.assertEqual(self.tabela.quantidade(), 1)
        self.assertFalse(self.tabela.esta_vazia())
        self.assertTrue(self.tabela.validar())

    def test_impedir_dados_nulos(self):
        with self.assertRaises(ValueError):
            self.tabela.inserir(101, None)

        self.assertTrue(self.tabela.esta_vazia())
        self.assertEqual(self.tabela.quantidade(), 0)

    def test_atualizar_paciente_com_mesmo_id(self):
        primeiro = {"nome": "Ana"}
        atualizado = {"nome": "Ana Atualizada"}

        self.tabela.inserir(101, primeiro)
        resultado = self.tabela.inserir(101, atualizado)

        self.assertIs(resultado, atualizado)
        self.assertIs(self.tabela.buscar(101), atualizado)
        self.assertEqual(self.tabela.quantidade(), 1)
        self.assertTrue(self.tabela.validar())

    def test_tratar_colisoes(self):
        tabela = TabelaHash(5)

        tabela.inserir(1, "Ana")
        tabela.inserir(6, "Bruno")
        tabela.inserir(11, "Carlos")

        self.assertEqual(tabela.total_colisoes, 2)
        self.assertEqual(tabela.quantidade(), 3)
        self.assertEqual(tabela.buscar(1), "Ana")
        self.assertEqual(tabela.buscar(6), "Bruno")
        self.assertEqual(tabela.buscar(11), "Carlos")
        self.assertTrue(tabela.validar())

    def test_inspecionar_bucket(self):
        tabela = TabelaHash(5)

        tabela.inserir(1, "Ana")
        tabela.inserir(6, "Bruno")

        bucket = tabela.inspecionar_bucket(1)

        self.assertEqual(
            bucket,
            [
                [1, "Ana"],
                [6, "Bruno"],
            ],
        )

        # A inspeção retorna uma cópia da lista do bucket.
        bucket.clear()

        self.assertEqual(tabela.quantidade(), 2)
        self.assertEqual(tabela.buscar(1), "Ana")

    def test_buscar_em_tabela_vazia(self):
        self.assertIsNone(self.tabela.buscar(101))
        self.assertFalse(self.tabela.existe(101))

    def test_buscar_paciente_inexistente(self):
        self.tabela.inserir(101, "Ana")

        self.assertIsNone(self.tabela.buscar(202))
        self.assertFalse(self.tabela.existe(202))

    def test_remover_de_tabela_vazia(self):
        self.assertFalse(self.tabela.remover(101))
        self.assertTrue(self.tabela.esta_vazia())

    def test_remover_paciente_inexistente(self):
        self.tabela.inserir(101, "Ana")

        self.assertFalse(self.tabela.remover(202))
        self.assertEqual(self.tabela.quantidade(), 1)
        self.assertTrue(self.tabela.validar())

    def test_remover_elementos_de_bucket_com_colisoes(self):
        tabela = TabelaHash(5)

        tabela.inserir(1, "Ana")
        tabela.inserir(6, "Bruno")
        tabela.inserir(11, "Carlos")

        # Remove o primeiro elemento.
        self.assertTrue(tabela.remover(1))
        self.assertEqual(tabela.buscar(1), None)

        # Remove o último elemento.
        self.assertTrue(tabela.remover(11))

        # O elemento restante continua acessível.
        self.assertEqual(tabela.buscar(6), "Bruno")
        self.assertEqual(tabela.quantidade(), 1)
        self.assertTrue(tabela.validar())

    def test_listar_pacientes(self):
        self.tabela.inserir(101, "Ana")
        self.tabela.inserir(102, "Bruno")
        self.tabela.inserir(103, "Carlos")

        pacientes = self.tabela.listar_pacientes()

        self.assertCountEqual(
            pacientes,
            ["Ana", "Bruno", "Carlos"],
        )

    def test_calcular_indice(self):
        tabela = TabelaHash(10)

        self.assertEqual(tabela._calcular_indice(15), 5)
        self.assertEqual(tabela._calcular_indice(20), 0)

        with self.assertRaises(ValueError):
            tabela._calcular_indice(-1)

    def test_ocupacao_e_percentual(self):
        tabela = TabelaHash(4)

        tabela.inserir(1, "Ana")
        tabela.inserir(2, "Bruno")

        self.assertEqual(tabela.ocupacao(), 0.5)
        self.assertEqual(tabela.ocupacao_percentual(), 50.0)

    def test_resumo(self):
        self.tabela.inserir(101, "Ana")
        self.tabela.inserir(102, "Bruno")

        resumo = self.tabela.resumo()

        self.assertEqual(resumo["capacidade"], 11)
        self.assertEqual(resumo["total_pacientes"], 2)
        self.assertAlmostEqual(resumo["ocupacao"], 2 / 11)
        self.assertEqual(resumo["total_colisoes"], 0)
        self.assertTrue(resumo["integra"])

    def test_redimensionamento_automatico(self):
        tabela = TabelaHash(4)

        tabela.inserir(1, "Ana")
        tabela.inserir(2, "Bruno")
        tabela.inserir(3, "Carlos")
        tabela.inserir(4, "Diana")

        # A ocupação está em 100%, mas ainda não houve redimensionamento.
        self.assertEqual(tabela.capacidade, 4)

        tabela.inserir(5, "Eduardo")

        self.assertEqual(tabela.capacidade, 8)
        self.assertEqual(tabela.quantidade(), 5)
        self.assertEqual(tabela.buscar(1), "Ana")
        self.assertEqual(tabela.buscar(2), "Bruno")
        self.assertEqual(tabela.buscar(3), "Carlos")
        self.assertEqual(tabela.buscar(4), "Diana")
        self.assertEqual(tabela.buscar(5), "Eduardo")
        self.assertTrue(tabela.validar())

    def test_redimensionamento_preserva_referencias(self):
        tabela = TabelaHash(2)

        paciente_a = {"nome": "Ana"}
        paciente_b = {"nome": "Bruno"}
        paciente_c = {"nome": "Carlos"}

        tabela.inserir(1, paciente_a)
        tabela.inserir(2, paciente_b)
        tabela.inserir(3, paciente_c)

        tabela.inserir(4, {"nome": "Diana"})

        self.assertIs(tabela.buscar(1), paciente_a)
        self.assertIs(tabela.buscar(2), paciente_b)
        self.assertIs(tabela.buscar(3), paciente_c)
        self.assertTrue(tabela.validar())

    def test_limpar_tabela(self):
        self.tabela.inserir(101, "Ana")
        self.tabela.inserir(112, "Bruno")

        self.tabela.limpar()

        self.assertTrue(self.tabela.esta_vazia())
        self.assertEqual(self.tabela.quantidade(), 0)
        self.assertEqual(self.tabela.total_colisoes, 0)
        self.assertEqual(self.tabela.listar_pacientes(), [])
        self.assertEqual(self.tabela.capacidade, 11)
        self.assertTrue(self.tabela.validar())

    def test_validar_detecta_capacidade_invalida(self):
        self.tabela.capacidade = 0
        self.assertFalse(self.tabela.validar())

    def test_validar_detecta_tamanho_incorreto(self):
        self.tabela.tabela.append([])

        self.assertFalse(self.tabela.validar())

    def test_validar_detecta_contadores_negativos(self):
        self.tabela.total_pacientes = -1
        self.assertFalse(self.tabela.validar())

        self.tabela.total_pacientes = 0
        self.tabela.total_colisoes = -1
        self.assertFalse(self.tabela.validar())

    def test_validar_detecta_bucket_invalido(self):
        self.tabela.tabela[0] = "inválido"

        self.assertFalse(self.tabela.validar())

    def test_validar_detecta_par_com_formato_invalido(self):
        self.tabela.tabela[0] = [[1]]

        self.assertFalse(self.tabela.validar())

    def test_validar_detecta_chave_invalida(self):
        casos = [
            True,
            False,
            "101",
            0,
            -1,
        ]

        for chave in casos:
            with self.subTest(chave=chave):
                tabela = TabelaHash(5)
                tabela.tabela[1] = [[chave, "Paciente"]]
                tabela.total_pacientes = 1

                self.assertFalse(tabela.validar())

    def test_validar_detecta_indice_incorreto(self):
        self.tabela.tabela[0] = [[101, "Ana"]]
        self.tabela.total_pacientes = 1

        self.assertFalse(self.tabela.validar())

    def test_validar_detecta_quantidade_incorreta(self):
        self.tabela.tabela[2] = [[101, "Ana"]]
        self.tabela.total_pacientes = 2

        self.assertFalse(self.tabela.validar())

    def test_validar_tabela_integra_apos_operacoes(self):
        for paciente_id in range(1, 30):
            self.tabela.inserir(
                paciente_id,
                {"id": paciente_id},
            )
            self.assertTrue(self.tabela.validar())

        for paciente_id in range(1, 15):
            self.assertTrue(self.tabela.remover(paciente_id))
            self.assertTrue(self.tabela.validar())


if __name__ == "__main__":
    unittest.main()
