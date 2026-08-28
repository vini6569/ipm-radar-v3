# ============================================================
# MOTOR IPM - IPM RADAR V4.2
# ============================================================

_odds_anteriores = {}


def _converter_odd(valor):
    try:
        numero = float(valor)
        return numero if numero > 0 else None
    except (TypeError, ValueError):
        return None


def calcular_variacao_odd(odd_anterior, odd_atual):
    anterior = _converter_odd(odd_anterior)
    atual = _converter_odd(odd_atual)

    if anterior is None or atual is None:
        return 0.0

    return ((atual - anterior) / anterior) * 100.0


def classificar_forca(variacao_odd):
    try:
        valor = abs(float(variacao_odd))
    except (TypeError, ValueError):
        return "ESTAVEL"

    if valor >= 10:
        return "MUITO FORTE"
    if valor >= 5:
        return "FORTE"
    if valor >= 2:
        return "MODERADO"
    if valor >= 0.5:
        return "FRACO"
    return "ESTAVEL"


def classificar_direcao(variacao_odd):
    try:
        valor = float(variacao_odd)
    except (TypeError, ValueError):
        return "ESTAVEL"

    if valor < -0.05:
        return "QUEDA"
    if valor > 0.05:
        return "ALTA"
    return "ESTAVEL"


def calcular_ipm(
    variacao_odd,
    minuto=0,
    gols=0,
    escanteios=0,
    finalizacoes=0,
    ataques_perigosos=0,
):
    try:
        variacao = float(variacao_odd)
        minuto = max(int(minuto), 0)
        gols = max(int(gols), 0)
        escanteios = max(int(escanteios), 0)
        finalizacoes = max(int(finalizacoes), 0)
        ataques_perigosos = max(int(ataques_perigosos), 0)

        movimento = min(abs(variacao) * 5.0, 60.0)
        confirmacao_gols = min(gols * 5.0, 10.0)
        confirmacao_escanteios = min(escanteios * 1.5, 10.0)
        confirmacao_finalizacoes = min(finalizacoes * 0.5, 10.0)
        confirmacao_ataques = min(ataques_perigosos * 0.2, 10.0)

        ipm = min(
            max(
                movimento
                + confirmacao_gols
                + confirmacao_escanteios
                + confirmacao_finalizacoes
                + confirmacao_ataques,
                0.0,
            ),
            100.0,
        )

        return {
            "ipm": round(ipm, 2),
            "variacao_odd": round(variacao, 2),
            "forca": classificar_forca(variacao),
            "direcao": classificar_direcao(variacao),
            "movimento": round(movimento, 2),
            "confirmacao_gols": round(confirmacao_gols, 2),
            "confirmacao_escanteios": round(confirmacao_escanteios, 2),
            "confirmacao_finalizacoes": round(confirmacao_finalizacoes, 2),
            "confirmacao_ataques": round(confirmacao_ataques, 2),
            "minuto": minuto,
            "gols": gols,
            "escanteios": escanteios,
            "finalizacoes": finalizacoes,
            "ataques_perigosos": ataques_perigosos,
        }
    except Exception as erro:
        return {
            "ipm": 0.0,
            "variacao_odd": 0.0,
            "forca": "ESTAVEL",
            "direcao": "ESTAVEL",
            "movimento": 0.0,
            "confirmacao_gols": 0.0,
            "confirmacao_escanteios": 0.0,
            "confirmacao_finalizacoes": 0.0,
            "confirmacao_ataques": 0.0,
            "minuto": minuto,
            "gols": gols,
            "escanteios": escanteios,
            "finalizacoes": finalizacoes,
            "ataques_perigosos": ataques_perigosos,
            "erro": str(erro),
        }


def analisar_ipm_com_memoria(
    chave_jogo,
    odd_atual,
    minuto=0,
    gols=0,
    escanteios=0,
    finalizacoes=0,
    ataques_perigosos=0,
):
    if chave_jogo is None:
        raise ValueError("chave_jogo é obrigatória")

    chave = str(chave_jogo)
    atual = _converter_odd(odd_atual)

    if atual is None:
        resultado = calcular_ipm(
            0.0,
            minuto,
            gols,
            escanteios,
            finalizacoes,
            ataques_perigosos,
        )
        resultado.update(
            {
                "odd_anterior": None,
                "odd_atual": odd_atual,
                "primeira_consulta": False,
                "erro": "odd_atual_invalida",
            }
        )
        return resultado

    anterior = _odds_anteriores.get(chave)
    variacao = (
        0.0
        if anterior is None
        else calcular_variacao_odd(anterior, atual)
    )

    resultado = calcular_ipm(
        variacao,
        minuto,
        gols,
        escanteios,
        finalizacoes,
        ataques_perigosos,
    )

    resultado.update(
        {
            "odd_anterior": anterior,
            "odd_atual": atual,
            "primeira_consulta": anterior is None,
        }
    )

    _odds_anteriores[chave] = atual
    return resultado


def limpar_memoria():
    _odds_anteriores.clear()


def _placar(jogo, mercados=None):
    jogo = jogo if isinstance(jogo, dict) else {}
    mercados = mercados if isinstance(mercados, dict) else {}

    fontes = (jogo, mercados)

    for fonte in fontes:
        for chave in ("score", "scores", "placar", "result"):
            valor = fonte.get(chave)

            if isinstance(valor, dict):
                pares = (
                    ("home", "away"),
                    ("home_score", "away_score"),
                    ("homeScore", "awayScore"),
                    ("goals_home", "goals_away"),
                )
                for a_key, b_key in pares:
                    a = valor.get(a_key)
                    b = valor.get(b_key)
                    if a is not None and b is not None:
                        try:
                            return int(a), int(b)
                        except (TypeError, ValueError):
                            pass

            if isinstance(valor, (list, tuple)) and len(valor) >= 2:
                try:
                    return int(valor[0]), int(valor[1])
                except (TypeError, ValueError):
                    pass

            if isinstance(valor, str) and "x" in valor.lower():
                try:
                    a, b = valor.lower().replace(" ", "").split("x", 1)
                    return int(a), int(b)
                except (TypeError, ValueError):
                    pass

    pares_diretos = (
        ("home_score", "away_score"),
        ("homeScore", "awayScore"),
        ("goals_home", "goals_away"),
    )

    for fonte in fontes:
        for a_key, b_key in pares_diretos:
            a = fonte.get(a_key)
            b = fonte.get(b_key)
            if a is not None and b is not None:
                try:
                    return int(a), int(b)
                except (TypeError, ValueError):
                    pass

    return None, None


def obter_status_jogo(jogo):
    if not isinstance(jogo, dict):
        return ""

    for chave in ("status", "state", "match_status"):
        valor = jogo.get(chave)

        if isinstance(valor, dict):
            for sub in ("short", "long", "name", "status", "code"):
                if valor.get(sub) is not None:
                    return str(valor[sub]).upper()
        elif valor is not None:
            return str(valor).upper()

    return ""


def jogo_finalizado(jogo):
    status = obter_status_jogo(jogo)
    marcadores = (
        "FINISHED",
        "FINISH",
        "FT",
        "FINALIZADO",
        "ENCERRADO",
        "AFTER",
        "ENDED",
        "COMPLETED",
    )
    return any(marcador in status for marcador in marcadores)


def resultado_empate(jogo, mercados=None):
    a, b = _placar(jogo, mercados)
    if a is None or b is None:
        return None
    return a == b


def avaliar_entrada(
    resultado,
    minuto,
    ipm_minimo=40.0,
    variacao_minima=0.5,
    minuto_minimo=1,
    minuto_maximo=5,
):
    try:
        m = int(minuto)
        ipm = float(resultado.get("ipm", 0))
        variacao = abs(float(resultado.get("variacao_odd", 0)))
    except (TypeError, ValueError, AttributeError):
        return False

    return (
        minuto_minimo <= m <= minuto_maximo
        and not resultado.get("primeira_consulta", False)
        and ipm >= float(ipm_minimo)
        and variacao >= float(variacao_minima)
    )


def formatar_radar(jogo, resultado, mercados=None):
    jogo = jogo if isinstance(jogo, dict) else {}
    resultado = resultado if isinstance(resultado, dict) else {}
    mercados = mercados if isinstance(mercados, dict) else {}

    casa = jogo.get("home") or "Casa"
    fora = jogo.get("away") or "Fora"

    a, b = _placar(jogo, mercados)
    placar = (
        f"{a} x {b}"
        if a is not None and b is not None
        else "não disponível"
    )

    primeira = resultado.get("primeira_consulta", False)
    variacao = resultado.get("variacao_odd", 0.0)
    texto_variacao = (
        "AGUARDANDO COMPARAÇÃO"
        if primeira
        else f"{float(variacao):+.2f}%"
    )

    return "\n".join(
        [
            "",
            "=" * 70,
            "📡 IPM RADAR V4.2",
            "=" * 70,
            f"⚽ {casa} x {fora}",
            f"⏱️ Minuto: {resultado.get('minuto', 0)}",
            f"📊 Placar: {placar}",
            f"💰 Odd empate anterior: {resultado.get('odd_anterior')}",
            f"💰 Odd empate atual: {resultado.get('odd_atual')}",
            f"📈 Variação: {texto_variacao}",
            f"🔥 Força: {resultado.get('forca', 'ESTAVEL')}",
            f"🧭 Direção: {resultado.get('direcao', 'ESTAVEL')}",
            f"🎯 IPM: {float(resultado.get('ipm', 0)):.2f}/100",
            f"⚽ Gols: {resultado.get('gols', 0)}",
            f"🚩 Escanteios: {resultado.get('escanteios', 0)}",
            f"🥅 Finalizações: {resultado.get('finalizacoes', 0)}",
            f"⚡ Ataques perigosos: {resultado.get('ataques_perigosos', 0)}",
            f"📊 FT: {len(mercados.get('odds_ft', []))} | HT: {len(mercados.get('odds_ht', []))}",
            "=" * 70,
        ]
)
