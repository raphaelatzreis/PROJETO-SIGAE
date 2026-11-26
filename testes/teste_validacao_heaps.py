import unittest
from datetime import datetime, timedelta

from servico.servico_atendimento import ServicoAtendimento


class TesteValidacaoDosHeaps(unittest.TestCase):
    """validar_integridade() também precisa conferir a ordem interna dos dois Min-Heaps."""

    def setUp(self):
        self.servico = ServicoAtendimento()
        base = datetime(2026, 11, 26, 8, 0)
        for i, prioridade in enumerate((3, 1, 4, 2, 5)):
            self.servico.cadastrar_paciente(
                f"Paciente {i}", 30, "F", prioridade, "Teste", base + timedelta(minutes=i)
            )
        for nome, carga in (("Dra. A", 2), ("Dr. B", 0), ("Dra. C", 5)):
            self.servico.cadastrar_medico(nome, atendimentos=carga)

    def test_estado_normal_e_integro(self):
        self.assertTrue(self.servico.validar_integridade())

    def test_detecta_heap_de_pacientes_fora_de_ordem(self):
        fila = self.servico.fila_pacientes.fila
        # Coloca o menos urgente na raiz "na mão", sem passar pelo heap.
        fila[0].prioridade, fila[-1].prioridade = fila[-1].prioridade, fila[0].prioridade
        self.assertFalse(self.servico.validar_integridade())

    def test_detecta_heap_de_medicos_fora_de_ordem(self):
        raiz = self.servico.fila_medicos.ver_proximo()
        raiz.atendimentos = 99  # muda a carga sem reorganizar o heap
        self.assertFalse(self.servico.validar_integridade())

    def test_detecta_mapa_de_posicoes_errado(self):
        fila = self.servico.fila_pacientes
        primeiro = fila.fila[0]
        fila.posicoes[primeiro.id] = 3
        self.assertFalse(self.servico.validar_integridade())


if __name__ == "__main__":
    unittest.main()
