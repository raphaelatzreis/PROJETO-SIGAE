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

    def rotacionar_esquerda(self, x):
        y = x.direita
        if y == self.NULO:
            return
        x.direita = y.esquerda
        if y.esquerda != self.NULO:
            y.esquerda.pai = x
        y.pai = x.pai
        if x.pai == self.NULO:
            self.raiz = y
        elif x == x.pai.esquerda:
            x.pai.esquerda = y
        else:
            x.pai.direita = y
        y.esquerda = x
        x.pai = y

    def rotacionar_direita(self, y):
        x = y.esquerda
        if x == self.NULO:
            return
        y.esquerda = x.direita
        if x.direita != self.NULO:
            x.direita.pai = y
        x.pai = y.pai
        if y.pai == self.NULO:
            self.raiz = x
        elif y == y.pai.direita:
            y.pai.direita = x
        else:
            y.pai.esquerda = x
        x.direita = y
        y.pai = x

