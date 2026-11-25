from datetime import datetime


class Paciente:
    """Representa um paciente cadastrado no SIGAE."""

    def __init__(
        self,
        id: int,
        nome: str,
        idade: int,
        sexo: str,
        prioridade: int,
        queixa: str,
        horario: datetime,
        sinais: dict | None = None,
        observacoes: str = "",
        senha: str = "",
    ):
        if isinstance(id, bool) or not isinstance(id, int) or id <= 0:
            raise ValueError("O ID deve ser um número inteiro positivo.")

        if not isinstance(nome, str) or not nome.strip():
            raise ValueError("O nome do paciente é obrigatório.")

        if (
            isinstance(idade, bool)
            or not isinstance(idade, int)
            or not 0 <= idade <= 130
        ):
            raise ValueError("A idade deve estar entre 0 e 130.")

        if sexo not in ("M", "F"):
            raise ValueError("O sexo deve ser M ou F.")

        if (
            isinstance(prioridade, bool)
            or not isinstance(prioridade, int)
            or prioridade not in (1, 2, 3, 4, 5)
        ):
            raise ValueError("A prioridade deve estar entre 1 e 5.")

        if not isinstance(horario, datetime):
            raise ValueError("O horário deve ser um objeto datetime.")

        self.id = id
        self.id_publico = f"PAC-{id}"
        self.nome = nome.strip()
        self.idade = idade
        self.sexo = sexo
        self.prioridade = prioridade
        self.queixa = queixa.strip()
        self.horario = horario
        self.sinais = dict(sinais) if sinais else {}
        self.observacoes = observacoes
        self.senha = senha

    @property
    def nivel(self):
        return self.prioridade

    @nivel.setter
    def nivel(self, novo_nivel):
        self.alterar_prioridade(novo_nivel)

    @property
    def chegada_dt(self):
        return self.horario

    def alterar_prioridade(self, nova_prioridade):
        if (
            isinstance(nova_prioridade, bool)
            or not isinstance(nova_prioridade, int)
            or nova_prioridade not in (1, 2, 3, 4, 5)
        ):
            raise ValueError("A prioridade deve estar entre 1 e 5.")

        self.prioridade = nova_prioridade

    def to_dict(self):
        return {
            "id": self.id_publico,
            "id_interno": self.id,
            "nome": self.nome,
            "idade": self.idade,
            "sexo": self.sexo,
            "nivel": self.prioridade,
            "prioridade": self.prioridade,
            "queixa": self.queixa,
            "chegada_dt": self.horario,
            "sinais": dict(self.sinais),
            "observacoes": self.observacoes,
            "senha": self.senha,
        }