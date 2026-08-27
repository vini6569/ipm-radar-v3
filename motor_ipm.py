# ============================================================
# MOTOR IPM - IPM RADAR V4.1
# ============================================================

_memoria = {}
_odds_anteriores = {}


def _num(v, default=0.0):
    try:
        if v in (None, ""):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _converter_odd(valor):
    numero = _num(valor, 0.0)
    return numero if numero > 0 else None


def calcular_variacao_odd(anterior, atual):
    anterior = _num(anterior)
    atual = _num(atual)
    if anterior <= 0 or atual <= 0:
        return 0.0
    return ((atual - anterior) / anterior) * 100.0


def classificar_forca(v):
    v = abs(_num(v))
    if v >= 10:
        return "MUITO FORTE"
    if v >= 5:
        return "FORTE"
    if v >= 2:
        return "MODERADO"
    if v >= 0.5:
        return "FRACO"
    return "ESTAVEL"


def classificar_direcao(v):
    v = _num(v)
    if v < -0.05:
        return "QUEDA"
    if v > 0.05:
        return "ALTA"
    return "ESTAVEL"


def analisar_movimento(evento_id, periodo, mercado, linha, selecao, odd_atual):
    atual = _num(odd_atual)
    chave = (
        str(evento_id), str(periodo), str(mercado),
        str(linha), str(selecao)
    )
    anterior = _memoria.get(chave)

    if atual <= 0:
        return {
            "odd_anterior": anterior,
            "odd_atual": atual,
            "variacao": 0.0,
            "primeira_consulta": False,
            "direcao": "ESTAVEL",
            "forca": "ESTAVEL",
        }

    if anterior is None:
        _memoria[chave] = atual
        return {
            "odd_anterior": None,
            "odd_atual": atual,
            "variacao": 0.0,
            "primeira_consulta": True,
            "direcao": "REFERENCIA",
            "forca": "ESTAVEL",
        }

    variacao = calcular_variacao_odd(anterior, atual)
    _memoria[chave] = atual

    return {
        "odd_anterior": anterior,
        "odd_atual": atual,
        "variacao": round(variacao, 4),
        "primeira_consulta": False,
        "direcao": classificar_direcao(variacao),
        "forca": classificar_forca(variacao),
    }


def calcular_ipm(
    variacao_odd=0,
    minuto=0,
    gols=0,
    escanteios=0,
    cartoes=0,
    finalizacoes=0,
    ataques_perigosos=0,
    **kwargs
):
    movimento = min(abs(_num(variacao_odd)) * 5.0, 60.0)
    gols_n = min(max(int(_num(gols)), 0) * 5.0, 10.0)
    esc = min(max(int(_num(escanteios)), 0) * 1.5, 10.0)
    cart = min(max(int(_num(cartoes)), 0), 10.0)
    fin = min(max(int(_num(finalizacoes)), 0) * 0.5, 10.0)
    ata = min(max(int(_num(ataques_perigosos)), 0) * 0.2, 10.0)

    ipm = min(100.0, movimento + gols_n + esc + cart + fin + ata)

    return {
        "ipm": round(ipm, 2),
        "variacao_odd": round(_num(variacao_odd), 4),
        "forca": classificar_forca(variacao_odd),
        "direcao": classificar_direcao(variacao_odd),
        "movimento": round(movimento, 2),
        "confirmacao_gols": round(gols_n, 2),
        "confirmacao_escanteios": round(esc, 2),
        "confirmacao_cartoes": round(cart, 2),
        "confirmacao_finalizacoes": round(fin, 2),
        "confirmacao_ataques": round(ata, 2),
        "minuto": minuto,
        "gols": gols,
        "escanteios": escanteios,
        "cartoes": cartoes,
        "finalizacoes": finalizacoes,
        "ataques_perigosos": ataques_perigosos,
    }


def analisar_ipm_com_memoria(
    chave_jogo,
    odd_atual,
    minuto=0,
    gols=0,
    escanteios=0,
    cartoes=0,
    finalizacoes=0,
    ataques_perigosos=0,
    **kwargs
):
    """Analisa a variação da odd usando a memória entre ciclos.

    Esta função mantém compatibilidade com main.py do Radar V4.1.
    Na primeira consulta, a odd vira referência e a variação é 0%.
    """
    if chave_jogo is None:
        raise ValueError("chave_jogo é obrigatória")

    chave = str(chave_jogo)
    atual = _converter_odd(odd_atual)

    if atual is None:
        resultado = calcular_ipm(
            0.0, minuto, gols, escanteios, cartoes,
            finalizacoes, ataques_perigosos
        )
        resultado.update({
            "odd_anterior": None,
            "odd_atual": odd_atual,
            "primeira_consulta": False,
            "erro": "odd_atual_invalida",
        })
        return resultado

    anterior = _odds_anteriores.get(chave)
    variacao = 0.0 if anterior is None else calcular_variacao_odd(anterior, atual)

    resultado = calcular_ipm(
        variacao,
        minuto,
        gols,
        escanteios,
        cartoes,
        finalizacoes,
        ataques_perigosos,
    )

    resultado.update({
        "odd_anterior": anterior,
        "odd_atual": atual,
        "primeira_consulta": anterior is None,
    })

    _odds_anteriores[chave] = atual
    return resultado


def limpar_memoria():
    _memoria.clear()
    _odds_anteriores.clear()


def formatar_radar(jogo, resultado, mercados=None):
    if not isinstance(jogo, dict):
        jogo = {}
    if not isinstance(resultado, dict):
        resultado = {}

    casa = jogo.get("home") or "Casa"
    fora = jogo.get("away") or "Fora"
    primeira = resultado.get("primeira_consulta", False)
    variacao = resultado.get("variacao_odd", 0.0)
    texto_variacao = "AGUARDANDO COMPARACAO" if primeira else f"{variacao:+.2f}%"

    linhas = [
        "",
        "=" * 60,
        "📡 IPM RADAR V4.1",
        "=" * 60,
        f"⚽ {casa} x {fora}",
        f"⏱️ Minuto: {resultado.get('minuto', 0)}",
        f"💰 Odd empate anterior: {resultado.get('odd_anterior')}",
        f"💰 Odd empate atual: {resultado.get('odd_atual')}",
        f"📈 Variação: {texto_variacao}",
        f"🔥 Força: {resultado.get('forca', 'ESTAVEL')}",
        f"🧭 Direção: {resultado.get('direcao', 'ESTAVEL')}",
        f"🎯 IPM: {resultado.get('ipm', 0):.2f}/100",
        f"⚽ Gols: {resultado.get('gols', 0)}",
        f"🚩 Escanteios: {resultado.get('escanteios', 0)}",
        f"🟨 Cartões: {resultado.get('cartoes', 0)}",
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

    linhas.append("=" * 60)
    return "\n".join(linhas)
    
