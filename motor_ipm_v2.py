# ============================================================
# MOTOR IPM - IPM RADAR V4
# ============================================================

_odds_anteriores = {}

def _converter_odd(valor):
    try:
        valor = float(valor)
        return valor if valor > 0 else None
    except (TypeError, ValueError):
        return None

def calcular_variacao_odd(
    odd_anterior,
    odd_atual
):
    anterior = _converter_odd(
        odd_anterior
    )
    atual = _converter_odd(
        odd_atual
    )

    if anterior is None or atual is None:
        return 0.0

    return (
        (atual - anterior)
        / anterior
    ) * 100.0

def classificar_forca(
    variacao_odd
):
    try:
        valor = abs(
            float(variacao_odd)
        )
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

def calcular_ipm(
    variacao_odd,
    minuto=0,
    gols=0,
    escanteios=0,
    finalizacoes=0,
    ataques_perigosos=0
):
    try:
        movimento = min(
            abs(float(variacao_odd))
            * 5.0,
            60.0
        )

        confirmacao_gols = min(
            max(int(gols), 0)
            * 5.0,
            10.0
        )

        confirmacao_escanteios = min(
            max(int(escanteios), 0)
            * 1.5,
            10.0
        )

        confirmacao_finalizacoes = min(
            max(int(finalizacoes), 0)
            * 0.5,
            10.0
        )

        confirmacao_ataques = min(
            max(int(ataques_perigosos), 0)
            * 0.2,
            10.0
        )

        ipm = min(
            max(
                movimento
                + confirmacao_gols
                + confirmacao_escanteios
                + confirmacao_finalizacoes
                + confirmacao_ataques,
                0.0
            ),
            100.0
        )

        return {
            "ipm": round(ipm, 2),
            "variacao_odd": round(
                float(variacao_odd),
                2
            ),
            "forca": classificar_forca(
                variacao_odd
            ),
            "movimento": round(
                movimento,
                2
            ),
            "confirmacao_gols": round(
                confirmacao_gols,
                2
            ),
            "confirmacao_escanteios": round(
                confirmacao_escanteios,
                2
            ),
            "confirmacao_finalizacoes": round(
                confirmacao_finalizacoes,
                2
            ),
            "confirmacao_ataques": round(
                confirmacao_ataques,
                2
            ),
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
    ataques_perigosos=0
):
    if chave_jogo is None:
        raise ValueError(
            "chave_jogo é obrigatória"
        )

    chave = str(
        chave_jogo
    )

    atual = _converter_odd(
        odd_atual
    )

    if atual is None:
        resultado = calcular_ipm(
            0.0,
            minuto,
            gols,
            escanteios,
            finalizacoes,
            ataques_perigosos
        )

        resultado.update({
            "odd_anterior": None,
            "odd_atual": odd_atual,
            "primeira_consulta": False,
            "erro": "odd_atual_invalida",
        })

        return resultado

    anterior = _odds_anteriores.get(
        chave
    )

    variacao = (
        0.0
        if anterior is None
        else calcular_variacao_odd(
            anterior,
            atual
        )
    )

    resultado = calcular_ipm(
        variacao,
        minuto,
        gols,
        escanteios,
        finalizacoes,
        ataques_perigosos
    )

    resultado.update({
        "odd_anterior": anterior,
        "odd_atual": atual,
        "primeira_consulta": (
            anterior is None
        ),
    })

    _odds_anteriores[chave] = atual

    return resultado

def limpar_memoria():
    _odds_anteriores.clear()

def formatar_radar(
    jogo,
    resultado,
    mercados=None
):
    if not isinstance(jogo, dict):
        jogo = {}

    if not isinstance(resultado, dict):
        resultado = {}

    casa = jogo.get(
        "home"
    ) or "Casa"

    fora = jogo.get(
        "away"
    ) or "Fora"

    primeira = resultado.get(
        "primeira_consulta",
        False
    )

    variacao = resultado.get(
        "variacao_odd",
        0.0
    )

    texto_variacao = (
        "AGUARDANDO COMPARACAO"
        if primeira
        else f"{variacao:+.2f}%"
    )

    linhas = [
        "",
        "=" * 60,
        "📡 IPM RADAR V4",
        "=" * 60,
        f"⚽ {casa} x {fora}",
        f"⏱️ Minuto: {resultado.get('minuto', 0)}",
        f"💰 Odd empate anterior: {resultado.get('odd_anterior')}",
        f"💰 Odd empate atual: {resultado.get('odd_atual')}",
        f"📈 Variação: {texto_variacao}",
        f"🔥 Força: {resultado.get('forca', 'ESTAVEL')}",
        f"🎯 IPM: {resultado.get('ipm', 0):.2f}/100",
        f"⚽ Gols: {resultado.get('gols', 0)}",
        f"🚩 Escanteios: {resultado.get('escanteios', 0)}",
        f"🥅 Finalizações: {resultado.get('finalizacoes', 0)}",
        f"⚡ Ataques perigosos: {resultado.get('ataques_perigosos', 0)}",
    ]

    if isinstance(mercados, dict):
        linhas.extend([
            f"📊 Mercados FT: {len(mercados.get('odds_ft', []))}",
            f"⏱️ Mercados HT: {len(mercados.get('odds_ht', []))}",
            f"🚩 Mercados escanteios: {len(mercados.get('odds_corners', []))}",
            f"🟨 Mercados cartões: {len(mercados.get('odds_cards', []))}",
        ])

    linhas.append(
        "=" * 60
    )

    return "\n".join(linhas)
