class Medico:
    """Representa um médico disponível para atendimento no SIGAE."""

    def __init__(
        self,
        id: int,
        nome: str,
        especialidade: str = "Clínica Geral",
        atendimentos: int = 0,
        ordem_cadastro: int = 0,
    ):
        if isinstance(id, bool) or not isinstance(id, int) or id <= 0:
            raise ValueError("O ID do médico deve ser positivo.")

        if not isinstance(nome, str) or not nome.strip():
            raise ValueError("O nome do médico é obrigatório.")

        if (
            isinstance(atendimentos, bool)
            or not isinstance(atendimentos, int)
            or atendimentos < 0
        ):
            raise ValueError("O número de atendimentos não pode ser negativo.")

        if (
            isinstance(ordem_cadastro, bool)
            or not isinstance(ordem_cadastro, int)
            or ordem_cadastro < 0
        ):
            raise ValueError("A ordem de cadastro deve ser não negativa.")

        self.id = id
        self.nome = nome.strip()
        self.especialidade = especialidade.strip()
        self.atendimentos = atendimentos
        self.ordem_cadastro = ordem_cadastro
        self.disponivel = True

    def iniciar_atendimento(self):
        if not self.disponivel:
            raise ValueError("O médico já está atendendo.")

        self.disponivel = False

    def finalizar_atendimento(self):
        if self.disponivel:
            raise ValueError("O médico não possui atendimento em andamento.")

        self.atendimentos += 1
        self.disponivel = True

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "especialidade": self.especialidade,
            "atendimentos": self.atendimentos,
            "ordem_cadastro": self.ordem_cadastro,
            "disponivel": self.disponivel,
        }