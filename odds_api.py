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

    for indice, evento in enumerate(eventos, 1):

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

    # Remove IDs duplicados
    ids = list(
        dict.fromkeys(ids)
    )

    # Limita quantidade
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

    # Algumas respostas podem vir como:
    #
    # {
    #     "123456": {...},
    #     "123457": {...}
    # }

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
    ).strip()

    # --------------------------------------------------------
    # LISTA
    # --------------------------------------------------------

    if isinstance(
        odds,
        list
    ):

        for item in odds:

            if not isinstance(
                item,
                dict
            ):

                continue

            item_id = item.get(
                "id"
            )

            if item_id is not None:

                if (
                    str(item_id).strip()
                    == alvo
                ):

                    return item

    # --------------------------------------------------------
    # DICIONÁRIO
    # --------------------------------------------------------

    if isinstance(
        odds,
        dict
    ):

        # O próprio objeto é o evento

        if odds.get("id") is not None:

            if (
                str(
                    odds.get("id")
                ).strip()
                == alvo
            ):

                return odds

        # Evento indexado pelo ID

        for chave, valor in odds.items():

            if (
                str(chave).strip()
                == alvo
            ):

                if isinstance(
                    valor,
                    dict
                ):

                    return valor

    return None


# ============================================================
# EXTRAIR PLACAR
# ============================================================

def _extrair_placar(jogo):

    candidatos = [

        jogo.get("score"),

        jogo.get("scores"),

        jogo.get("result")

    ]

    for valor in candidatos:

        if isinstance(
            valor,
            dict
        ):

            casa = valor.get(
                "home"
            )

            if casa is None:

                casa = valor.get(
                    "homeScore"
                )

            fora = valor.get(
                "away"
            )

            if fora is None:

                fora = valor.get(
                    "awayScore"
                )

            if (
                casa is not None
                or fora is not None
            ):

                return (
                    _inteiro(casa),
                    _inteiro(fora)
                )

        if (
            isinstance(
                valor,
                list
            )
            and len(valor) >= 2
        ):

            return (
                _inteiro(valor[0]),
                _inteiro(valor[1])
            )

    if (
        "homeScore" in jogo
        or "awayScore" in jogo
    ):

        return (

            _inteiro(
                jogo.get("homeScore")
            ),

            _inteiro(
                jogo.get("awayScore")
            )

        )

    return 0, 0


# ============================================================
# EXTRAIR MINUTO
# ============================================================

def _extrair_minuto(jogo):

    candidatos = (

        jogo.get("minute"),

        jogo.get("elapsed"),

        jogo.get("timer"),

        jogo.get("clock")

    )

    for valor in candidatos:

        if isinstance(
            valor,
            dict
        ):

            minuto = valor.get(
                "minute"
            )

            if minuto is None:

                minuto = valor.get(
                    "elapsed"
                )

            valor = minuto

        if isinstance(
            valor,
            str
        ):

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

    # Não inventar estatísticas.

    return 0, 0, 0


# ============================================================
# EXTRAIR MERCADOS
# ============================================================

def extrair_mercados(
    jogo,
    odds
):

    if not isinstance(
        jogo,
        dict
    ):
        return {}

    event_id = jogo.get(
        "id"
    )

    evento_odds = _evento_odds_por_id(
        odds,
        event_id
    )

    # Caso o próprio evento já contenha bookmakers
    if evento_odds is None:
        evento_odds = jogo

    mercados = _mercados_bet365(
        evento_odds
    )

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

        print()
        print(
            "🔎 LINHA DE ODDS:"
        )

        print(linha)

        if isinstance(
            linha,
            dict
        ):

            # Tentativa 1 - draw
            odd_atual = _numero(
                linha.get("draw")
            )

            # Tentativa 2 - X
            if odd_atual <= 0:
                odd_atual = _numero(
                    linha.get("X")
                )

            # Tentativa 3 - tie
            if odd_atual <= 0:
                odd_atual = _numero(
                    linha.get("tie")
                )

            # Tentativa 4 - Draw
            if odd_atual <= 0:
                odd_atual = _numero(
                    linha.get("Draw")
                )

            # Tentativa 5 - drawOdd
            if odd_atual <= 0:
                odd_atual = _numero(
                    linha.get("drawOdd")
                )

            # Tentativa 6 - odd_draw
            if odd_atual <= 0:
                odd_atual = _numero(
                    linha.get("odd_draw")
                )

        print()
        print(
            "💰 ODD EMPATE EXTRAÍDA:",
            odd_atual
        )

    else:

        print()
        print(
            "⚠️ MERCADO ML / 1X2 NÃO ENCONTRADO"
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

    # ========================================================
    # PRIMEIRA ODD VÁLIDA
    # ========================================================

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
    # ATUALIZA MEMÓRIA
    # ========================================================

    if (
        event_id is not None
        and odd_atual > 0
    ):

        _ODD_ANTERIOR[
            event_id
        ] = odd_atual

    # ========================================================
    # RESULTADO
    # ========================================================

    return {
        "odd_empate": odd_atual,
        "odd_inicial": odd_inicial,
        "odd_anterior": odd_anterior,
        "variacao_desde_inicio": variacao_desde_inicio,
        "variacao_recente": variacao_recente
    }
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

    evento_odds = _evento_odds_por_id(
        odds,
        event_id
    )

    # Caso o próprio evento já contenha bookmakers
    if evento_odds is None:
        evento_odds = jogo

    mercados = _mercados_bet365(
        evento_odds
    )

    # ========================================================
    # FUNÇÃO AUXILIAR
    # ========================================================

    def pegar_linha(nomes):

        mercado = _encontrar_mercado(
            mercados,
            nomes
        )

        if mercado is None:
            return None

        linha = _primeiro_odds(
            mercado
        )

        if not isinstance(linha, dict):
            return None

        return linha

    # ========================================================
    # INICIALIZA RESULTADO
    # ========================================================

    resultado = {

        "event_id": event_id,

        # ----------------------------------------------------
        # 1X2
        # ----------------------------------------------------

        "odd_home": 0.0,
        "odd_draw": 0.0,
        "odd_away": 0.0,

        # Mantém compatibilidade com o IPM atual
        "odd_atual": 0.0,
        "odd_anterior": 0.0,
        "odd_inicial": 0.0,

        "variacao_desde_inicio": 0.0,
        "variacao_recente": 0.0,

        # ----------------------------------------------------
        # OVER / UNDER
        # ----------------------------------------------------

        "over_linha": 0.0,
        "odd_over": 0.0,

        "under_linha": 0.0,
        "odd_under": 0.0,

        # ----------------------------------------------------
        # AMBAS MARCAM
        # ----------------------------------------------------

        "odd_btts_sim": 0.0,
        "odd_btts_nao": 0.0,

        # ----------------------------------------------------
        # ASIÁTICO / SPREAD
        # ----------------------------------------------------

        "handicap_linha": 0.0,
        "odd_handicap_home": 0.0,
        "odd_handicap_away": 0.0,

        # ----------------------------------------------------
        # DOUBLE CHANCE
        # ----------------------------------------------------

        "odd_1x": 0.0,
        "odd_12": 0.0,
        "odd_x2": 0.0,

        # ----------------------------------------------------
        # DNB
        # ----------------------------------------------------

        "odd_dnb_home": 0.0,
        "odd_dnb_away": 0.0,

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        "mercados_encontrados": [],

        "mercados_disponiveis": []

    }

    # ========================================================
    # 1️⃣ MERCADO ML / 1X2
    # ========================================================

    mercado_ml = _encontrar_mercado(
        mercados,
        (
            "ML",
            "Moneyline",
            "1X2"
        )
    )

    if mercado_ml:

        linha = _primeiro_odds(
            mercado_ml
        )

        if isinstance(linha, dict):

            resultado["odd_home"] = _numero(
                linha.get("home")
            )

            resultado["odd_draw"] = _numero(
                linha.get("draw")
            )

            resultado["odd_away"] = _numero(
                linha.get("away")
            )

            # A odd principal do IPM continua sendo
            # a odd do EMPATE.

            resultado["odd_atual"] = (
                resultado["odd_draw"]
            )

            resultado[
                "mercados_encontrados"
            ].append("ML")

    # ========================================================
    # 2️⃣ OVER / UNDER
    # ========================================================

    mercado_totals = _encontrar_mercado(
        mercados,
        (
            "Totals",
            "Total",
            "Over/Under",
            "Over Under",
            "O/U"
        )
    )

    if mercado_totals:

        linha = _primeiro_odds(
            mercado_totals
        )

        if isinstance(linha, dict):

            resultado["over_linha"] = _numero(
                linha.get("hdp"),
                0.0
            )

            resultado["under_linha"] = (
                resultado["over_linha"]
            )

            resultado["odd_over"] = _numero(
                linha.get("over")
            )

            resultado["odd_under"] = _numero(
                linha.get("under")
            )

            resultado[
                "mercados_encontrados"
            ].append("TOTALS")

    # ========================================================
    # 3️⃣ AMBAS MARCAM
    # ========================================================

    mercado_btts = _encontrar_mercado(
        mercados,
        (
            "Both Teams To Score",
            "Both Teams to Score",
            "BTTS",
            "Both Teams Score"
        )
    )

    if mercado_btts:

        linha = _primeiro_odds(
            mercado_btts
        )

        if isinstance(linha, dict):

            resultado["odd_btts_sim"] = _numero(
                linha.get("yes")
            )

            if resultado["odd_btts_sim"] <= 0:

                resultado["odd_btts_sim"] = _numero(
                    linha.get("Yes")
                )

            resultado["odd_btts_nao"] = _numero(
                linha.get("no")
            )

            if resultado["odd_btts_nao"] <= 0:

                resultado["odd_btts_nao"] = _numero(
                    linha.get("No")
                )

            resultado[
                "mercados_encontrados"
            ].append("BTTS")

    # ========================================================
    # 4️⃣ ASIAN HANDICAP / SPREAD
    # ========================================================

    mercado_handicap = _encontrar_mercado(
        mercados,
        (
            "Spread",
            "Asian Handicap",
            "Handicap",
            "Asian Handicap 3-Way"
        )
    )

    if mercado_handicap:

        linha = _primeiro_odds(
            mercado_handicap
        )

        if isinstance(linha, dict):

            resultado[
                "handicap_linha"
            ] = _numero(
                linha.get("hdp")
            )

            resultado[
                "odd_handicap_home"
            ] = _numero(
                linha.get("home")
            )

            resultado[
                "odd_handicap_away"
            ] = _numero(
                linha.get("away")
            

            resultado[
                "mercados_encontrados"
            ].append("HANDICAP")

    # ========================================================
    # VARIAÇÃO DESDE O INÍCIO
    # ========================================================

    if odd_inicial > 0:

        resultado["variacao_desde_inicio"] = (
            (
                odd_atual
                - odd_inicial
            )
            / odd_inicial
        ) * 100.0

    # ========================================================
    # VARIAÇÃO ENTRE CONSULTAS
    # ========================================================

    if odd_anterior > 0:

        resultado["variacao_recente"] = (
            (
                odd_atual
                - odd_anterior
            )
            / odd_anterior
        ) * 100.0

    # ========================================================
    # SALVAR MEMÓRIA
    # ========================================================

    if (
        event_id is not None
        and odd_atual > 0
    ):

        _ODD_ANTERIOR[event_id] = odd_atual

    # ========================================================
    # VALORES FINAIS
    # ========================================================

    resultado["odd_anterior"] = odd_anterior

    resultado["odd_inicial"] = odd_inicial

    # ========================================================
    # LOG FINAL
    # ========================================================

    print()
    print("=" * 60)
    print("📊 MERCADOS EXTRAÍDOS")
    print("=" * 60)

    print("EVENT ID:", event_id)

    print(
        "1X2:",
        resultado["odd_home"],
        "|",
        resultado["odd_draw"],
        "|",
        resultado["odd_away"]
    )

    print(
        "OVER:",
        resultado["over_linha"],
        "|",
        resultado["odd_over"]
    )

    print(
        "UNDER:",
        resultado["under_linha"],
        "|",
        resultado["odd_under"]
    )

    print(
        "BTTS:",
        resultado["odd_btts_sim"],
        "|",
        resultado["odd_btts_nao"]
    )

    print(
        "HANDICAP:",
        resultado["handicap_linha"],
        "|",
        resultado["odd_handicap_home"],
        "|",
        resultado["odd_handicap_away"]
    )

    print(
        "DOUBLE CHANCE:",
        resultado["odd_1x"],
        "|",
        resultado["odd_12"],
        "|",
        resultado["odd_x2"]
    )

    print(
        "DNB:",
        resultado["odd_dnb_home"],
        "|",
        resultado["odd_dnb_away"]
    )

    print(
        "MERCADOS RECEBIDOS:",
        resultado["mercados_disponiveis"]
    )

    print(
        "VARIAÇÃO EMPATE:",
        f"{resultado['variacao_recente']:.2f}%"
    )

    print("=" * 60)

    return resultado

    # ========================================================
    # FUNÇÃO AUXILIAR
    # ========================================================

    def pegar_linha(nomes):

        mercado = _encontrar_mercado(
            mercados,
            nomes
        )

        if mercado is None:
            return None

        linha = _primeiro_odds(
            mercado
        )

        if not isinstance(linha, dict):
            return None

        return linha

    # ========================================================
    # INICIALIZA RESULTADO
    # ========================================================

    resultado = {

        "event_id": event_id,

        # ----------------------------------------------------
        # 1X2
        # ----------------------------------------------------

        "odd_home": 0.0,
        "odd_draw": 0.0,
        "odd_away": 0.0,

        # Mantém compatibilidade com o IPM atual
        "odd_atual": 0.0,
        "odd_anterior": 0.0,
        "odd_inicial": 0.0,

        "variacao_desde_inicio": 0.0,
        "variacao_recente": 0.0,

        # ----------------------------------------------------
        # OVER / UNDER
        # ----------------------------------------------------

        "over_linha": 0.0,
        "odd_over": 0.0,

        "under_linha": 0.0,
        "odd_under": 0.0,

        # ----------------------------------------------------
        # AMBAS MARCAM
        # ----------------------------------------------------

        "odd_btts_sim": 0.0,
        "odd_btts_nao": 0.0,

        # ----------------------------------------------------
        # ASIÁTICO / SPREAD
        # ----------------------------------------------------

        "handicap_linha": 0.0,
        "odd_handicap_home": 0.0,
        "odd_handicap_away": 0.0,

        # ----------------------------------------------------
        # DOUBLE CHANCE
        # ----------------------------------------------------

        "odd_1x": 0.0,
        "odd_12": 0.0,
        "odd_x2": 0.0,

        # ----------------------------------------------------
        # DNB
        # ----------------------------------------------------

        "odd_dnb_home": 0.0,
        "odd_dnb_away": 0.0,

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        "mercados_encontrados": [],

        "mercados_disponiveis": []

    }

    # ========================================================
    # 1️⃣ MERCADO ML / 1X2
    # ========================================================

    mercado_ml = _encontrar_mercado(
        mercados,
        (
            "ML",
            "Moneyline",
            "1X2"
        )
    )

    if mercado_ml:

        linha = _primeiro_odds(
            mercado_ml
        )

        if isinstance(linha, dict):

            resultado["odd_home"] = _numero(
                linha.get("home")
            )

            resultado["odd_draw"] = _numero(
                linha.get("draw")
            )

            resultado["odd_away"] = _numero(
                linha.get("away")
            )

            # A odd principal do IPM continua sendo
            # a odd do EMPATE.

            resultado["odd_atual"] = (
                resultado["odd_draw"]
            )

            resultado[
                "mercados_encontrados"
            ].append("ML")

    # ========================================================
    # 2️⃣ OVER / UNDER
    # ========================================================

    mercado_totals = _encontrar_mercado(
        mercados,
        (
            "Totals",
            "Total",
            "Over/Under",
            "Over Under",
            "O/U"
        )
    )

    if mercado_totals:

        linha = _primeiro_odds(
            mercado_totals
        )

        if isinstance(linha, dict):

            resultado["over_linha"] = _numero(
                linha.get("hdp"),
                0.0
            )

            resultado["under_linha"] = (
                resultado["over_linha"]
            )

            resultado["odd_over"] = _numero(
                linha.get("over")
            )

            resultado["odd_under"] = _numero(
                linha.get("under")
            )

            resultado[
                "mercados_encontrados"
            ].append("TOTALS")

    # ========================================================
    # 3️⃣ AMBAS MARCAM
    # ========================================================

    mercado_btts = _encontrar_mercado(
        mercados,
        (
            "Both Teams To Score",
            "Both Teams to Score",
            "BTTS",
            "Both Teams Score"
        )
    )

    if mercado_btts:

        linha = _primeiro_odds(
            mercado_btts
        )

        if isinstance(linha, dict):

            resultado["odd_btts_sim"] = _numero(
                linha.get("yes")
            )

            if resultado["odd_btts_sim"] <= 0:

                resultado["odd_btts_sim"] = _numero(
                    linha.get("Yes")
                )

            resultado["odd_btts_nao"] = _numero(
                linha.get("no")
            )

            if resultado["odd_btts_nao"] <= 0:

                resultado["odd_btts_nao"] = _numero(
                    linha.get("No")
                )

            resultado[
                "mercados_encontrados"
            ].append("BTTS")

    # ========================================================
    # 4️⃣ ASIAN HANDICAP / SPREAD
    # ========================================================

    mercado_handicap = _encontrar_mercado(
        mercados,
        (
            "Spread",
            "Asian Handicap",
            "Handicap",
            "Asian Handicap 3-Way"
        )
    )

    if mercado_handicap:

        linha = _primeiro_odds(
            mercado_handicap
        )

        if isinstance(linha, dict):

            resultado[
                "handicap_linha"
            ] = _numero(
                linha.get("hdp")
            )

            resultado[
                "odd_handicap_home"
            ] = _numero(
                linha.get("home")
            )

            resultado[
                "odd_handicap_away"
            ] = _numero(
                linha.get("away")
            )

            resultado[
                "mercados_encontrados"
            ].append("HANDICAP")

    # ========================================================
    # 5️⃣ DOUBLE CHANCE
    # ========================================================

    mercado_dc = _encontrar_mercado(
        mercados,
        (
            "Double Chance",
            "DoubleChance",
            "DC"
        )
    )

    if mercado_dc:

        linha = _primeiro_odds(
            mercado_dc
        )

        if isinstance(linha, dict):

            resultado["odd_1x"] = _numero(
                linha.get("1X")
            )

            resultado["odd_12"] = _numero(
                linha.get("12")
            )

            resultado["odd_x2"] = _numero(
                linha.get("X2")
            )

            resultado[
                "mercados_encontrados"
            ].append("DOUBLE_CHANCE")

    # ========================================================
    # 6️⃣ DRAW NO BET
    # ========================================================

    mercado_dnb = _encontrar_mercado(
        mercados,
        (
            "Draw No Bet",
            "DrawNoBet",
            "DNB"
        )
    )

    if mercado_dnb:

        linha = _primeiro_odds(
            mercado_dnb
        )

        if isinstance(linha, dict):

            resultado[
                "odd_dnb_home"
            ] = _numero(
                linha.get("home")
            )

            resultado[
                "odd_dnb_away"
            ] = _numero(
                linha.get("away")
            )

            resultado[
                "mercados_encontrados"
            ].append("DNB")

    # ========================================================
    # LISTA DE TODOS OS MERCADOS RECEBIDOS
    # ========================================================

    for mercado in mercados:

        if not isinstance(
            mercado,
            dict
        ):
            continue

        nome = mercado.get(
            "name"
        )

        if nome:

            resultado[
                "mercados_disponiveis"
            ].append(
                str(nome)
            )

    # Remove duplicados mantendo ordem

    resultado[
        "mercados_disponiveis"
    ] = list(
        dict.fromkeys(
            resultado[
                "mercados_disponiveis"
            ]
        )
    )

    # ========================================================
    # MEMÓRIA DAS ODDS DO EMPATE
    # ========================================================

    odd_atual = resultado[
        "odd_atual"
    ]

    odd_anterior = 0.0

    if event_id is not None:

        odd_anterior = _ODD_ANTERIOR.get(
            event_id,
            0.0
        )

    # ========================================================
    # PRIMEIRA ODD VÁLIDA
    # ========================================================

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
    # VARIAÇÃO DESDE O INÍCIO
    # ========================================================

    if odd_inicial > 0:

        resultado[
            "variacao_desde_inicio"
        ] = (

            (
                odd_atual
                - odd_inicial
            )
            / odd_inicial

        ) * 100.0

    # ========================================================
    # VARIAÇÃO ENTRE CONSULTAS
    # ========================================================

    if odd_anterior > 0:

        resultado[
            "variacao_recente"
        ] = (

            (
                odd_atual
                - odd_anterior
            )
            / odd_anterior

        ) * 100.0

    # ========================================================
    # SALVA MEMÓRIA
    # ========================================================

    if (
        event_id is not None
        and odd_atual > 0
    ):

        _ODD_ANTERIOR[
            event_id
        ] = odd_atual

    # ========================================================
    # VALORES FINAIS
    # ========================================================

    resultado[
        "odd_anterior"
    ] = odd_anterior

    resultado[
        "odd_inicial"
    ] = odd_inicial

    # ========================================================
    # LOG
    # ========================================================

    print()
    print("=" * 60)
    print("📊 MERCADOS EXTRAÍDOS")
    print("=" * 60)

    print(
        "EVENT ID:",
        event_id
    )

    print(
        "1X2:",
        resultado["odd_home"],
        "|",
        resultado["odd_draw"],
        "|",
        resultado["odd_away"]
    )

    print(
        "OVER:",
        resultado["over_linha"],
        "|",
        resultado["odd_over"]
    )

    print(
        "UNDER:",
        resultado["under_linha"],
        "|",
        resultado["odd_under"]
    )

    print(
        "BTTS SIM:",
        resultado["odd_btts_sim"],
        "| NÃO:",
        resultado["odd_btts_nao"]
    )

    print(
        "HANDICAP:",
        resultado["handicap_linha"],
        "| CASA:",
        resultado["odd_handicap_home"],
        "| FORA:",
        resultado["odd_handicap_away"]
    )

    print(
        "DOUBLE CHANCE:",
        resultado["odd_1x"],
        "|",
        resultado["odd_12"],
        "|",
        resultado["odd_x2"]
    )

    print(
        "DNB:",
        resultado["odd_dnb_home"],
        "|",
        resultado["odd_dnb_away"]
    )

    print(
        "MERCADOS RECEBIDOS:",
        resultado[
            "mercados_disponiveis"
        ]
    )

    print(
        "VARIAÇÃO EMPATE:",
        f"{resultado['variacao_recente']:.2f}%"
    )

    print("=" * 60)

    return resultado
