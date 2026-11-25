
import unittest
from datetime import datetime

from servico.paciente import Paciente
from servico.medico import Medico


class TestePaciente(unittest.TestCase):

    def setUp(self):
        self.paciente = Paciente(
            id=1049,
            nome="Paciente Teste",
            idade=19,
            sexo="M",
            prioridade=2,
            queixa="Dor de cabeça",
            horario=datetime(2026, 11, 24, 10, 30),
        )

    def test_criacao_paciente(self):
        self.assertEqual(self.paciente.id, 1049)
        self.assertEqual(self.paciente.id_publico, "PAC-1049")
        self.assertEqual(self.paciente.nome, "Paciente Teste")
        self.assertEqual(self.paciente.prioridade, 2)

    def test_alterar_prioridade(self):
        self.paciente.alterar_prioridade(1)
        self.assertEqual(self.paciente.prioridade, 1)

    def test_prioridade_invalida(self):
        with self.assertRaises(ValueError):
            self.paciente.alterar_prioridade(6)

    def test_id_invalido(self):
        with self.assertRaises(ValueError):
            Paciente(
                0, "Teste", 20, "M", 2, "Queixa",
                datetime.now()
            )

    def test_conversao_para_dicionario(self):
        dados = self.paciente.to_dict()

        self.assertEqual(dados["id"], "PAC-1049")
        self.assertEqual(dados["id_interno"], 1049)
        self.assertEqual(dados["nivel"], 2)


class TesteMedico(unittest.TestCase):

    def setUp(self):
        self.medico = Medico(1, "Dra. Ana")

    def test_criacao_medico(self):
        self.assertEqual(self.medico.id, 1)
        self.assertEqual(self.medico.nome, "Dra. Ana")
        self.assertEqual(self.medico.atendimentos, 0)
        self.assertTrue(self.medico.disponivel)

    def test_iniciar_atendimento(self):
        self.medico.iniciar_atendimento()
        self.assertFalse(self.medico.disponivel)

    def test_finalizar_atendimento(self):
        self.medico.iniciar_atendimento()
        self.medico.finalizar_atendimento()

        self.assertEqual(self.medico.atendimentos, 1)
        self.assertTrue(self.medico.disponivel)

    def test_registrar_ausencia_sem_contabilizar_atendimento(self):
        self.medico.iniciar_atendimento()
        self.medico.registrar_ausencia()

        self.assertEqual(self.medico.atendimentos, 0)
        self.assertTrue(self.medico.disponivel)

    def test_impedir_atendimento_simultaneo(self):
        self.medico.iniciar_atendimento()

        with self.assertRaises(ValueError):
            self.medico.iniciar_atendimento()

    def test_impedir_finalizacao_sem_atendimento(self):
        with self.assertRaises(ValueError):
            self.medico.finalizar_atendimento()

    def test_conversao_para_dicionario(self):
        dados = self.medico.to_dict()

        self.assertEqual(dados["id"], 1)
        self.assertEqual(dados["atendimentos"], 0)
        self.assertTrue(dados["disponivel"])


if __name__ == "__main__":
    unittest.main()
