# SIGAE — Árvore Rubro-Negra (Memória Cronológica)

Implementação da **Issue 1 (Integrante 1)** do trabalho final **SIGAE (Estrutura de Dados Avançados)**.

Este módulo implementa do zero, em Python puro e **sem uso de bibliotecas**, uma **Árvore Rubro-Negra** responsável por manter os pacientes indexados em ordem cronológica de chegada.

---

## Arquivos

- `arvore_rubro_negra.py` — implementação das classes `NoArvore` e `ArvoreRubroNegra`.
- `test_arvore_rubro_negra.py` — testes manuais com `assert` cobrindo inserção, rotações, busca, menor elemento, listagem, remoção e validação.

---

## Chave de Indexação

Cada paciente é indexado pela chave composta:

```python
(horario, id_paciente)
```

- O `horario` define a ordem cronológica de chegada (ex.: `"08:05"`, `"08:15"`).
- Em caso de empate no horário, o desempate é feito automaticamente pelo `id_paciente`.

> **Observação para integração:** mantenha o `horario` em formato padronizado (ex.: `"HH:MM"` com zero à esquerda ou inteiro em minutos) para preservar a ordenação cronológica correta.

---

## Classes e Métodos Implementados

### `NoArvore`
Representa um nó da árvore, armazenando `horario`, `id`, `chave`, `dados`, `cor` (`"VERMELHO"` ou `"PRETO"`), `esquerda`, `direita` e `pai`.

### `ArvoreRubroNegra`
Utiliza um nó sentinela `NULO` (sempre preto) para representar folhas vazias.

- `rotacionar_esquerda(x)` / `rotacionar_direita(y)`: rotações simples mantendo ponteiros de filhos, pais e raiz atualizados.
- `inserir(horario, id_paciente, dados=None)`: insere um novo registro pela chave `(horario, id_paciente)` (lança `ValueError` em chave duplicada) e chama `ajustar_insercao(novo)`.
- `ajustar_insercao(z)`: corrige cores e aplica rotações após a inserção.
- `buscar(horario, id_paciente)`: retorna o `NoArvore` correspondente ou `None` se não existir.
- `menor_elemento(no=None)`: retorna o nó com menor `(horario, id)` na árvore (ou subárvore).
- `listar_em_ordem()`: executa o percurso em ordem (*in-order*) e retorna uma lista de dicionários em ordem cronológica.
- `remover(horario, id_paciente)`: remove o nó pela chave e chama `ajustar_remocao(x)` quando um nó preto é removido. Retorna `True` se removeu ou `False` se não encontrou.
- `ajustar_remocao(x)`: reequilibra cores e rotações após remoção.
- `validar()`: comprova que a árvore respeita todas as propriedades rubro-negras (raiz preta, sem dois nós vermelhos consecutivos, mesma altura preta em todos os caminhos e ordenação de árvore binária de busca).

---

## Exemplo de Uso

```python
from arvore_rubro_negra import ArvoreRubroNegra

arvore = ArvoreRubroNegra()
arvore.inserir("08:15", 2, {"nome": "Bruno", "prioridade": 3})
arvore.inserir("08:05", 1, {"nome": "Diana", "prioridade": 1})
arvore.inserir("08:15", 5, {"nome": "Ana", "prioridade": 2})

print(arvore.listar_em_ordem())
print("Válida?", arvore.validar())
```

---

## Como Executar os Testes

No diretório do projeto, execute:

```bash
python test_arvore_rubro_negra.py
```

Saída esperada:

```text
Todos os testes passaram!
```
