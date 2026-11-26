import unittest
from copy import deepcopy
from datetime import datetime, timedelta

import app


class BaseApi(unittest.TestCase):
    def setUp(self):
        self.db_original = deepcopy(app.db)
        app.db.clear()
        app.db.update(app._estado_inicial())
        self.cliente = app.app.test_client()

    def tearDown(self):
        app.db.clear()
        app.db.update(self.db_original)

    def post(self, url, corpo):
        return self.cliente.post(url, json=corpo, headers={"X-Requested-With": "fetch"})


class TesteHoraDeChegada(BaseApi):
    PACIENTE = {"nome": "Paciente Teste", "idade": 30, "sexo": "F", "nivel": 3, "queixa": "Dor de cabeça"}

    def test_sem_hora_usa_o_horario_atual(self):
        antes = datetime.now().replace(microsecond=0)
        resp = self.post("/api/pacientes", dict(self.PACIENTE, chegada=""))
        self.assertEqual(resp.status_code, 201)

        paciente = app.db["servico"].buscar_paciente(resp.get_json()["criado_id"])
        self.assertGreaterEqual(paciente.horario, antes)
        self.assertLessEqual(paciente.horario, datetime.now())

    def test_hora_informada_reordena_a_lista_por_chegada(self):
        servico = app.db["servico"]
        mais_antigo = min(p.horario for p in servico.listar_pacientes())
        chegada = (mais_antigo - timedelta(minutes=1)).replace(second=0, microsecond=0)
        if chegada.date() != datetime.now().date():
            self.skipTest("Perto da meia-noite não dá para escolher um horário anterior no mesmo dia.")

        resp = self.post("/api/pacientes", dict(self.PACIENTE, chegada=chegada.strftime("%H:%M")))
        self.assertEqual(resp.status_code, 201)
        criado = resp.get_json()["criado_id"]

        # Foi cadastrado por último, mas a Rubro-Negra o coloca primeiro na ordem de chegada.
        self.assertEqual(servico.listar_pacientes()[0].id_publico, criado)
        self.assertEqual(resp.get_json()["pacientes_chegada"][0]["id"], criado)
        self.assertEqual(servico.buscar_paciente(criado).horario, chegada)
        self.assertTrue(servico.validar_integridade())

    def test_hora_invalida_e_recusada_sem_cadastrar(self):
        total = len(app.db["servico"].listar_pacientes())
        for valor in ("25:00", "abc", "12h30"):
            resp = self.post("/api/pacientes", dict(self.PACIENTE, chegada=valor))
            self.assertEqual(resp.status_code, 400, valor)
        self.assertEqual(len(app.db["servico"].listar_pacientes()), total)

    def test_hora_no_futuro_e_recusada(self):
        futuro = datetime.now() + timedelta(minutes=5)
        if futuro.date() != datetime.now().date():
            self.skipTest("Perto da meia-noite o horário futuro cairia no dia seguinte.")
        resp = self.post("/api/pacientes", dict(self.PACIENTE, chegada=futuro.strftime("%H:%M")))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("futuro", resp.get_json()["erro"])


class TesteCargaDoMedico(BaseApi):
    def _medico(self, nome):
        return next(m for m in app.db["servico"].listar_medicos() if m.nome == nome)

    def test_cadastra_medico_com_atendimentos_concluidos(self):
        resp = self.post("/api/medicos", {"nome": "Dr. Carga Alta", "atendimentos": 7})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self._medico("Dr. Carga Alta").atendimentos, 7)

    def test_sem_atendimentos_comeca_em_zero(self):
        for nome, corpo in (("Dr. Sem Campo", {}), ("Dr. Campo Vazio", {"atendimentos": ""})):
            resp = self.post("/api/medicos", dict(corpo, nome=nome))
            self.assertEqual(resp.status_code, 201)
            self.assertEqual(self._medico(nome).atendimentos, 0)

    def test_carga_invalida_e_recusada(self):
        total = len(app.db["servico"].listar_medicos())
        for valor in (-1, 2.5, "abc", True, 10000):
            resp = self.post("/api/medicos", {"nome": "Dr. Invalido", "atendimentos": valor})
            self.assertEqual(resp.status_code, 400, valor)
        self.assertEqual(len(app.db["servico"].listar_medicos()), total)

    def test_medico_com_menor_carga_e_designado(self):
        # Teste C da apresentação: os médicos de exemplo têm 1, 2 e 3 concluídos.
        resp = self.post("/api/medicos", {"nome": "Dr. Recem Chegado", "atendimentos": 0})
        self.assertEqual(resp.status_code, 201)

        resp = self.post("/api/chamar", {})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["atendimentos"][0]["medico"], "Dr. Recem Chegado")


if __name__ == "__main__":
    unittest.main()
