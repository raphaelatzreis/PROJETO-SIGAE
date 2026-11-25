
import unittest
from datetime import datetime
from unittest.mock import patch

from servico.servico_atendimento import ServicoAtendimento


class TesteServicoAtendimento(unittest.TestCase):

    def setUp(self):
        self.servico = ServicoAtendimento()

    def cadastrar_paciente(self, nome="Paciente Teste", prioridade=3):
        return self.servico.cadastrar_paciente(
            nome=nome,
            idade=25,
            sexo="M",
            prioridade=prioridade,
            queixa="Queixa de teste",
            horario=datetime(2026, 11, 24, 10, 30),
        )

    def test_cadastrar_paciente_nas_tres_estruturas(self):
        paciente = self.cadastrar_paciente()

        self.assertIsNotNone(
            self.servico.tabela_hash.buscar(paciente.id)
        )
        self.assertTrue(
            self.servico.fila_pacientes.esta_na_fila(paciente.id)
        )
        self.assertIsNotNone(
            self.servico.arvore.buscar(paciente.horario, paciente.id)
        )
        self.assertTrue(self.servico.validar_integridade())

    def test_buscar_paciente_por_id(self):
        paciente = self.cadastrar_paciente()

        encontrado = self.servico.buscar_paciente(paciente.id_publico)

        self.assertIs(encontrado, paciente)

    def test_reclassificar_paciente(self):
        paciente = self.cadastrar_paciente(prioridade=4)

        self.servico.reclassificar_paciente(paciente.id, 1)

        self.assertEqual(paciente.prioridade, 1)
        self.assertIs(
            self.servico.fila_pacientes.ver_proximo(),
            paciente,
        )
        self.assertTrue(self.servico.validar_integridade())

    def test_cancelar_paciente(self):
        paciente = self.cadastrar_paciente()

        resultado = self.servico.cancelar_paciente(paciente.id)

        self.assertTrue(resultado)
        self.assertIsNone(self.servico.buscar_paciente(paciente.id))
        self.assertFalse(
            self.servico.fila_pacientes.esta_na_fila(paciente.id)
        )
        self.assertIsNone(
            self.servico.arvore.buscar(paciente.horario, paciente.id)
        )
        self.assertTrue(self.servico.validar_integridade())

    def test_cancelar_paciente_inexistente(self):
        self.assertFalse(self.servico.cancelar_paciente(9999))

    def test_rollback_se_insercao_na_fila_falhar(self):
        id_esperado = self.servico.proximo_id_paciente

        with patch.object(
            self.servico.fila_pacientes,
            "inserir",
            side_effect=RuntimeError("Falha simulada"),
        ):
            with self.assertRaises(RuntimeError):
                self.cadastrar_paciente()

        self.assertIsNone(
            self.servico.tabela_hash.buscar(id_esperado)
        )
        self.assertEqual(self.servico.arvore.listar_em_ordem(), [])
        self.assertTrue(self.servico.fila_pacientes.esta_vazia())
        self.assertEqual(self.servico.proximo_id_paciente, id_esperado)
        self.assertTrue(self.servico.validar_integridade())

    def test_selecionar_medico_com_menos_atendimentos(self):
        medico_a = self.servico.cadastrar_medico(
            "Dra. Ana", atendimentos=3
        )
        medico_b = self.servico.cadastrar_medico(
            "Dr. Bruno", atendimentos=1
        )

        paciente = self.cadastrar_paciente()

        resultado = self.servico.chamar_proximo()

        self.assertIs(resultado["paciente"], paciente)
        self.assertIs(resultado["medico"], medico_b)
        self.assertFalse(medico_b.disponivel)
        self.assertTrue(medico_a.disponivel)
        self.assertTrue(self.servico.validar_integridade())

    def test_finalizar_atendimento_devolve_medico_a_fila(self):
        self.servico.cadastrar_medico("Dra. Ana")
        self.cadastrar_paciente()

        resultado = self.servico.chamar_proximo()
        medico = resultado["medico"]

        self.servico.finalizar_atendimento(medico.id)

        self.assertEqual(medico.atendimentos, 1)
        self.assertTrue(medico.disponivel)
        self.assertTrue(
            self.servico.fila_medicos.esta_na_fila(medico.id)
        )
        self.assertTrue(self.servico.validar_integridade())

    def test_nao_chamar_sem_pacientes(self):
        self.servico.cadastrar_medico("Dra. Ana")

        with self.assertRaises(ValueError):
            self.servico.chamar_proximo()

    def test_nao_chamar_sem_medicos(self):
        self.cadastrar_paciente()

        with self.assertRaises(ValueError):
            self.servico.chamar_proximo()


if __name__ == "__main__":
    unittest.main()
