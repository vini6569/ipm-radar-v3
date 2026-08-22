# ============================================================
# ODDS API
# IPM-RADAR-V3
#
# Função:
# - Buscar jogos ao vivo
# - Buscar odds Bet365
# - Extrair ML
# - Extrair Totals
# - Extrair Spread
# - Registrar horário de atualização das odds
#
# Esta versão foi preparada para diagnóstico.
# ============================================================

import os
import json
import urllib.request
import urllib.parse
import urllib.error


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

    print()
    print("CONSULTANDO:")
    print(url.replace(
        obter_api_key(),
        "***"
    ))

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
            timeout=20
        ) as resposta:

            conteudo = resposta.read().decode(
                "utf-8"
            )

            dados = json.loads(conteudo)

            return dados

    except urllib.error.HTTPError as erro:

        detalhe = ""

        try:

            detalhe = erro.read().decode(
                "utf-8"
            )

        except Exception:

            pass

        print()
        print("========================================")
        print("ERRO HTTP ODDS API")
        print("Código:", erro.code)
        print("Detalhes:", detalhe)
        print("========================================")

        return []

    except urllib.error.URLError as erro:

        print()
        print("========================================")
        print("ERRO DE CONEXÃO ODDS API")
        print(type(erro).__name__)
        print(erro)
        print("========================================")

        return []

    except json.JSONDecodeError as erro:

        print()
        print("========================================")
        print("ERRO JSON ODDS API")
        print(erro)
        print("========================================")

        return []

    except Exception as erro:

        print()
        print("========================================")
        print("ERRO NA REQUISIÇÃO ODDS API")
        print(type(erro).__name__)
        print(erro)
        print("========================================")

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

    resposta = fazer_requisicao(
        url
    )

    if not isinstance(
        resposta,
        list
    ):

        print(
            "Resposta de jogos ao vivo não é uma lista."
        )

        return []

    print()
    print("========================================")
    print("JOGOS AO VIVO")
    print("Total:", len(resposta))
    print("========================================")

    for jogo in resposta:

        if not isinstance(
            jogo,
            dict
        ):
            continue

        print(
            "ID:",
            jogo.get("id"),
            "|",
            jogo.get("home"),
            "x",
            jogo.get("away"),
            "| Placar:",
            jogo.get("scores")
        )

    return resposta


# ============================================================
# BUSCAR ODDS DE MÚLTIPLOS EVENTOS
# ============================================================

def buscar_odds_multiplos(eventos):

    api_key = obter_api_key()

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

        if evento_id:

            ids.append(
                str(evento_id)
            )

    if not ids:

        print(
            "Nenhum ID disponível para buscar odds."
        )

        return []

    # ========================================================
    # /odds/multi suporta até 10 eventos.
    # ========================================================

    ids = ids[:10]

    print()
    print("========================================")
    print("IDS ENVIADOS PARA ODDS API")
    print("========================================")

    for evento_id in ids:

        print(
            "ID:",
            evento_id
        )


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
            "Resposta de odds em formato desconhecido."
        )

        return []


    print()
    print("========================================")
    print("RESULTADO ODDS API")
    print("Eventos recebidos:",
          len(eventos_odds))
    print("========================================")


    # ========================================================
    # DIAGNÓSTICO COMPLETO
    # ========================================================

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
        print("----------------------------------------")

        print(
            "EVENTO:",
            evento_id
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
            "PLACAR:",
            evento.get("scores")
        )

        print(
            "STATUS:",
            evento.get("status")
        )


        bookmakers = evento.get(
            "bookmakers",
            {}
        )


        if not bookmakers:

            print(
                "⚠️ NENHUM BOOKMAKER RETORNADO."
            )

            continue


        if not isinstance(
            bookmakers,
            dict
        ):

            print(
                "⚠️ Formato de bookmakers:",
                type(bookmakers).__name__
            )

            continue


        print(
            "BOOKMAKERS:",
            list(
                bookmakers.keys()
            )
        )


        # ====================================================
        # PROCURAR BET365
        # ====================================================

        mercados = None


        for nome, valor in bookmakers.items():

            if str(nome).strip().lower() == \
               BOOKMAKER.lower():

                mercados = valor

                break


        if mercados is None:

            print(
                "⚠️ BET365 NÃO RETORNADA PARA ESTE EVENTO."
            )

            continue


        print(
            "✅ BET365 ENCONTRADA."
        )


        if not isinstance(
            mercados,
            list
        ):

            print(
                "⚠️ Formato dos mercados:",
                type(mercados).__name__
            )

            continue


        # ====================================================
        # MOSTRAR MERCADOS
        # ====================================================

        for mercado in mercados:

            if not isinstance(
                mercado,
                dict
            ):
                continue


            nome_mercado = mercado.get(
                "name",
                ""
            )


            atualizado = mercado.get(
                "updatedAt"
            )


            odds = mercado.get(
                "odds",
                []
            )


            print()
            print(
                "  MERCADO:",
                nome_mercado
            )

            print(
                "  ATUALIZADO:",
                atualizado
            )


            if not isinstance(
                odds,
                list
            ):

                print(
                    "  Odds em formato:",
                    type(odds).__name__
                )

                continue


            for odd in odds:

                if not isinstance(
                    odd,
                    dict
                ):
                    continue


                print(
                    "  ODDS:",
                    odd
                )


    print()
    print("========================================")

    return eventos_odds


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


    if not isinstance(
        bookmakers,
        dict
    ):

        return resultado


    # ========================================================
    # LOCALIZAR BET365
    # ========================================================

    mercados = None


    for nome, valor in bookmakers.items():

        if str(nome).strip().lower() == \
           BOOKMAKER.lower():

            mercados = valor

            break


    if mercados is None:

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


        nome = str(
            mercado.get(
                "name",
                ""
            )
        ).strip()


        atualizado = mercado.get(
            "updatedAt"
        )


        outcomes = mercado.get(
            "odds",
            []
        )


        if not isinstance(
            outcomes,
            list
        ):

            continue


        # ====================================================
        # RESULTADO 1X2
        # ====================================================

        if nome.lower() == "ml":

            for odd in outcomes:

                if not isinstance(
                    odd,
                    dict
                ):
                    continue


                resultado[
                    "resultado"
                ].append({

                    "home": odd.get(
                        "home"
                    ),

                    "draw": odd.get(
                        "draw"
                    ),

                    "away": odd.get(
                        "away"
                    ),

                    "updatedAt": atualizado

                })


        # ====================================================
        # TOTAL GOALS
        # ====================================================

        elif nome.lower() == "totals":

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

                    "updatedAt": atualizado

                })


        # ====================================================
        # ASIAN HANDICAP
        # ====================================================

        elif nome.lower() == "spread":

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

                    "updatedAt": atualizado

                })


    return resultado


# ============================================================
# RESUMO
# ============================================================

def mostrar_resumo_odds(
    odds_evento
):

    mercados = extrair_mercados(
        odds_evento
    )


    print()
    print("========================================")
    print("RESUMO ODDS")
    print("========================================")


    # ========================================================
    # RESULTADO
    # ========================================================

    print()
    print("RESULTADO 1X2")


    if mercados["resultado"]:

        for odd in mercados["resultado"]:

            print(
                "  Casa:",
                odd.get("home"),
                "| Empate:",
                odd.get("draw"),
                "| Fora:",
                odd.get("away"),
                "| Atualizado:",
                odd.get("updatedAt")
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


    if mercados["gols"]:

        for odd in mercados["gols"]:

            print(
                "  Linha:",
                odd.get("linha"),
                "| Over:",
                odd.get("over"),
                "| Under:",
                odd.get("under"),
                "| Atualizado:",
                odd.get("updatedAt")
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


    if mercados["handicap"]:

        for odd in mercados["handicap"]:

            print(
                "  Linha:",
                odd.get("linha"),
                "| Casa:",
                odd.get("home"),
                "| Fora:",
                odd.get("away"),
                "| Atualizado:",
                odd.get("updatedAt")
            )

    else:

        print(
            "  Sem odds de Asian Handicap."
        )


    print()
    print("========================================")
