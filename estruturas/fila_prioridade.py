class FilaPrioridade:
    def __init__(self, regra_de_atendimento, campo_prioridade="prioridade"):
        self.fila = []
        self.posicoes = []
        self.vem_antes = regra_de_atendimento
        self.campo_prioridade = campo_prioridade

    def tamanho(self):
        return len(self.fila)

    def __len__(self):
        return self.tamanho()

    def esta_vazia(self):
        return len(self.fila) == 0

    def esta_na_fila(self, id_pessoa):
        return self._buscar_posicao(id_pessoa) is not None

    def ver_proximo(self):
        if self.esta_vazia():
            return None
        return self.fila[0]

    # ---------- mapa de posicoes (vetor com index pelo id) ----------

    @staticmethod
    def _id_valido(id_pessoa):
        return (
            isinstance(id_pessoa, int)
            and not isinstance(id_pessoa, bool)
            and id_pessoa >= 0
        )

    def _guardar_posicao(self, id_pessoa, posicao):
        while len(self.posicoes) <= id_pessoa:
            self.posicoes.append(None)
        self.posicoes[id_pessoa] = posicao

    def _buscar_posicao(self, id_pessoa):
        if not self._id_valido(id_pessoa) or id_pessoa >= len(self.posicoes):
            return None
        return self.posicoes[id_pessoa]

    def _apagar_posicao(self, id_pessoa):
        self.posicoes[id_pessoa] = None

    # ---------- navegacao na arvore do heap ----------

    @staticmethod
    def _posicao_acima(posicao_atual):
        return (posicao_atual - 1) // 2

    @staticmethod
    def _posicao_abaixo_esquerda(posicao_atual):
        return 2 * posicao_atual + 1

    @staticmethod
    def _posicao_abaixo_direita(posicao_atual):
        return 2 * posicao_atual + 2

    def _trocar(self, posicao_primeira_pessoa, posicao_segunda_pessoa):
        primeira_pessoa = self.fila[posicao_primeira_pessoa]
        segunda_pessoa = self.fila[posicao_segunda_pessoa]

        self.fila[posicao_primeira_pessoa] = segunda_pessoa
        self.fila[posicao_segunda_pessoa] = primeira_pessoa

        self._guardar_posicao(segunda_pessoa.id, posicao_primeira_pessoa)
        self._guardar_posicao(primeira_pessoa.id, posicao_segunda_pessoa)

    def subir(self, posicao_atual):
        while posicao_atual > 0:
            posicao_de_quem_esta_acima = self._posicao_acima(posicao_atual)

            pessoa_que_esta_subindo = self.fila[posicao_atual]
            pessoa_que_esta_acima = self.fila[posicao_de_quem_esta_acima]

            if self.vem_antes(pessoa_que_esta_subindo, pessoa_que_esta_acima):
                self._trocar(posicao_atual, posicao_de_quem_esta_acima)
                posicao_atual = posicao_de_quem_esta_acima
            else:
                break

    def descer(self, posicao_atual):
        quantidade_na_fila = len(self.fila)

        while True:
            posicao_abaixo_esquerda = self._posicao_abaixo_esquerda(posicao_atual)
            posicao_abaixo_direita = self._posicao_abaixo_direita(posicao_atual)
            posicao_mais_urgente = posicao_atual

            if posicao_abaixo_esquerda < quantidade_na_fila:
                if self.vem_antes(self.fila[posicao_abaixo_esquerda], self.fila[posicao_mais_urgente]):
                    posicao_mais_urgente = posicao_abaixo_esquerda

            if posicao_abaixo_direita < quantidade_na_fila:
                if self.vem_antes(self.fila[posicao_abaixo_direita], self.fila[posicao_mais_urgente]):
                    posicao_mais_urgente = posicao_abaixo_direita

            if posicao_mais_urgente == posicao_atual:
                break

            self._trocar(posicao_atual, posicao_mais_urgente)
            posicao_atual = posicao_mais_urgente

    # ---------- operacoes da fila ----------

    def inserir(self, pessoa):
        if not self._id_valido(pessoa.id):
            raise ValueError(f"O id {pessoa.id!r} precisa ser um inteiro maior ou igual a zero.")
        if self.esta_na_fila(pessoa.id):
            raise ValueError(f"O id {pessoa.id} já está na fila.")

        self.fila.append(pessoa)
        posicao_no_fim_da_fila = len(self.fila) - 1
        self._guardar_posicao(pessoa.id, posicao_no_fim_da_fila)

        try:
            self.subir(posicao_no_fim_da_fila)
        except Exception:
            self._desfazer_insercao(pessoa, posicao_no_fim_da_fila)
            raise

    def _desfazer_insercao(self, pessoa, posicao_onde_entrou):
        posicao_atual = self._buscar_posicao(pessoa.id)

        caminho_percorrido = []
        posicao = posicao_onde_entrou
        while posicao != posicao_atual:
            caminho_percorrido.append(posicao)
            posicao = self._posicao_acima(posicao)

        for posicao_de_volta in reversed(caminho_percorrido):
            self._trocar(posicao_atual, posicao_de_volta)
            posicao_atual = posicao_de_volta

        self.fila.pop()
        self._apagar_posicao(pessoa.id)

    def remover_minimo(self):
        if self.esta_vazia():
            return None

        pessoa_mais_urgente = self.fila[0]
        posicao_da_ultima_pessoa = len(self.fila) - 1

        self._trocar(0, posicao_da_ultima_pessoa)
        self.fila.pop()
        self._apagar_posicao(pessoa_mais_urgente.id)

        if not self.esta_vazia():
            self.descer(0)

        return pessoa_mais_urgente

    def alterar_prioridade(self, id_pessoa, nova_prioridade=None):
        posicao_atual = self._buscar_posicao(id_pessoa)
        if posicao_atual is None:
            raise ValueError(f"O id {id_pessoa!r} não está na fila.")

        pessoa_reclassificada = self.fila[posicao_atual]
        if nova_prioridade is not None:
            # altera o campo certo: "prioridade" (pacientes) ou "atendimentos" (medicos)
            setattr(pessoa_reclassificada, self.campo_prioridade, nova_prioridade)

        self.subir(posicao_atual)

        posicao_depois_de_subir = self._buscar_posicao(id_pessoa)
        self.descer(posicao_depois_de_subir)

        return pessoa_reclassificada

    def remover(self, id_pessoa):
        posicao_de_quem_sai = self._buscar_posicao(id_pessoa)
        if posicao_de_quem_sai is None:
            raise ValueError(f"O id {id_pessoa!r} não está na fila.")

        pessoa_removida = self.fila[posicao_de_quem_sai]
        posicao_da_ultima_pessoa = len(self.fila) - 1

        self._trocar(posicao_de_quem_sai, posicao_da_ultima_pessoa)
        self.fila.pop()
        self._apagar_posicao(pessoa_removida.id)

        if posicao_de_quem_sai < len(self.fila):
            pessoa_que_ocupou_o_lugar = self.fila[posicao_de_quem_sai]
            self.subir(posicao_de_quem_sai)
            posicao_depois_de_subir = self._buscar_posicao(pessoa_que_ocupou_o_lugar.id)
            self.descer(posicao_depois_de_subir)

        return pessoa_removida

    def listar_ordenado(self):
        copia_da_fila = FilaPrioridade(self.vem_antes, self.campo_prioridade)
        copia_da_fila.fila = self.fila[:]
        copia_da_fila.posicoes = self.posicoes[:]

        pessoas_em_ordem = []
        while not copia_da_fila.esta_vazia():
            pessoas_em_ordem.append(copia_da_fila.remover_minimo())

        return pessoas_em_ordem

    # ---------- verificacao de integridade ----------

    def validar(self):
        quantidade_na_fila = len(self.fila)

        for posicao_atual in range(1, quantidade_na_fila):
            posicao_de_quem_esta_acima = self._posicao_acima(posicao_atual)
            pessoa_atual = self.fila[posicao_atual]
            pessoa_acima = self.fila[posicao_de_quem_esta_acima]

            if self.vem_antes(pessoa_atual, pessoa_acima):
                return False, (
                    f"Ordem quebrada: o id {pessoa_atual.id} (posição {posicao_atual}) "
                    f"deveria estar acima do id {pessoa_acima.id} "
                    f"(posição {posicao_de_quem_esta_acima})."
                )

        for posicao_atual in range(quantidade_na_fila):
            pessoa_atual = self.fila[posicao_atual]
            posicao_no_mapa = self._buscar_posicao(pessoa_atual.id)

            if posicao_no_mapa != posicao_atual:
                return False, (
                    f"Mapa de posições errado: o id {pessoa_atual.id} está na posição "
                    f"{posicao_atual}, mas o mapa indica {posicao_no_mapa}."
                )

        quantidade_no_mapa = 0
        for posicao_guardada in self.posicoes:
            if posicao_guardada is not None:
                quantidade_no_mapa = quantidade_no_mapa + 1

        if quantidade_no_mapa != quantidade_na_fila:
            return False, (
                f"Mapa de posições com sobra: o mapa guarda {quantidade_no_mapa} ids, "
                f"mas a fila tem {quantidade_na_fila}."
            )

        return True, f"Fila íntegra: ordem e mapa de posições corretos ({quantidade_na_fila} na fila)."


# ---------- regras de comparacao SIGAE ----------

def paciente_vem_antes(paciente_avaliado, paciente_comparado):
    if paciente_avaliado.prioridade != paciente_comparado.prioridade:
        return paciente_avaliado.prioridade < paciente_comparado.prioridade
    if paciente_avaliado.horario != paciente_comparado.horario:
        return paciente_avaliado.horario < paciente_comparado.horario
    return paciente_avaliado.id < paciente_comparado.id


def medico_vem_antes(medico_avaliado, medico_comparado):
    if medico_avaliado.atendimentos != medico_comparado.atendimentos:
        return medico_avaliado.atendimentos < medico_comparado.atendimentos
    if medico_avaliado.ordem_cadastro != medico_comparado.ordem_cadastro:
        return medico_avaliado.ordem_cadastro < medico_comparado.ordem_cadastro
    return medico_avaliado.id < medico_comparado.id