class TabelaHash:
    """Tabela Hash do SIGAE para localizar pacientes por ID com encadeamento separado."""

    def __init__(self, capacidade: int = 11):
        if capacidade <= 0:
            raise ValueError("A capacidade inicial da TabelaHash deve ser maior que zero.")
        self.capacidade = capacidade
        self.tabela = [[] for _ in range(capacidade)]
        self.total_pacientes = 0
        self.total_colisoes = 0

    def _calcular_indice(self, id_paciente: int) -> int:
        pass

    def ocupacao(self) -> float:
        pass

    def inserir(self, id_paciente: int, paciente):
        pass

    def buscar(self, id_paciente: int):
        pass

    def remover(self, id_paciente: int) -> bool:
        pass

    def _redimensionar(self) -> None:
        pass

    def validar(self) -> bool:
        pass
