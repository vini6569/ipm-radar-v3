# ============================================================
# ODDS API
# IPM-RADAR-V3
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
            "ODDS_API_KEY não configurada no Render."
        )

    return api_key


# ============================================================
# REQUISIÇÃO
# ============================================================

def fazer_requisicao(url):

    requisicao = urllib.request.Request(
        url,
        headers={
            "User-Agent": "IPM-Radar-V3/3.0",
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
                print("Resposta vazia da Odds API.")
                return []

            return json.loads(conteudo)

    except urllib.error.HTTPError as erro:

        print()
        print("=" * 60)
        print("ERRO HTTP ODDS API")
        print("=" * 60)

        print("Código:", erro.code)

        try:
            detalhe = erro.read().decode("utf-8")
            print("Detalhes:", detalhe)
        except Exception:
            pass

        if erro.code == 401:
            print("API KEY inválida ou não autorizada.")

        elif erro.code == 403:
            print("Acesso negado pela Odds API.")

        elif erro.code == 429:
            print("LIMITE 429 DA ODDS API.")

        print("=" * 60)

        return []

    except urllib.error.URLError as erro:

        print()
        print("=" * 60)
        print("ERRO DE CONEXÃO ODDS API")
        print("=" * 60)

        print(type(erro).__name__)
        print(erro)

        print("=" * 60)

        return []

    except json.JSONDecodeError as erro:

        print()
        print("=" * 60)
        print("ERRO JSON ODDS API")
        print("=" * 60)

        print(erro)

        print("=" * 60)

        return []

    except Exception as erro:

        print()
        print("=" * 60)
        print("ERRO NA REQUISIÇÃO ODDS API")
        print("=" * 60)

        print(type(erro).__name__)
        print(erro)

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
    print("=" * 60)
    print("CONSULTANDO JOGOS AO VIVO...")
    print("=" * 60)

    resposta = fazer_requisicao(url)

    if not isinstance(resposta, list):

        print(
            "Resposta de jogos não é uma lista."
        )

        print(
            "Tipo:",
            type(resposta).__name__
        )

        return []

    print(
        "Jogos ao vivo encontrados:",
        len(resposta)
    )

    # ========================================================
    # MOSTRAR JOGOS
    # ========================================================

    for jogo in resposta:

        if not isinstance(jogo, dict):
            continue

        print(
            "ID:",
            jogo.get("id"),
            "|",
            jogo.get("home"),
            "x",
            jogo.get("away")
        )

    print("=" * 60)

    return resposta


# ============================================================
# BUSCAR ODDS DE VÁRIOS EVENTOS
# ============================================================

def buscar_odds_multiplos(eventos):

    api_key = obter_api_key()

    if not isinstance(eventos, list):
        return []

    ids = []

    # ========================================================
    # PEGAR IDS
    # ========================================================

    for evento in eventos:

        if not isinstance(evento, dict):
            continue

        evento_id = evento.get("id")

        if evento_id:

            evento_id = str(evento_id)

            if evento_id not in ids:
                ids.append(evento_id)

    if not ids:

        print(
            "Nenhum ID de evento disponível."
        )

        return []

    # ========================================================
    # LIMITE DE 10 EVENTOS
    # ========================================================

    if len(ids) > MAX_EVENTOS_POR_CONSULTA:

        print()
        print(
            "Limite econômico ativado."
        )

        print(
            "Eventos encontrados:",
            len(ids)
        )

        print(
            "Eventos consultados:",
            MAX_EVENTOS_POR_CONSULTA
        )

        ids = ids[:MAX_EVENTOS_POR_CONSULTA]

    # ========================================================
    # CONSULTA
    # ========================================================

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

    print()
    print("=" * 60)
    print("CONSULTANDO ODDS")
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

    resposta = fazer_requisicao(url)

    # ========================================================
    # NORMALIZAR
    # ========================================================

    if isinstance(resposta, list):

        eventos_odds = resposta

    elif isinstance(resposta, dict):

        eventos_odds = [resposta]

    else:

        print(
            "Resposta desconhecida da Odds API."
        )

        return []

    print(
        "Eventos com odds recebidos:",
        len(eventos_odds)
    )

    # ========================================================
    # DIAGNÓSTICO
    # ========================================================

    for evento in eventos_odds:

        if not isinstance(evento, dict):
            continue

        print()
        print(
            "EVENTO:",
            evento.get("id")
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
                "Nenhum bookmaker retornado."
            )

            continue

        if not isinstance(bookmakers, dict):

            print(
                "Formato de bookmakers:",
                type(bookmakers).__name__
            )

            continue

        print(
            "BOOKMAKERS:",
            list(bookmakers.keys())
        )

        for nome, mercados in bookmakers.items():

            print(
                "BOOKMAKER:",
                nome
            )

            if not isinstance(mercados, list):
                continue

            for mercado in mercados:

                if not isinstance(mercado, dict):
                    continue

                print(
                    "  MERCADO:",
                    mercado.get("name")
                )

    return eventos_odds


# ============================================================
# NORMALIZAR MERCADO
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

    if not isinstance(bookmakers, dict):
        return None

    mercados = bookmakers.get(
        BOOKMAKER
    )

    if mercados is not None:
        return mercados

    nome_procurado = (
        BOOKMAKER
        .strip()
        .lower()
    )

    for nome, valor in bookmakers.items():

        if (
            str(nome)
            .strip()
            .lower()
            ==
            nome_procurado
        ):

            return valor

    return None


# ============================================================
# EXTRAIR ODDS
# ============================================================

def extrair_odds_mercado(mercado):

    if not isinstance(mercado, dict):
        return []

    odds = mercado.get(
        "odds",
        []
    )

    if isinstance(odds, list):
        return odds

    if isinstance(odds, dict):
        return [odds]

    return []


# ============================================================
# EXTRAIR MERCADOS
# ============================================================

def extrair_mercados(odds_evento):

    resultado = {
        "resultado": [],
        "gols": [],
        "handicap": []
    }

    if not isinstance(odds_evento, dict):
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

    if not isinstance(mercados, list):
        return resultado

    # ========================================================
    # PROCESSAR CADA MERCADO
    # ========================================================

    for mercado in mercados:

        if not isinstance(mercado, dict):
            continue

        nome = mercado.get(
            "name",
            ""
        )

        nome_normalizado = (
            normalizar_nome_mercado(nome)
        )

        outcomes = (
            extrair_odds_mercado(mercado)
        )

        if not outcomes:
            continue

        print(
            "PROCESSANDO MERCADO:",
            repr(nome)
        )

        # ====================================================
        # RESULTADO 1X2
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

                if not isinstance(odd, dict):
                    continue

                home = odd.get("home")
                draw = odd.get("draw")
                away = odd.get("away")

                if (
                    home is None
                    and draw is None
                    and away is None
                ):
                    continue

                resultado["resultado"].append({
                    "home": home,
                    "draw": draw,
                    "away": away
                })

        # ====================================================
        # TOTAL GOALS
        # ====================================================

        elif nome_normalizado in {
            "totals",
            "total goals",
            "total goal",
            "goals",
            "goal totals"
        }:

            for odd in outcomes:

                if not isinstance(odd, dict):
                    continue

                linha = odd.get("hdp")
                over = odd.get("over")
                under = odd.get("under")

                if (
                    linha is None
                    and over is None
                    and under is None
                ):
                    continue

                resultado["gols"].append({
                    "linha": linha,
                    "over": over,
                    "under": under
                })

        # ====================================================
        # ASIAN HANDICAP
        # ====================================================

        elif nome_normalizado in {
            "spread",
            "asian handicap",
            "handicap"
        }:

            for odd in outcomes:

                if not isinstance(odd, dict):
                    continue

                linha = odd.get("hdp")
                home = odd.get("home")
                away = odd.get("away")

                if (
                    linha is None
                    and home is None
                    and away is None
                ):
                    continue

                resultado["handicap"].append({
                    "linha": linha,
                    "home": home,
                    "away": away
                })

    return resultado


# ============================================================
# RESUMO
# ============================================================

def mostrar_resumo_odds(odds_evento):

    mercados = extrair_mercados(
        odds_evento
    )

    print()
    print("=" * 60)
    print("RESUMO DAS ODDS")
    print("=" * 60)

    print()
    print("RESULTADO 1X2")

    if mercados["resultado"]:

        for odd in mercados["resultado"]:

            print(
                "Casa:",
                odd.get("home"),
                "| Empate:",
                odd.get("draw"),
                "| Fora:",
                odd.get("away")
            )

    else:

        print(
            "Sem odds de Resultado."
        )

    print()
    print("TOTAL GOALS")

    if mercados["gols"]:

        for odd in mercados["gols"]:

            print(
                "Linha:",
                odd.get("linha"),
                "| Over:",
                odd.get("over"),
                "| Under:",
                odd.get("under")
            )

    else:

        print(
            "Sem odds de Total Goals."
        )

    print()
    print("ASIAN HANDICAP")

    if mercados["handicap"]:

        for odd in mercados["handicap"]:

            print(
                "Linha:",
                odd.get("linha"),
                "| Casa:",
                odd.get("home"),
                "| Fora:",
                odd.get("away")
            )

    else:

        print(
            "Sem odds de Asian Handicap."
        )

    print("=" * 60)
