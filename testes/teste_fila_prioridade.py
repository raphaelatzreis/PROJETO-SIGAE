import os
import sys

pasta_do_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(pasta_do_projeto)

from estruturas.fila_prioridade import FilaPrioridade, paciente_vem_antes, medico_vem_antes


class PacienteTeste:
    def __init__(self, id, nome, prioridade, horario):
        self.id = id
        self.nome = nome
        self.prioridade = prioridade
        self.horario = horario


class MedicoTeste:
    def __init__(self, id, nome, atendimentos, ordem_cadastro):
        self.id = id
        self.nome = nome
        self.atendimentos = atendimentos
        self.ordem_cadastro = ordem_cadastro


def mostrar_painel_de_posicoes(fila):
    print("Painel de posições (id: posição):")
    for id_pessoa in range(len(fila.posicoes)):
        posicao = fila.posicoes[id_pessoa]
        if posicao is not None:
            print(f"  {id_pessoa}: {posicao}")


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


print()
print("=== Teste da fila de médicos ===")

fila_medicos = FilaPrioridade(medico_vem_antes)

fila_medicos.inserir(MedicoTeste(1, "Dra. Ana", 3, 1))
fila_medicos.inserir(MedicoTeste(2, "Dr. Bruno", 1, 2))
fila_medicos.inserir(MedicoTeste(3, "Dra. Carla", 1, 3))
assert fila_medicos.ver_proximo().nome == "Dr. Bruno"
print(f"Teste 13 ok: Dra. Ana (3 atendimentos), Dr. Bruno (1) e Dra. Carla (1) disponíveis. "
    f"Bruno e Carla empatam, mas Bruno foi cadastrado antes. Próximo: Dr. Bruno "
    f"({fila_medicos.tamanho()} disponíveis)")

bruno = fila_medicos.remover_minimo()
assert bruno.nome == "Dr. Bruno"
assert not fila_medicos.esta_na_fila(2)
assert fila_medicos.ver_proximo().nome == "Dra. Carla"
print(f"Teste 14 ok: Dr. Bruno foi chamado e ficou ocupado, saindo da fila. "
    f"Próximo: Dra. Carla ({fila_medicos.tamanho()} disponíveis)")

bruno.atendimentos = bruno.atendimentos + 1
fila_medicos.inserir(bruno)
assert fila_medicos.ver_proximo().nome == "Dra. Carla"
assert fila_medicos.tamanho() == 3
print(f"Teste 15 ok: Dr. Bruno concluiu o atendimento (agora com 2) e voltou à fila. "
    f"Próximo continua Dra. Carla (1) ({fila_medicos.tamanho()} disponíveis)")

carla = fila_medicos.remover_minimo()
assert carla.nome == "Dra. Carla"
assert fila_medicos.ver_proximo().nome == "Dr. Bruno"
print(f"Teste 16 ok: Dra. Carla foi chamada. Próximo: Dr. Bruno (2 atendimentos), "
    f"à frente da Dra. Ana (3) ({fila_medicos.tamanho()} disponíveis)")

fila_medicos.remover_minimo()
fila_medicos.remover_minimo()
assert fila_medicos.esta_vazia()
assert fila_medicos.remover_minimo() is None
print("Teste 17 ok: todos os médicos ocupados, a chamada do próximo fica bloqueada (nenhum disponível)")

valida, mensagem = fila.validar()
assert valida, mensagem
valida_medicos, mensagem_medicos = fila_medicos.validar()
assert valida_medicos, mensagem_medicos
print(f"Teste 18 ok: depois de todas as operações, as duas filas passaram na validação. "
    f"Pacientes: {mensagem}")


print()
print("=== Teste da validação (filas corrompidas de propósito) ===")

fila_quebrada = FilaPrioridade(paciente_vem_antes)
fila_quebrada.inserir(PacienteTeste(201, "Ana", 2, "09:00"))
fila_quebrada.inserir(PacienteTeste(202, "Beto", 4, "09:05"))
fila_quebrada.inserir(PacienteTeste(203, "Caio", 5, "09:10"))
fila_quebrada.fila[0], fila_quebrada.fila[2] = fila_quebrada.fila[2], fila_quebrada.fila[0]
valida, mensagem = fila_quebrada.validar()
assert not valida
print(f"Teste 19 ok: trocamos duas pessoas de lugar por fora da fila e a validação percebeu. {mensagem}")

fila_quebrada = FilaPrioridade(paciente_vem_antes)
fila_quebrada.inserir(PacienteTeste(201, "Ana", 2, "09:00"))
fila_quebrada.inserir(PacienteTeste(202, "Beto", 4, "09:05"))
fila_quebrada.posicoes[202] = 0
valida, mensagem = fila_quebrada.validar()
assert not valida
print(f"Teste 20 ok: estragamos o mapa de posições e a validação percebeu. {mensagem}")

fila_quebrada = FilaPrioridade(paciente_vem_antes)
fila_quebrada.inserir(PacienteTeste(201, "Ana", 2, "09:00"))
fila_quebrada.posicoes.append(None)
fila_quebrada.posicoes.append(5)
valida, mensagem = fila_quebrada.validar()
assert not valida
print(f"Teste 21 ok: deixamos um id fantasma no mapa e a validação percebeu. {mensagem}")

print()
print("=== Teste da fila de espera (listar_ordenado) ===")

posicoes_antes_de_listar = fila.posicoes[:]
fila_de_espera = fila.listar_ordenado()
nomes_em_ordem = []
for paciente in fila_de_espera:
    nomes_em_ordem.append(paciente.nome)
assert nomes_em_ordem == ["Brenno", "Raphaela", "Marcos"]
print(f"Teste 22 ok: fila de espera na ordem de atendimento: {nomes_em_ordem} "
    f"(Brenno e Raphaela têm prioridade 3 e Brenno chegou antes; Marcos tem prioridade 5)")

assert fila.tamanho() == 3
assert fila.ver_proximo().nome == "Brenno"
assert fila.posicoes == posicoes_antes_de_listar
valida, mensagem = fila.validar()
assert valida, mensagem
print(f"Teste 23 ok: depois de listar, a fila original continua intacta. {mensagem}")

fila_vazia = FilaPrioridade(paciente_vem_antes)
assert fila_vazia.listar_ordenado() == []
print("Teste 24 ok: com o pronto-socorro vazio, a fila de espera aparece vazia")

print()
print("=== Teste das correções da revisão do PR ===")

try:
    fila.inserir(PacienteTeste(True, "Booleano", 2, "09:00"))
    print("Teste 25 FALHOU: deixou entrar um id True")
except ValueError:
    print(f"Teste 25 ok: id True foi recusado e não foi confundido com o número 1 "
        f"({fila.tamanho()} na fila)")


class PacienteIncompleto:
    def __init__(self, id, nome):
        self.id = id
        self.nome = nome


posicoes_antes_do_erro = fila.posicoes[:]
try:
    fila.inserir(PacienteIncompleto(105, "Sem triagem"))
    print("Teste 26 FALHOU: deixou entrar um paciente sem prioridade e sem horário")
except AttributeError:
    assert fila.tamanho() == 3
    assert not fila.esta_na_fila(105)
    assert fila.posicoes[:len(posicoes_antes_do_erro)] == posicoes_antes_do_erro
    valida, mensagem = fila.validar()
    assert valida, mensagem
    print(f"Teste 26 ok: paciente sem prioridade e sem horário deu erro e a fila voltou "
        f"a ser exatamente como antes ({fila.tamanho()} na fila)")

try:
    fila.inserir(PacienteTeste(106, "Prioridade em texto", "1", "09:00"))
    print("Teste 27 FALHOU: deixou entrar prioridade em texto")
except TypeError:
    assert fila.tamanho() == 3
    assert not fila.esta_na_fila(106)
    valida, mensagem = fila.validar()
    assert valida, mensagem
    print(f"Teste 27 ok: prioridade \"1\" em texto deu erro e a fila voltou "
        f"a ser exatamente como antes ({fila.tamanho()} na fila)")

fila.alterar_prioridade(101, 1)
assert marcos.prioridade == 1
assert fila.ver_proximo().nome == "Marcos"
valida, mensagem = fila.validar()
assert valida, mensagem
print(f"Teste 28 ok: Marcos reclassificado para 1 numa única operação, "
    f"alterar_prioridade(101, 1). Próximo: Marcos ({fila.tamanho()} na fila)")

print("=== Todos os testes passaram ===")