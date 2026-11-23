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

    def inserir(self, horario, id_paciente, dados=None):
        novo = NoArvore(horario, id_paciente, dados, VERMELHO)
        novo.esquerda = self.NULO
        novo.direita = self.NULO
        novo.pai = self.NULO

        pai = self.NULO
        atual = self.raiz
        while atual != self.NULO:
            pai = atual
            if novo.chave < atual.chave:
                atual = atual.esquerda
            elif novo.chave > atual.chave:
                atual = atual.direita
            else:
                raise ValueError("Chave duplicada na árvore.")

        novo.pai = pai
        if pai == self.NULO:
            self.raiz = novo
        elif novo.chave < pai.chave:
            pai.esquerda = novo
        else:
            pai.direita = novo

        self.ajustar_insercao(novo)
        return novo

    def ajustar_insercao(self, z):
        while z.pai.cor == VERMELHO:
            if z.pai == z.pai.pai.esquerda:
                tio = z.pai.pai.direita
                if tio.cor == VERMELHO:
                    z.pai.cor = PRETO
                    tio.cor = PRETO
                    z.pai.pai.cor = VERMELHO
                    z = z.pai.pai
                else:
                    if z == z.pai.direita:
                        z = z.pai
                        self.rotacionar_esquerda(z)
                    z.pai.cor = PRETO
                    z.pai.pai.cor = VERMELHO
                    self.rotacionar_direita(z.pai.pai)
            else:
                tio = z.pai.pai.esquerda
                if tio.cor == VERMELHO:
                    z.pai.cor = PRETO
                    tio.cor = PRETO
                    z.pai.pai.cor = VERMELHO
                    z = z.pai.pai
                else:
                    if z == z.pai.esquerda:
                        z = z.pai
                        self.rotacionar_direita(z)
                    z.pai.cor = PRETO
                    z.pai.pai.cor = VERMELHO
                    self.rotacionar_esquerda(z.pai.pai)
        self.raiz.cor = PRETO

    def buscar(self, horario, id_paciente):
        chave = (horario, id_paciente)
        atual = self.raiz
        while atual != self.NULO:
            if chave == atual.chave:
                return atual
            atual = atual.esquerda if chave < atual.chave else atual.direita
        return None

    def menor_elemento(self, no=None):
        atual = self.raiz if no is None else no
        if atual == self.NULO:
            return None
        while atual.esquerda != self.NULO:
            atual = atual.esquerda
        return atual

    def listar_em_ordem(self):
        lista = []
        self._em_ordem(self.raiz, lista)
        return lista

    def _em_ordem(self, no, lista):
        if no == self.NULO:
            return
        self._em_ordem(no.esquerda, lista)
        lista.append({
            "horario": no.horario,
            "id": no.id,
            "dados": no.dados,
        })
        self._em_ordem(no.direita, lista)

