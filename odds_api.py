# IPM-RADAR-V4 - odds_api.py
# Diagnóstico e leitura robusta dos mercados da Odds-API.io v3

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
    """Busca eventos LIVE diretamente na Odds-API.io."""
    parametros = urllib.parse.urlencode({
        "apiKey": obter_api_key(),
        "sport": "football",
    })

    resposta = fazer_requisicao(BASE_URL + "/events/live?" + parametros)

    if isinstance(resposta, list):
        return resposta

    print("[DIAGNOSTICO] /events/live não retornou lista.")
    print("[DIAGNOSTICO] Tipo:", type(resposta).__name__)
    return []


def buscar_odds_multiplos(eventos):
    """Busca odds para até 10 eventos da Odds-API.io."""
    ids = [str(e.get("id")) for e in eventos if isinstance(e, dict) and e.get("id")]

    if not ids:
        print("[DIAGNOSTICO] Nenhum ID da Odds-API.io foi recebido.")
        return []

    ids = ids[:10]

    print("[DIAGNOSTICO] IDs enviados para Odds-API.io:", ",".join(ids))

    parametros = urllib.parse.urlencode({
        "apiKey": obter_api_key(),
        "eventIds": ",".join(ids),
        "bookmakers": BOOKMAKER,
    })

    url = BASE_URL + "/odds/multi?" + parametros
    resposta = fazer_requisicao(url)

    print("[DIAGNOSTICO] Tipo da resposta /odds/multi:", type(resposta).__name__)

    # Normalmente a API retorna uma lista de eventos.
    if isinstance(resposta, list):
        print("[DIAGNOSTICO] Eventos com resposta de odds:", len(resposta))
        return resposta

    # Compatibilidade caso um único objeto seja retornado.
    if isinstance(resposta, dict):
        if "bookmakers" in resposta:
            print("[DIAGNOSTICO] Resposta contém bookmakers diretamente.")
            return [resposta]

        # Compatibilidade caso a API devolva um dicionário indexado por ID.
        eventos_dict = []
        for valor in resposta.values():
            if isinstance(valor, dict) and "bookmakers" in valor:
                eventos_dict.append(valor)
            elif isinstance(valor, list):
                eventos_dict.extend(
                    item for item in valor
                    if isinstance(item, dict) and "bookmakers" in item
                )

        if eventos_dict:
            print("[DIAGNOSTICO] Eventos recuperados de resposta indexada:", len(eventos_dict))
            return eventos_dict

        print("[DIAGNOSTICO] Dicionário sem estrutura de bookmakers reconhecida.")
        print("[DIAGNOSTICO] Chaves recebidas:", list(resposta.keys())[:20])

    return []


def extrair_mercados(odds_evento):
    """Extrai ML, Totals e Spread/Asian Handicap."""
    resultado = {
        "resultado": [],
        "gols": [],
        "handicap": [],
    }

    if not isinstance(odds_evento, dict):
        return resultado

    bookmakers = odds_evento.get("bookmakers", {})

    print("[DIAGNOSTICO] Bookmakers recebidos:", list(bookmakers.keys()) if isinstance(bookmakers, dict) else type(bookmakers).__name__)

    mercados = None

    # Formato atual da Odds-API.io:
    # {"bookmakers": {"Bet365": [{"name":"ML"}, {"name":"Totals"}, {"name":"Spread"}]}}
    if isinstance(bookmakers, dict):
        mercados = bookmakers.get(BOOKMAKER)

        if mercados is None:
            for nome, valor in bookmakers.items():
                if str(nome).strip().lower() == BOOKMAKER.lower():
                    mercados = valor
                    break

    # Compatibilidade com formatos em lista.
    elif isinstance(bookmakers, list):
        for bookmaker in bookmakers:
            if not isinstance(bookmaker, dict):
                continue

            nome = str(bookmaker.get("name", "")).strip().lower()
            if nome == BOOKMAKER.lower():
                mercados = bookmaker.get("markets", bookmaker.get("odds", []))
                break

    if not isinstance(mercados, list):
        print("[DIAGNOSTICO] Bet365 não encontrado para este evento.")
        return resultado

    nomes = [str(m.get("name", "")) for m in mercados if isinstance(m, dict)]
    print("[DIAGNOSTICO] Mercados Bet365:", nomes)

    processar_mercados(mercados, resultado)

    print(
        "[DIAGNOSTICO] Resultado extraído ->",
        "ML:", len(resultado["resultado"]),
        "Totals:", len(resultado["gols"]),
        "Spread:", len(resultado["handicap"]),
    )

    return resultado


def processar_mercados(mercados, resultado):
    for mercado in mercados:
        if not isinstance(mercado, dict):
            continue

        nome = str(mercado.get("name", "")).strip().lower()
        outcomes = mercado.get("odds", [])

        if not isinstance(outcomes, list):
            continue

        # Resultado 1X2
        if nome in ("ml", "moneyline", "match result", "matchresult"):
            resultado["resultado"].extend(outcomes)

        # Total de gols / Over-Under
        elif nome in ("totals", "total goals", "total", "over/under", "over under"):
            for odd in outcomes:
                if isinstance(odd, dict):
                    resultado["gols"].append({
                        "linha": odd.get("hdp"),
                        "over": odd.get("over"),
                        "under": odd.get("under"),
                    })

        # Handicap / Spread
        elif nome in (
            "spread",
            "asian handicap",
            "asian handicap - 3 way",
            "handicap",
        ):
            for odd in outcomes:
                if isinstance(odd, dict):
                    resultado["handicap"].append({
                        "linha": odd.get("hdp"),
                        "home": odd.get("home"),
                        "away": odd.get("away"),
                    })
    
