# ============================================================
# ODDS API
# IPM-RADAR-V3
#
# Consulta:
# - Jogos ao vivo
# - Total Goals (Over / Under)
# - Asian Handicap
#
# A chave fica na variável ODDS_API_KEY
# ============================================================

import os
import json
import urllib.request
import urllib.parse


BASE_URL = "https://api.odds-api.io/v3"

BOOKMAKER = "Bet365"


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

    with urllib.request.urlopen(
        requisicao,
        timeout=20
    ) as resposta:

        conteudo = resposta.read().decode("utf-8")

        return json.loads(conteudo)


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

    resposta = fazer_requisicao(url)

    if not isinstance(resposta, list):
        return []

    return resposta


# ============================================================
# ODDS DOS JOGOS
# ============================================================

def buscar_odds_multiplos(eventos):

    api_key = obter_api_key()

    ids = []

    for evento in eventos:

        evento_id = evento.get("id")

        if evento_id:
            ids.append(str(evento_id))

    if not ids:
        return []

    # A API permite consultar até 10 eventos
    ids = ids[:10]

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

    resposta = fazer_requisicao(url)

    if not isinstance(resposta, list):
        return []

    return resposta


# ============================================================
# EXTRAÇÃO DOS MERCADOS
# ============================================================

def extrair_mercados(odds_evento):

    resultado = {
        "resultado": [],
        "gols": [],
        "handicap": []
    }

    if not isinstance(odds_evento, dict):
        return resultado

    # ========================================================
    # A API retorna bookmakers como DICIONÁRIO
    #
    # Exemplo:
    #
    # "bookmakers": {
    #     "Bet365": [
    #         {...},
    #         {...}
    #     ]
    # }
    # ========================================================

    bookmakers = odds_evento.get("bookmakers", {})

    if not isinstance(bookmakers, dict):
        return resultado

    # Pega somente a Bet365
    mercados = bookmakers.get(BOOKMAKER, [])

    if not isinstance(mercados, list):
        return resultado

    for mercado in mercados:

        if not isinstance(mercado, dict):
            continue

        nome = mercado.get("name")

        # ====================================================
        # TESTE
        # ====================================================

        print("MERCADO ENCONTRADO:", nome)

        outcomes = mercado.get("odds", [])

        if not isinstance(outcomes, list):
            continue

        # ====================================================
        # RESULTADO 1X2
        # ====================================================

        if nome == "ML":

            resultado["resultado"].extend(
                outcomes
            )

        # ====================================================
        # TOTAL GOALS
        # ====================================================

        elif nome == "Totals":

            for odd in outcomes:

                resultado["gols"].append({
                    "linha": odd.get("hdp"),
                    "over": odd.get("over"),
                    "under": odd.get("under")
                })

        # ====================================================
        # ASIAN HANDICAP
        # ====================================================

        elif nome == "Spread":

            for odd in outcomes:

                resultado["handicap"].append({
                    "linha": odd.get("hdp"),
                    "home": odd.get("home"),
                    "away": odd.get("away")
                })

    return resultado
