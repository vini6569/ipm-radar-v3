# ============================================================
# ODDS API
# IPM-RADAR-V3
#
# VERSÃO ECONÔMICA
#
# - Jogos ao vivo
# - Odds em lote
# - Máximo de 10 eventos por consulta
# - Bet365
# - Total Goals
# - Asian Handicap / Spread
# - Resultado 1X2 / ML
# - Diagnóstico dos mercados
# - Controle de erro 429
# - Sem requisições desnecessárias
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
# API KEY
# ============================================================

def obter_api_key():

    api_key = os.getenv("ODDS_API_KEY")

    if not api_key:

        raise RuntimeError(
            "ODDS_API_KEY não configurada."
        )

    return api_key


# ============================================================
# REQUISIÇÃO
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

            conteudo = resposta.read().decode(
                "utf-8"
            )

            if not conteudo:

                print(
                    "Resposta vazia da Odds API."
                )

                return []

            return json.loads(
                conteudo
            )

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
            "Detalhes:",
            detalhe
        )

        # ====================================================
        # LIMITE DA API
        # ====================================================

        if erro.code == 429:

            print()
            print(
                "⚠️ LIMITE 429 DA ODDS API."
            )

            print(
                "A consulta atual será encerrada."
            )

        print("=" * 60)

        return []

    except urllib.error.URLError as erro:

        print()
        print("=" * 60)
        print("ERRO DE CONEXÃO ODDS API")
        print("=" * 60)

        print(
            erro
        )

        print("=" * 60)

        return []

    except json.JSONDecodeError as erro:

        print()
        print("=" * 60)
        print("ERRO JSON ODDS API")
        print("=" * 60)

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
# JOGOS AO VIVO
# ============================================================

def buscar_jogos_ao_vivo():

    api_key = obter_api_key()

    parametros = urllib.parse.urlencode({

        "apiKey": api_key,

        "sport": "football"

    })

    url = (
        BASE_URL
        + "/events/live?"
        + parametros
    )

    print()
    print(
        "Consultando jogos ao vivo..."
    )

    resposta = fazer_requisicao(
        url
    )

    if not isinstance(
        resposta,
        list
    ):

        print(
            "Resposta de jogos não é uma lista."
        )

        return []

    print(
        "Jogos ao vivo encontrados:",
        len(resposta)
    )

    return resposta


# ============================================================
# ODDS DOS JOGOS
# ============================================================

def buscar_odds_multiplos(eventos):

    api_key = obter_api_key()

    if not isinstance(
        eventos,
        list
    ):

        return []

    ids = []

    # ========================================================
    # COLETAR IDs
    # ========================================================

    for evento in eventos:

        if not isinstance(
            evento,
            dict
        ):

            continue

        evento_id = evento.get(
            "id"
        )

        if evento_id:

            evento_id = str(
                evento_id
            )

            if evento_id not in ids:

                ids.append(
                    evento_id
                )

    if not ids:

        print(
            "Nenhum ID de evento disponível."
        )

        return []

    # ========================================================
    # LIMITAÇÃO ECONÔMICA
    #
    # Trabalhamos somente com os primeiros 10 eventos.
    # Isso evita chamadas excessivas à API.
    # ========================================================

    if len(ids) > MAX_EVENTOS_POR_CONSULTA:

        print()
        print(
            "⚠️ Limite econômico:"
        )

        print(
            "Eventos encontrados:",
            len(ids)
        )

        print(
            "Eventos consultados:",
            MAX_EVENTOS_POR_CONSULTA
        )

        ids = ids[
            :MAX_EVENTOS_POR_CONSULTA
        ]

    # ========================================================
    # CONSULTA
    # ========================================================

    print()
    print("=" * 60)
    print("CONSULTA DE ODDS")
    print("=" * 60)

    print(
        "Eventos enviados:",
        len(ids)
    )

    print(
        "IDs:",
        ids
    )

    print(
        "Bookmaker:",
        BOOKMAKER
    )

    print("=" * 60)

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

    resposta = fazer_requisicao(
        url
    )

    # ========================================================
    # DIAGNÓSTICO DA RESPOSTA
    # ========================================================

    print()
    print(
        "TIPO DA RESPOSTA ODDS:"
    )

    print(
        type(resposta).__name__
    )

    # ========================================================
    # NORMALIZAÇÃO
    # ========================================================

    if isinstance(
        resposta,
        list
    ):

        eventos_odds = resposta

    elif isinstance(
        resposta,
        dict
    ):

        eventos_odds = [
            resposta
        ]

    else:

        print(
            "Resposta desconhecida da Odds API."
        )

        return []

    print(
        "EVENTOS COM ODDS:",
        len(eventos_odds)
    )

    # ========================================================
    # DIAGNÓSTICO
    # ========================================================

    print()
    print("=" * 60)
    print("DIAGNÓSTICO ODDS")
    print("=" * 60)

    for evento in eventos_odds:

        if not isinstance(
            evento,
            dict
        ):

            continue

        evento_id = evento.get(
            "id"
        )

        print()
        print(
            "EVENTO:",
            evento_id
        )

        print(
            "JOGO:",
            evento.get("home"),
            "x",
            evento.get("away")
        )

        bookmakers = evento.get(
            "bookmakers",
            {}
        )

        if not bookmakers:

            print(
                "  Nenhum bookmaker retornado."
            )

            continue

        if not isinstance(
            bookmakers,
            dict
        ):

            print(
                "  Formato bookmakers:",
                type(bookmakers).__name__
            )

            continue

        print(
            "  BOOKMAKERS:",
            list(
                bookmakers.keys()
            )
        )

        for nome, mercados in bookmakers.items():

            print()
            print(
                "  BOOKMAKER:",
                nome
            )

            if not isinstance(
                mercados,
                list
            ):

                print(
                    "    Formato:",
                    type(mercados).__name__
                )

                continue

            for mercado in mercados:

                if not isinstance(
                    mercado,
                    dict
                ):

                    continue

                nome_mercado = mercado.get(
                    "name"
                )

                print(
                    "    MERCADO:",
                    repr(nome_mercado)
                )

    print()
    print("=" * 60)

    return eventos_odds


# ============================================================
# NORMALIZAR NOME DO MERCADO
# ============================================================

def normalizar_nome_mercado(nome):

    if nome is None:

        return ""

    return (
        str(nome)
        .strip()
        .lower()
        .replace("-", " ")
        .replace("_", " ")
    )


# ============================================================
# LOCALIZAR BOOKMAKER
# ============================================================

def localizar_bookmaker(bookmakers):

    if not isinstance(
        bookmakers,
        dict
    ):

        return None

    # ========================================================
    # PRIMEIRA TENTATIVA
    # ========================================================

    mercados = bookmakers.get(
        BOOKMAKER
    )

    if mercados is not None:

        return mercados

    # ========================================================
    # SEGUNDA TENTATIVA
    # Ignorar maiúsculas/minúsculas
    # ========================================================

    bookmaker_normalizado = (
        BOOKMAKER.strip().lower()
    )

    for nome, valor in bookmakers.items():

        if (
            str(nome)
            .strip()
            .lower()
            ==
            bookmaker_normalizado
        ):

            return valor

    return None


# ============================================================
# EXTRAIR ODDS DE UM MERCADO
# ============================================================

def extrair_odds_mercado(
    mercado
):

    if not isinstance(
        mercado,
        dict
    ):

        return []

    odds = mercado.get(
        "odds",
        []
    )

    if isinstance(
        odds,
        list
    ):

        return odds

    # ========================================================
    # Algumas respostas podem eventualmente vir como objeto.
    # ========================================================

    if isinstance(
        odds,
        dict
    ):

        return [
            odds
        ]

    return []


# ============================================================
# EXTRAÇÃO DOS MERCADOS
# ============================================================

def extrair_mercados(
    odds_evento
):

    resultado = {

        "resultado": [],

        "gols": [],

        "handicap": []

    }

    if not isinstance(
        odds_evento,
        dict
    ):

        return resultado

    bookmakers = odds_evento.get(
        "bookmakers",
        {}
    )

    mercados = localizar_bookmaker(
        bookmakers
    )

    if mercados is None:

        print(
            "Bookmaker não encontrado:",
            BOOKMAKER
        )

        return resultado

    if not isinstance(
        mercados,
        list
    ):

        return resultado

    # ========================================================
    # PROCESSAR MERCADOS
    # ========================================================

    for mercado in mercados:

        if not isinstance(
            mercado,
            dict
        ):

            continue

        nome = mercado.get(
            "name",
            ""
        )

        nome_normalizado = (
            normalizar_nome_mercado(
                nome
            )
        )

        print(
            "PROCESSANDO MERCADO:",
            repr(nome)
        )

        outcomes = (
            extrair_odds_mercado(
                mercado
            )
        )

        if not outcomes:

            continue

        # ====================================================
        # RESULTADO 1X2
        #
        # API:
        # ML
        # ====================================================

        if nome_normalizado in {

            "ml",
            "moneyline",
            "1x2",
            "match winner",
            "match_winner",
            "winner"

        }:

            for odd in outcomes:

                if not isinstance(
                    odd,
                    dict
                ):

                    continue

                home = odd.get(
                    "home"
                )

                draw = odd.get(
                    "draw"
                )

                away = odd.get(
                    "away"
                )

                if (
                    home is None
                    and
                    draw is None
                    and
                    away is None
                ):

                    continue

                resultado[
                    "resultado"
                ].append({

                    "home": home,

                    "draw": draw,

                    "away": away

                })

        # ====================================================
        # TOTAL GOALS
        #
        # API:
        # Totals
        # ====================================================

        elif nome_normalizado in {

            "totals",
            "total goals",
            "total goal",
            "goals",
            "goal totals"

        }:

            for odd in outcomes:

                if not isinstance(
                    odd,
                    dict
                ):

                    continue

                linha = odd.get(
                    "hdp"
                )

                over = odd.get(
                    "over"
                )

                under = odd.get(
                    "under"
                )

                if (
                    linha is None
                    and
                    over is None
                    and
                    under is None
                ):

                    continue

                resultado[
                    "gols"
                ].append({

                    "linha": linha,

                    "over": over,

                    "under": under

                })

        # ====================================================
        # ASIAN HANDICAP
        #
        # API:
        # Spread
        # ====================================================

        elif nome_normalizado in {

            "spread",
            "asian handicap",
            "handicap"

        }:

            for odd in outcomes:

                if not isinstance(
                    odd,
                    dict
                ):

                    continue

                linha = odd.get(
                    "hdp"
                )

                home = odd.get(
                    "home"
                )

                away = odd.get(
                    "away"
                )

                if (
                    linha is None
                    and
                    home is None
                    and
                    away is None
                ):

                    continue

                resultado[
                    "handicap"
                ].append({

                    "linha": linha,

                    "home": home,

                    "away": away

                })

    return resultado


# ============================================================
# RESUMO DOS MERCADOS
# ============================================================

def mostrar_resumo_odds(
    odds_evento
):

    mercados = extrair_mercados(
        odds_evento
    )

    print()
    print("=" * 60)
    print("RESUMO DAS ODDS")
    print("=" * 60)

    # ========================================================
    # RESULTADO
    # ========================================================

    print()
    print("RESULTADO 1X2")

    if mercados[
        "resultado"
    ]:

        for odd in mercados[
            "resultado"
        ]:

            print(
                "  Casa:",
                odd.get("home"),
                "| Empate:",
                odd.get("draw"),
                "| Fora:",
                odd.get("away")
            )

    else:

        print(
            "  Sem odds de Resultado."
        )

    # ========================================================
    # TOTAL GOALS
    # ========================================================

    print()
    print("TOTAL GOALS")

    if mercados[
        "gols"
    ]:

        for odd in mercados[
            "gols"
        ]:

            print(
                "  Linha:",
                odd.get("linha"),
                "| Over:",
                odd.get("over"),
                "| Under:",
                odd.get("under")
            )

    else:

        print(
            "  Sem odds de Total Goals."
        )

    # ========================================================
    # ASIAN HANDICAP
    # ========================================================

    print()
    print("ASIAN HANDICAP")

    if mercados[
        "handicap"
    ]:

        for odd in mercados[
            "handicap"
        ]:

            print(
                "  Linha:",
                odd.get("linha"),
                "| Casa:",
                odd.get("home"),
                "| Fora:",
                odd.get("away")
            )

    else:

        print(
            "  Sem odds de Asian Handicap."
        )

    print()
    print("=" * 60)
