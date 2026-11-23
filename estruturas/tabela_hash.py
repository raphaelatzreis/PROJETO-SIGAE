class TabelaHash:
    """Tabela Hash do SIGAE para localizar pacientes por ID com encadeamento separado."""

    FATOR_CARGA_MAXIMO = 0.75

    def __init__(self, capacidade: int = 11):
        if capacidade <= 0:
            raise ValueError("A capacidade inicial da TabelaHash deve ser maior que zero.")
        self.capacidade = capacidade
        self.tabela = [[] for _ in range(capacidade)]
        self.total_pacientes = 0
        self.total_colisoes = 0

    def _calcular_indice(self, id_paciente: int) -> int:
        return id_paciente % self.capacidade

    def esta_vazia(self) -> bool:
        return self.total_pacientes == 0

    def quantidade(self) -> int:
        return self.total_pacientes

    def ocupacao(self) -> float:
        return self.total_pacientes / self.capacidade

    def _redimensionar(self) -> None:
        registros_atuais = [
            par for bucket in self.tabela for par in bucket
        ]
        self.capacidade *= 2
        self.tabela = [[] for _ in range(self.capacidade)]
        self.total_pacientes = 0
        self.total_colisoes = 0

        for id_paciente, paciente in registros_atuais:
            self.inserir(id_paciente, paciente)

    def inserir(self, id_paciente: int, paciente):
        indice = self._calcular_indice(id_paciente)
        bucket = self.tabela[indice]

        for par in bucket:
            if par[0] == id_paciente:
                par[1] = paciente
                return paciente

        if self.ocupacao() > self.FATOR_CARGA_MAXIMO:
            self._redimensionar()
            indice = self._calcular_indice(id_paciente)
            bucket = self.tabela[indice]

        if len(bucket) > 0:
            self.total_colisoes += 1

        bucket.append([id_paciente, paciente])
        self.total_pacientes += 1
        return paciente

    def buscar(self, id_paciente: int):
        if self.esta_vazia():
            return None

        indice = self._calcular_indice(id_paciente)
        bucket = self.tabela[indice]

        for par in bucket:
            if par[0] == id_paciente:
                return par[1]

        return None

    def remover(self, id_paciente: int) -> bool:
        if self.esta_vazia():
            return False

        indice = self._calcular_indice(id_paciente)
        bucket = self.tabela[indice]

        for i, par in enumerate(bucket):
            if par[0] == id_paciente:
                bucket.pop(i)
                self.total_pacientes -= 1
                return True

        return False

    def validar(self) -> bool:
        pass

    def validar(self) -> bool:
        pass
