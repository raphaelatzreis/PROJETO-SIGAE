class FilaPrioridade:
    """
    Min-Heap genérico implementado manualmente para gerenciar
    a fila de pacientes (por urgência) e a escala de médicos (por carga).
    """

    def __init__(self, regra_comparacao, capacidade_de_id=10000):
        self.dados = []
        self.posicoes = [-1] * capacidade_de_id
        self.vem_antes = regra_comparacao

    def tamanho(self):
        return len(self.dados)

    def esta_vazia(self):
        return len(self.dados) == 0

    def espiar_minimo(self):
        if self.esta_vazia():
            return None
        return self.dados[0]