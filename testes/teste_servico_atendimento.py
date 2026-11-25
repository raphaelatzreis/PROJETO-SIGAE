
import unittest
from datetime import datetime
from unittest.mock import patch

from servico.servico_atendimento import ServicoAtendimento
from servico.medico import Medico


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

        self.assertIsNotNone(self.servico.tabela_hash.buscar(paciente.id))
        self.assertTrue(self.servico.fila_pacientes.esta_na_fila(paciente.id))
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
        self.assertIs(self.servico.fila_pacientes.ver_proximo(), paciente)
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

        self.assertIsNone(self.servico.tabela_hash.buscar(id_esperado))
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
        self.assertTrue(self.servico.fila_medicos.esta_na_fila(medico.id))
        self.assertTrue(self.servico.validar_integridade())

    def test_nao_chamar_sem_pacientes(self):
        self.servico.cadastrar_medico("Dra. Ana")

        with self.assertRaises(ValueError):
            self.servico.chamar_proximo()

    def test_nao_chamar_sem_medicos(self):
        self.cadastrar_paciente()

        with self.assertRaises(ValueError):
            self.servico.chamar_proximo()

    def test_integridade_detecta_medico_duplicado_na_fila(self):
        medico = self.servico.cadastrar_medico("Dra. Ana")
        self.servico.fila_medicos.fila.append(medico)

        self.assertFalse(self.servico.validar_integridade())

    def test_integridade_detecta_medico_diferente_do_registrado(self):
        medico = self.servico.cadastrar_medico("Dra. Ana")

        substituto = Medico(
            id=medico.id,
            nome="Dr. Substituto",
            especialidade=medico.especialidade,
            atendimentos=medico.atendimentos,
            ordem_cadastro=medico.ordem_cadastro,
        )

        self.servico.fila_medicos.fila[0] = substituto

        self.assertFalse(self.servico.validar_integridade())

    def test_integridade_detecta_medico_indisponivel_na_fila(self):
        medico = self.servico.cadastrar_medico("Dra. Ana")
        medico.disponivel = False

        self.assertFalse(self.servico.validar_integridade())

    def test_rollback_se_remocao_do_medico_falhar_apos_remover(self):
        paciente = self.cadastrar_paciente()
        medico = self.servico.cadastrar_medico("Dra. Ana")

        remover_original = self.servico.fila_medicos.remover

        def remover_e_falhar(id_medico):
            remover_original(id_medico)
            raise RuntimeError("Falha simulada após remover médico")

        with patch.object(
            self.servico.fila_medicos,
            "remover",
            side_effect=remover_e_falhar,
        ):
            with self.assertRaises(RuntimeError):
                self.servico.chamar_proximo()

        self.assertIs(self.servico.buscar_paciente(paciente.id), paciente)
        self.assertTrue(
            self.servico.fila_pacientes.esta_na_fila(paciente.id)
        )

        paciente_na_arvore = self.servico.arvore.buscar(
            paciente.horario, paciente.id
        )
        self.assertIsNotNone(paciente_na_arvore)
        self.assertIs(paciente_na_arvore.dados, paciente)

        self.assertTrue(medico.disponivel)
        self.assertEqual(medico.atendimentos, 0)
        self.assertTrue(self.servico.fila_medicos.esta_na_fila(medico.id))
        self.assertTrue(self.servico.validar_integridade())

    def test_rollback_se_inicio_do_atendimento_falhar_apos_alterar_estado(self):
        paciente = self.cadastrar_paciente()
        medico = self.servico.cadastrar_medico("Dra. Ana")

        def iniciar_e_falhar():
            medico.disponivel = False
            raise RuntimeError("Falha simulada ao iniciar atendimento")

        with patch.object(
            medico,
            "iniciar_atendimento",
            side_effect=iniciar_e_falhar,
        ):
            with self.assertRaises(RuntimeError):
                self.servico.chamar_proximo()

        self.assertIs(self.servico.buscar_paciente(paciente.id), paciente)
        self.assertTrue(
            self.servico.fila_pacientes.esta_na_fila(paciente.id)
        )
        self.assertTrue(medico.disponivel)
        self.assertEqual(medico.atendimentos, 0)
        self.assertTrue(self.servico.fila_medicos.esta_na_fila(medico.id))
        self.assertTrue(self.servico.validar_integridade())


if __name__ == "__main__":
    unittest.main()
