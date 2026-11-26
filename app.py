from copy import deepcopy
from datetime import datetime, timedelta
import os
from threading import Lock

from flask import Flask, jsonify, redirect, render_template, request, url_for

from servico.servico_atendimento import ServicoAtendimento

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # 64 KB

NIVEIS_EMERGENCIA = {
    1: {"codigo": 1, "slug": "emergencia", "nome": "Emergência", "tempo_alvo": "Imediato", "alvo_min": 0},
    2: {"codigo": 2, "slug": "muito-urgente", "nome": "Muito Urgente", "tempo_alvo": "Até 10 min", "alvo_min": 10},
    3: {"codigo": 3, "slug": "urgente", "nome": "Urgente", "tempo_alvo": "Até 60 min", "alvo_min": 60},
    4: {"codigo": 4, "slug": "pouco-urgente", "nome": "Pouco Urgente", "tempo_alvo": "Até 120 min", "alvo_min": 120},
    5: {"codigo": 5, "slug": "nao-urgente", "nome": "Não Urgente", "tempo_alvo": "Até 240 min", "alvo_min": 240},
}

CONSULTORIOS = ["Consultório 1", "Consultório 2", "Consultório 3", "Consultório 4", "Sala de Emergência"]

DESFECHOS = {
    "alta": "Alta",
    "observacao": "Em observação",
    "encaminhamento": "Encaminhado",
    "internacao": "Internação",
    "nao_compareceu": "Não compareceu",
}

CAMPOS_PRONTUARIO = ("anamnese", "exame_fisico", "hipotese", "conduta")

_lock = Lock()

# (id, nome, idade, sexo, nível, queixa, espera_min, sinais vitais)
_DADOS_BASE = [
    ("PAC-1042", "Carlos Eduardo Mendes", 64, "M", 1, "Dor torácica intensa com irradiação e dispneia", 3,
     {"pa": "170/105", "fc": 118, "temp": 36.8, "spo2": 89}),
    ("PAC-1045", "Mariana Silva Costa", 29, "F", 2, "Crise asmática aguda, saturação reduzida", 8,
     {"pa": "130/85", "fc": 112, "temp": 37.1, "spo2": 91}),
    ("PAC-1048", "João Pedro Albuquerque", 51, "M", 2, "Trauma craniano leve após queda, tontura", 5,
     {"pa": "145/90", "fc": 96, "temp": 36.5, "spo2": 97}),
    ("PAC-1039", "Fernanda Oliveira Lima", 42, "F", 3, "Dor abdominal moderada em quadrante inferior direito", 27,
     {"pa": "125/80", "fc": 98, "temp": 37.9, "spo2": 98}),
    ("PAC-1041", "Roberto Nascimento", 73, "M", 3, "Pico hipertensivo sem sintomas neurológicos", 19,
     {"pa": "190/110", "fc": 84, "temp": 36.4, "spo2": 96}),
    ("PAC-1044", "Beatriz Rocha Ferreira", 18, "F", 3, "Febre persistente acima de 39°C há 24h", 14,
     {"pa": "110/70", "fc": 104, "temp": 39.4, "spo2": 97}),
    ("PAC-1035", "Lucas Henrique Souza", 34, "M", 4, "Entorse de tornozelo direito com edema leve", 46,
     {"pa": "120/80", "fc": 76, "temp": 36.6, "spo2": 99}),
    ("PAC-1038", "Patrícia Gomes Martins", 56, "F", 4, "Cefaleia tensional há 2 dias", 33,
     {"pa": "135/85", "fc": 72, "temp": 36.7, "spo2": 98}),
    ("PAC-1046", "André Luiz Teixeira", 25, "M", 4, "Odinofagia e congestão nasal sem febre", 11,
     {"pa": "118/76", "fc": 70, "temp": 37.2, "spo2": 99}),
    ("PAC-1032", "Sônia Maria Carvalho", 48, "F", 5, "Renovação de receita de uso contínuo", 58,
     {"pa": "128/82", "fc": 68, "temp": 36.5, "spo2": 98}),
    ("PAC-1040", "Thiago Batista Dias", 22, "M", 5, "Escoriação superficial em antebraço", 24,
     {"pa": "115/75", "fc": 74, "temp": 36.6, "spo2": 99}),
]


def _gerar_senha(nome, pid):
    """Senha do painel: iniciais do primeiro e último nome + número do atendimento (ex.: PM-38)."""
    partes = nome.split()
    iniciais = (partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")).upper()
    numero = int(pid.split("-")[1]) % 1000
    return f"{iniciais}-{numero:02d}"


def _criar_servico():
    """Monta o ServicoAtendimento da equipe com os dados de teste (pacientes e médicos)."""
    agora = datetime.now()
    servico = ServicoAtendimento()
    for pid, nome, idade, sexo, nivel, queixa, espera, sinais in _DADOS_BASE:
        servico.proximo_id_paciente = int(pid.split("-")[1])
        servico.cadastrar_paciente(nome, idade, sexo, nivel, queixa, agora - timedelta(minutes=espera),
                                   sinais=sinais, senha=_gerar_senha(nome, pid))
    servico.proximo_id_paciente = 1049
    for nome, concluidos in (("Dra. Ana Paula Reis", 1), ("Dr. Bruno Tavares", 3), ("Dra. Clara Monteiro", 2)):
        servico.cadastrar_medico(nome, atendimentos=concluidos)
    return servico


def _estado_inicial():
    return {
        "servico": _criar_servico(),
        "historico": [],  # chamadas, mais recente primeiro
        "atendimentos": {},  # consultório -> atendimento em andamento
        "evento_seq": 0,  # incrementa a cada chamada/rechamada (o telão usa para tocar o aviso)
        "ultimo_evento": None,
    }


db = _estado_inicial()


def _serializar_paciente(paciente, agora):
    """`paciente` é o servico.paciente.Paciente guardado na Hash/árvore/heap."""
    p = paciente.to_dict()
    p.pop("chegada_dt")
    info = NIVEIS_EMERGENCIA[p["nivel"]]
    espera = max(0, int((agora - paciente.chegada_dt).total_seconds() // 60))
    registro = deepcopy(p)
    registro.update(
        {
            "chegada": paciente.chegada_dt.strftime("%H:%M"),
            "chegada_iso": paciente.chegada_dt.isoformat(timespec="seconds"),
            "espera_min": espera,
            "nivel_nome": info["nome"],
            "nivel_slug": info["slug"],
            "tempo_alvo": info["tempo_alvo"],
            "alvo_min": info["alvo_min"],
            "atrasado": espera > info["alvo_min"],
        }
    )
    return registro


def _medicos_dict():
    """Disponíveis na ordem do Min-Heap de médicos, depois os ocupados."""
    servico = db["servico"]
    ordem = servico.fila_medicos.listar_ordenado()  # cópia do heap; o original não muda
    ocupados = [m for m in servico.listar_medicos() if not m.disponivel]
    em_atend = {a["medico_id"]: a["paciente"]["nome"] for a in db["atendimentos"].values()}
    return [
        {"id": m.id, "nome": m.nome, "concluidos": m.atendimentos, "disponivel": m.disponivel,
         "paciente": em_atend.get(m.id)}
        for m in ordem + ocupados
    ]


def _fila_ordenada():
    """Ordem de atendimento extraída do Min-Heap (FilaPrioridade)."""
    agora = datetime.now()
    resultado = []
    for idx, p in enumerate(db["servico"].fila_pacientes.listar_ordenado(), start=1):
        registro = _serializar_paciente(p, agora)
        registro["ordem"] = idx
        resultado.append(registro)
    return resultado


def _ordem_chegada(posicoes):
    """Ordem cronológica extraída da Árvore Rubro-Negra (percurso em ordem)."""
    agora = datetime.now()
    resultado = []
    for idx, p in enumerate(db["servico"].listar_pacientes(), start=1):  # in-order da Rubro-Negra
        registro = _serializar_paciente(p, agora)
        registro["chegada_ordem"] = idx
        registro["ordem"] = posicoes.get(registro["id"])
        resultado.append(registro)
    return resultado


def _arvore_para_dict(arvore, no):
    """Leitura recursiva da Rubro-Negra (sem alterar nada) para desenhar na tela."""
    if no == arvore.NULO:
        return None
    return {
        "id": f"PAC-{no.id}",
        "horario": no.horario.strftime("%H:%M"),
        "nivel": no.dados.prioridade,
        "cor": no.cor,
        "esq": _arvore_para_dict(arvore, no.esquerda),
        "dir": _arvore_para_dict(arvore, no.direita),
    }


def _altura(no):
    return 0 if no is None else 1 + max(_altura(no["esq"]), _altura(no["dir"]))


def _resumo_estruturas(servico=None):
    servico = servico or db["servico"]
    tabela = servico.tabela_hash
    arvore = _arvore_para_dict(servico.arvore, servico.arvore.raiz)
    return {
        "integra": servico.validar_integridade(),
        "arvore_valida": servico.arvore.validar(),
        "arvore": arvore,
        "arvore_altura": _altura(arvore),
        # vetores internos dos heaps, na ordem real do array (índice 0 = raiz)
        "heap_pacientes": [{"id": p.id_publico, "nivel": p.prioridade} for p in servico.fila_pacientes.fila],
        "heap_medicos": [{"id": m.id, "nome": m.nome, "concluidos": m.atendimentos} for m in servico.fila_medicos.fila],
        "hash": {
            "capacidade": tabela.capacidade,
            "total": tabela.quantidade(),
            "colisoes": tabela.total_colisoes,
            "ocupacao": tabela.ocupacao_percentual(),
            "buckets": [[f"PAC-{par[0]}" for par in bucket] for bucket in tabela.tabela],
        },
    }


def _obter_estado():
    medicos = _medicos_dict()
    ordenados = _fila_ordenada()
    contagem = {nivel: 0 for nivel in NIVEIS_EMERGENCIA}
    for p in ordenados:
        contagem[p["nivel"]] += 1

    esperas = [p["espera_min"] for p in ordenados]
    atendidos = db["historico"]
    atendimentos_realizados = [c for c in atendidos if c.get("desfecho") != "nao_compareceu"]
    espera_atendidos = [c["espera_min"] for c in atendimentos_realizados]

    return {
        "total": len(ordenados),
        "proximo": ordenados[0] if ordenados else None,
        "seguintes": ordenados[1:6],
        "pacientes": ordenados,
        "pacientes_chegada": _ordem_chegada({p["id"]: p["ordem"] for p in ordenados}),
        "contagem_niveis": contagem,
        "historico": atendidos[:50],
        "ultimo_chamado": atendidos[0] if atendidos else None,
        "ultimo_evento": db["ultimo_evento"],
        "estatisticas": {
            "criticos": contagem[1] + contagem[2],
            "atrasados": sum(1 for p in ordenados if p["atrasado"]),
            "espera_media": round(sum(esperas) / len(esperas)) if esperas else 0,
            "atendidos": len(atendimentos_realizados),
            "espera_media_atendidos": round(sum(espera_atendidos) / len(espera_atendidos)) if espera_atendidos else 0,
        },
        "consultorios": CONSULTORIOS,
        "medicos": medicos,
        "proximo_medico": next((m for m in medicos if m["disponivel"]), None),
        "estruturas": _resumo_estruturas(),
        "atendimentos": deepcopy(list(db["atendimentos"].values())),
        "desfechos": [{"codigo": k, "nome": v} for k, v in DESFECHOS.items()],
        "servidor_hora": datetime.now().strftime("%H:%M:%S"),
    }


def _registrar_evento(tipo, chamada):
    db["evento_seq"] += 1
    db["ultimo_evento"] = {
        "seq": db["evento_seq"],
        "tipo": tipo,
        "chamada": deepcopy(chamada),
    }


def _erro(msg, status=400):
    return jsonify({"erro": msg}), status


def _json_body():
    """Corpo JSON da requisição; qualquer coisa que não seja objeto vira {}."""
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}


@app.before_request
def _exigir_json_em_mutacoes():
    """Proteção CSRF: mutações na API exigem JSON e header customizado (força preflight CORS)."""
    if request.method in ("POST", "PATCH", "DELETE", "PUT") and request.path.startswith("/api/"):
        if request.method != "DELETE" and not request.is_json:
            return _erro("Content-Type deve ser application/json.", 415)
        if request.headers.get("X-Requested-With") != "fetch":
            return _erro("Requisição não permitida.", 403)
    return None


@app.after_request
def _headers_seguranca(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault(
        "Content-Security-Policy", "frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
    )
    return resp


@app.route("/")
def index():
    with _lock:
        estado = _obter_estado()
    return render_template("index.html", estado=estado, niveis=NIVEIS_EMERGENCIA)


@app.route("/estruturas")
def estruturas():
    """Acesso direto à seção Estruturas, que não aparece no menu."""
    return redirect(url_for("index") + "#/estruturas")


@app.route("/painel")
def painel():
    with _lock:
        estado = _obter_estado()
    return render_template("painel.html", estado=estado)


@app.route("/api/estado", methods=["GET"])
def api_estado():
    with _lock:
        return jsonify(_obter_estado())


@app.route("/api/pacientes", methods=["POST"])
def api_criar_paciente():
    dados = _json_body()
    nome = str(dados.get("nome", "")).strip()[:120]
    queixa = str(dados.get("queixa", "")).strip()[:500]
    sexo = str(dados.get("sexo", "")).strip().upper()
    try:
        idade = int(dados.get("idade"))
        nivel = int(dados.get("nivel"))
    except (TypeError, ValueError):
        return _erro("Idade e nível de emergência são obrigatórios.")

    if len(nome) < 3:
        return _erro("Informe o nome completo do paciente.")
    if not queixa:
        return _erro("Informe a queixa principal.")
    if not 0 <= idade <= 130:
        return _erro("Idade inválida.")
    if nivel not in NIVEIS_EMERGENCIA:
        return _erro("Nível de emergência inválido.")
    if sexo not in ("M", "F"):
        return _erro("Sexo deve ser M ou F.")

    agora = datetime.now()
    chegada_txt = str(dados.get("chegada") or "").strip()
    if chegada_txt:
        # Hora informada na triagem (HH:MM de hoje): a árvore rubro-negra ordena por ela,
        # então um paciente cadastrado depois pode aparecer antes na lista por chegada.
        try:
            hora = datetime.strptime(chegada_txt, "%H:%M")
        except ValueError:
            return _erro("Hora de chegada inválida. Use o formato HH:MM.")
        chegada = agora.replace(hour=hora.hour, minute=hora.minute, second=0, microsecond=0)
        if chegada > agora:
            return _erro("A hora de chegada não pode estar no futuro.")
    else:
        chegada = agora  # opção "Agora"

    sinais_in = dados.get("sinais")
    if not isinstance(sinais_in, dict):
        sinais_in = {}
    sinais = {}
    for chave, conv in (("pa", str), ("fc", int), ("temp", float), ("spo2", int)):
        valor = sinais_in.get(chave)
        if valor in (None, ""):
            continue
        try:
            sinais[chave] = conv(valor).strip()[:10] if conv is str else conv(valor)
        except (TypeError, ValueError):
            return _erro(f"Valor inválido para o sinal vital '{chave}'.")

    with _lock:
        servico = db["servico"]
        senha = _gerar_senha(nome, f"PAC-{servico.proximo_id_paciente}")
        try:
            paciente = servico.cadastrar_paciente(
                nome, idade, sexo, nivel, queixa, chegada, sinais=sinais,
                observacoes=str(dados.get("observacoes", "")).strip()[:2000], senha=senha,
            )
        except ValueError as exc:
            return _erro(str(exc))
        estado = _obter_estado()
        estado["criado_id"] = paciente.id_publico
        return jsonify(estado), 201


@app.route("/api/pacientes/<pid>", methods=["GET"])
def api_paciente(pid):
    with _lock:
        try:
            paciente = db["servico"].buscar_paciente(pid)  # busca pela Tabela Hash
        except ValueError:
            paciente = None
        if paciente is not None:
            return jsonify(next(p for p in _fila_ordenada() if p["id"] == paciente.id_publico))
    return _erro("Paciente não encontrado na fila.", 404)


@app.route("/api/pacientes/<pid>", methods=["PATCH"])
def api_atualizar_paciente(pid):
    """Reclassifica o nível de urgência de um paciente que está na fila."""
    dados = _json_body()
    try:
        nivel = int(dados.get("nivel"))
    except (TypeError, ValueError):
        return _erro("Informe o novo nível de urgência.")
    if nivel not in NIVEIS_EMERGENCIA:
        return _erro("Nível de emergência inválido.")

    with _lock:
        try:
            db["servico"].reclassificar_paciente(pid, nivel)
        except ValueError:
            return _erro("Paciente não encontrado na fila.", 404)
        return jsonify(_obter_estado())


@app.route("/api/pacientes/<pid>", methods=["DELETE"])
def api_remover_paciente(pid):
    with _lock:
        try:
            removido = db["servico"].cancelar_paciente(pid)
        except ValueError:
            removido = False
        if not removido:
            return _erro("Paciente não encontrado na fila.", 404)
        return jsonify(_obter_estado())


def _criterio_paciente(escolhido, segundo):
    """Explica por que o paciente estava na raiz do Min-Heap (mesma ordem de paciente_vem_antes)."""
    nome_nivel = NIVEIS_EMERGENCIA[escolhido.prioridade]["nome"]
    base = f"Raiz do Min-Heap de pacientes: nível {escolhido.prioridade} ({nome_nivel})"
    if segundo is None:
        return {"texto": base + ", único paciente aguardando.", "segundo": None}
    if escolhido.prioridade != segundo.prioridade:
        motivo = f"nível {escolhido.prioridade} é mais urgente que o nível {segundo.prioridade} de {segundo.id_publico}"
    elif escolhido.horario != segundo.horario:
        motivo = (f"mesmo nível de {segundo.id_publico}, mas chegou antes "
                  f"({escolhido.horario:%H:%M} × {segundo.horario:%H:%M})")
    else:
        motivo = f"mesmo nível e horário de {segundo.id_publico}; desempate pelo menor ID"
    return {"texto": f"{base}; {motivo}.", "segundo": segundo.id_publico}


def _criterio_medico(escolhido, segundo):
    """Explica por que o médico estava na raiz do Min-Heap (mesma ordem de medico_vem_antes)."""
    base = f"Raiz do Min-Heap de médicos: {escolhido.atendimentos} atendimento(s) concluído(s)"
    if segundo is None:
        return {"texto": base + ", único médico disponível.", "segundo": None}
    if escolhido.atendimentos != segundo.atendimentos:
        motivo = f"menos que {segundo.nome} (#{segundo.id}), que tinha {segundo.atendimentos}"
    elif escolhido.ordem_cadastro != segundo.ordem_cadastro:
        motivo = f"empate com {segundo.nome} (#{segundo.id}); cadastrado antes"
    else:
        motivo = f"empate com {segundo.nome} (#{segundo.id}); desempate pelo menor ID"
    return {"texto": f"{base}; {motivo}.", "segundo": f"#{segundo.id}"}


@app.route("/api/chamar", methods=["POST"])
def api_chamar():
    """Chama o próximo da fila ou, se `id` for enviado, um paciente específico."""
    dados = _json_body()
    consultorio = str(dados.get("consultorio") or CONSULTORIOS[0])
    if consultorio not in CONSULTORIOS:
        return _erro("Consultório inválido.")
    if dados.get("id"):
        return _erro("A chamada segue a fila de prioridade: use 'chamar próximo'.", 400)

    with _lock:
        if consultorio in db["atendimentos"]:
            atual = db["atendimentos"][consultorio]["paciente"]["nome"]
            return _erro(f"{consultorio} está atendendo {atual}. Encerre o atendimento antes de chamar outro paciente.", 409)
        try:
            resultado = db["servico"].chamar_proximo()  # raiz do heap de pacientes + do heap de médicos
        except ValueError as exc:
            return _erro(str(exc), 409)
        alvo = _serializar_paciente(resultado["paciente"], datetime.now())
        medico = resultado["medico"]
        # Depois da retirada, a nova raiz de cada heap é quem ficou em 2º lugar:
        # o critério é gravado agora, porque os heaps mudam depois.
        criterio = {
            "paciente": _criterio_paciente(resultado["paciente"], db["servico"].fila_pacientes.ver_proximo()),
            "medico": _criterio_medico(medico, db["servico"].fila_medicos.ver_proximo()),
            "medico_concluidos": medico.atendimentos,
        }

        chamada = {
            "seq": db["evento_seq"] + 1,
            "id": alvo["id"],
            "nome": alvo["nome"],
            "senha": alvo["senha"],
            "nivel": alvo["nivel"],
            "nivel_nome": alvo["nivel_nome"],
            "nivel_slug": alvo["nivel_slug"],
            "queixa": alvo["queixa"],
            "espera_min": alvo["espera_min"],
            "consultorio": consultorio,
            "medico": medico.nome,
            "medico_id": medico.id,
            "horario": datetime.now().strftime("%H:%M"),
            "vezes": 1,
            "status": "em_atendimento",
        }
        agora = datetime.now()
        db["atendimentos"][consultorio] = {
            "seq": chamada["seq"],
            "consultorio": consultorio,
            "paciente": alvo,
            "medico": medico.nome,
            "medico_id": medico.id,
            "criterio": criterio,
            "inicio": agora.strftime("%H:%M"),
            "inicio_iso": agora.isoformat(timespec="seconds"),
            "prontuario": {**{c: "" for c in CAMPOS_PRONTUARIO}, "desfecho": ""},
            "salvo_em": None,
        }
        db["historico"].insert(0, chamada)
        _registrar_evento("chamada", chamada)
        return jsonify(_obter_estado())


@app.route("/api/rechamar", methods=["POST"])
def api_rechamar():
    """Repete o aviso de uma chamada (padrão: a mais recente)."""
    dados = _json_body()
    seq = dados.get("seq")

    with _lock:
        if not db["historico"]:
            return _erro("Nenhuma chamada para repetir.", 409)
        chamada = db["historico"][0]
        if seq is not None:
            chamada = next((c for c in db["historico"] if c["seq"] == seq), None)
            if chamada is None:
                return _erro("Chamada não encontrada.", 404)
        if chamada.get("status") == "encerrado":
            return _erro("Este atendimento já foi encerrado.", 409)
        chamada["vezes"] += 1
        chamada["horario"] = datetime.now().strftime("%H:%M")
        _registrar_evento("rechamada", chamada)
        return jsonify(_obter_estado())


def _achar_atendimento(seq):
    return next((a for a in db["atendimentos"].values() if a["seq"] == seq), None)


def _aplicar_prontuario(atendimento, dados):
    """Copia para o prontuário apenas os campos conhecidos (texto, com limite de tamanho)."""
    prontuario = (dados or {}).get("prontuario") or {}
    for campo in CAMPOS_PRONTUARIO:
        if campo in prontuario:
            atendimento["prontuario"][campo] = str(prontuario[campo] or "")[:5000]
    desfecho = prontuario.get("desfecho")
    if desfecho in DESFECHOS or desfecho == "":
        atendimento["prontuario"]["desfecho"] = desfecho


@app.route("/api/atendimentos/<int:seq>", methods=["PATCH"])
def api_salvar_atendimento(seq):
    """Salvamento automático do prontuário enquanto o médico digita."""
    dados = _json_body()
    with _lock:
        atendimento = _achar_atendimento(seq)
        if atendimento is None:
            return _erro("Atendimento não encontrado ou já encerrado.", 404)
        _aplicar_prontuario(atendimento, dados)
        atendimento["salvo_em"] = datetime.now().strftime("%H:%M:%S")
        return jsonify({"seq": seq, "salvo_em": atendimento["salvo_em"]})


@app.route("/api/atendimentos/<int:seq>/encerrar", methods=["POST"])
def api_encerrar_atendimento(seq):
    dados = _json_body()
    with _lock:
        atendimento = _achar_atendimento(seq)
        if atendimento is None:
            return _erro("Atendimento não encontrado ou já encerrado.", 404)
        _aplicar_prontuario(atendimento, dados)
        desfecho = atendimento["prontuario"]["desfecho"]
        if desfecho not in DESFECHOS:
            return _erro("Selecione o desfecho do atendimento para encerrar.")

        # Primeiro o serviço (o médico volta ao heap, com rollback próprio); só se der certo
        # o estado da aplicação é alterado. Assim uma falha não deixa o médico preso como ocupado.
        try:
            db["servico"].finalizar_atendimento(atendimento["medico_id"])
        except ValueError as exc:
            return _erro(str(exc), 409)

        agora = datetime.now()
        inicio = datetime.fromisoformat(atendimento["inicio_iso"])
        chamada = next((c for c in db["historico"] if c["seq"] == seq), None)
        if chamada is not None:
            chamada.update(
                {
                    "status": "encerrado",
                    "desfecho": desfecho,
                    "desfecho_nome": DESFECHOS[desfecho],
                    "duracao_min": max(0, int((agora - inicio).total_seconds() // 60)),
                    "fim": agora.strftime("%H:%M"),
                    "prontuario": deepcopy(atendimento["prontuario"]),
                }
            )
        db["atendimentos"].pop(atendimento["consultorio"], None)
        return jsonify(_obter_estado())


@app.route("/api/estruturas/hash/<pid>", methods=["GET"])
def api_buscar_hash(pid):
    """Busca pelo ID usando exclusivamente a Tabela Hash e mostra o bucket consultado."""
    with _lock:
        servico = db["servico"]
        try:
            id_interno = servico._normalizar_id_paciente(pid.strip().upper())
            paciente = servico.buscar_paciente(id_interno)  # TabelaHash.buscar
            bucket = servico.tabela_hash.inspecionar_bucket(id_interno)
        except ValueError:
            return _erro("ID inválido. Use o formato PAC-1042.")
        situacao = "aguardando" if paciente else None
        if paciente is None:
            if any(a["paciente"]["id_interno"] == id_interno for a in db["atendimentos"].values()):
                situacao = "em_atendimento"
            elif any(h["id"] == f"PAC-{id_interno}" for h in db["historico"]):
                situacao = "historico"
        return jsonify({
            "id": f"PAC-{id_interno}",
            "indice": id_interno % servico.tabela_hash.capacidade,  # mesma função h(ID) da TabelaHash
            "bucket": [f"PAC-{par[0]}" for par in bucket],
            "encontrado": paciente is not None,
            "nome": paciente.nome if paciente else None,
            "situacao": situacao,
        })


@app.route("/api/medicos", methods=["POST"])
def api_cadastrar_medico():
    dados = _json_body()
    nome = str(dados.get("nome", "")).strip()[:120]
    if len(nome) < 3:
        return _erro("Informe o nome completo do médico.")
    # Carga inicial: atendimentos já concluídos (usada pelo Min-Heap de médicos).
    concluidos = dados.get("atendimentos", 0)
    if concluidos in (None, ""):
        concluidos = 0
    try:
        if isinstance(concluidos, bool) or float(concluidos) != int(float(concluidos)):
            raise ValueError
        concluidos = int(float(concluidos))
    except (TypeError, ValueError):
        return _erro("Atendimentos concluídos deve ser um número inteiro.")
    if not 0 <= concluidos <= 9999:
        return _erro("Atendimentos concluídos deve estar entre 0 e 9999.")
    with _lock:
        try:
            db["servico"].cadastrar_medico(nome, atendimentos=concluidos)
        except ValueError as exc:
            return _erro(str(exc))
        return jsonify(_obter_estado()), 201


# ---------------------------------------------------------------------------
# Demonstrações dos testes ao vivo (A, B e C)
# Cada uma roda num ServicoAtendimento novo, só para a demonstração: usa as
# estruturas da equipe sem mexer na fila real que está sendo operada.
# ---------------------------------------------------------------------------
def _demo_paciente(servico, pid, nome, nivel, horario):
    servico.proximo_id_paciente = pid
    return servico.cadastrar_paciente(nome, 40, "M", nivel, "Paciente de demonstração", horario)


def _quadro_hash(servico, titulo, destaque=(), alvo=None):
    tabela = servico.tabela_hash
    return {
        "tipo": "hash",
        "titulo": titulo,
        "capacidade": tabela.capacidade,
        "buckets": [[f"PAC-{par[0]}" for par in bucket] for bucket in tabela.tabela],
        "destaque": [f"PAC-{pid}" for pid in destaque],
        "alvo": alvo,
    }


def _quadro_heap_pacientes(servico, titulo, alvo=None, mudanca=None):
    """`alvo` é o ID do paciente alterado no passo; `mudanca` descreve a alteração (ex.: "P2 → P1")."""
    return {
        "tipo": "heap_pacientes",
        "titulo": titulo,
        "itens": [{"id": p.id_publico, "nome": p.nome, "nivel": p.prioridade} for p in servico.fila_pacientes.fila],
        "alvo": f"PAC-{alvo}" if alvo else None,
        "mudanca": mudanca,
    }


def _quadro_heap_medicos(servico, titulo, alvo=None, mudanca=None):
    return {
        "tipo": "heap_medicos",
        "titulo": titulo,
        "itens": [{"id": m.id, "nome": m.nome, "concluidos": m.atendimentos} for m in servico.fila_medicos.fila],
        "alvo": alvo,
        "mudanca": mudanca,
    }


def _demo_colisao():
    servico = ServicoAtendimento()
    hoje = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    cap = servico.tabela_hash.capacidade
    passos = []

    _demo_paciente(servico, 101, "Paciente Cento e Um", 3, hoje)
    passos.append({
        "texto": f"Cadastra PAC-101: h(101) = 101 % {cap} = {101 % cap}.",
        "detalhe": f"O bucket {101 % cap} estava vazio, então o PAC-101 entra sozinho.",
        "quadro": _quadro_hash(servico, "Tabela Hash", (101,), 101 % cap),
    })
    _demo_paciente(servico, 112, "Paciente Cento e Doze", 3, hoje + timedelta(minutes=1))
    passos.append({
        "texto": f"Cadastra PAC-112: h(112) = 112 % {cap} = {112 % cap}. Mesmo bucket do PAC-101: colisão.",
        "detalhe": f"Encadeamento separado: o bucket {112 % cap} passa a guardar os dois. "
                   f"Colisões registradas: {servico.tabela_hash.total_colisoes}.",
        "quadro": _quadro_hash(servico, "Tabela Hash com a colisão", (101, 112), 112 % cap),
    })
    for pid in (101, 112):
        achado = servico.buscar_paciente(pid)
        bucket = [f"PAC-{par[0]}" for par in servico.tabela_hash.inspecionar_bucket(pid)]
        passos.append({
            "texto": f"Localiza PAC-{pid} pela Hash.",
            "detalhe": f"Calcula {pid} % {cap} = {pid % cap}, vai direto ao bucket {pid % cap} "
                       f"({', '.join(bucket)}), percorre a lista e encontra \"{achado.nome}\".",
            "quadro": _quadro_hash(servico, f"Busca do PAC-{pid}", (pid,), pid % cap),
        })

    pid = 102
    while servico.tabela_hash.capacidade == cap:
        _demo_paciente(servico, pid, f"Paciente {pid}", 5, hoje + timedelta(minutes=pid - 100))
        pid += 1
    nova = servico.tabela_hash.capacidade
    juntos = 101 % nova == 112 % nova
    passos.append({
        "texto": f"Cadastra mais pacientes até a ocupação passar de 75%: a tabela dobra de {cap} para {nova} "
                 f"buckets e redistribui todos.",
        "detalhe": f"Com a nova capacidade, 101 % {nova} = {101 % nova} e 112 % {nova} = {112 % nova}: "
                   + ("os dois continuam juntos." if juntos else "os dois ficam em buckets diferentes."),
        "quadro": _quadro_hash(servico, "Depois do redimensionamento", (101, 112)),
    })
    for pid in (101, 112):
        achado = servico.buscar_paciente(pid)
        passos.append({
            "texto": f"Localiza PAC-{pid} de novo, na tabela redimensionada.",
            "detalhe": (f"Calcula {pid} % {nova} = {pid % nova} e encontra \"{achado.nome}\" no bucket {pid % nova}."
                        if achado else f"PAC-{pid} não encontrado!"),
            "quadro": _quadro_hash(servico, f"Busca do PAC-{pid}", (pid,), pid % nova),
        })
    return {"titulo": "Teste A · Colisão na Tabela Hash", "passos": passos,
            "integra": servico.validar_integridade()}


def _demo_prioridade():
    servico = ServicoAtendimento()
    hoje = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    for i, (nivel, nome) in enumerate(((2, "Ana"), (3, "Bruno"), (1, "Carla"), (4, "Diego"), (5, "Elisa"))):
        _demo_paciente(servico, 201 + i, nome, nivel, hoje + timedelta(minutes=5 * i))

    def raiz():
        p = servico.fila_pacientes.ver_proximo()
        return f"{p.id_publico} ({p.nome}, nível {p.prioridade}, chegou {p.horario:%H:%M})"

    passos = [{
        "texto": "Cadastra 5 pacientes: Ana (nível 2, 08:00), Bruno (3, 08:05), Carla (1, 08:10), "
                 "Diego (4, 08:15) e Elisa (5, 08:20).",
        "detalhe": "Raiz do Min-Heap: " + raiz() + ", a única com nível 1.",
        "quadro": _quadro_heap_pacientes(servico, "Heap inicial"),
    }]
    servico.reclassificar_paciente(201, 1)
    passos.append({
        "texto": "Reclassifica Ana (PAC-201) de nível 2 para 1.",
        "detalhe": "Empata com Carla no nível 1, mas chegou antes (08:00 × 08:10), então vira a raiz.",
        "quadro": _quadro_heap_pacientes(servico, "Depois de reclassificar Ana", 201, "P2 → P1"),
    })
    servico.reclassificar_paciente(205, 1)
    passos.append({
        "texto": "Reclassifica Elisa (PAC-205) de nível 5 para 1.",
        "detalhe": "Elisa sobe, mas não passa da Ana: mesmo nível, e a Ana chegou antes (08:00 × 08:20).",
        "quadro": _quadro_heap_pacientes(servico, "Depois de reclassificar Elisa", 205, "P5 → P1"),
    })
    servico.reclassificar_paciente(201, 4)
    passos.append({
        "texto": "Reclassifica Ana de volta, agora para nível 4.",
        "detalhe": "Ana desce, e a Carla, que chegou antes da Elisa, volta para a raiz.",
        "quadro": _quadro_heap_pacientes(servico, "Depois de rebaixar Ana", 201, "P1 → P4"),
    })
    return {"titulo": "Teste B · Prioridade no Min-Heap de pacientes", "passos": passos,
            "integra": servico.validar_integridade()}


def _demo_medicos():
    servico = ServicoAtendimento()
    hoje = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    for nome, carga in (("Dr. André", 3), ("Dra. Beatriz", 1), ("Dr. Caio", 1)):
        servico.cadastrar_medico(nome, atendimentos=carga)
    for i in range(6):
        _demo_paciente(servico, 301 + i, f"Paciente {i + 1}", 3, hoje + timedelta(minutes=i))

    def heap(titulo, alvo=None, mudanca=None):
        return _quadro_heap_medicos(servico, titulo, alvo, mudanca)

    passos = [{
        "texto": "Cadastra 3 clínicos com cargas diferentes: Dr. André (3 atendimentos), "
                 "Dra. Beatriz (1) e Dr. Caio (1), nessa ordem.",
        "detalhe": "Raiz do Min-Heap de médicos: Dra. Beatriz. Empata com Dr. Caio em 1, mas foi cadastrada antes.",
        "quadro": heap("Heap de médicos inicial"),
    }]

    def chamar(extra=None):
        r = servico.chamar_proximo()
        m = r["medico"]
        crit = _criterio_medico(m, servico.fila_medicos.ver_proximo())["texto"]
        passos.append({
            "texto": f"Chama {r['paciente'].id_publico}: designado {m.nome} (#{m.id}).",
            "detalhe": crit + (" " + extra if extra else "") + " Enquanto atende, sai do heap de disponíveis.",
            "quadro": heap(f"{m.nome} em atendimento", m.id, "saiu do heap (foi atender)"),
        })
        return m

    def finalizar(m):
        servico.finalizar_atendimento(m.id)
        passos.append({
            "texto": f"{m.nome} conclui o atendimento.",
            "detalhe": f"O contador passa para {m.atendimentos} e {m.nome} volta ao heap de disponíveis.",
            "quadro": heap(f"{m.nome} volta com {m.atendimentos}", m.id,
                           f"{m.atendimentos - 1} → {m.atendimentos} at."),
        })

    finalizar(chamar())
    finalizar(chamar())
    chamar()
    chamar()
    chamar("Dr. André só é chamado agora, porque era quem tinha mais atendimentos.")
    try:
        servico.chamar_proximo()
        passos.append({"texto": "Erro: a chamada deveria ter sido bloqueada."})
    except ValueError as exc:
        passos.append({
            "texto": "Nova chamada com os três médicos ocupados.",
            "detalhe": f"O heap de médicos está vazio, então a chamada fica bloqueada (\"{exc}\").",
            "quadro": heap("Heap de médicos vazio"),
        })
    return {"titulo": "Teste C · Balanceamento dos médicos", "passos": passos,
            "integra": servico.validar_integridade()}


_DEMONSTRACOES = {"a": _demo_colisao, "b": _demo_prioridade, "c": _demo_medicos}


@app.route("/api/demonstracao/<teste>", methods=["GET"])
def api_demonstracao(teste):
    """Roda o teste ao vivo pedido num serviço separado e devolve o passo a passo."""
    demo = _DEMONSTRACOES.get(teste.lower())
    if demo is None:
        return _erro("Teste inexistente. Use A, B ou C.", 404)
    return jsonify(demo())


@app.route("/api/resetar", methods=["POST"])
def api_resetar():
    if os.environ.get("SIGAE_PERMITIR_RESET", "1") != "1":
        return _erro("Reset desabilitado neste ambiente.", 403)
    with _lock:
        seq = db["evento_seq"]
        db.clear()
        db.update(_estado_inicial())
        db["evento_seq"] = seq  # mantém a sequência para o telão não repetir avisos antigos
        return jsonify(_obter_estado())


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", host="127.0.0.1", port=5000)
