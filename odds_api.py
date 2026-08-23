# ============================================================
# ODDS API - IPM RADAR V3
# ============================================================

import os
import json
import urllib.request
import urllib.parse
import urllib.error


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_URL = "https://api.odds-api.io/v3"

BOOKMAKER = "Bet365"

MAX_EVENTOS_POR_CONSULTA = 10

TIMEOUT_REQUISICAO = 20


# ============================================================
# MEMÓRIA DAS ODDS
# ============================================================

# Primeira odd observada no evento
_ODD_INICIAL = {}

# Última odd observada no evento
_ODD_ANTERIOR = {}


# ============================================================
# API KEY
# ============================================================

def obter_api_key():

    api_key = os.getenv("ODDS_API_KEY")

    if not api_key:

        raise RuntimeError(
            "ODDS_API_KEY não configurada no Render."
        )

    return api_key.strip()


# ============================================================
# REQUISIÇÃO HTTP
# ============================================================

def fazer_requisicao(url):

    requisicao = urllib.request.Request(
        url,
        headers={
            "User-Agent": "IPM-Radar/3.0",
            "Accept": "application/json"
        }
    )

    try:

        with urllib.request.urlopen(
            requisicao,
            timeout=TIMEOUT_REQUISICAO
        ) as resposta:

            status = resposta.status

            conteudo = resposta.read().decode(
                "utf-8"
            )

        print(
            "HTTP STATUS ODDS API:",
            status
        )

        if not conteudo:

            print(
                "Resposta vazia da Odds API."
            )

            return []

        try:

            return json.loads(
                conteudo
            )

        except json.JSONDecodeError:

            print()
            print("=" * 60)
            print("RESPOSTA NÃO É JSON")
            print("=" * 60)

            print(
                conteudo[:2000]
            )

            print("=" * 60)

            return []

    except urllib.error.HTTPError as erro:

        detalhe = ""

        try:

            detalhe = erro.read().decode(
                "utf-8"
            )

        except Exception:

            pass

        print()
        print("=" * 60)
        print("ERRO HTTP ODDS API")
        print("=" * 60)

        print(
            "Código:",
            erro.code
        )

        print(
            "URL:",
            url
        )

        print(
            "Detalhes:",
            detalhe[:2000]
        )

        if erro.code == 401:

            print(
                "⚠️ API KEY inválida ou não autorizada."
            )

        elif erro.code == 403:

            print(
                "⚠️ Acesso negado pela Odds API."
            )

        elif erro.code == 429:

            print(
                "⚠️ LIMITE 429 DA ODDS API."
            )

        print("=" * 60)

        return []

    except urllib.error.URLError as erro:

        print()
        print("=" * 60)
        print("ERRO DE CONEXÃO ODDS API")
        print("=" * 60)

        print(
            type(erro).__name__
        )

        print(
            erro
        )

        print("=" * 60)

        return []

    except Exception as erro:

        print()
        print("=" * 60)
        print("ERRO NA REQUISIÇÃO ODDS API")
        print("=" * 60)

        print(
            type(erro).__name__
        )

        print(
            erro
        )

        print("=" * 60)

        return []


# ============================================================
# NORMALIZAR LISTA DE EVENTOS
# ============================================================

def _lista_eventos(resposta):

    if isinstance(
        resposta,
        list
    ):

        return resposta

    if not isinstance(
        resposta,
        dict
    ):

        return []

    for chave in (
        "events",
        "data",
        "results"
    ):

        valor = resposta.get(
            chave
        )

        if isinstance(
            valor,
            list
        ):

            return valor

    if resposta.get("id") is not None:

        return [
            resposta
        ]

    return []


# ============================================================
# JOGOS AO VIVO
# ============================================================

def buscar_jogos_ao_vivo():

    print()
    print("=" * 60)
    print("📡 CONSULTANDO JOGOS AO VIVO")
    print("=" * 60)

    try:

        api_key = obter_api_key()

    except Exception as erro:

        print(
            "ERRO API KEY:",
            erro
        )

        return []

    parametros = urllib.parse.urlencode({

        "apiKey": api_key,

        "sport": "football"

    })

    url = (
        BASE_URL
        + "/events/live?"
        + parametros
    )

    print(
        "Endpoint:",
        BASE_URL + "/events/live"
    )

    resposta = fazer_requisicao(
        url
    )

    print(
        "TIPO DA RESPOSTA LIVE:",
        type(resposta).__name__
    )

    eventos = _lista_eventos(
        resposta
    )

    print()
    print(
        "JOGOS AO VIVO ENCONTRADOS:",
        len(eventos)
    )

    if not eventos:

        print()
        print(
            "⚠️ NENHUM EVENTO AO VIVO FOI RETORNADO."
        )

        return []

    print()
    print("=" * 60)
    print("EVENTOS LIVE RECEBIDOS")
    print("=" * 60)

    for indice, evento in enumerate(
        eventos,
        start=1
    ):

        if not isinstance(
            evento,
            dict
        ):

            continue

        liga = evento.get(
            "league"
        )

        if isinstance(
            liga,
            dict
        ):

            liga = (
                liga.get("name")
                or liga.get("slug")
            )

        print()
        print(
            f"EVENTO {indice}"
        )

        print(
            "ID:",
            evento.get("id")
        )

        print(
            "CASA:",
            evento.get("home")
        )

        print(
            "FORA:",
            evento.get("away")
        )

        print(
            "STATUS:",
            evento.get("status")
        )

        print(
            "DATA:",
            evento.get("date")
        )

        print(
            "LIGA:",
            liga
        )

    print()
    print("=" * 60)

    return eventos


# ============================================================
# ODDS DOS EVENTOS
# ============================================================

def buscar_odds_multiplos(eventos):

    print()
    print("=" * 60)
    print("📊 CONSULTANDO ODDS")
    print("=" * 60)

    if not eventos:

        return []

    try:

        api_key = obter_api_key()

    except Exception as erro:

        print(
            "ERRO API KEY:",
            erro
        )

        return []

    ids = []

    for evento in eventos:

        if not isinstance(
            evento,
            dict
        ):

            continue

        event_id = evento.get(
            "id"
        )

        if event_id is not None:

            ids.append(
                str(event_id)
            )

    ids = list(
        dict.fromkeys(ids)
    )

    ids = ids[
        :MAX_EVENTOS_POR_CONSULTA
    ]

    if not ids:

        print(
            "⚠️ Nenhum ID de evento disponível."
        )

        return []

    parametros = urllib.parse.urlencode({

        "apiKey": api_key,

        "eventIds": ",".join(ids),

        "bookmakers": BOOKMAKER

    })

    url = (
        BASE_URL
        + "/odds/multi?"
        + parametros
    )

    print(
        "Eventos enviados:",
        len(ids)
    )

    print(
        "Bookmaker:",
        BOOKMAKER
    )

    print(
        "Endpoint:",
        BASE_URL + "/odds/multi"
    )

    resposta = fazer_requisicao(
        url
    )

    eventos_odds = _lista_eventos(
        resposta
    )

    if (
        not eventos_odds
        and isinstance(
            resposta,
            dict
        )
    ):

        valores = []

        for valor in resposta.values():

            if (
                isinstance(
                    valor,
                    dict
                )
                and valor.get("id") is not None
            ):

                valores.append(
                    valor
                )

        eventos_odds = valores

    print(
        "EVENTOS COM ODDS RECEBIDOS:",
        len(eventos_odds)
    )

    if not eventos_odds:

        print(
            "⚠️ Nenhum odds válido retornado."
        )

        return []

    return eventos_odds


# ============================================================
# CONVERSÃO NUMÉRICA
# ============================================================

def _numero(
    valor,
    padrao=0.0
):

    try:

        if valor is None or valor == "":

            return padrao

        return float(
            valor
        )

    except (
        TypeError,
        ValueError
    ):

        return padrao


def _inteiro(
    valor,
    padrao=0
):

    try:

        if valor is None or valor == "":

            return padrao

        return int(
            float(valor)
        )

    except (
        TypeError,
        ValueError
    ):

        return padrao


# ============================================================
# PRIMEIRA LINHA DE ODDS
# ============================================================

def _primeiro_odds(mercado):

    if not isinstance(
        mercado,
        dict
    ):

        return {}

    valores = mercado.get(
        "odds"
    )

    if isinstance(
        valores,
        list
    ):

        if valores:

            if isinstance(
                valores[0],
                dict
            ):

                return valores[0]

    if isinstance(
        valores,
        dict
    ):

        return valores

    return {}


# ============================================================
# MERCADOS BET365
# ============================================================

def _mercados_bet365(evento_odds):

    if not isinstance(
        evento_odds,
        dict
    ):

        return []

    bookmakers = evento_odds.get(
        "bookmakers",
        {}
    )

    if not isinstance(
        bookmakers,
        dict
    ):

        return []

    mercados = bookmakers.get(
        BOOKMAKER,
        []
    )

    if isinstance(
        mercados,
        list
    ):

        return mercados

    return []


# ============================================================
# LOCALIZAR MERCADO
# ============================================================

def _encontrar_mercado(
    mercados,
    nomes
):

    nomes = {
        str(nome)
        .strip()
        .lower()
        for nome in nomes
    }

    for mercado in mercados:

        if not isinstance(
            mercado,
            dict
        ):

            continue

        nome = str(
            mercado.get(
                "name",
                ""
            )
        ).strip().lower()

        if nome in nomes:

            return mercado

    return None


# ============================================================
# EVENTO ODDS POR ID
# ============================================================

def _evento_odds_por_id(
    odds,
    event_id
):

    if event_id is None:

        return None

    alvo = str(
        event_id
    )

    if isinstance(
        odds,
        list
    ):

        for item in odds:

            if (
                isinstance(
                    item,
                    dict
                )
                and str(
                    item.get("id")
                ) == alvo
            ):

                return item

    if isinstance(
        odds,
        dict
    ):

        if str(
            odds.get("id")
        ) == alvo:

            return odds

        for chave, valor in odds.items():

            if (
                str(chave) == alvo
                and isinstance(
                    valor,
                    dict
                )
            ):

                return valor

    return None


# ============================================================
# EXTRAIR PLACAR
# ============================================================

def _extrair_placar(jogo):

    if not isinstance(jogo, dict):
        return 0, 0

    # Formato oficial Odds-API.io
    scores = jogo.get("scores")

    if isinstance(scores, dict):

        casa = scores.get("home", 0)
        fora = scores.get("away", 0)

        return (
            _inteiro(casa),
            _inteiro(fora)
        )

    # Compatibilidade com outros formatos
    score = jogo.get("score")

    if isinstance(score, dict):

        casa = score.get("home", 0)
        fora = score.get("away", 0)

        return (
            _inteiro(casa),
            _inteiro(fora)
        )

    if isinstance(score, list) and len(score) >= 2:

        return (
            _inteiro(score[0]),
            _inteiro(score[1])
        )

    return 0, 0


# ============================================================
# EXTRAIR MINUTO
# ============================================================

def _extrair_minuto(jogo):

    if not isinstance(jogo, dict):
        return 0

    candidatos = (

        jogo.get("minute"),

        jogo.get("elapsed"),

        jogo.get("timer"),

        jogo.get("clock")

    )

    for valor in candidatos:

        if isinstance(valor, dict):

            minuto = valor.get("minute")

            if minuto is None:
                minuto = valor.get("elapsed")

            valor = minuto

        if isinstance(valor, str):

            valor = (
                valor
                .replace("'", "")
                .replace("min", "")
                .strip()
            )

        minuto = _inteiro(
            valor,
            -1
        )

        if minuto >= 0:
            return minuto

    return 0


# ============================================================
# EXTRAIR ESTATÍSTICAS
# ============================================================

def _extrair_estatisticas(jogo):

    fontes = []

    for chave in (
        "statistics",
        "stats",
        "matchStatistics"
    ):

        valor = jogo.get(
            chave
        )

        if isinstance(
            valor,
            dict
        ):

            fontes.append(
                valor
            )

    for fonte in fontes:

        escanteios = fonte.get(
            "corners"
        )

        finalizacoes = fonte.get(
            "shots"
        )

        ataques = fonte.get(
            "dangerousAttacks"
        )

        if (
            escanteios is not None
            or finalizacoes is not None
            or ataques is not None
        ):

            return (

                _inteiro(
                    escanteios
                ),

                _inteiro(
                    finalizacoes
                ),

                _inteiro(
                    ataques
                )

            )

    return 0, 0, 0


# ============================================================
# EXTRAIR MERCADOS
# ============================================================

def extrair_mercados(
    jogo,
    odds
):

    if not isinstance(jogo, dict):
        return {}

    event_id = jogo.get("id")

    # ========================================================
    # LOCALIZAR ODDS DO EVENTO
    # ========================================================

    evento_odds = _evento_odds_por_id(
        odds,
        event_id
    )

    if evento_odds is None:

        evento_odds = jogo

    # ========================================================
    # BOOKMAKER
    # ========================================================

    mercados = _mercados_bet365(
        evento_odds
    )

    print()
    print("🔎 DEBUG ODDS")
    print(
        "Evento:",
        event_id
    )

    print(
        "Times:",
        jogo.get("home"),
        "x",
        jogo.get("away")
    )

    print(
        "Mercados encontrados:",
        len(mercados)
    )

    # ========================================================
    # PROCURAR ML
    # ========================================================

    mercado_ml = _encontrar_mercado(

        mercados,

        (
            "ML",
            "Moneyline",
            "1X2"
        )

    )

    odd_atual = 0.0

    if mercado_ml:

        print(
            "✅ Mercado ML encontrado"
        )

        linha = _primeiro_odds(
            mercado_ml
        )

        print(
            "Linha ML:",
            linha
        )

        # Odd do empate
        odd_atual = _numero(
            linha.get("draw")
        )

    else:

        print(
            "⚠️ Mercado ML NÃO encontrado"
        )

        # Mostrar os mercados existentes
        for mercado in mercados:

            if isinstance(
                mercado,
                dict
            ):

                print(
                    "Mercado:",
                    mercado.get("name")
                )

    # ========================================================
    # PRIMEIRA ODD
    # ========================================================

    if (
        event_id is not None
        and odd_atual > 0
    ):

        if event_id not in _ODD_INICIAL:

            _ODD_INICIAL[
                event_id
            ] = odd_atual

            print(
                "🟢 PRIMEIRA ODD REGISTRADA:",
                odd_atual
            )

    odd_inicial = _ODD_INICIAL.get(

        event_id,

        odd_atual

    )

    # ========================================================
    # MINUTO
    # ========================================================

    minuto = _extrair_minuto(
        jogo
    )

    # ========================================================
    # PLACAR
    # ========================================================

    casa,
    fora = _extrair_placar(
        jogo
    )

    gols = casa + fora

    # ========================================================
    # ESTATÍSTICAS
    # ========================================================

    (
        escanteios,
        finalizacoes,
        ataques_perigosos
    ) = _extrair_estatisticas(
        jogo
    )

    # ========================================================
    # RESULTADO
    # ========================================================

    resultado = {

        "odd_inicial": odd_inicial,

        "odd_atual": odd_atual,

        "minuto": minuto,

        "gols": gols,

        "escanteios": escanteios,

        "finalizacoes": finalizacoes,

        "ataques_perigosos": ataques_perigosos

    }

    # ========================================================
    # LOG
    # ========================================================

    print()
    print(
        "📊",
        jogo.get("home"),
        "x",
        jogo.get("away")
    )

    print(
        "   ID:",
        event_id
    )

    print(
        "   Minuto:",
        minuto
    )

    print(
        "   Placar:",
        casa,
        "x",
        fora
    )

    print(
        "   Gols:",
        gols
    )

    print(
        "   Odd empate:",
        f"{odd_inicial:.2f}",
        "->",
        f"{odd_atual:.2f}"
    )

    print(
        "   Variação será calculada pelo motor IPM."
    )

    print(
        "   Escanteios:",
        escanteios
    )

    print(
        "   Finalizações:",
        finalizacoes
    )

    print(
        "   Ataques perigosos:",
        ataques_perigosos
    )

    print(
        "------------------------------------------------------------"
    )

    return resultado

    # ========================================================
    # MERCADO ML / MONEYLINE / 1X2
    # ========================================================

    mercado_ml = _encontrar_mercado(

        mercados,

        (
            "ML",
            "Moneyline",
            "1X2"
        )

    )

    odd_atual = 0.0

    if mercado_ml:

        linha = _primeiro_odds(
            mercado_ml
        )

        # Odd do empate
        odd_atual = _numero(
            linha.get(
                "draw"
            )
        )

    # ========================================================
    # MEMÓRIA DAS ODDS
    # ========================================================

    odd_anterior = 0.0

    if event_id is not None:

        odd_anterior = _ODD_ANTERIOR.get(
            event_id,
            0.0
        )

    # Primeira odd válida
    if (
        event_id is not None
        and odd_atual > 0
    ):

        if event_id not in _ODD_INICIAL:

            _ODD_INICIAL[
                event_id
            ] = odd_atual

    odd_inicial = _ODD_INICIAL.get(

        event_id,

        odd_atual

    )

    # ========================================================
    # VARIAÇÕES
    # ========================================================

    variacao_desde_inicio = 0.0

    variacao_recente = 0.0

    if odd_inicial > 0:

        variacao_desde_inicio = (
            (
                odd_atual
                - odd_inicial
            )
            / odd_inicial
        ) * 100.0

    if odd_anterior > 0:

        variacao_recente = (
            (
                odd_atual
                - odd_anterior
            )
            / odd_anterior
        ) * 100.0

    # ========================================================
    # ATUALIZAR MEMÓRIA
    # ========================================================

    if (
        event_id is not None
        and odd_atual > 0
    ):

        _ODD_ANTERIOR[
            event_id
        ] = odd_atual

    # ========================================================
    # MINUTO
    # ========================================================

    minuto = _extrair_minuto(
        jogo
    )

    # ========================================================
    # PLACAR
    # ========================================================

    casa, fora = _extrair_placar(
        jogo
    )

    gols = casa + fora

    # ========================================================
    # ESTATÍSTICAS
    # ========================================================

    (
        escanteios,
        finalizacoes,
        ataques_perigosos
    ) = _extrair_estatisticas(
        jogo
    )

    # ========================================================
    # RESULT
