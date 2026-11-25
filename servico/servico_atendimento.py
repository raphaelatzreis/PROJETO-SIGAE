
from estruturas.fila_prioridade import (
    FilaPrioridade,
    paciente_vem_antes,
    medico_vem_antes,
)
from estruturas.arvore_rubro_negra import ArvoreRubroNegra
from estruturas.tabela_hash import TabelaHash

from servico.paciente import Paciente
from servico.medico import Medico


class ServicoAtendimento:
    """Centraliza as regras de negócio e mantém as estruturas sincronizadas."""

    def __init__(self, proximo_id_paciente=1049):
        if (
            isinstance(proximo_id_paciente, bool)
            or not isinstance(proximo_id_paciente, int)
            or proximo_id_paciente <= 0
        ):
            raise ValueError("O próximo ID de paciente deve ser positivo.")

        self.tabela_hash = TabelaHash()
        self.arvore = ArvoreRubroNegra()

        self.fila_pacientes = FilaPrioridade(paciente_vem_antes)
        self.fila_medicos = FilaPrioridade(medico_vem_antes)

        self.pacientes = {}
        self.medicos = {}

        self.proximo_id_paciente = proximo_id_paciente
        self.proximo_id_medico = 1
        self.ordem_cadastro_medico = 0

    @staticmethod
    def _normalizar_id_paciente(id_paciente):
        """Aceita tanto o ID interno quanto o formato PAC-1049."""
        if isinstance(id_paciente, str):
            if not id_paciente.startswith("PAC-"):
                raise ValueError("Formato de ID de paciente inválido.")

            try:
                id_paciente = int(id_paciente[4:])
            except ValueError:
                raise ValueError("Formato de ID de paciente inválido.")

        if (
            isinstance(id_paciente, bool)
            or not isinstance(id_paciente, int)
            or id_paciente <= 0
        ):
            raise ValueError("O ID do paciente deve ser positivo.")

        return id_paciente

    def cadastrar_paciente(
        self,
        nome,
        idade,
        sexo,
        prioridade,
        queixa,
        horario,
        sinais=None,
        observacoes="",
        senha="",
    ):
        """Cadastra o paciente nas três estruturas com rollback em caso de falha."""
        id_paciente = self.proximo_id_paciente

        paciente = Paciente(
            id=id_paciente,
            nome=nome,
            idade=idade,
            sexo=sexo,
            prioridade=prioridade,
            queixa=queixa,
            horario=horario,
            sinais=sinais,
            observacoes=observacoes,
            senha=senha,
        )

        hash_inserida = False
        arvore_inserida = False
        fila_inserida = False

        try:
            self.tabela_hash.inserir(id_paciente, paciente)
            hash_inserida = True

            self.arvore.inserir(
                paciente.horario,
                paciente.id,
                paciente,
            )
            arvore_inserida = True

            self.fila_pacientes.inserir(paciente)
            fila_inserida = True

        except Exception:
            if fila_inserida:
                self.fila_pacientes.remover(id_paciente)

            if arvore_inserida:
                self.arvore.remover(paciente.horario, id_paciente)

            if hash_inserida:
                self.tabela_hash.remover(id_paciente)

            raise

        self.pacientes[id_paciente] = paciente
        self.proximo_id_paciente += 1

        return paciente

    def buscar_paciente(self, id_paciente):
        """Busca um paciente diretamente pela tabela Hash."""
        id_interno = self._normalizar_id_paciente(id_paciente)
        return self.tabela_hash.buscar(id_interno)

    def reclassificar_paciente(self, id_paciente, nova_prioridade):
        """Altera a prioridade e reorganiza o Heap de pacientes."""
        paciente = self.buscar_paciente(id_paciente)

        if paciente is None:
            raise ValueError("Paciente não encontrado.")

        prioridade_anterior = paciente.prioridade
        paciente.alterar_prioridade(nova_prioridade)

        try:
            self.fila_pacientes.alterar_prioridade(paciente.id)
        except Exception:
            paciente.alterar_prioridade(prioridade_anterior)
            self.fila_pacientes.alterar_prioridade(paciente.id)
            raise

        return paciente

    def cancelar_paciente(self, id_paciente):
        """Remove o paciente da Hash, árvore e Heap."""
        id_interno = self._normalizar_id_paciente(id_paciente)
        paciente = self.tabela_hash.buscar(id_interno)

        if paciente is None:
            return False

        hash_removida = False
        arvore_removida = False
        fila_removida = False

        try:
            self.fila_pacientes.remover(id_interno)
            fila_removida = True

            if not self.arvore.remover(paciente.horario, id_interno):
                raise RuntimeError(
                    "Não foi possível remover o paciente da árvore."
                )
            arvore_removida = True

            if not self.tabela_hash.remover(id_interno):
                raise RuntimeError(
                    "Não foi possível remover o paciente da Hash."
                )
            hash_removida = True

        except Exception:
            if hash_removida:
                self.tabela_hash.inserir(id_interno, paciente)

            if arvore_removida:
                self.arvore.inserir(
                    paciente.horario,
                    paciente.id,
                    paciente,
                )

            if fila_removida:
                self.fila_pacientes.inserir(paciente)

            raise

        self.pacientes.pop(id_interno, None)
        return True

    def cadastrar_medico(
        self,
        nome,
        especialidade="Clínica Geral",
        atendimentos=0,
    ):
        """Cadastra um médico e o coloca na fila de disponíveis."""
        medico = Medico(
            id=self.proximo_id_medico,
            nome=nome,
            especialidade=especialidade,
            atendimentos=atendimentos,
            ordem_cadastro=self.ordem_cadastro_medico,
        )

        self.fila_medicos.inserir(medico)
        self.medicos[medico.id] = medico

        self.proximo_id_medico += 1
        self.ordem_cadastro_medico += 1

        return medico

    def buscar_medico(self, id_medico):
        return self.medicos.get(id_medico)

    def chamar_proximo(self):
        """Seleciona o paciente mais urgente e o médico disponível com menos atendimentos."""
        paciente = self.fila_pacientes.ver_proximo()
        medico = self.fila_medicos.ver_proximo()

        if paciente is None:
            raise ValueError("Não há pacientes aguardando atendimento.")

        if medico is None:
            raise ValueError("Não há médicos disponíveis.")

        id_paciente = paciente.id
        id_medico = medico.id

        try:
            if not self.cancelar_paciente(id_paciente):
                raise RuntimeError(
                    "Não foi possível retirar o paciente da fila."
                )

            self.fila_medicos.remover(id_medico)
            medico.iniciar_atendimento()

        except Exception:
            if id_paciente not in self.pacientes:
                self.tabela_hash.inserir(id_paciente, paciente)
                self.arvore.inserir(
                    paciente.horario,
                    paciente.id,
                    paciente,
                )
                self.fila_pacientes.inserir(paciente)
                self.pacientes[id_paciente] = paciente

            if (
                medico.disponivel
                and not self.fila_medicos.esta_na_fila(id_medico)
            ):
                self.fila_medicos.inserir(medico)

            raise

        return {
            "paciente": paciente,
            "medico": medico,
        }

    def finalizar_atendimento(self, id_medico):
        """Finaliza o atendimento e devolve o médico à fila de disponíveis."""
        medico = self.buscar_medico(id_medico)

        if medico is None:
            raise ValueError("Médico não encontrado.")

        medico.finalizar_atendimento()

        try:
            self.fila_medicos.inserir(medico)
        except Exception:
            medico.atendimentos -= 1
            medico.disponivel = False
            raise

        return medico

    def listar_pacientes(self):
        """Retorna os pacientes em ordem de chegada pela árvore."""
        return [
            registro["dados"]
            for registro in self.arvore.listar_em_ordem()
        ]

    def listar_medicos(self):
        return list(self.medicos.values())

    def validar_integridade(self):
        """Confere a consistência dos pacientes e médicos nas estruturas."""

        if not self.tabela_hash.validar():
            return False

        if not self.arvore.validar():
            return False

        pacientes_hash = {
            paciente.id: paciente
            for paciente in self.tabela_hash.listar_pacientes()
        }

        pacientes_arvore = {
            registro["id"]: registro["dados"]
            for registro in self.arvore.listar_em_ordem()
        }

        pacientes_fila = {
            paciente.id: paciente
            for paciente in self.fila_pacientes.fila
        }

        if set(pacientes_hash) != set(pacientes_arvore):
            return False

        if set(pacientes_hash) != set(pacientes_fila):
            return False

        if set(pacientes_hash) != set(self.pacientes):
            return False

        if len(pacientes_fila) != len(self.fila_pacientes.fila):
            return False

        for id_paciente, paciente in pacientes_hash.items():
            if pacientes_arvore[id_paciente] is not paciente:
                return False

            if pacientes_fila[id_paciente] is not paciente:
                return False

            if self.pacientes[id_paciente] is not paciente:
                return False

        medicos_na_fila = self.fila_medicos.fila

        ids_medicos_na_fila = [
            medico.id for medico in medicos_na_fila
        ]

        if len(ids_medicos_na_fila) != len(set(ids_medicos_na_fila)):
            return False

        for id_medico, medico in self.medicos.items():
            if medico.id != id_medico:
                return False

            if not isinstance(medico.disponivel, bool):
                return False

        for medico in medicos_na_fila:
            medico_registrado = self.medicos.get(medico.id)

            if medico_registrado is not medico:
                return False

            if not medico.disponivel:
                return False

        medicos_esperados = {
            medico.id
            for medico in self.medicos.values()
            if medico.disponivel
        }

        if set(ids_medicos_na_fila) != medicos_esperados:
            return False

        return True
