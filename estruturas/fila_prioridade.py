class FilaPrioridade:
    def __init__(self, regra_de_atendimento):
        self.fila = []
        self.posicoes = []
        self.vem_antes = regra_de_atendimento

    def tamanho(self):
        return len(self.fila)

    def __len__(self):
        return self.tamanho()

    def esta_vazia(self):
        return len(self.fila) == 0

    def esta_na_fila(self, id_pessoa):
        return self._buscar_posicao(id_pessoa) is not None

    def ver_proximo(self):
        if self.esta_vazia():
            return None
        return self.fila[0]

    # ---------- mapa de posicoes (vetor com index pelo id) ----------

    def _guardar_posicao(self, id_pessoa, posicao):
        while len(self.posicoes) <= id_pessoa:
            self.posicoes.append(None)
        self.posicoes[id_pessoa] = posicao

    def _buscar_posicao(self, id_pessoa):
        if id_pessoa < 0 or id_pessoa >= len(self.posicoes):
            return None
        return self.posicoes[id_pessoa]

    def _apagar_posicao(self, id_pessoa):
        self.posicoes[id_pessoa] = None

    # ---------- navegacao na arvore do heap ----------

    @staticmethod
    def _posicao_acima(posicao_atual):
        return (posicao_atual - 1) // 2

    @staticmethod
    def _posicao_abaixo_esquerda(posicao_atual):
        return 2 * posicao_atual + 1

    @staticmethod
    def _posicao_abaixo_direita(posicao_atual):
        return 2 * posicao_atual + 2

    def _trocar(self, posicao_primeira_pessoa, posicao_segunda_pessoa):
        primeira_pessoa = self.fila[posicao_primeira_pessoa]
        segunda_pessoa = self.fila[posicao_segunda_pessoa]

        self.fila[posicao_primeira_pessoa] = segunda_pessoa
        self.fila[posicao_segunda_pessoa] = primeira_pessoa

        self._guardar_posicao(segunda_pessoa.id, posicao_primeira_pessoa)
        self._guardar_posicao(primeira_pessoa.id, posicao_segunda_pessoa)

    def subir(self, posicao_atual):
        while posicao_atual > 0:
            posicao_de_quem_esta_acima = self._posicao_acima(posicao_atual)

            pessoa_que_esta_subindo = self.fila[posicao_atual]
            pessoa_que_esta_acima = self.fila[posicao_de_quem_esta_acima]

            if self.vem_antes(pessoa_que_esta_subindo, pessoa_que_esta_acima):
                self._trocar(posicao_atual, posicao_de_quem_esta_acima)
                posicao_atual = posicao_de_quem_esta_acima
            else:
                break

    def descer(self, posicao_atual):
        quantidade_na_fila = len(self.fila)

        while True:
            posicao_abaixo_esquerda = self._posicao_abaixo_esquerda(posicao_atual)
            posicao_abaixo_direita = self._posicao_abaixo_direita(posicao_atual)
            posicao_mais_urgente = posicao_atual

            if posicao_abaixo_esquerda < quantidade_na_fila:
                if self.vem_antes(self.fila[posicao_abaixo_esquerda], self.fila[posicao_mais_urgente]):
                    posicao_mais_urgente = posicao_abaixo_esquerda

            if posicao_abaixo_direita < quantidade_na_fila:
                if self.vem_antes(self.fila[posicao_abaixo_direita], self.fila[posicao_mais_urgente]):
                    posicao_mais_urgente = posicao_abaixo_direita

            if posicao_mais_urgente == posicao_atual:
                break

            self._trocar(posicao_atual, posicao_mais_urgente)
            posicao_atual = posicao_mais_urgente

    # ---------- operacoes da fila ----------

    def inserir(self, pessoa):
        if not isinstance(pessoa.id, int) or pessoa.id < 0:
            raise ValueError(f"O id {pessoa.id} precisa ser um inteiro maior ou igual a zero.")
        if self.esta_na_fila(pessoa.id):
            raise ValueError(f"O id {pessoa.id} já está na fila.")

        self.fila.append(pessoa)
        posicao_no_fim_da_fila = len(self.fila) - 1
        self._guardar_posicao(pessoa.id, posicao_no_fim_da_fila)

        self.subir(posicao_no_fim_da_fila)

    def remover_minimo(self):
        if self.esta_vazia():
            return None

        pessoa_mais_urgente = self.fila[0]
        posicao_da_ultima_pessoa = len(self.fila) - 1

        self._trocar(0, posicao_da_ultima_pessoa)
        self.fila.pop()
        self._apagar_posicao(pessoa_mais_urgente.id)

        if not self.esta_vazia():
            self.descer(0)

        return pessoa_mais_urgente
    
    def alterar_prioridade(self, id_pessoa):
        posicao_atual = self._buscar_posicao(id_pessoa)
        if posicao_atual is None:
            raise ValueError(f"O id {id_pessoa} não está na fila.")

        pessoa_reclassificada = self.fila[posicao_atual]

        self.subir(posicao_atual)

        posicao_depois_de_subir = self._buscar_posicao(id_pessoa)
        self.descer(posicao_depois_de_subir)

        return pessoa_reclassificada