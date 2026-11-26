import unittest
from copy import deepcopy

import app


class TesteIndicadoresApp(unittest.TestCase):
    def setUp(self):
        self.db_original = deepcopy(app.db)
        app.db.clear()
        app.db.update(app._estado_inicial())

    def tearDown(self):
        app.db.clear()
        app.db.update(self.db_original)

    def test_paciente_que_faltou_nao_conta_como_atendido(self):
        app.db["historico"] = [
            {"seq": 1, "desfecho": "nao_compareceu", "espera_min": 30},
            {"seq": 2, "desfecho": "alta", "espera_min": 10},
        ]

        estado = app._obter_estado()

        self.assertEqual(len(estado["historico"]), 2)
        self.assertEqual(estado["estatisticas"]["atendidos"], 1)
        self.assertEqual(estado["estatisticas"]["espera_media_atendidos"], 10)

    def test_historico_antigo_sem_desfecho_continua_contabilizado(self):
        app.db["historico"] = [
            {"seq": 1, "espera_min": 20},
            {"seq": 2, "desfecho": "nao_compareceu", "espera_min": 30},
        ]

        estado = app._obter_estado()

        self.assertEqual(estado["estatisticas"]["atendidos"], 1)
        self.assertEqual(estado["estatisticas"]["espera_media_atendidos"], 20)


if __name__ == "__main__":
    unittest.main()