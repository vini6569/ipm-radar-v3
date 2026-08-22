# ============================================================
# ODDS API
# IPM-RADAR-V3
#
# VERSÃO CORRIGIDA - DIAGNÓSTICO LIVE
#
# Funções:
# - Buscar jogos ao vivo
# - Buscar odds em lote
# - Bet365
# - ML / 1X2
# - Totals
# - Spread / Asian Handicap
# - Diagnóstico completo
# - Controle de erro
# - Sem apostas automáticas
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
            detalhe
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

    print()
    print(
        "TIPO DA RESPOSTA LIVE:",
        type(resposta).__name__
    )

    # ========================================================
    # RESPOSTA EM LISTA
    # ========================================================

    if isinstance(
        resposta,
        list
    ):

        eventos = resposta

    # ========================================================
    # RESPOSTA EM OBJETO
    # ========================================================

    elif isinstance(
        resposta,
        dict
    ):

        print(
            "Chaves recebidas:",
            list(resposta.keys())
        )

        eventos = []

        # Algumas APIs podem envolver a lista
        # dentro de uma chave.

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

                eventos = valor

                break

        if not eventos:

            # Caso a própria resposta seja um evento
            if resposta.get("id"):

                eventos = [
                    resposta
                ]

    else:

        eventos = []

    print()
    print(
        "JOGOS AO VIVO ENCONTRADOS:",
        len(eventos)
    )

    # ========================================================
    # NENHUM JOGO
    # ========================================================

    if not eventos:

        print()
        print(
            "⚠️ NENHUM EVENTO AO VIVO FOI RETORNADO."
        )

        print(
            "A API respondeu corretamente, porém"
        )

        print(
            "não entregou partidas live nesta consulta."
        )

        print()
        print(
            "Isso pode ocorrer quando:"
        )

        print(
            "1. Não há eventos disponíveis para o filtro."
        )

        print(
            "2. A cobertura live não está disponível."
        )

        print(
            "3. O plano/chave não possui determinado acesso."
        )

        print(
            "4. A API está sem eventos naquele momento."
        )

        return []

    # ========================================================
    # MOSTRAR EVENTOS
    # ========================================================

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
            evento.get("league")
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

    try:

        api_key = obter_api_key()

    except Exception as erro:

        print(
            "ERRO API KEY:",
            erro
            )
