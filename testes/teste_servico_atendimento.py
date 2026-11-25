
import copy
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

    # ---------------------------------------------------------
    # Inicialização e normalização de IDs
    # ---------------------------------------------------------

    def test_inicializar_servico(self):
        self.assertEqual(self.servico.proximo_id_paciente, 1049)
        self.assertEqual(self.servico.proximo_id_medico, 1)
        self.assertEqual(self.servico.ordem_cadastro_medico, 0)
        self.assertTrue(self.servico.validar_integridade())

    def test_impedir_proximo_id_invalido(self):
        for valor in [0, -1, True, False, "1049", 1.5, None]:
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    ServicoAtendimento(valor)

    def test_normalizar_id_publico(self):
        paciente = self.cadastrar_paciente()

        encontrado = self.servico.buscar_paciente(paciente.id_publico)

        self.assertIs(encontrado, paciente)

    def test_normalizar_id_numerico(self):
        paciente = self.cadastrar_paciente()

        self.assertIs(
            self.servico.buscar_paciente(paciente.id),
            paciente,
        )

    def test_rejeitar_prefixo_invalido(self):
        with self.assertRaises(ValueError):
            self.servico.buscar_paciente("ABC-1049")

    def test_rejeitar_numero_invalido_no_id_publico(self):
        with self.assertRaises(ValueError):
            self.servico.buscar_paciente("PAC-ABC")

    def test_rejeitar_id_publico_vazio(self):
        with self.assertRaises(ValueError):
            self.servico.buscar_paciente("PAC-")

    def test_rejeitar_ids_numericos_invalidos(self):
        for valor in [0, -1, True, False, 1.5, None]:
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    self.servico.buscar_paciente(valor)

    # ---------------------------------------------------------
    # Cadastro e busca de pacientes
    # ---------------------------------------------------------

    def test_cadastrar_paciente_nas_tres_estruturas(self):
        paciente = self.cadastrar_paciente()

        self.assertIsNotNone(
            self.servico.tabela_hash.buscar(paciente.id)
        )
        self.assertTrue(
            self.servico.fila_pacientes.esta_na_fila(paciente.id)
        )
        self.assertIsNotNone(
            self.servico.arvore.buscar(
                paciente.horario,
                paciente.id,
            )
        )
        self.assertTrue(self.servico.validar_integridade())

    def test_buscar_paciente_por_id(self):
        paciente = self.cadastrar_paciente()
        encontrado = self.servico.buscar_paciente(paciente.id_publico)

        self.assertIs(encontrado, paciente)

    def test_buscar_paciente_inexistente(self):
        self.assertIsNone(self.servico.buscar_paciente(9999))

    def test_rollback_se_hash_falhar_no_cadastro(self):
        id_esperado = self.servico.proximo_id_paciente

        with patch.object(
            self.servico.tabela_hash,
            "inserir",
            side_effect=RuntimeError("Falha simulada na Hash"),
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

    def test_rollback_se_arvore_falhar_no_cadastro(self):
        id_esperado = self.servico.proximo_id_paciente

        with patch.object(
            self.servico.arvore,
            "inserir",
            side_effect=RuntimeError("Falha simulada na árvore"),
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

    # ---------------------------------------------------------
    # Reclassificação
    # ---------------------------------------------------------

    def test_reclassificar_paciente(self):
        paciente = self.cadastrar_paciente(prioridade=4)

        self.servico.reclassificar_paciente(paciente.id, 1)

        self.assertEqual(paciente.prioridade, 1)
        self.assertIs(
            self.servico.fila_pacientes.ver_proximo(),
            paciente,
        )
        self.assertTrue(self.servico.validar_integridade())

    def test_reclassificar_paciente_inexistente(self):
        with self.assertRaises(ValueError):
            self.servico.reclassificar_paciente(9999, 1)

    def test_rollback_se_reclassificacao_falhar(self):
        paciente = self.cadastrar_paciente(prioridade=4)

        with patch.object(
            self.servico.fila_pacientes,
            "alterar_prioridade",
            side_effect=[
                RuntimeError("Falha simulada"),
                None,
            ],
        ):
            with self.assertRaises(RuntimeError):
                self.servico.reclassificar_paciente(
                    paciente.id,
                    1,
                )

        self.assertEqual(paciente.prioridade, 4)
        self.assertTrue(self.servico.validar_integridade())

    # ---------------------------------------------------------
    # Cancelamento
    # ---------------------------------------------------------

    def test_cancelar_paciente(self):
        paciente = self.cadastrar_paciente()

        resultado = self.servico.cancelar_paciente(paciente.id)

        self.assertTrue(resultado)
        self.assertIsNone(self.servico.buscar_paciente(paciente.id))
        self.assertFalse(
            self.servico.fila_pacientes.esta_na_fila(paciente.id)
        )
        self.assertIsNone(
            self.servico.arvore.buscar(
                paciente.horario,
                paciente.id,
            )
        )
        self.assertTrue(self.servico.validar_integridade())

    def test_cancelar_paciente_inexistente(self):
        self.assertFalse(self.servico.cancelar_paciente(9999))

    def test_cancelar_paciente_com_id_publico(self):
        paciente = self.cadastrar_paciente()

        self.assertTrue(
            self.servico.cancelar_paciente(paciente.id_publico)
        )
        self.assertIsNone(self.servico.buscar_paciente(paciente.id))

    def test_cancelar_paciente_com_id_invalido(self):
        with self.assertRaises(ValueError):
            self.servico.cancelar_paciente("ABC-10")

    def test_rollback_se_remocao_da_arvore_falhar(self):
        paciente = self.cadastrar_paciente()

        with patch.object(
            self.servico.arvore,
            "remover",
            return_value=False,
        ):
            with self.assertRaises(RuntimeError):
                self.servico.cancelar_paciente(paciente.id)

        self.assertIs(
            self.servico.buscar_paciente(paciente.id),
            paciente,
        )
        self.assertTrue(
            self.servico.fila_pacientes.esta_na_fila(paciente.id)
        )
        self.assertTrue(self.servico.validar_integridade())

    def test_rollback_se_remocao_da_hash_falhar(self):
        paciente = self.cadastrar_paciente()

        with patch.object(
            self.servico.tabela_hash,
            "remover",
            return_value=False,
        ):
            with self.assertRaises(RuntimeError):
                self.servico.cancelar_paciente(paciente.id)

        self.assertIs(
            self.servico.buscar_paciente(paciente.id),
            paciente,
        )
        self.assertIsNotNone(
            self.servico.arvore.buscar(
                paciente.horario,
                paciente.id,
            )
        )
        self.assertTrue(
            self.servico.fila_pacientes.esta_na_fila(paciente.id)
        )
        self.assertTrue(self.servico.validar_integridade())

    # ---------------------------------------------------------
    # Cadastro e busca de médicos
    # ---------------------------------------------------------

    def test_cadastrar_medico(self):
        medico = self.servico.cadastrar_medico("Dra. Ana")

        self.assertEqual(medico.id, 1)
        self.assertEqual(medico.nome, "Dra. Ana")
        self.assertTrue(medico.disponivel)
        self.assertIs(self.servico.buscar_medico(medico.id), medico)
        self.assertEqual(self.servico.proximo_id_medico, 2)
        self.assertEqual(self.servico.ordem_cadastro_medico, 1)
        self.assertTrue(self.servico.validar_integridade())

    def test_cadastrar_medicos_preserva_ordem(self):
        primeiro = self.servico.cadastrar_medico("Dra. Ana")
        segundo = self.servico.cadastrar_medico("Dr. Bruno")

        self.assertEqual(primeiro.ordem_cadastro, 0)
        self.assertEqual(segundo.ordem_cadastro, 1)
        self.assertEqual(segundo.id, primeiro.id + 1)

    def test_buscar_medico_inexistente(self):
        self.assertIsNone(self.servico.buscar_medico(9999))

    def test_listar_medicos(self):
        primeiro = self.servico.cadastrar_medico("Dra. Ana")
        segundo = self.servico.cadastrar_medico("Dr. Bruno")

        resultado = self.servico.listar_medicos()

        self.assertEqual(len(resultado), 2)
        self.assertIn(primeiro, resultado)
        self.assertIn(segundo, resultado)

    def test_rollback_se_cadastro_medico_falhar_apos_inserir_na_fila(self):
        proximo_id_esperado = self.servico.proximo_id_medico
        ordem_esperada = self.servico.ordem_cadastro_medico

        inserir_original = self.servico.fila_medicos.inserir

        def inserir_e_falhar(medico):
            inserir_original(medico)
            raise RuntimeError("Falha simulada após inserir na fila")

        with patch.object(
            self.servico.fila_medicos,
            "inserir",
            side_effect=inserir_e_falhar,
        ):
            with self.assertRaises(RuntimeError):
                self.servico.cadastrar_medico("Dra. Ana")

        self.assertEqual(self.servico.medicos, {})
        self.assertTrue(self.servico.fila_medicos.esta_vazia())
        self.assertEqual(
            self.servico.proximo_id_medico,
            proximo_id_esperado,
        )
        self.assertEqual(
            self.servico.ordem_cadastro_medico,
            ordem_esperada,
        )
        self.assertTrue(self.servico.validar_integridade())

    # ---------------------------------------------------------
    # Chamada e finalização de atendimentos
    # ---------------------------------------------------------

    def test_selecionar_medico_com_menos_atendimentos(self):
        medico_a = self.servico.cadastrar_medico(
            "Dra. Ana",
            atendimentos=3,
        )
        medico_b = self.servico.cadastrar_medico(
            "Dr. Bruno",
            atendimentos=1,
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

    def test_finalizar_atendimento_com_medico_inexistente(self):
        with self.assertRaises(ValueError):
            self.servico.finalizar_atendimento(9999)

    def test_nao_chamar_sem_pacientes(self):
        self.servico.cadastrar_medico("Dra. Ana")

        with self.assertRaises(ValueError):
            self.servico.chamar_proximo()

    def test_nao_chamar_sem_medicos(self):
        self.cadastrar_paciente()

        with self.assertRaises(ValueError):
            self.servico.chamar_proximo()

    def test_rollback_se_cancelamento_falhar_ao_chamar(self):
        paciente = self.cadastrar_paciente()
        medico = self.servico.cadastrar_medico("Dra. Ana")

        with patch.object(
            self.servico,
            "cancelar_paciente",
            return_value=False,
        ):
            with self.assertRaises(RuntimeError):
                self.servico.chamar_proximo()

        self.assertIs(
            self.servico.buscar_paciente(paciente.id),
            paciente,
        )
        self.assertTrue(
            self.servico.fila_pacientes.esta_na_fila(paciente.id)
        )
        self.assertTrue(medico.disponivel)
        self.assertTrue(
            self.servico.fila_medicos.esta_na_fila(medico.id)
        )
        self.assertTrue(self.servico.validar_integridade())

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

        self.assertIs(
            self.servico.buscar_paciente(paciente.id),
            paciente,
        )
        self.assertTrue(
            self.servico.fila_pacientes.esta_na_fila(paciente.id)
        )

        paciente_na_arvore = self.servico.arvore.buscar(
            paciente.horario,
            paciente.id,
        )
        self.assertIsNotNone(paciente_na_arvore)
        self.assertIs(paciente_na_arvore.dados, paciente)

        self.assertTrue(medico.disponivel)
        self.assertEqual(medico.atendimentos, 0)
        self.assertTrue(
            self.servico.fila_medicos.esta_na_fila(medico.id)
        )
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

        self.assertIs(
            self.servico.buscar_paciente(paciente.id),
            paciente,
        )
        self.assertTrue(
            self.servico.fila_pacientes.esta_na_fila(paciente.id)
        )
        self.assertTrue(medico.disponivel)
        self.assertEqual(medico.atendimentos, 0)
        self.assertTrue(
            self.servico.fila_medicos.esta_na_fila(medico.id)
        )
        self.assertTrue(self.servico.validar_integridade())

    def test_rollback_se_finalizacao_falhar_apos_inserir_medico(self):
        self.servico.cadastrar_medico("Dra. Ana")
        self.cadastrar_paciente()

        resultado = self.servico.chamar_proximo()
        medico = resultado["medico"]

        atendimentos_anteriores = medico.atendimentos
        inserir_original = self.servico.fila_medicos.inserir

        def inserir_e_falhar(medico_inserido):
            inserir_original(medico_inserido)
            raise RuntimeError("Falha simulada após inserir médico")

        with patch.object(
            self.servico.fila_medicos,
            "inserir",
            side_effect=inserir_e_falhar,
        ):
            with self.assertRaises(RuntimeError):
                self.servico.finalizar_atendimento(medico.id)

        self.assertFalse(medico.disponivel)
        self.assertEqual(medico.atendimentos, atendimentos_anteriores)
        self.assertFalse(
            self.servico.fila_medicos.esta_na_fila(medico.id)
        )
        self.assertTrue(self.servico.validar_integridade())

    # ---------------------------------------------------------
    # Listagem de pacientes
    # ---------------------------------------------------------

    def test_listar_pacientes(self):
        primeiro = self.cadastrar_paciente("Ana")
        segundo = self.servico.cadastrar_paciente(
            nome="Bruno",
            idade=30,
            sexo="M",
            prioridade=2,
            queixa="Teste",
            horario=datetime(2026, 11, 24, 10, 40),
        )

        resultado = self.servico.listar_pacientes()

        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[0], primeiro)
        self.assertEqual(resultado[1], segundo)

    def test_listar_pacientes_vazio(self):
        self.assertEqual(self.servico.listar_pacientes(), [])

    # ---------------------------------------------------------
    # Validação de integridade dos pacientes
    # ---------------------------------------------------------

    def test_integridade_detecta_hash_invalida(self):
        self.cadastrar_paciente()
        self.servico.tabela_hash.total_pacientes = -1

        self.assertFalse(self.servico.validar_integridade())

    def test_integridade_detecta_arvore_invalida(self):
        self.cadastrar_paciente()
        self.servico.arvore.raiz.cor = "VERMELHO"

        self.assertFalse(self.servico.validar_integridade())

    def test_integridade_detecta_paciente_ausente_na_arvore(self):
        paciente = self.cadastrar_paciente()

        self.servico.arvore.remover(
            paciente.horario,
            paciente.id,
        )

        self.assertFalse(self.servico.validar_integridade())

    def test_integridade_detecta_paciente_ausente_na_fila(self):
        paciente = self.cadastrar_paciente()

        self.servico.fila_pacientes.remover(paciente.id)

        self.assertFalse(self.servico.validar_integridade())

    def test_integridade_detecta_paciente_ausente_no_dicionario(self):
        paciente = self.cadastrar_paciente()

        self.servico.pacientes.pop(paciente.id)

        self.assertFalse(self.servico.validar_integridade())

    def test_integridade_detecta_paciente_duplicado_na_fila(self):
        paciente = self.cadastrar_paciente()

        self.servico.fila_pacientes.fila.append(paciente)

        self.assertFalse(self.servico.validar_integridade())

    def test_integridade_detecta_objeto_diferente_na_arvore(self):
        paciente = self.cadastrar_paciente()

        no = self.servico.arvore.buscar(
            paciente.horario,
            paciente.id,
        )
        no.dados = copy.copy(paciente)

        self.assertFalse(self.servico.validar_integridade())

    def test_integridade_detecta_objeto_diferente_na_fila(self):
        paciente = self.cadastrar_paciente()

        self.servico.fila_pacientes.fila[0] = copy.copy(paciente)

        self.assertFalse(self.servico.validar_integridade())

    def test_integridade_detecta_objeto_diferente_no_dicionario(self):
        paciente = self.cadastrar_paciente()

        self.servico.pacientes[paciente.id] = copy.copy(paciente)

        self.assertFalse(self.servico.validar_integridade())

    # ---------------------------------------------------------
    # Validação de integridade dos médicos
    # ---------------------------------------------------------

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

    def test_integridade_detecta_chave_incorreta_no_dicionario_medicos(self):
        medico = self.servico.cadastrar_medico("Dra. Ana")

        self.servico.medicos[999] = medico

        self.assertFalse(self.servico.validar_integridade())

    def test_integridade_detecta_disponibilidade_nao_booleana(self):
        medico = self.servico.cadastrar_medico("Dra. Ana")
        medico.disponivel = "sim"

        self.assertFalse(self.servico.validar_integridade())

    def test_integridade_detecta_medico_nao_registrado_na_fila(self):
        self.servico.cadastrar_medico("Dra. Ana")

        substituto = Medico(
            id=999,
            nome="Dr. Desconhecido",
            especialidade="Clínica Geral",
            atendimentos=0,
            ordem_cadastro=99,
        )

        self.servico.fila_medicos.fila[0] = substituto

        self.assertFalse(self.servico.validar_integridade())

    def test_integridade_detecta_medico_disponivel_fora_da_fila(self):
        self.servico.cadastrar_medico("Dra. Ana")

        self.servico.fila_medicos.fila.clear()

        self.assertFalse(self.servico.validar_integridade())


if __name__ == "__main__":
    unittest.main()
