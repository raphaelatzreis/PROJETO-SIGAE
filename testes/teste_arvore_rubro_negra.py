from estruturas.arvore_rubro_negra import ArvoreRubroNegra, PRETO, VERMELHO


def testar_arvore_vazia():
    arvore = ArvoreRubroNegra()
    assert arvore.validar() is True
    assert arvore.menor_elemento() is None
    assert arvore.buscar("08:00", 1) is None
    assert arvore.listar_em_ordem() == []
    assert arvore.remover("08:00", 1) is False


def testar_insercao_ordem_e_busca():
    arvore = ArvoreRubroNegra()
    pacientes = [
        ("08:30", 3, "Carlos"),
        ("08:15", 5, "Ana"),
        ("08:15", 2, "Bruno"),
        ("08:05", 1, "Diana"),
        ("08:45", 4, "Eduardo"),
    ]
    for horario, pid, nome in pacientes:
        arvore.inserir(horario, pid, {"nome": nome})
        assert arvore.validar() is True

    ordem = arvore.listar_em_ordem()
    assert [(p["horario"], p["id"]) for p in ordem] == [
        ("08:05", 1),
        ("08:15", 2),
        ("08:15", 5),
        ("08:30", 3),
        ("08:45", 4),
    ]
    assert arvore.menor_elemento().chave == ("08:05", 1)
    assert arvore.buscar("08:15", 5).dados["nome"] == "Ana"
    assert arvore.buscar("09:00", 99) is None


def testar_rotacoes():
    arvore = ArvoreRubroNegra()
    arvore.inserir("08:00", 1)
    arvore.inserir("08:10", 2)
    arvore.inserir("08:20", 3)
    assert arvore.raiz.chave == ("08:10", 2)
    assert arvore.raiz.cor == PRETO
    assert arvore.raiz.esquerda.chave == ("08:00", 1)
    assert arvore.raiz.direita.chave == ("08:20", 3)
    assert arvore.validar() is True


def testar_remocao_e_reequilibrio():
    arvore = ArvoreRubroNegra()
    itens = [(f"08:{i:02d}", i) for i in range(1, 31)]
    for horario, pid in itens:
        arvore.inserir(horario, pid, {"id": pid})
        assert arvore.validar() is True

    for horario, pid in [("08:10", 10), ("08:01", 1), ("08:30", 30), arvore.raiz.chave]:
        assert arvore.remover(horario, pid) is True
        assert arvore.validar() is True
        assert arvore.buscar(horario, pid) is None

    for p in arvore.listar_em_ordem():
        assert arvore.remover(p["horario"], p["id"]) is True
        assert arvore.validar() is True

    assert arvore.listar_em_ordem() == []


def testar_validar_detecta_erro():
    arvore = ArvoreRubroNegra()
    arvore.inserir("08:00", 1)
    arvore.inserir("08:10", 2)
    arvore.inserir("08:20", 3)

    arvore.raiz.cor = VERMELHO
    assert arvore.validar() is False

    arvore.raiz.cor = PRETO
    arvore.raiz.esquerda.cor = VERMELHO
    arvore.raiz.esquerda.esquerda = arvore.raiz.direita
    assert arvore.validar() is False


if __name__ == "__main__":
    testar_arvore_vazia()
    testar_insercao_ordem_e_busca()
    testar_rotacoes()
    testar_remocao_e_reequilibrio()
    testar_validar_detecta_erro()
    print("Todos os testes passaram!")
