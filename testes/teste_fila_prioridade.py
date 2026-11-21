import os
import sys

pasta_do_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(pasta_do_projeto)

from estruturas.fila_prioridade import FilaPrioridade


class PacienteTeste:
    def __init__(self, id, nome, prioridade, horario):
        self.id = id
        self.nome = nome
        self.prioridade = prioridade
        self.horario = horario


def paciente_vem_antes(paciente_avaliado, paciente_comparado):
    if paciente_avaliado.prioridade != paciente_comparado.prioridade:
        return paciente_avaliado.prioridade < paciente_comparado.prioridade
    if paciente_avaliado.horario != paciente_comparado.horario:
        return paciente_avaliado.horario < paciente_comparado.horario
    return paciente_avaliado.id < paciente_comparado.id


def mostrar_painel_de_posicoes(fila):
    print("Painel de posições (número de atendimento: posição):")
    for numero_de_atendimento in range(len(fila.posicoes)):
        posicao = fila.posicoes[numero_de_atendimento]
        if posicao is not None:
            print(f"  {numero_de_atendimento}: {posicao}")


print("=== Teste da fila de pacientes ===")

fila = FilaPrioridade(paciente_vem_antes)

assert fila.esta_vazia() == True
assert fila.ver_proximo() == None
print(f"Teste 1 ok: pronto-socorro abriu, ninguém aguardando ({fila.tamanho()} na fila)")

fila.inserir(PacienteTeste(101, "Marcos", 4, "08:00"))
fila.inserir(PacienteTeste(102, "Brenno", 3, "08:05"))
assert fila.ver_proximo().nome == "Brenno"
print(f"Teste 2 ok: chegaram Marcos (prioridade 4) e Brenno (prioridade 3). "
      f"Próximo: Brenno ({fila.tamanho()} na fila)")

fila.inserir(PacienteTeste(103, "Raphaela", 3, "08:02"))
assert fila.ver_proximo().nome == "Raphaela"
print(f"Teste 3 ok: chegou Raphaela (prioridade 3, 08:02), antes de Brenno (08:05). "
      f"Próximo: Raphaela ({fila.tamanho()} na fila)")

fila.inserir(PacienteTeste(104, "Matheus", 1, "08:15"))
assert fila.ver_proximo().nome == "Matheus"
assert fila.tamanho() == 4
print(f"Teste 4 ok: chegou Matheus (prioridade 1, emergência). "
      f"Próximo: Matheus ({fila.tamanho()} na fila)")

try:
    fila.inserir(PacienteTeste(101, "Repetido", 1, "09:00"))
    print("Teste 5 FALHOU: deixou entrar número de atendimento repetido")
except ValueError:
    print(f"Teste 5 ok: número 101 (Marcos) já está na fila, cadastro repetido bloqueado "
          f"({fila.tamanho()} na fila)")

mostrar_painel_de_posicoes(fila)
print("=== Todos os testes passaram ===")