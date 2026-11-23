VERMELHO = "VERMELHO"
PRETO = "PRETO"


class NoArvore:
    def __init__(self, horario, id_paciente, dados=None, cor=VERMELHO):
        self.horario = horario
        self.id = id_paciente
        self.chave = (horario, id_paciente)
        self.dados = dados
        self.cor = cor
        self.esquerda = None
        self.direita = None
        self.pai = None


class ArvoreRubroNegra:
    def __init__(self):
        self.NULO = NoArvore(None, -1, cor=PRETO)
        self.NULO.esquerda = self.NULO
        self.NULO.direita = self.NULO
        self.NULO.pai = self.NULO
        self.raiz = self.NULO

