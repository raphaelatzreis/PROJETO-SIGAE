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

assert fila.esta_vazia()
assert fila.ver_proximo() is None
print(f"Teste 1 ok: pronto-socorro abriu, ninguém aguardando ({fila.tamanho()} na fila)")

fila.inserir(PacienteTeste(101, "Marcos", 4, "08:00"))
fila.inserir(PacienteTeste(102, "Brenno", 3, "08:05"))
assert fila.ver_proximo().nome == "Brenno"
print(f"Teste 2 ok: chegaram Marcos (prioridade 4) e Brenno (prioridade 3). "
    f"Próximo: Brenno ({fila.tamanho()} na fila)")

fila.inserir(PacienteTeste(103, "Raphaela", 3, "08:10"))
assert fila.ver_proximo().nome == "Brenno"
print(f"Teste 3 ok: chegou Raphaela (prioridade 3, 08:10). Empata com Brenno, "
    f"mas ele chegou antes (08:05). Próximo continua Brenno ({fila.tamanho()} na fila)")

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

marcos = fila.fila[fila.posicoes[101]]
marcos.prioridade = 1

fila.alterar_prioridade(101)
assert fila.ver_proximo().nome == "Marcos"
print(f"Teste 6 ok: Marcos reclassificado de 4 para 1 (emergência). Empata com Matheus, "
    f"mas chegou antes (08:00 contra 08:15). Próximo: Marcos ({fila.tamanho()} na fila)")

marcos.prioridade = 5

fila.alterar_prioridade(101)
assert fila.ver_proximo().nome == "Matheus"
print(f"Teste 7 ok: Marcos reclassificado de 1 para 5 (não urgente). "
    f"Próximo: Matheus ({fila.tamanho()} na fila)")

try:
    fila.alterar_prioridade(999)
    print("Teste 8 FALHOU: deixou reclassificar um número que não está na fila")
except ValueError:
    print("Teste 8 ok: número 999 não está na fila, reclassificação bloqueada")

removida = fila.remover(103)
assert removida.nome == "Raphaela"
assert not fila.esta_na_fila(103)
assert fila.tamanho() == 3
assert fila.ver_proximo().nome == "Matheus"
print(f"Teste 9 ok: Raphaela cancelou o atendimento e saiu do meio da fila. "
    f"Próximo continua Matheus ({fila.tamanho()} na fila)")

removido = fila.remover(104)
assert removido.nome == "Matheus"
assert fila.ver_proximo().nome == "Brenno"
assert fila.tamanho() == 2
print(f"Teste 10 ok: Matheus cancelou e saiu da raiz da fila. "
    f"Próximo: Brenno ({fila.tamanho()} na fila)")

try:
    fila.remover(999)
    print("Teste 11 FALHOU: deixou cancelar um número que não está na fila")
except ValueError:
    print("Teste 11 ok: número 999 não está na fila, cancelamento bloqueado")

fila.inserir(PacienteTeste(103, "Raphaela", 3, "08:30"))
assert fila.esta_na_fila(103)
assert fila.ver_proximo().nome == "Brenno"
assert fila.tamanho() == 3
print(f"Teste 12 ok: Raphaela voltou às 08:30 com o mesmo número 103 e entrou no fim da fila "
    f"da prioridade 3. Próximo continua Brenno (08:05) ({fila.tamanho()} na fila)")

mostrar_painel_de_posicoes(fila)
print("=== Todos os testes passaram ===")