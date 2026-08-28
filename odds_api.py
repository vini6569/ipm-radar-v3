# ============================================================
# ODDS API - IPM RADAR V4.3
# ============================================================
#
# FUNÇÕES:
# 1) Busca jogos ao vivo;
# 2) Busca jogos próximos do início;
# 3) Captura odds pré-live;
# 4) Busca odds atuais;
# 5) Extrai mercados;
# 6) Mantém a odd pré-live em memória por jogo;
# 7) Mantém compatibilidade com o MOTOR IPM V4.3.
#
# IMPORTANTE:
# Não altera a fórmula do IPM.
# ============================================================

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from config import (
    BASE_URL,
    BOOKMAKER,
    SPORT,
    MAX_EVENTOS_POR_CONSULTA,
    TIMEOUT_REQUISICAO,
    obter_api_key,
    PRE_LIVE_JANELA_MINUTOS,
)


# ============================================================
# MEMÓRIA DA ODDS PRÉ-LIVE
# ============================================================

_odds_pre_live = {}


# ============================================================
# REQUEST
# ============================================================

def _request_json(endpoint, params):
    url = f"{BASE_URL}/{endpoint.lstrip('/')}?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "IPM-Radar/4.3",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(
            req,
            timeout=TIMEOUT_REQUISICAO
        ) as resp:

            body = resp.read().decode("utf-8")

            print(
                "HTTP STATUS ODDS API:",
                resp.status
            )

        return json.loads(body) if body else []

    except urllib.error.HTTPError as e:

        try:
            detalhe = e.read().decode("utf-8")
        except Exception:
            detalhe = ""

        print(
            f"❌ ERRO HTTP ODDS API: "
            f"{e.code} | {detalhe[:500]}"
        )

        return []

    except (urllib.error.URLError, TimeoutError) as e:

        print(
            "❌ ERRO DE CONEXÃO ODDS API:",
            e
        )

        return []

    except Exception as e:

        print(
            f"❌ ERRO ODDS API: "
            f"{type(e).__name__}: {e}"
        )

        return []


# ============================================================
# LISTA DE EVENTOS
# ============================================================

def _lista_eventos(resposta):

    if isinstance(resposta, list):

        return [
            x for x in resposta
            if isinstance(x, dict)
        ]

    if not isinstance(resposta, dict):
        return []

    for chave in (
        "events",
        "data",
        "results"
    ):

        valor = resposta.get(chave)

        if isinstance(valor, list):

            return [
                x for x in valor
                if isinstance(x, dict)
            ]

    if resposta.get("id") is not None:
        return [resposta]

    return [
        v for v in resposta.values()
        if isinstance(v, dict)
        and v.get("id") is not None
    ]


# ============================================================
# JOGOS AO VIVO
# ============================================================

def buscar_jogos_ao_vivo():

    try:
        key = obter_api_key()

    except Exception as e:

        print(
            "❌ ERRO API KEY:",
            e
        )

        return []

    resposta = _request_json(
        "/events/live",
        {
            "apiKey": key,
            "sport": SPORT,
        },
    )

    eventos = _lista_eventos(resposta)

    print(
        "JOGOS AO VIVO ENCONTRADOS:",
        len(eventos)
    )

    return eventos


# ============================================================
# DATA DO EVENTO
# ============================================================

def _parse_data_evento(evento):

    if not isinstance(evento, dict):
        return None

    valor = (
        evento.get("date")
        or evento.get("startTime")
        or evento.get("start_time")
        or evento.get("commenceTime")
        or evento.get("commence_time")
    )

    if not valor:
        return None

    try:

        texto = str(valor).replace(
            "Z",
            "+00:00"
        )

        dt = datetime.fromisoformat(texto)

        if dt.tzinfo is None:

            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        )

    except Exception:

        return None


# ============================================================
# CONVERSÕES
# ============================================================

def _numero(valor, padrao=0.0):

    try:

        if valor in (None, ""):
            return padrao

        return float(valor)

    except (TypeError, ValueError):

        return padrao


def _inteiro(valor, padrao=0):

    try:

        if valor in (None, ""):
            return padrao

        return int(float(valor))

    except (TypeError, ValueError):

        return padrao


# ============================================================
# NORMALIZAÇÃO DE TEXTO
# ============================================================

def _normalizar_texto(valor):

    return (
        str(valor or "")
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


# ============================================================
# BUSCAR JOGOS PRÉ-LIVE
# ============================================================

def buscar_jogos_pre_live():

    """
    Busca partidas pendentes próximas do início.

    Também tenta capturar a odd pré-live imediatamente.
    """

    try:

        key = obter_api_key()

    except Exception as e:

        print(
            "❌ ERRO API KEY:",
            e
        )

        return []

    resposta = _request_json(
        "/events",
        {
            "apiKey": key,
            "sport": SPORT,
            "status": "pending",
            "limit": 100,
            "bookmaker": BOOKMAKER,
        },
    )

    eventos = _lista_eventos(resposta)

    agora = datetime.now(
        timezone.utc
    )

    limite = (
        agora.timestamp()
        + PRE_LIVE_JANELA_MINUTOS * 60
    )

    proximos = []

    agora_ts = agora.timestamp()

    for evento in eventos:

        dt = _parse_data_evento(evento)

        if dt is None:
            continue

        ts = dt.timestamp()

        if agora_ts <= ts <= limite:

            proximos.append(evento)

    proximos.sort(
        key=lambda e: (
            _parse_data_evento(e)
            or agora
        )
    )

    proximos = proximos[
        :MAX_EVENTOS_POR_CONSULTA
    ]

    print(
        "⏳ JOGOS PRÉ-LIVE PRÓXIMOS:",
        len(proximos)
    )

    # --------------------------------------------------------
    # CAPTURA PRÉ-LIVE
    # --------------------------------------------------------

    if proximos:

        try:

            odds_pre = buscar_odds_multiplos(
                proximos
            )

            for jogo in proximos:

                event_id = jogo.get("id")

                dados = extrair_mercados(
                    jogo,
                    odds_pre
                )

                odd_draw = _numero(
                    dados.get("odd_draw")
                )

                if odd_draw > 0:

                    _odds_pre_live[
                        str(event_id)
                    ] = odd_draw

                    jogo[
                        "odd_pre_live"
                    ] = odd_draw

                    print(
                        f"💾 PRÉ-LIVE "
                        f"{event_id}: "
                        f"{odd_draw}"
                    )

        except Exception as e:

            print(
                "⚠️ ERRO CAPTURA PRÉ-LIVE:",
                e
            )

    return proximos


# ============================================================
# BUSCA ODDS DE MÚLTIPLOS EVENTOS
# ============================================================

def buscar_odds_multiplos(eventos):

    if not eventos:
        return []

    try:

        key = obter_api_key()

    except Exception as e:

        print(
            "❌ ERRO API KEY:",
            e
        )

        return []

    ids = []

    for evento in eventos:

        if (
            isinstance(evento, dict)
            and evento.get("id") is not None
        ):

            ids.append(
                str(evento["id"])
            )

    ids = list(
        dict.fromkeys(ids)
    )[:MAX_EVENTOS_POR_CONSULTA]

    if not ids:

        return []

    resposta = _request_json(
        "/odds/multi",
        {
            "apiKey": key,
            "eventIds": ",".join(ids),
            "bookmakers": BOOKMAKER,
        },
    )

    eventos_odds = _lista_eventos(
        resposta
    )

    print(
        "EVENTOS COM ODDS RECEBIDOS:",
        len(eventos_odds)
    )

    return eventos_odds


# ============================================================
# LOCALIZA EVENTO PELO ID
# ============================================================

def _evento_odds_por_id(
    odds,
    event_id
):

    if event_id is None:
        return None

    alvo = str(event_id)

    if isinstance(odds, list):

        for item in odds:

            if (
                isinstance(item, dict)
                and str(item.get("id")) == alvo
            ):

                return item

    if isinstance(odds, dict):

        if str(odds.get("id")) == alvo:

            return odds

        item = odds.get(alvo)

        if isinstance(item, dict):

            return item

    return None


# ============================================================
# EXTRAÇÃO ROBUSTA DO BOOKMAKER
# ============================================================

def _mercados_bet365(evento):

    if not isinstance(evento, dict):
        return []

    bookmakers = evento.get(
        "bookmakers",
        {}
    )

    # --------------------------------------------------------
    # FORMATO DICT
    # --------------------------------------------------------

    if isinstance(bookmakers, dict):

        # Primeiro tenta pelo nome exato
        mercados = bookmakers.get(
            BOOKMAKER
        )

        if isinstance(mercados, dict):

            mercados = mercados.get(
                "markets",
                mercados.get(
                    "bookmakers",
                    []
                )
            )

        # Procura ignorando maiúsculas/minúsculas
        if mercados is None:

            for nome, valor in bookmakers.items():

                if (
                    _normalizar_texto(nome)
                    == _normalizar_texto(BOOKMAKER)
                ):

                    mercados = valor
                    break

        if isinstance(mercados, dict):

            mercados = mercados.get(
                "markets",
                []
            )

        if isinstance(mercados, list):

            return mercados

    # --------------------------------------------------------
    # FORMATO LIST
    # --------------------------------------------------------

    if isinstance(bookmakers, list):

        for bookmaker in bookmakers:

            if not isinstance(
                bookmaker,
                dict
            ):
                continue

            nome = (
                bookmaker.get("name")
                or bookmaker.get("key")
                or bookmaker.get("title")
                or ""
            )

            if (
                _normalizar_texto(nome)
                == _normalizar_texto(BOOKMAKER)
            ):

                mercados = (
                    bookmaker.get("markets")
                    or bookmaker.get("data")
                    or []
                )

                if isinstance(
                    mercados,
                    list
                ):

                    return mercados

    return []


# ============================================================
# PRIMEIRA LINHA DE ODDS
# ============================================================

def _primeiro_odds(mercado):

    if not isinstance(
        mercado,
        dict
    ):

        return {}

    valores = (
        mercado.get("odds")
        or mercado.get("outcomes")
        or mercado.get("selections")
        or mercado.get("lines")
    )

    if isinstance(valores, list):

        for item in valores:

            if isinstance(
                item,
                dict
            ):

                return item

        return {}

    if isinstance(
        valores,
        dict
    ):

        return valores

    # Alguns formatos entregam os campos
    # diretamente no mercado.

    return mercado


# ============================================================
# TODAS AS LINHAS DE ODDS
# ============================================================

def _linhas_odds(mercado):

    if not isinstance(
        mercado,
        dict
    ):

        return []

    valores = (
        mercado.get("odds")
        or mercado.get("outcomes")
        or mercado.get("selections")
        or mercado.get("lines")
    )

    if isinstance(
        valores,
        list
    ):

        return [
            x for x in valores
            if isinstance(x, dict)
        ]

    if isinstance(
        valores,
        dict
    ):

        return [valores]

    # Se os valores estiverem diretamente
    # no mercado.

    return [mercado]


# ============================================================
# ENCONTRAR MERCADO
# ============================================================

def _encontrar_mercado(
    mercados,
    nomes
):

    nomes_normalizados = {
        _normalizar_texto(n)
        for n in nomes
    }

    for mercado in mercados:

        if not isinstance(
            mercado,
            dict
        ):
            continue

        nome = mercado.get(
            "name",
            mercado.get(
                "key",
                mercado.get(
                    "type",
                    ""
                )
            )
        )

        nome_normalizado = _normalizar_texto(
            nome
        )

        if nome_normalizado in nomes_normalizados:

            return mercado

    # Segunda tentativa:
    # procura por palavras-chave.

    for mercado in mercados:

        if not isinstance(
            mercado,
            dict
        ):
            continue

        nome = _normalizar_texto(
            mercado.get(
                "name",
                mercado.get(
                    "key",
                    mercado.get(
                        "type",
                        ""
                    )
                )
            )
        )

        for alvo in nomes_normalizados:

            if (
                alvo
                and (
                    alvo in nome
                    or nome in alvo
                )
            ):

                return mercado

    return None


# ============================================================
# CATEGORIA DO MERCADO
# ============================================================

def _eh_ht(nome):

    n = _normalizar_texto(nome)

    return any(
        termo in n
        for termo in (
            "half time",
            "halftime",
            "1st half",
            "first half",
            "1h",
            "ht result",
            "ht totals",
            "half time result",
        )
    )


def _categoria_mercado(nome):

    n = _normalizar_texto(nome)

    if _eh_ht(nome):
        return "HT"

    if (
        "corner" in n
        or "escante" in n
    ):

        return "CORNERS"

    if (
        "card" in n
        or "cartão" in n
        or "cartoes" in n
        or "booking" in n
    ):

        return "CARDS"

    return "FT"


# ============================================================
# PLACAR
# ============================================================

def _extrair_placar(jogo):

    if not isinstance(
        jogo,
        dict
    ):

        return 0, 0

    for valor in (
        jogo.get("score"),
        jogo.get("scores"),
        jogo.get("result"),
        jogo.get("currentScore"),
    ):

        if isinstance(
            valor,
            dict
        ):

            casa = (
                valor.get("home")
                if valor.get("home") is not None
                else valor.get("homeScore")
            )

            fora = (
                valor.get("away")
                if valor.get("away") is not None
                else valor.get("awayScore")
            )

            if (
                casa is not None
                or fora is not None
            ):

                return (
                    _inteiro(casa),
                    _inteiro(fora),
                )

        elif (
            isinstance(valor, list)
            and len(valor) >= 2
        ):

            return (
                _inteiro(valor[0]),
                _inteiro(valor[1]),
            )

        elif isinstance(
            valor,
            str
        ):

            texto = (
                valor
                .lower()
                .replace(" ", "")
            )

            if "x" in texto:

                try:

                    a, b = texto.split(
                        "x",
                        1
                    )

                    return (
                        _inteiro(a),
                        _inteiro(b),
                    )

                except Exception:
                    pass

    return (
        _inteiro(
            jogo.get("homeScore")
        ),
        _inteiro(
            jogo.get("awayScore")
        ),
    )


# ============================================================
# MINUTO
# ============================================================

def _extrair_minuto(jogo):

    if not isinstance(
        jogo,
        dict
    ):

        return 0

    for valor in (
        jogo.get("minute"),
        jogo.get("elapsed"),
        jogo.get("timer"),
        jogo.get("clock"),
    ):

        if isinstance(
            valor,
            dict
        ):

            valor = (
                valor.get("minute")
                if valor.get("minute") is not None
                else valor.get("elapsed")
            )

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
# ESTATÍSTICAS
# ============================================================

def _extrair_estatisticas(jogo):

    if not isinstance(
        jogo,
        dict
    ):

        return 0, 0, 0

    for chave in (
        "statistics",
        "stats",
        "matchStatistics",
    ):

        fonte = jogo.get(chave)

        if not isinstance(
            fonte,
            dict
        ):

            continue

        esc = (
            fonte.get("corners")
            or fonte.get("corner")
            or fonte.get("cornerKicks")
        )

        fin = (
            fonte.get("shots")
            or fonte.get("shotsTotal")
            or fonte.get("totalShots")
        )

        atq = (
            fonte.get("dangerousAttacks")
            or fonte.get("dangerous_attacks")
            or fonte.get("attacksDangerous")
        )

        if (
            esc is not None
            or fin is not None
            or atq is not None
        ):

            return (
                _inteiro(esc),
                _inteiro(fin),
                _inteiro(atq),
            )

    return 0, 0, 0


# =======================================
