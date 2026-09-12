# ============================================================
# ODDS API
# IPM-RADAR-V5.1
#
# Odds-API.io v3
#
# FUNÇÕES:
# - Buscar jogos ao vivo
# - Buscar jogos ao vivo por IDs
# - Buscar odds de múltiplos eventos
# - Extrair mercado 1X2
# - Extrair Odd Casa
# - Extrair Odd Empate
# - Extrair Odd Visitante
# - Extrair minuto quando disponível
# - Total Goals
# - Asian Handicap
# ============================================================

import os
import json
import urllib.request
import urllib.parse


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_URL = "https://api.odds-api.io/v3"

BOOKMAKER = os.getenv(
    "ODDS_BOOKMAKER",
    "Bet365"
)


# ============================================================
# API KEY
# ============================================================

def obter_api_key():

    api_key = os.getenv(
        "ODDS_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "ODDS_API_KEY não configurada."
        )

    return api_key


# ============================================================
# CONVERSÃO NUMÉRICA
# ============================================================

def numero(
    valor,
    padrao=0.0
):

    try:

        if valor in (
            None,
            ""
        ):
            return padrao

        return float(valor)

    except (
        TypeError,
        ValueError
    ):

        return padrao


# ============================================================
# REQUISIÇÃO
# ============================================================

def fazer_requisicao(url):

    requisicao = urllib.request.Request(

        url,

        headers={
            "User-Agent": "IPM-Radar/5.1",
            "Accept": "application/json",
        },
    )

    try:

        with urllib.request.urlopen(
            requisicao,
            timeout=20
        ) as resposta:

            conteudo = (
                resposta
                .read()
                .decode("utf-8")
            )

            return json.loads(
                conteudo
            )

    except Exception as erro:

        print(
            "ERRO NA REQUISICAO:",
            type(erro).__name__,
            erro
        )

        return []


# ============================================================
# JOGOS AO VIVO
# ============================================================

def buscar_jogos_ao_vivo():

    api_key = obter_api_key()

    parametros = urllib.parse.urlencode({

        "apiKey": api_key,

        "sport": "football",
    })

    url = (
        f"{BASE_URL}/events/live?"
        f"{parametros}"
    )

    print(
        "CONSULTANDO JOGOS AO VIVO..."
    )

    resposta = fazer_requisicao(
        url
    )

    if isinstance(
        resposta,
        list
    ):

        print(
            "JOGOS LIVE RECEBIDOS:",
            len(resposta)
        )

        return resposta

    print(
        "RESPOSTA DE JOGOS AO VIVO "
        "NAO E LISTA:",
        type(resposta).__name__
    )

    return []


# ============================================================
# JOGOS AO VIVO POR IDS
#
# O MAIN V5.1 USA ESTA FUNÇÃO.
#
# Primeiro consultamos o endpoint LIVE
# e filtramos pelos IDs monitorados.
# ============================================================

def buscar_jogos_ao_vivo_por_ids(
    ids
):

    if not ids:

        return []

    ids_normalizados = {
        str(event_id)
        for event_id in ids
        if event_id is not None
    }

    if not ids_normalizados:

        return []

    jogos_live = (
        buscar_jogos_ao_vivo()
        or []
    )

    encontrados = []

    for jogo in jogos_live:

        if not isinstance(
            jogo,
            dict
        ):

            continue

        event_id = jogo.get(
            "id"
        )

        if event_id is None:

            continue

        if str(event_id) in ids_normalizados:

            encontrados.append(
                jogo
            )

    print(
        "LIVE FILTRADO | "
        f"MONITORADOS={len(ids_normalizados)} | "
        f"ENCONTRADOS={len(encontrados)}"
    )

    return encontrados


# ============================================================
# ODDS DE MÚLTIPLOS EVENTOS
# ============================================================

def buscar_odds_multiplos(
    eventos
):

    api_key = obter_api_key()

    if not isinstance(
        eventos,
        list
    ):

        return []

    ids = []

    for evento in eventos:

        if not isinstance(
            evento,
            dict
        ):

            continue

        evento_id = evento.get(
            "id"
        )

        if evento_id is not None:

            ids.append(
                str(evento_id)
            )

    if not ids:

        print(
            "ODDS | NENHUM ID RECEBIDO."
        )

        return []

    # ========================================================
    # A API trabalha com até 10 eventos
    # por consulta.
    # ========================================================

    ids_unicos = []

    for event_id in ids:

        if event_id not in ids_unicos:

            ids_unicos.append(
                event_id
            )

    respostas = []

    # ========================================================
    # DIVIDE EM LOTES DE 10
    # ========================================================

    for inicio in range(
        0,
        len(ids_unicos),
        10
    ):

        lote = ids_unicos[
            inicio:inicio + 10
        ]

        parametros = urllib.parse.urlencode({

            "apiKey": api_key,

            "eventIds": ",".join(
                lote
            ),

            "bookmakers": BOOKMAKER,
        })

        url = (
            f"{BASE_URL}/odds/multi?"
            f"{parametros}"
        )

        print(
            "CONSULTANDO ODDS PARA:",
            ",".join(lote)
        )

        resposta = fazer_requisicao(
            url
        )

        # ====================================================
        # RESPOSTA NORMAL
        # ====================================================

        if isinstance(
            resposta,
            list
        ):

            respostas.extend(
                resposta
            )

        # ====================================================
        # COMPATIBILIDADE:
        # ALGUMAS RESPOSTAS PODEM SER OBJETO.
        # ====================================================

        elif isinstance(
            resposta,
            dict
        ):

            # Objeto de evento diretamente
            if (
                resposta.get("bookmakers")
                is not None
            ):

                respostas.append(
                    resposta
                )

            else:

                # Resposta indexada por ID
                for valor in resposta.values():

                    if isinstance(
                        valor,
                        dict
                    ):

                        if (
                            valor.get(
                                "bookmakers"
                            )
                            is not None
                        ):

                            respostas.append(
                                valor
                            )

                    elif isinstance(
                        valor,
                        list
                    ):

                        for item in valor:

                            if not isinstance(
                                item,
                                dict
                            ):

                                continue

                            if (
                                item.get(
                                    "bookmakers"
                                )
                                is not None
                            ):

                                respostas.append(
                                    item
                                )

    print(
        "ODDS RECEBIDAS:",
        len(respostas)
    )

    return respostas


# ============================================================
# LOCALIZAR EVENTO DE ODDS PELO ID
# ============================================================

def localizar_odds_evento(
    event_id,
    odds
):

    if event_id is None:

        return None

    event_id = str(
        event_id
    )

    if not isinstance(
        odds,
        list
    ):

        return None

    for evento in odds:

        if not isinstance(
            evento,
            dict
        ):

            continue

        evento_id = evento.get(
            "id"
        )

        if evento_id is None:

            continue

        if str(evento_id) == event_id:

            return evento

    return None


# ============================================================
# EXTRAIR MINUTO
# ============================================================

def extrair_minuto(
    evento
):

    if not isinstance(
        evento,
        dict
    ):

        return 0

    candidatos = [

        evento.get("minute"),

        evento.get("min"),

        evento.get("clock"),

        evento.get("elapsed"),

        evento.get("matchMinute"),

        evento.get("match_minute"),
    ]

    # ========================================================
    # PRIMEIRA FORMA SIMPLES
    # ========================================================

    for valor in candidatos:

        if isinstance(
            valor,
            (int, float)
        ):

            return int(
                max(
                    0,
                    valor
                )
            )

        if isinstance(
            valor,
            str
        ):

            texto = valor.strip()

            if not texto:

                continue

            # Exemplo:
            # "35"
            if texto.isdigit():

                return int(
                    texto
                )

            # Exemplo:
            # "35'"
            texto_limpo = (
                texto
                .replace(
                    "'",
                    ""
                )
                .strip()
            )

            if texto_limpo.isdigit():

                return int(
                    texto_limpo
                )

            # Exemplo:
            # "35:20"
            if ":" in texto:

                parte = texto.split(
                    ":"
                )[0]

                if parte.isdigit():

                    return int(
                        parte
                    )

    # ========================================================
    # CLOCK COMO DICIONÁRIO
    # ========================================================

    clock = evento.get(
        "clock"
    )

    if isinstance(
        clock,
        dict
    ):

        for chave in (
            "minute",
            "min",
            "elapsed",
        ):

            valor = clock.get(
                chave
            )

            if valor is not None:

                minuto = numero(
                    valor,
                    0
                )

                return int(
                    max(
                        0,
                        minuto
                    )
                )

    return 0


# ============================================================
# EXTRAIR MERCADOS
#
# COMPATÍVEL COM O MAIN V5.1:
#
# extrair_mercados(jogo_live, odds)
#
# Também aceita:
#
# extrair_mercados(odds_evento)
#
# ============================================================

def extrair_mercados(
    evento,
    odds=None
):

    resultado = {

        "resultado": [],

        "gols": [],

        "handicap": [],

        "odd_casa": 0.0,

        "odd_empate": 0.0,

        "odd_visitante": 0.0,

        "odd_draw": 0.0,

        "minuto": 0,
    }

    # ========================================================
    # IDENTIFICAR O OBJETO DE ODDS
    # ========================================================

    odds_evento = None

    if (
        isinstance(
            evento,
            dict
        )
        and evento.get(
            "bookmakers"
        ) is not None
    ):

        odds_evento = evento

    elif odds is not None:

        event_id = (
            evento.get("id")
            if isinstance(
                evento,
                dict
            )
            else evento
        )

        odds_evento = (
            localizar_odds_evento(
                event_id,
                odds
            )
        )

    if not isinstance(
        odds_evento,
        dict
    ):

        # Mesmo sem odds, tentamos
        # extrair o minuto do evento live.

        resultado["minuto"] = (
            extrair_minuto(
                evento
            )
        )

        return resultado

    # ========================================================
    # MINUTO
    # ========================================================

    resultado["minuto"] = (
        extrair_minuto(
            evento
        )
    )

    if resultado["minuto"] <= 0:

        resultado["minuto"] = (
            extrair_minuto(
                odds_evento
            )
        )

    # ========================================================
    # BOOKMAKERS
    #
    # A Odds-API.io v3 retorna:
    #
    # bookmakers:
    # {
    #   "Bet365": [
    #       {
    #           "name": "ML",
    #           "odds": [
    #               {
    #                   "home": "...",
    #                   "draw": "...",
    #                   "away": "..."
    #               }
    #           ]
    #       }
    #   ]
    # }
    # ========================================================

    bookmakers = odds_evento.get(
        "bookmakers",
        {}
    )

    # ========================================================
    # FORMATO NORMAL: DICT
    # ========================================================

    if isinstance(
        bookmakers,
        dict
    ):

        grupos = []

        for nome, mercados in bookmakers.items():

            grupos.append(
                (
                    nome,
                    mercados
                )
            )

    # ========================================================
    # COMPATIBILIDADE COM LISTA
    # ========================================================

    elif isinstance(
        bookmakers,
        list
    ):

        grupos = []

        for bookmaker in bookmakers:

            if not isinstance(
                bookmaker,
                dict
            ):

                continue

            nome = bookmaker.get(
                "name",
                ""
            )

            mercados = bookmaker.get(
                "markets",
                []
            )

            grupos.append(
                (
                    nome,
                    mercados
                )
            )

    else:

        return resultado

    # ========================================================
    # PERCORRER BOOKMAKERS
    # ========================================================

    for bookmaker_nome, mercados in grupos:

        if not isinstance(
            mercados,
            list
        ):

            continue

        for mercado in mercados:

            if not isinstance(
                mercado,
                dict
            ):

                continue

            nome_mercado = str(
                mercado.get(
                    "name",
                    ""
                )
            ).strip()

            outcomes = mercado.get(
                "odds",
                []
            )

            if not isinstance(
                outcomes,
                list
            ):

                continue

            # =================================================
            # 1X2
            # =================================================

            if nome_mercado.lower() == "ml":

                resultado[
                    "resultado"
                ].extend(
                    outcomes
                )

                # ---------------------------------------------
                # PRIMEIRO OUTCOME DO ML
                # ---------------------------------------------

                if outcomes:

                    outcome = outcomes[0]

                    if isinstance(
                        outcome,
                        dict
                    ):

                        odd_casa = numero(
                            outcome.get(
                                "home"
                            )
                        )

                        odd_empate = numero(
                            outcome.get(
                                "draw"
                            )
                        )

                        odd_visitante = numero(
                            outcome.get(
                                "away"
                            )
                        )

                        if (
                            odd_casa > 0
                            and resultado[
                                "odd_casa"
                            ] <= 0
                        ):

                            resultado[
                                "odd_casa"
                            ] = odd_casa

                        if (
                            odd_empate > 0
                            and resultado[
                                "odd_empate"
                            ] <= 0
                        ):

                            resultado[
                                "odd_empate"
                            ] = odd_empate

                            resultado[
                                "odd_draw"
                            ] = odd_empate

                        if (
                            odd_visitante > 0
                            and resultado[
                                "odd_visitante"
                            ] <= 0
                        ):

                            resultado[
                                "odd_visitante"
                            ] = odd_visitante

            # =================================================
            # TOTAL GOALS
            # =================================================

            elif (
                nome_mercado.lower()
                == "totals"
            ):

                for odd in outcomes:

                    if not isinstance(
                        odd,
                        dict
                    ):

                        continue

                    resultado[
                        "gols"
                    ].append({

                        "linha": odd.get(
                            "hdp"
                        ),

                        "over": odd.get(
                            "over"
                        ),

                        "under": odd.get(
                            "under"
                        ),

                        "bookmaker": (
                            bookmaker_nome
                        ),
                    })

            # ============================================================
# ODDS API
# IPM-RADAR-V5.1
#
# Odds-API.io v3
#
# FUNÇÕES:
# - Buscar jogos ao vivo
# - Buscar jogos ao vivo por IDs
# - Buscar odds de múltiplos eventos
# - Extrair mercado 1X2
# - Extrair Odd Casa
# - Extrair Odd Empate
# - Extrair Odd Visitante
# - Extrair minuto quando disponível
# - Total Goals
# - Asian Handicap
# ============================================================

import os
import json
import urllib.request
import urllib.parse


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_URL = "https://api.odds-api.io/v3"

BOOKMAKER = os.getenv(
    "ODDS_BOOKMAKER",
    "Bet365"
)


# ============================================================
# API KEY
# ============================================================

def obter_api_key():

    api_key = os.getenv(
        "ODDS_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "ODDS_API_KEY não configurada."
        )

    return api_key


# ============================================================
# CONVERSÃO NUMÉRICA
# ============================================================

def numero(
    valor,
    padrao=0.0
):

    try:

        if valor in (
            None,
            ""
        ):
            return padrao

        return float(valor)

    except (
        TypeError,
        ValueError
    ):

        return padrao


# ============================================================
# REQUISIÇÃO
# ============================================================

def fazer_requisicao(url):

    requisicao = urllib.request.Request(

        url,

        headers={
            "User-Agent": "IPM-Radar/5.1",
            "Accept": "application/json",
        },
    )

    try:

        with urllib.request.urlopen(
            requisicao,
            timeout=20
        ) as resposta:

            conteudo = (
                resposta
                .read()
                .decode("utf-8")
            )

            return json.loads(
                conteudo
            )

    except Exception as erro:

        print(
            "ERRO NA REQUISICAO:",
            type(erro).__name__,
            erro
        )

        return []


# ============================================================
# JOGOS AO VIVO
# ============================================================

def buscar_jogos_ao_vivo():

    api_key = obter_api_key()

    parametros = urllib.parse.urlencode({

        "apiKey": api_key,

        "sport": "football",
    })

    url = (
        f"{BASE_URL}/events/live?"
        f"{parametros}"
    )

    print(
        "CONSULTANDO JOGOS AO VIVO..."
    )

    resposta = fazer_requisicao(
        url
    )

    if isinstance(
        resposta,
        list
    ):

        print(
            "JOGOS LIVE RECEBIDOS:",
            len(resposta)
        )

        return resposta

    print(
        "RESPOSTA DE JOGOS AO VIVO "
        "NAO E LISTA:",
        type(resposta).__name__
    )

    return []


# ============================================================
# JOGOS AO VIVO POR IDS
#
# O MAIN V5.1 USA ESTA FUNÇÃO.
#
# Primeiro consultamos o endpoint LIVE
# e filtramos pelos IDs monitorados.
# ============================================================

def buscar_jogos_ao_vivo_por_ids(
    ids
):

    if not ids:

        return []

    ids_normalizados = {
        str(event_id)
        for event_id in ids
        if event_id is not None
    }

    if not ids_normalizados:

        return []

    jogos_live = (
        buscar_jogos_ao_vivo()
        or []
    )

    encontrados = []

    for jogo in jogos_live:

        if not isinstance(
            jogo,
            dict
        ):

            continue

        event_id = jogo.get(
            "id"
        )

        if event_id is None:

            continue

        if str(event_id) in ids_normalizados:

            encontrados.append(
                jogo
            )

    print(
        "LIVE FILTRADO | "
        f"MONITORADOS={len(ids_normalizados)} | "
        f"ENCONTRADOS={len(encontrados)}"
    )

    return encontrados


# ============================================================
# ODDS DE MÚLTIPLOS EVENTOS
# ============================================================

def buscar_odds_multiplos(
    eventos
):

    api_key = obter_api_key()

    if not isinstance(
        eventos,
        list
    ):

        return []

    ids = []

    for evento in eventos:

        if not isinstance(
            evento,
            dict
        ):

            continue

        evento_id = evento.get(
            "id"
        )

        if evento_id is not None:

            ids.append(
                str(evento_id)
            )

    if not ids:

        print(
            "ODDS | NENHUM ID RECEBIDO."
        )

        return []

    # ========================================================
    # A API trabalha com até 10 eventos
    # por consulta.
    # ========================================================

    ids_unicos = []

    for event_id in ids:

        if event_id not in ids_unicos:

            ids_unicos.append(
                event_id
            )

    respostas = []

    # ========================================================
    # DIVIDE EM LOTES DE 10
    # ========================================================

    for inicio in range(
        0,
        len(ids_unicos),
        10
    ):

        lote = ids_unicos[
            inicio:inicio + 10
        ]

        parametros = urllib.parse.urlencode({

            "apiKey": api_key,

            "eventIds": ",".join(
                lote
            ),

            "bookmakers": BOOKMAKER,
        })

        url = (
            f"{BASE_URL}/odds/multi?"
            f"{parametros}"
        )

        print(
            "CONSULTANDO ODDS PARA:",
            ",".join(lote)
        )

        resposta = fazer_requisicao(
            url
        )

        # ====================================================
        # RESPOSTA NORMAL
        # ====================================================

        if isinstance(
            resposta,
            list
        ):

            respostas.extend(
                resposta
            )

        # ====================================================
        # COMPATIBILIDADE:
        # ALGUMAS RESPOSTAS PODEM SER OBJETO.
        # ====================================================

        elif isinstance(
            resposta,
            dict
        ):

            # Objeto de evento diretamente
            if (
                resposta.get("bookmakers")
                is not None
            ):

                respostas.append(
                    resposta
                )

            else:

                # Resposta indexada por ID
                for valor in resposta.values():

                    if isinstance(
                        valor,
                        dict
                    ):

                        if (
                            valor.get(
                                "bookmakers"
                            )
                            is not None
                        ):

                            respostas.append(
                                valor
                            )

                    elif isinstance(
                        valor,
                        list
                    ):

                        for item in valor:

                            if not isinstance(
                                item,
                                dict
                            ):

                                continue

                            if (
                                item.get(
                                    "bookmakers"
                                )
                                is not None
                            ):

                                respostas.append(
                                    item
                                )

    print(
        "ODDS RECEBIDAS:",
        len(respostas)
    )

    return respostas


# ============================================================
# LOCALIZAR EVENTO DE ODDS PELO ID
# ============================================================

def localizar_odds_evento(
    event_id,
    odds
):

    if event_id is None:

        return None

    event_id = str(
        event_id
    )

    if not isinstance(
        odds,
        list
    ):

        return None

    for evento in odds:

        if not isinstance(
            evento,
            dict
        ):

            continue

        evento_id = evento.get(
            "id"
        )

        if evento_id is None:

            continue

        if str(evento_id) == event_id:

            return evento

    return None


# ============================================================
# EXTRAIR MINUTO
# ============================================================

def extrair_minuto(
    evento
):

    if not isinstance(
        evento,
        dict
    ):

        return 0

    candidatos = [

        evento.get("minute"),

        evento.get("min"),

        evento.get("clock"),

        evento.get("elapsed"),

        evento.get("matchMinute"),

        evento.get("match_minute"),
    ]

    # ========================================================
    # PRIMEIRA FORMA SIMPLES
    # ========================================================

    for valor in candidatos:

        if isinstance(
            valor,
            (int, float)
        ):

            return int(
                max(
                    0,
                    valor
                )
            )

        if isinstance(
            valor,
            str
        ):

            texto = valor.strip()

            if not texto:

                continue

            # Exemplo:
            # "35"
            if texto.isdigit():

                return int(
                    texto
                )

            # Exemplo:
            # "35'"
            texto_limpo = (
                texto
                .replace(
                    "'",
                    ""
                )
                .strip()
            )

            if texto_limpo.isdigit():

                return int(
                    texto_limpo
                )

            # Exemplo:
            # "35:20"
            if ":" in texto:

                parte = texto.split(
                    ":"
                )[0]

                if parte.isdigit():

                    return int(
                        parte
                    )

    # ========================================================
    # CLOCK COMO DICIONÁRIO
    # ========================================================

    clock = evento.get(
        "clock"
    )

    if isinstance(
        clock,
        dict
    ):

        for chave in (
            "minute",
            "min",
            "elapsed",
        ):

            valor = clock.get(
                chave
            )

            if valor is not None:

                minuto = numero(
                    valor,
                    0
                )

                return int(
                    max(
                        0,
                        minuto
                    )
                )

    return 0


# ============================================================
# EXTRAIR MERCADOS
#
# COMPATÍVEL COM O MAIN V5.1:
#
# extrair_mercados(jogo_live, odds)
#
# Também aceita:
#
# extrair_mercados(odds_evento)
#
# ============================================================

def extrair_mercados(
    evento,
    odds=None
):

    resultado = {

        "resultado": [],

        "gols": [],

        "handicap": [],

        "odd_casa": 0.0,

        "odd_empate": 0.0,

        "odd_visitante": 0.0,

        "odd_draw": 0.0,

        "minuto": 0,
    }

    # ========================================================
    # IDENTIFICAR O OBJETO DE ODDS
    # ========================================================

    odds_evento = None

    if (
        isinstance(
            evento,
            dict
        )
        and evento.get(
            "bookmakers"
        ) is not None
    ):

        odds_evento = evento

    elif odds is not None:

        event_id = (
            evento.get("id")
            if isinstance(
                evento,
                dict
            )
            else evento
        )

        odds_evento = (
            localizar_odds_evento(
                event_id,
                odds
            )
        )

    if not isinstance(
        odds_evento,
        dict
    ):

        # Mesmo sem odds, tentamos
        # extrair o minuto do evento live.

        resultado["minuto"] = (
            extrair_minuto(
                evento
            )
        )

        return resultado

    # ========================================================
    # MINUTO
    # ========================================================

    resultado["minuto"] = (
        extrair_minuto(
            evento
        )
    )

    if resultado["minuto"] <= 0:

        resultado["minuto"] = (
            extrair_minuto(
                odds_evento
            )
        )

    # ========================================================
    # BOOKMAKERS
    #
    # A Odds-API.io v3 retorna:
    #
    # bookmakers:
    # {
    #   "Bet365": [
    #       {
    #           "name": "ML",
    #           "odds": [
    #               {
    #                   "home": "...",
    #                   "draw": "...",
    #                   "away": "..."
    #               }
    #           ]
    #       }
    #   ]
    # }
    # ========================================================

    bookmakers = odds_evento.get(
        "bookmakers",
        {}
    )

    # ========================================================
    # FORMATO NORMAL: DICT
    # ========================================================

    if isinstance(
        bookmakers,
        dict
    ):

        grupos = []

        for nome, mercados in bookmakers.items():

            grupos.append(
                (
                    nome,
                    mercados
                )
            )

    # ========================================================
    # COMPATIBILIDADE COM LISTA
    # ========================================================

    elif isinstance(
        bookmakers,
        list
    ):

        grupos = []

        for bookmaker in bookmakers:

            if not isinstance(
                bookmaker,
                dict
            ):

                continue

            nome = bookmaker.get(
                "name",
                ""
            )

            mercados = bookmaker.get(
                "markets",
                []
            )

            grupos.append(
                (
                    nome,
                    mercados
                )
            )

    else:

        return resultado

    # ========================================================
    # PERCORRER BOOKMAKERS
    # ========================================================

    for bookmaker_nome, mercados in grupos:

        if not isinstance(
            mercados,
            list
        ):

            continue

        for mercado in mercados:

            if not isinstance(
                mercado,
                dict
            ):

                continue

            nome_mercado = str(
                mercado.get(
                    "name",
                    ""
                )
            ).strip()

            outcomes = mercado.get(
                "odds",
                []
            )

            if not isinstance(
                outcomes,
                list
            ):

                continue

            # =================================================
            # 1X2
            # =================================================

            if nome_mercado.lower() == "ml":

                resultado[
                    "resultado"
                ].extend(
                    outcomes
                )

                # ---------------------------------------------
                # PRIMEIRO OUTCOME DO ML
                # ---------------------------------------------

                if outcomes:

                    outcome = outcomes[0]

                    if isinstance(
                        outcome,
                        dict
                    ):

                        odd_casa = numero(
                            outcome.get(
                                "home"
                            )
                        )

                        odd_empate = numero(
                            outcome.get(
                                "draw"
                            )
                        )

                        odd_visitante = numero(
                            outcome.get(
                                "away"
                            )
                        )

                        if (
                            odd_casa > 0
                            and resultado[
                                "odd_casa"
                            ] <= 0
                        ):

                            resultado[
                                "odd_casa"
                            ] = odd_casa

                        if (
                            odd_empate > 0
                            and resultado[
                                "odd_empate"
                            ] <= 0
                        ):

                            resultado[
                                "odd_empate"
                            ] = odd_empate

                            resultado[
                                "odd_draw"
                            ] = odd_empate

                        if (
                            odd_visitante > 0
                            and resultado[
                                "odd_visitante"
                            ] <= 0
                        ):

                            resultado[
                                "odd_visitante"
                            ] = odd_visitante

            # =================================================
            # TOTAL GOALS
            # =================================================

            elif (
                nome_mercado.lower()
                == "totals"
            ):

                for odd in outcomes:

                    if not isinstance(
                        odd,
                        dict
                    ):

                        continue

                    resultado[
                        "gols"
                    ].append({

                        "linha": odd.get(
                            "hdp"
                        ),

                        "over": odd.get(
                            "over"
                        ),

                        "under": odd.get(
                            "under"
                        ),

                        "bookmaker": (
                            bookmaker_nome
                        ),
                    })

            # =================================================
            # ASIAN HANDICAP
            # =================================================

            elif (
                nome_mercado.lower()
                == "spread"
            ):

                for odd in outcomes:

                    if not isinstance(
                        odd,
                        dict
                    ):

                        continue

                    resultado[
                        "handicap"
                    ].append({

                        "linha": odd.get(
                            "hdp"
                        ),

                        "home": odd.get(
                            "home"
                        ),

                        "away": odd.get(
                            "away"
                        ),

                        "bookmaker": (
                            bookmaker_nome
                        ),
                    })

    # ========================================================
    # RETORNO
    # ========================================================

    return resultado


# ============================================================
# FUNÇÃO DE CONVENIÊNCIA
# ============================================================

def buscar_odds_e_extrair(
    eventos
):

    odds = (
        buscar_odds_multiplos(
            eventos
        )
        or []
    )

    resultados = []

    for evento in eventos:

        if not isinstance(
            evento,
            dict
        ):

            continue

        event_id = evento.get(
            "id"
        )

        mercados = extrair_mercados(
            evento,
            odds
        )

        resultados.append({

            "evento_id": event_id,

            "mercados": mercados,
        })

    return resultados


# ============================================================
# DIAGNÓSTICO
# ============================================================

def testar_conexao():

    print(
        "=========================================="
    )

    print(
        "TESTE ODDS API"
    )

    print(
        f"BASE URL: {BASE_URL}"
    )

    print(
        f"BOOKMAKER: {BOOKMAKER}"
    )

    print(
        "=========================================="
    )

    api_key = obter_api_key()

    print(
        "ODDS_API_KEY: CONFIGURADA"
    )

    print(
        f"TAMANHO DA CHAVE: {len(api_key)}"
    )

    jogos = (
        buscar_jogos_ao_vivo()
        or []
    )

    print(
        f"JOGOS LIVE: {len(jogos)}"
    )

    if jogos:

        print(
            "PRIMEIRO EVENTO:"
        )

        print(
            json.dumps(
                jogos[0],
                indent=2,
                ensure_ascii=False
            )[:5000]
        )

    print(
        "=========================================="
    )

    return jogos


# ============================================================
# FIM
# ============================================================
