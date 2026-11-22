from copy import deepcopy
from datetime import datetime, timedelta
from threading import Lock

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

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


def _criar_dados_iniciais():
    agora = datetime.now()
    pacientes = {}
    for pid, nome, idade, sexo, nivel, queixa, espera, sinais in _DADOS_BASE:
        pacientes[pid] = {
            "id": pid,
            "nome": nome,
            "idade": idade,
            "sexo": sexo,
            "nivel": nivel,
            "queixa": queixa,
            "sinais": dict(sinais),
            "observacoes": "",
            "chegada_dt": agora - timedelta(minutes=espera),
            "senha": _gerar_senha(nome, pid),
        }
    return pacientes


def _estado_inicial():
    return {
        "fila": _criar_dados_iniciais(),
        "historico": [],  # chamadas, mais recente primeiro
        "atendimentos": {},  # consultório -> atendimento em andamento
        "evento_seq": 0,  # incrementa a cada chamada/rechamada (o telão usa para tocar o aviso)
        "ultimo_evento": None,
        "proximo_id": 1049,
    }


db = _estado_inicial()


def _serializar_paciente(p, agora):
    info = NIVEIS_EMERGENCIA[p["nivel"]]
    espera = max(0, int((agora - p["chegada_dt"]).total_seconds() // 60))
    registro = {k: deepcopy(v) for k, v in p.items() if k != "chegada_dt"}
    registro.update(
        {
            "chegada": p["chegada_dt"].strftime("%H:%M"),
            "chegada_iso": p["chegada_dt"].isoformat(timespec="seconds"),
            "espera_min": espera,
            "nivel_nome": info["nome"],
            "nivel_slug": info["slug"],
            "tempo_alvo": info["tempo_alvo"],
            "alvo_min": info["alvo_min"],
            "atrasado": espera > info["alvo_min"],
        }
    )
    return registro


def _fila_ordenada():
    """Maior prioridade primeiro (menor nível); empate resolvido por quem chegou antes."""
    agora = datetime.now()
    ordenados = sorted(db["fila"].values(), key=lambda p: (p["nivel"], p["chegada_dt"], p["id"]))
    resultado = []
    for idx, p in enumerate(ordenados, start=1):
        registro = _serializar_paciente(p, agora)
        registro["ordem"] = idx
        resultado.append(registro)
    return resultado


def _obter_estado():
    ordenados = _fila_ordenada()
    contagem = {nivel: 0 for nivel in NIVEIS_EMERGENCIA}
    for p in ordenados:
        contagem[p["nivel"]] += 1

    esperas = [p["espera_min"] for p in ordenados]
    atendidos = db["historico"]
    espera_atendidos = [c["espera_min"] for c in atendidos]

    return {
        "total": len(ordenados),
        "proximo": ordenados[0] if ordenados else None,
        "seguintes": ordenados[1:6],
        "pacientes": ordenados,
        "contagem_niveis": contagem,
        "historico": atendidos[:50],
        "ultimo_chamado": atendidos[0] if atendidos else None,
        "ultimo_evento": db["ultimo_evento"],
        "estatisticas": {
            "criticos": contagem[1] + contagem[2],
            "atrasados": sum(1 for p in ordenados if p["atrasado"]),
            "espera_media": round(sum(esperas) / len(esperas)) if esperas else 0,
            "atendidos": len(atendidos),
            "espera_media_atendidos": round(sum(espera_atendidos) / len(espera_atendidos)) if espera_atendidos else 0,
        },
        "consultorios": CONSULTORIOS,
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


@app.route("/")
def index():
    with _lock:
        estado = _obter_estado()
    return render_template("index.html", estado=estado, niveis=NIVEIS_EMERGENCIA)


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
    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("nome", "")).strip()
    queixa = str(dados.get("queixa", "")).strip()
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

    sinais_in = dados.get("sinais") or {}
    sinais = {}
    for chave, conv in (("pa", str), ("fc", int), ("temp", float), ("spo2", int)):
        valor = sinais_in.get(chave)
        if valor in (None, ""):
            continue
        try:
            sinais[chave] = conv(valor).strip() if conv is str else conv(valor)
        except (TypeError, ValueError):
            return _erro(f"Valor inválido para o sinal vital '{chave}'.")

    with _lock:
        pid = f"PAC-{db['proximo_id']}"
        db["proximo_id"] += 1
        db["fila"][pid] = {
            "id": pid,
            "nome": nome,
            "idade": idade,
            "sexo": sexo,
            "nivel": nivel,
            "queixa": queixa,
            "sinais": sinais,
            "observacoes": str(dados.get("observacoes", "")).strip(),
            "chegada_dt": datetime.now(),
            "senha": _gerar_senha(nome, pid),
        }
        estado = _obter_estado()
        estado["criado_id"] = pid
        return jsonify(estado), 201


@app.route("/api/pacientes/<pid>", methods=["GET"])
def api_paciente(pid):
    with _lock:
        for p in _fila_ordenada():
            if p["id"] == pid:
                return jsonify(p)
    return _erro("Paciente não encontrado na fila.", 404)


@app.route("/api/pacientes/<pid>", methods=["PATCH"])
def api_atualizar_paciente(pid):
    """Reclassifica o nível de urgência de um paciente que está na fila."""
    dados = request.get_json(silent=True) or {}
    try:
        nivel = int(dados.get("nivel"))
    except (TypeError, ValueError):
        return _erro("Informe o novo nível de urgência.")
    if nivel not in NIVEIS_EMERGENCIA:
        return _erro("Nível de emergência inválido.")

    with _lock:
        paciente = db["fila"].get(pid)
        if paciente is None:
            return _erro("Paciente não encontrado na fila.", 404)
        paciente["nivel"] = nivel
        return jsonify(_obter_estado())


@app.route("/api/pacientes/<pid>", methods=["DELETE"])
def api_remover_paciente(pid):
    with _lock:
        if db["fila"].pop(pid, None) is None:
            return _erro("Paciente não encontrado na fila.", 404)
        return jsonify(_obter_estado())


@app.route("/api/chamar", methods=["POST"])
def api_chamar():
    """Chama o próximo da fila ou, se `id` for enviado, um paciente específico."""
    dados = request.get_json(silent=True) or {}
    consultorio = str(dados.get("consultorio") or CONSULTORIOS[0])
    pid = dados.get("id")

    with _lock:
        if consultorio in db["atendimentos"]:
            atual = db["atendimentos"][consultorio]["paciente"]["nome"]
            return _erro(f"{consultorio} está atendendo {atual}. Encerre o atendimento antes de chamar outro paciente.", 409)
        ordenados = _fila_ordenada()
        if not ordenados:
            return _erro("Não há pacientes na fila.", 409)
        if pid:
            alvo = next((p for p in ordenados if p["id"] == pid), None)
            if alvo is None:
                return _erro("Paciente não encontrado na fila.", 404)
        else:
            alvo = ordenados[0]

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
            "horario": datetime.now().strftime("%H:%M"),
            "vezes": 1,
            "status": "em_atendimento",
        }
        agora = datetime.now()
        db["atendimentos"][consultorio] = {
            "seq": chamada["seq"],
            "consultorio": consultorio,
            "paciente": alvo,
            "inicio": agora.strftime("%H:%M"),
            "inicio_iso": agora.isoformat(timespec="seconds"),
            "prontuario": {**{c: "" for c in CAMPOS_PRONTUARIO}, "desfecho": ""},
            "salvo_em": None,
        }
        db["historico"].insert(0, chamada)
        db["fila"].pop(alvo["id"], None)
        _registrar_evento("chamada", chamada)
        return jsonify(_obter_estado())


@app.route("/api/rechamar", methods=["POST"])
def api_rechamar():
    """Repete o aviso de uma chamada (padrão: a mais recente)."""
    dados = request.get_json(silent=True) or {}
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
    dados = request.get_json(silent=True) or {}
    with _lock:
        atendimento = _achar_atendimento(seq)
        if atendimento is None:
            return _erro("Atendimento não encontrado ou já encerrado.", 404)
        _aplicar_prontuario(atendimento, dados)
        atendimento["salvo_em"] = datetime.now().strftime("%H:%M:%S")
        return jsonify({"seq": seq, "salvo_em": atendimento["salvo_em"]})


@app.route("/api/atendimentos/<int:seq>/encerrar", methods=["POST"])
def api_encerrar_atendimento(seq):
    dados = request.get_json(silent=True) or {}
    with _lock:
        atendimento = _achar_atendimento(seq)
        if atendimento is None:
            return _erro("Atendimento não encontrado ou já encerrado.", 404)
        _aplicar_prontuario(atendimento, dados)
        desfecho = atendimento["prontuario"]["desfecho"]
        if desfecho not in DESFECHOS:
            return _erro("Selecione o desfecho do atendimento para encerrar.")

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


@app.route("/api/resetar", methods=["POST"])
def api_resetar():
    with _lock:
        seq = db["evento_seq"]
        db.clear()
        db.update(_estado_inicial())
        db["evento_seq"] = seq  # mantém a sequência para o telão não repetir avisos antigos
        return jsonify(_obter_estado())


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
