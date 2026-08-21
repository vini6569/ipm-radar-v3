# ============================================================
# ODDS API - IPM RADAR V3
# VERSAO DE DIAGNOSTICO
# ============================================================

import os
import json
import urllib.request
import urllib.parse

BASE_URL = "https://api.odds-api.io/v3"
BOOKMAKER = "Bet365"


def obter_api_key():
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key:
        raise RuntimeError("ODDS_API_KEY não configurada.")
    return api_key


def fazer_requisicao(url):
    requisicao = urllib.request.Request(
        url,
        headers={
            "User-Agent": "IPM-Radar/3.0",
            "Accept": "application/json"
        }
    )

    with urllib.request.urlopen(requisicao, timeout=20) as resposta:
        conteudo = resposta.read().decode("utf-8")
        return json.loads(conteudo)


def buscar_jogos_ao_vivo():
    api_key = obter_api_key()

    parametros = urllib.parse.urlencode({
        "apiKey": api_key,
        "sport": "football",
        "status": "live"
    })

    url = BASE_URL + "/events?" + parametros

    resposta = fazer_requisicao(url)

    if not isinstance(resposta, list):
        return []

    return resposta


def buscar_odds_multiplos(eventos):
    api_key = obter_api_key()

    ids = []

    for evento in eventos:
        if not isinstance(evento, dict):
            continue

        evento_id = evento.get("id")

        if evento_id:
            ids.append(str(evento_id))

    if not ids:
        return []

    ids = ids[:10]

    parametros = urllib.parse.urlencode({
        "apiKey": api_key,
        "eventIds": ",".join(ids),
        "bookmakers": BOOKMAKER
    })

    url = BASE_URL + "/odds/multi?" + parametros

    resposta = fazer_requisicao(url)

    if not isinstance(resposta, list):
        if isinstance(resposta, dict):
            return [resposta]
        return []

    return resposta


def extrair_mercados(odds_evento):

    resultado = {
        "resultado": [],
        "gols": [],
        "handicap": []
    }

    if not isinstance(odds_evento, dict):
        print("DIAGNOSTICO: odds_evento não é dict")
        return resultado

    bookmakers = odds_evento.get("bookmakers", {})

    print("==============================================")
    print("DIAGNOSTICO ODDS")
    print("EVENTO:", odds_evento.get("id"))
    print("BOOKMAKERS TYPE:", type(bookmakers).__name__)

    if isinstance(bookmakers, dict):
        print("BOOKMAKERS ENCONTRADOS:", list(bookmakers.keys()))

        for bookmaker_nome, mercados in bookmakers.items():

            print("----------------------------------------------")
            print("BOOKMAKER:", bookmaker_nome)
            print("MERCADOS TYPE:", type(mercados).__name__)

            if not isinstance(mercados, list):
                print("MERCADOS NÃO É LISTA")
                continue

            print(
                "MERCADOS:",
                [m.get("name") for m in mercados if isinstance(m, dict)]
            )

            for mercado in mercados:

                if not isinstance(mercado, dict):
                    continue

                nome = mercado.get("name")
                outcomes = mercado.get("odds", [])

                print("MERCADO:", nome)
                print("ODDS:", outcomes)

                if not isinstance(outcomes, list):
                    continue

                # ------------------------------------------
                # RESULTADO 1X2
                # ------------------------------------------
                if str(nome).lower() in ("ml", "moneyline", "1x2"):

                    for odd in outcomes:
                        if isinstance(odd, dict):
                            resultado["resultado"].append({
                                "home": odd.get("home"),
                                "draw": odd.get("draw"),
                                "away": odd.get("away")
                            })

                # ------------------------------------------
                # TOTAL GOALS
                # ------------------------------------------
                elif str(nome).lower() in (
                    "totals",
                    "total",
                    "total goals"
                ):

                    for odd in outcomes:
                        if isinstance(odd, dict):
                            resultado["gols"].append({
                                "linha": odd.get("hdp"),
                                "over": odd.get("over"),
                                "under": odd.get("under")
                            })

                # ------------------------------------------
                # ASIAN HANDICAP
                # ------------------------------------------
                elif str(nome).lower() in (
                    "spread",
                    "asian handicap",
                    "handicap"
                ):

                    for odd in outcomes:
                        if isinstance(odd, dict):
                            resultado["handicap"].append({
                                "linha": odd.get("hdp"),
                                "home": odd.get("home"),
                                "away": odd.get("away")
                            })

    elif isinstance(bookmakers, list):

        print("BOOKMAKERS TYPE LIST")

        for bookmaker in bookmakers:

            if not isinstance(bookmaker, dict):
                continue

            nome_bookmaker = bookmaker.get("name")
            mercados = bookmaker.get("markets", [])

            print("BOOKMAKER:", nome_bookmaker)

            if not isinstance(mercados, list):
                continue

            for mercado in mercados:

                if not isinstance(mercado, dict):
                    continue

                nome = mercado.get("name")
                outcomes = mercado.get("odds", [])

                print("MERCADO:", nome)

                if not isinstance(outcomes, list):
                    continue

                if str(nome).lower() in ("ml", "moneyline", "1x2"):
                    for odd in outcomes:
                        if isinstance(odd, dict):
                            resultado["resultado"].append({
                                "home": odd.get("home"),
                                "draw": odd.get("draw"),
                                "away": odd.get("away")
                            })

                elif str(nome).lower() in (
                    "totals", "total", "total goals"
                ):
                    for odd in outcomes:
                        if isinstance(odd, dict):
                            resultado["gols"].append({
                                "linha": odd.get("hdp"),
                                "over": odd.get("over"),
                                "under": odd.get("under")
                            })

                elif str(nome).lower() in (
                    "spread", "asian handicap", "handicap"
                ):
                    for odd in outcomes:
                        if isinstance(odd, dict):
                            resultado["handicap"].append({
                                "linha": odd.get("hdp"),
                                "home": odd.get("home"),
                                "away": odd.get("away")
                            })

    else:
        print("BOOKMAKERS EM FORMATO DESCONHECIDO")

    print("RESULTADO EXTRAIDO:", resultado)
    print("==============================================")

    return resultado
    
