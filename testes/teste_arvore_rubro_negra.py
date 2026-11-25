
import unittest

from estruturas.arvore_rubro_negra import (
    ArvoreRubroNegra,
    NoArvore,
    PRETO,
    VERMELHO,
)


class TesteArvoreRubroNegra(unittest.TestCase):

    def setUp(self):
        self.arvore = ArvoreRubroNegra()

    def inserir_varios(self, itens):
        for horario, paciente_id in itens:
            self.arvore.inserir(horario, paciente_id)
            self.assertTrue(self.arvore.validar())

    def test_arvore_vazia(self):
        self.assertTrue(self.arvore.validar())
        self.assertIsNone(self.arvore.menor_elemento())
        self.assertIsNone(self.arvore.buscar("08:00", 1))
        self.assertEqual(self.arvore.listar_em_ordem(), [])
        self.assertFalse(self.arvore.remover("08:00", 1))

    def test_criacao_no(self):
        no = NoArvore("08:00", 10, {"nome": "Ana"})

        self.assertEqual(no.horario, "08:00")
        self.assertEqual(no.id, 10)
        self.assertEqual(no.chave, ("08:00", 10))
        self.assertEqual(no.dados, {"nome": "Ana"})
        self.assertEqual(no.cor, VERMELHO)
        self.assertIsNone(no.esquerda)
        self.assertIsNone(no.direita)
        self.assertIsNone(no.pai)

    def test_insercao_ordem_e_busca(self):
        pacientes = [
            ("08:30", 3, "Carlos"),
            ("08:15", 5, "Ana"),
            ("08:15", 2, "Bruno"),
            ("08:05", 1, "Diana"),
            ("08:45", 4, "Eduardo"),
        ]

        for horario, paciente_id, nome in pacientes:
            self.arvore.inserir(
                horario,
                paciente_id,
                {"nome": nome},
            )
            self.assertTrue(self.arvore.validar())

        ordem = self.arvore.listar_em_ordem()

        self.assertEqual(
            [(p["horario"], p["id"]) for p in ordem],
            [
                ("08:05", 1),
                ("08:15", 2),
                ("08:15", 5),
                ("08:30", 3),
                ("08:45", 4),
            ],
        )

        self.assertEqual(
            self.arvore.menor_elemento().chave,
            ("08:05", 1),
        )

        self.assertEqual(
            self.arvore.buscar("08:15", 5).dados["nome"],
            "Ana",
        )

        self.assertIsNone(self.arvore.buscar("09:00", 99))

    def test_impedir_chave_duplicada(self):
        self.arvore.inserir("08:00", 1)

        with self.assertRaises(ValueError):
            self.arvore.inserir("08:00", 1)

        self.assertEqual(len(self.arvore.listar_em_ordem()), 1)
        self.assertTrue(self.arvore.validar())

    def test_rotacao_esquerda_na_insercao(self):
        self.inserir_varios([
            ("08:00", 1),
            ("08:10", 2),
            ("08:20", 3),
        ])

        self.assertEqual(self.arvore.raiz.chave, ("08:10", 2))
        self.assertEqual(self.arvore.raiz.cor, PRETO)
        self.assertEqual(
            self.arvore.raiz.esquerda.chave,
            ("08:00", 1),
        )
        self.assertEqual(
            self.arvore.raiz.direita.chave,
            ("08:20", 3),
        )

    def test_rotacao_direita_na_insercao(self):
        self.inserir_varios([
            ("08:20", 3),
            ("08:10", 2),
            ("08:00", 1),
        ])

        self.assertEqual(self.arvore.raiz.chave, ("08:10", 2))
        self.assertEqual(self.arvore.raiz.cor, PRETO)
        self.assertTrue(self.arvore.validar())

    def test_rotacoes_duplas_na_insercao(self):
        cenarios = [
            [
                ("08:20", 3),
                ("08:00", 1),
                ("08:10", 2),
            ],
            [
                ("08:00", 1),
                ("08:20", 3),
                ("08:10", 2),
            ],
        ]

        for itens in cenarios:
            arvore = ArvoreRubroNegra()

            for horario, paciente_id in itens:
                arvore.inserir(horario, paciente_id)

            self.assertEqual(arvore.raiz.chave, ("08:10", 2))
            self.assertTrue(arvore.validar())

    def test_recoloracao_com_tio_vermelho(self):
        self.inserir_varios([
            ("08:10", 10),
            ("08:05", 5),
            ("08:15", 15),
            ("08:01", 1),
        ])

        self.assertEqual(self.arvore.raiz.cor, PRETO)
        self.assertTrue(self.arvore.validar())

    def test_rotacoes_sem_filho_nao_alteram_arvore(self):
        no = self.arvore.inserir("08:00", 1)

        self.arvore.rotacionar_esquerda(no)
        self.arvore.rotacionar_direita(no)

        self.assertIs(self.arvore.raiz, no)
        self.assertTrue(self.arvore.validar())

    def test_menor_elemento_em_subarvore(self):
        self.inserir_varios([
            ("08:20", 20),
            ("08:10", 10),
            ("08:30", 30),
            ("08:05", 5),
            ("08:15", 15),
        ])

        subarvore = self.arvore.buscar("08:20", 20)
        menor = self.arvore.menor_elemento(subarvore)

        self.assertEqual(menor.chave, ("08:05", 5))

    def test_listagem_preserva_dados(self):
        self.arvore.inserir("08:00", 1, {"nome": "Ana"})
        self.arvore.inserir("08:10", 2, {"nome": "Bruno"})

        resultado = self.arvore.listar_em_ordem()

        self.assertEqual(
            resultado,
            [
                {"horario": "08:00", "id": 1, "dados": {"nome": "Ana"}},
                {"horario": "08:10", "id": 2, "dados": {"nome": "Bruno"}},
            ],
        )

    def test_remover_elemento_inexistente(self):
        self.inserir_varios([
            ("08:00", 1),
            ("08:10", 2),
        ])

        self.assertFalse(self.arvore.remover("09:00", 99))
        self.assertEqual(len(self.arvore.listar_em_ordem()), 2)
        self.assertTrue(self.arvore.validar())

    def test_remover_folha_um_filho_e_raiz(self):
        self.inserir_varios([
            ("08:20", 20),
            ("08:10", 10),
            ("08:30", 30),
            ("08:05", 5),
            ("08:15", 15),
            ("08:25", 25),
            ("08:35", 35),
        ])

        # Remoção de elemento folha.
        self.assertTrue(self.arvore.remover("08:05", 5))
        self.assertTrue(self.arvore.validar())

        # Remoção de outro elemento da árvore.
        self.assertTrue(self.arvore.remover("08:15", 15))
        self.assertTrue(self.arvore.validar())

        # Remoção da raiz atual.
        raiz = self.arvore.raiz
        self.assertTrue(self.arvore.remover(*raiz.chave))
        self.assertTrue(self.arvore.validar())

    def test_remover_no_com_dois_filhos(self):
        self.inserir_varios([
            ("08:20", 20),
            ("08:10", 10),
            ("08:30", 30),
            ("08:05", 5),
            ("08:15", 15),
            ("08:25", 25),
            ("08:35", 35),
        ])

        self.assertTrue(self.arvore.remover("08:20", 20))
        self.assertIsNone(self.arvore.buscar("08:20", 20))
        self.assertTrue(self.arvore.validar())

    def test_remover_todos_os_elementos(self):
        itens = [(f"08:{i:02d}", i) for i in range(1, 31)]
        self.inserir_varios(itens)

        for horario, paciente_id in itens:
            self.assertTrue(self.arvore.remover(horario, paciente_id))
            self.assertTrue(self.arvore.validar())
            self.assertIsNone(self.arvore.buscar(horario, paciente_id))

        self.assertEqual(self.arvore.listar_em_ordem(), [])
        self.assertIsNone(self.arvore.menor_elemento())

    def test_remocao_em_ordem_inversa(self):
        itens = [(f"08:{i:02d}", i) for i in range(1, 21)]
        self.inserir_varios(itens)

        for horario, paciente_id in reversed(itens):
            self.assertTrue(self.arvore.remover(horario, paciente_id))
            self.assertTrue(self.arvore.validar())

        self.assertEqual(self.arvore.listar_em_ordem(), [])

    def test_validar_detecta_raiz_vermelha(self):
        self.arvore.inserir("08:00", 1)
        self.arvore.raiz.cor = VERMELHO

        self.assertFalse(self.arvore.validar())

    def test_validar_detecta_dois_vermelhos_consecutivos(self):
        self.inserir_varios([
            ("08:10", 10),
            ("08:05", 5),
            ("08:15", 15),
        ])

        self.arvore.raiz.esquerda.cor = VERMELHO
        self.arvore.raiz.esquerda.esquerda = self.arvore.raiz.direita

        self.assertFalse(self.arvore.validar())

    def test_validar_detecta_ordem_incorreta(self):
        self.inserir_varios([
            ("08:10", 10),
            ("08:05", 5),
            ("08:15", 15),
        ])

        self.arvore.raiz.esquerda.chave = self.arvore.raiz.chave

        self.assertFalse(self.arvore.validar())

    def test_validar_detecta_altura_negra_diferente(self):
        self.inserir_varios([
            ("08:10", 10),
            ("08:05", 5),
            ("08:15", 15),
        ])

        self.arvore.raiz.esquerda.cor = PRETO

        self.assertFalse(self.arvore.validar())


if __name__ == "__main__":
    unittest.main()
