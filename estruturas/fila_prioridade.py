class FilaPrioridade:
    def __init__(self, regra_de_atendimento):
        self.fila = []
        self.posicoes = {}
        self.vem_antes = regra_de_atendimento

    def tamanho(self):
        return len(self.fila)

    def __len__(self):
        return self.tamanho()

    def esta_vazia(self):
        return len(self.fila) == 0

    def esta_na_fila(self, id_pessoa):
        return id_pessoa in self.posicoes

    def ver_proximo(self):
        if self.esta_vazia():
            return None
        return self.fila[0]

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

        self.posicoes[segunda_pessoa.id] = posicao_primeira_pessoa
        self.posicoes[primeira_pessoa.id] = posicao_segunda_pessoa

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