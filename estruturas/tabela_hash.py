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

    def _validar_id(self, id_paciente: int) -> None:
        if isinstance(id_paciente, bool) or not isinstance(id_paciente, int) or id_paciente <= 0:
            raise ValueError("O ID do paciente deve ser um número inteiro positivo.")

    def _calcular_indice(self, id_paciente: int) -> int:
        self._validar_id(id_paciente)
        return id_paciente % self.capacidade

    def esta_vazia(self) -> bool:
        return self.total_pacientes == 0

    def quantidade(self) -> int:
        return self.total_pacientes

    def ocupacao(self) -> float:
        return self.total_pacientes / self.capacidade
        
    def listar_pacientes(self) -> list:
        return [par[1] for bucket in self.tabela for par in bucket]

    def limpar(self) -> None:
        self.tabela = [[] for _ in range(self.capacidade)]
        self.total_pacientes = 0
        self.total_colisoes = 0

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
        self._validar_id(id_paciente)
        if paciente is None:
            raise ValueError("Os dados do paciente não podem ser nulos.")

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
        self._validar_id(id_paciente)
        if self.esta_vazia():
            return None

        indice = self._calcular_indice(id_paciente)
        bucket = self.tabela[indice]

        for par in bucket:
            if par[0] == id_paciente:
                return par[1]

        return None

    def remover(self, id_paciente: int) -> bool:
        self._validar_id(id_paciente)
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
        if self.capacidade <= 0 or len(self.tabela) != self.capacidade:
            return False
        if self.total_pacientes < 0 or self.total_colisoes < 0:
            return False

        contagem_real = 0
        for indice, bucket in enumerate(self.tabela):
            if not isinstance(bucket, list):
                return False
            for par in bucket:
                if not isinstance(par, list) or len(par) != 2:
                    return False
                chave, _ = par
                if isinstance(chave, bool) or not isinstance(chave, int) or chave <= 0:
                    return False
                if (chave % self.capacidade) != indice:
                    return False
                contagem_real += 1

        return contagem_real == self.total_pacientes
