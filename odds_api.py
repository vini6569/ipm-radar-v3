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
            "User-Agent": "IPM-Radar/4.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(requisicao, timeout=20) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def buscar_jogos_ao_vivo():
    """
    Busca eventos de futebol ao vivo na Odds-API.io.
    """

    parametros = urllib.parse.urlencode(
        {
            "apiKey": obter_api_key(),
            "sport": "football",
        }
    )

    url = BASE_URL + "/events/live?" + parametros

    resposta = fazer_requisicao(url)

    if isinstance(resposta, list):
        print("[DIAGNOSTICO] Jogos ao vivo encontrados:", len(resposta))
        return resposta

    print("[DIAGNOSTICO] /events/live não retornou uma lista.")
    print("[DIAGNOSTICO] Tipo recebido:", type(resposta).__name__)

    return []


def buscar_odds_multiplos(eventos):
    """
    Busca odds para até 10 eventos.
    """

    if not isinstance(eventos, list):
        return []

    ids = [
        str(evento.get("id"))
        for evento in eventos
        if isinstance(evento, dict) and evento.get("id")
    ]

    if not ids:
        print("[DIAGNOSTICO] Nenhum ID recebido.")
        return []

    ids = ids[:10]

    parametros = urllib.parse.urlencode(
        {
            "apiKey": obter_api_key(),
            "eventIds": ",".join(ids),
            "bookmakers": BOOKMAKER,
        }
    )

    url = BASE_URL + "/odds/multi?" + parametros

    resposta = fazer_requisicao(url)

    if isinstance(resposta, list):
        return resposta

    if isinstance(resposta, dict):
        if "bookmakers" in resposta:
            return [resposta]

        eventos_dict = []

        for valor in resposta.values():
            if isinstance(valor, dict) and "bookmakers" in valor:
                eventos_dict.append(valor)

            elif isinstance(valor, list):
                for item in valor:
                    if isinstance(item, dict) and "bookmakers" in item:
                        eventos_dict.append(item)

        return eventos_dict

    return []


def extrair_mercados(odds_evento):
    """
    Extrai Resultado, Total de Gols e Handicap.
    """

    resultado = {
        "resultado": [],
        "gols": [],
        "handicap": [],
    }

    if not isinstance(odds_evento, dict):
        return resultado

    bookmakers = odds_evento.get("bookmakers", {})

    mercados = None

    if isinstance(bookmakers, dict):

        mercados = bookmakers.get(BOOKMAKER)

        if mercados is None:
            for nome, valor in bookmakers.items():
                if str(nome).strip().lower() == BOOKMAKER.lower():
                    mercados = valor
                    break

    elif isinstance(bookmakers, list):

        for bookmaker in bookmakers:

            if not isinstance(bookmaker, dict):
                continue

            nome = str(bookmaker.get("name", "")).strip().lower()

            if nome == BOOKMAKER.lower():
                mercados = bookmaker.get(
                    "markets",
                    bookmaker.get("odds", [])
                )
                break

    if not isinstance(mercados, list):
        return resultado

    for mercado in mercados:

        if not isinstance(mercado, dict):
            continue

        nome = str(
            mercado.get("name", "")
        ).strip().lower()

        odds = mercado.get("odds", [])

        if not isinstance(odds, list):
            continue

        # RESULTADO 1X2
        if nome in (
            "ml",
            "moneyline",
            "match result",
            "matchresult",
        ):

            for odd in odds:

                if not isinstance(odd, dict):
                    continue

                if (
                    odd.get("home") is not None
                    or odd.get("draw") is not None
                    or odd.get("away") is not None
                ):
                    resultado["resultado"].append(
                        {
                            "home": odd.get("home"),
                            "draw": odd.get("draw"),
                            "away": odd.get("away"),
                        }
                    )

        # TOTAL DE GOLS
        elif nome in (
            "totals",
            "total goals",
            "total",
            "over/under",
            "over under",
        ):

            for odd in odds:

                if not isinstance(odd, dict):
                    continue

                resultado["gols"].append(
                    {
                        "linha": odd.get("hdp"),
                        "over": odd.get("over"),
                        "under": odd.get("under"),
                    }
                )

        # HANDICAP
        elif nome in (
            "spread",
            "asian handicap",
            "asian handicap - 3 way",
            "handicap",
        ):

            for odd in odds:

                if not isinstance(odd, dict):
                    continue

                resultado["handicap"].append(
                    {
                        "linha": odd.get("hdp"),
                        "home": odd.get("home"),
                        "away": odd.get("away"),
                    }
                )

    return resultado
