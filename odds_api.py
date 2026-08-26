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

# Odds API será a fonte das odds
# Não limitar o Radar a uma casa específica
BOOKMAKER = "Bet365"

MAX_EVENTOS_POR_CONSULTA = 10

TIMEOUT_REQUISICAO = 20


# ============================================================
# MEMÓRIA DA ODD - IPM RADAR V3
# ============================================================

_ODD_ANTERIOR = {}


def _memorizar_odd(evento_id, odd_atual):
    """
    Guarda a última odd de cada jogo.

    Primeira consulta:
        anterior = None

    Próximas consultas:
        anterior = última odd registrada
    """

    if evento_id is None:
        return None

    if odd_atual is None:
        return None

    try:
        odd_atual = float(odd_atual)
    except (ValueError, TypeError):
        return None

    if odd_atual <= 0:
        return None

    evento_id = str(evento_id)

    anterior = _ODD_ANTERIOR.get(evento_id)

    # Atualiza somente depois de guardar a anterior
    _ODD_ANTERIOR[evento_id] = odd_atual

    return anterior


def _calcular_variacao_odd(odd_anterior, odd_atual):
    """
    Calcula a variação percentual da odd.
    """

    if odd_anterior is None:
        return 0.0

    if odd_atual is None:
        return 0.0

    try:
        odd_anterior = float(odd_anterior)
        odd_atual = float(odd_atual)

        if odd_anterior <= 0:
            return 0.0

        variacao = (
            (odd_atual - odd_anterior)
            / odd_anterior
        ) * 100

        return round(variacao, 2)

    except (ValueError, TypeError, ZeroDivisionError):
        return 0.0


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

    try:

        requisicao = urllib.request.Request(

            url,

            headers={
                "User-Agent": "IPM-RADAR-V3"
            }

        )

        with urllib.request.urlopen(
            requisicao,
            timeout=TIMEOUT_REQUISICAO
        ) as resposta:

            conteudo = resposta.read().decode(
                "utf-8"
            )

            if not conteudo:

                print(
                    "⚠️ Resposta HTTP vazia."
                )

                return {}

            try:

                return json.loads(
                    conteudo
                )

            except json.JSONDecodeError:

                print(
                    "⚠️ Resposta não é JSON válido."
                )

                print(
                    conteudo[:2000]
                )

                return {}

    except urllib.error.HTTPError as erro:

        print(
            f"❌ HTTP ERROR: {erro.code}"
        )

        try:

            corpo = erro.read().decode(
                "utf-8",
                errors="replace"
            )

            print(
                "Resposta da API:",
                corpo[:2000]
            )

        except Exception:

            pass

        return {}

    except urllib.error.URLError as erro:

        print(
            "❌ URL ERROR:",
            erro
        )

        return {}

    except TimeoutError:

        print(
            "❌ Timeout na requisição."
        )

        return {}

    except Exception as erro:

        print(
            "❌ Erro na requisição:",
            erro
        )

        return {}

    # ========================================================
    # VERIFICAÇÃO DA RESPOSTA
    # ========================================================

    if not resposta:
        print("Resposta vazia da Odds API")
        return []

    # ========================================================
    # CONVERSÃO PARA JSON
    # ========================================================

    if isinstance(resposta, (dict, list)):
        return resposta

    try:
        return json.loads(resposta)

    except json.JSONDecodeError:
        print("Erro ao decodificar JSON da Odds API")
        return []


# ============================================================
# NORMALIZAR LISTA DE EVENTOS
# ============================================================

def _lista_eventos(resposta):

    if isinstance(resposta, list):
        return resposta

    if not isinstance(resposta, dict):
        return []

    for chave in (
        "events",
        "data",
        "results"
    ):

        valor = resposta.get(chave)

        if isinstance(valor, list):
            return valor

        if isinstance(valor, dict):
            return [valor]

    return []

# ============================================================
# CONVERSÃO PARA JSON
# ============================================================

def buscar_odds_multiplos(url):

    resposta = fazer_requisicao(url)

    print()
    print("=" * 60)
    print("🔬 DEBUG - RESPOSTA BRUTA ODDS API")
    print("=" * 60)

    try:
        print(
            json.dumps(
                resposta,
                indent=2,
                ensure_ascii=False
            )[:10000]
        )
    except Exception:
        print(resposta)

    print("=" * 60)

    if not resposta:
        print("Resposta vazia da Odds API")
        return []

    if isinstance(resposta, (dict, list)):
        return resposta

    try:
        return json.loads(resposta)

    except json.JSONDecodeError:
        print("Erro ao decodificar JSON da Odds API")
        return []


# ============================================================
# NORMALIZAR LISTA DE EVENTOS
# ============================================================

def _lista_eventos(resposta):

    if isinstance(resposta, list):
        return resposta

    if not isinstance(resposta, dict):
        return []

    for chave in (
        "events",
        "data",
        "results"
    ):

        valor = resposta.get(chave)

        if isinstance(valor, list):
            return valor

        if isinstance(valor, dict):
            return [valor]

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

    print("IDs ENVIADOS:", ids)

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

    # --------------------------------------------------------
    # VALIDAR JOGO
    # --------------------------------------------------------

    if not isinstance(
        jogo,
        dict
    ):

        return {}

    # --------------------------------------------------------
    # ID DO EVENTO
    # --------------------------------------------------------

    event_id = jogo.get(
        "id"
    )

    # --------------------------------------------------------
    # LOCALIZAR EVENTO NAS ODDS
    # --------------------------------------------------------

    evento_odds = _evento_odds_por_id(
        odds,
        event_id
    )

    if not isinstance(
        evento_odds,
        dict
    ):

        print(
            "⚠️ Odds não encontradas para o evento:",
            event_id
        )

        return {
            "odd_empate": 0.0,
            "odd_atual": 0.0,
            "mercados": []
        }

    # --------------------------------------------------------
    # LOCALIZAR MERCADOS DA BET365
    # --------------------------------------------------------

    mercados = _mercados_bet365(
        evento_odds
    )

    print()
    print(
        "🔎 MERCADOS ENCONTRADOS:",
        len(mercados)
    )

    # --------------------------------------------------------
    # MOSTRAR NOMES DOS MERCADOS
    # --------------------------------------------------------

    for mercado in mercados:

        if not isinstance(
            mercado,
            dict
        ):

            continue

        print(
            "📌 Mercado:",
            mercado.get("name")
        )
    # --------------------------------------------------------
    # MERCADO DE RESULTADO / MATCH WINNER
    # --------------------------------------------------------

    odd_empate = 0.0

    mercado_1x2 = _encontrar_mercado(
        mercados,
        (
            "ML",
            "1X2",
            "Match Winner",
            "Match Result",
            "Full Time Result",
            "Moneyline"
        )
    )
# --------------------------------------------------------
# LOCALIZAR OUTROS MERCADOS
# --------------------------------------------------------

mercado_draw_no_bet = _encontrar_mercado(
    mercados,
    ("Draw No Bet",)
)

mercado_double_chance = _encontrar_mercado(
    mercados,
    ("Double Chance",)
)

mercado_spread = _encontrar_mercado(
    mercados,
    ("Spread",)
)

mercado_totals = _encontrar_mercado(
    mercados,
    ("Totals",)
)

mercado_odd_even = _encontrar_mercado(
    mercados,
    ("Odd/Even",)
)

mercado_european_handicap = _encontrar_mercado(
    mercados,
    ("European Handicap",)
)

mercado_correct_score = _encontrar_mercado(
    mercados,
    ("Correct Score",)
)

mercado_last_team_to_score = _encontrar_mercado(
    mercados,
    ("Last Team To Score",)
)

mercado_corners_totals = _encontrar_mercado(
    mercados,
    ("Corners Totals",)
)

mercado_ml_2h = _encontrar_mercado(
    mercados,
    ("ML 2H",)
)

    # --------------------------------------------------------
    # PROCURAR A ODD DO EMPATE
    # --------------------------------------------------------

if mercado_1x2:

        print()
        print("🎯 MERCADO DE RESULTADO ENCONTRADO:")
        print(
            mercado_1x2.get("name")
        )

        linhas = mercado_1x2.get(
            "odds",
            []
        )

        # ----------------------------------------------------
        # NORMALIZAR ODDS
        # ----------------------------------------------------

        if isinstance(
            linhas,
            dict
        ):

            linhas = [
                linhas
            ]

        if not isinstance(
            linhas,
            list
        ):

            linhas = []

        print(
            "📊 LINHAS DE ODDS:",
            len(linhas)
        )

        # ----------------------------------------------------
        # PERCORRER TODAS AS LINHAS
        # ----------------------------------------------------

        for linha in linhas:

            if not isinstance(
                linha,
                dict
            ):

                continue

            print()
            print(
                "🔎 LINHA:",
                linha
            )

            # ------------------------------------------------
            # TENTATIVA 1 - DRAW
            # ------------------------------------------------

            odd_empate = _numero(
                linha.get(
                    "draw"
                )
            )

            # ------------------------------------------------
            # TENTATIVA 2 - X
            # ------------------------------------------------

            if odd_empate <= 0:

                odd_empate = _numero(
                    linha.get(
                        "X"
                    )
                )

            # ------------------------------------------------
            # TENTATIVA 3 - TIE
            # ------------------------------------------------

            if odd_empate <= 0:

                odd_empate = _numero(
                    linha.get(
                        "tie"
                    )
                )

            # ------------------------------------------------
            # TENTATIVA 4 - DRAW MAIÚSCULO
            # ------------------------------------------------

            if odd_empate <= 0:

                odd_empate = _numero(
                    linha.get(
                        "Draw"
                    )
                )

            # ------------------------------------------------
            # TENTATIVA 5 - DRAWODD
            # ------------------------------------------------

            if odd_empate <= 0:

                odd_empate = _numero(
                    linha.get(
                        "drawOdd"
                    )
                )

            # ------------------------------------------------
            # TENTATIVA 6 - ODD_DRAW
            # ------------------------------------------------

            if odd_empate <= 0:

                odd_empate = _numero(
                    linha.get(
                        "odd_draw"
                    )
                )

            # ------------------------------------------------
            # SE ENCONTROU, PARA
            # ------------------------------------------------

            if odd_empate > 0:

                print()
                print(
                    "✅ ODD DE EMPATE ENCONTRADA:",
                    odd_empate
                )

                break

        else:

        print()
        print(
            "⚠️ MERCADO ML / 1X2 NÃO ENCONTRADO."
        )

    # --------------------------------------------------------
    # RESULTADO DA EXTRAÇÃO
    # --------------------------------------------------------

    print()
    print(
        "💰 ODD EMPATE EXTRAÍDA:",
        odd_empate
    )
    

    # --------------------------------------------------------
    # MEMÓRIA DA ODD
    # --------------------------------------------------------

    odd_anterior = _memorizar_odd(
        event_id,
        odd_empate
    )

    # --------------------------------------------------------
    # VARIAÇÃO DA ODD
    # --------------------------------------------------------

    variacao_odd = _calcular_variacao_odd(
        odd_anterior,
        odd_empate
    )

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    resultado = {

        "odd_empate": round(
            odd_empate,
            2
        ),

        "odd_atual": round(
            odd_empate,
            2
        ),

        "odd_anterior": (
            round(
                odd_anterior,
                2
            )
            if odd_anterior is not None
            else 0.0
        ),

        "variacao_odd": round(
            variacao_odd,
            2
        ),

        "mercados": mercados

    }

    # --------------------------------------------------------
    # DEBUG FINAL
    # --------------------------------------------------------

    print()
    print(
        "💰 ODD ATUAL:",
        resultado["odd_atual"]
    )

    print(
        "💰 ODD ANTERIOR:",
        resultado["odd_anterior"]
    )

    print(
        "📈 VARIAÇÃO:",
        resultado["variacao_odd"],
        "%"
    )

    return resultado


        
