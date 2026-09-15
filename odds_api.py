# ============================================================
# ODDS API - IPM RADAR V5.0
# CASA / EMPATE / VISITANTE
# ============================================================
#
# Função:
#   - Buscar jogos ao vivo.
#   - Buscar jogos pré-live.
#   - Buscar odds 1X2.
#   - Extrair mercados.
#   - Calcular Q pré-live.
#   - Calcular R pré-live.
#   - Preparar dados para o Scanner.
#
# IMPORTANTE:
#   Este módulo NÃO realiza apostas.
#   Este módulo NÃO gera entrada.
#   Este módulo apenas coleta e organiza dados.
#
# CÁLCULO PRÉ-LIVE:
#
#   Q = 2 × (W1 × W2) / (W1 + W2)
#   R = max(W1, W2) / min(W1, W2)
#
# Q mede a estrutura das duas pontas.
# R mede o desequilíbrio entre casa e visitante.
#
# ============================================================

import json
import gzip
import zlib
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
# MEMÓRIA LIVE
# ============================================================

_IDS_LIVE_SELECIONADOS = []


# ============================================================
# CONVERSÃO NUMÉRICA
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
# REQUISIÇÃO HTTP
# ============================================================

def _request_json(endpoint, params):
    url = (
        f"{BASE_URL}/{endpoint.lstrip('/')}"
        f"?{urllib.parse.urlencode(params)}"
    )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "IPM-Radar/5.0",
            "Accept": "application/json",
            # Evita que o servidor devolva gzip quando possível.
            "Accept-Encoding": "identity",
        },
    )

    def _decodificar_corpo(resp):
        bruto = resp.read()
        if not bruto:
            return ""

        # urllib não descompacta gzip automaticamente.
        encoding = str(resp.headers.get("Content-Encoding", "")).lower()
        if "gzip" in encoding or bruto[:2] == b"\x1f\x8b":
            try:
                bruto = gzip.decompress(bruto)
            except (OSError, EOFError):
                pass
        elif "deflate" in encoding:
            try:
                bruto = zlib.decompress(bruto)
            except zlib.error:
                try:
                    bruto = zlib.decompress(bruto, -zlib.MAX_WBITS)
                except zlib.error:
                    pass

        # JSON da API deve ser UTF-8. O fallback impede que uma
        # resposta mal rotulada derrube o ciclo inteiro do radar.
        try:
            return bruto.decode("utf-8")
        except UnicodeDecodeError:
            charset = "utf-8"
            content_type = str(resp.headers.get("Content-Type", ""))
            if "charset=" in content_type.lower():
                charset = content_type.lower().split("charset=", 1)[1].split(";", 1)[0].strip()
            try:
                return bruto.decode(charset, errors="replace")
            except (LookupError, UnicodeDecodeError):
                return bruto.decode("utf-8", errors="replace")

    try:
        with urllib.request.urlopen(
            req,
            timeout=TIMEOUT_REQUISICAO,
        ) as resp:
            body = _decodificar_corpo(resp)
            print("HTTP STATUS ODDS API:", resp.status)
            return json.loads(body) if body else []

    except urllib.error.HTTPError as erro:
        try:
            detalhe = erro.read().decode("utf-8")
        except Exception:
            detalhe = ""
        print(
            f"ERRO HTTP ODDS API: {erro.code} | "
            f"{detalhe[:500]}"
        )
        return []

    except (urllib.error.URLError, TimeoutError) as erro:
        print("ERRO DE CONEXAO ODDS API:", erro)
        return []

    except Exception as erro:
        print("ERRO ODDS API:", type(erro).__name__, erro)
        return []


# ============================================================
# NORMALIZAÇÃO DE EVENTOS
# ============================================================

def _lista_eventos(resposta):
    if isinstance(resposta, list):
        return [x for x in resposta if isinstance(x, dict)]

    if not isinstance(resposta, dict):
        return []

    for chave in ("events", "data", "results"):
        valor = resposta.get(chave)
        if isinstance(valor, list):
            return [x for x in valor if isinstance(x, dict)]

    if resposta.get("id") is not None:
        return [resposta]

    return [
        valor
        for valor in resposta.values()
        if isinstance(valor, dict)
        and valor.get("id") is not None
    ]


# ============================================================
# EXTRAIR MINUTO
# ============================================================

def _extrair_minuto(jogo):
    if not isinstance(jogo, dict):
        return 0

    clock = jogo.get("clock")

    if isinstance(clock, dict):
        minuto = _inteiro(clock.get("minute"), -1)
        if minuto >= 0:
            return minuto

    for valor in (
        jogo.get("minute"),
        jogo.get("elapsed"),
        jogo.get("timer"),
    ):
        if isinstance(valor, dict):
            valor = valor.get("minute", valor.get("elapsed"))

        if isinstance(valor, str):
            valor = (
                valor.replace("'", "")
                .replace("min", "")
                .strip()
            )

        minuto = _inteiro(valor, -1)
        if minuto >= 0:
            return minuto

    return 0


# ============================================================
# EXTRAIR PLACAR
# ============================================================

def _extrair_placar(jogo):
    for valor in (
        jogo.get("scores"),
        jogo.get("score"),
        jogo.get("result"),
    ):
        if isinstance(valor, dict):
            casa = valor.get("home", valor.get("homeScore"))
            fora = valor.get("away", valor.get("awayScore"))

            if casa is not None or fora is not None:
                return _inteiro(casa), _inteiro(fora)

        elif isinstance(valor, list) and len(valor) >= 2:
            return _inteiro(valor[0]), _inteiro(valor[1])

    return (
        _inteiro(jogo.get("homeScore")),
        _inteiro(jogo.get("awayScore")),
    )


# ============================================================
# EXTRAIR ESTATÍSTICAS
# ============================================================

def _extrair_estatisticas(jogo):
    for chave in ("statistics", "stats", "matchStatistics"):
        fonte = jogo.get(chave)

        if isinstance(fonte, dict):
            esc = fonte.get("corners")
            fin = fonte.get("shots")
            atq = fonte.get("dangerousAttacks")
            cart = fonte.get("cards")

            if (
                esc is not None
                or fin is not None
                or atq is not None
                or cart is not None
            ):
                return (
                    _inteiro(esc),
                    _inteiro(fin),
                    _inteiro(atq),
                    _inteiro(cart),
                )

    return 0, 0, 0, 0


# ============================================================
# DATA DO EVENTO
# ============================================================

def _parse_data_evento(evento):
    valor = (
        evento.get("date")
        or evento.get("startTime")
        or evento.get("start_time")
    )

    if not valor:
        return None

    try:
        dt = datetime.fromisoformat(
            str(valor).replace("Z", "+00:00")
        )

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


# ============================================================
# BUSCAR JOGOS AO VIVO
# ============================================================

def buscar_jogos_ao_vivo():
    global _IDS_LIVE_SELECIONADOS

    try:
        key = obter_api_key()
    except Exception as erro:
        print("ERRO API KEY:", erro)
        return []

    resposta = _request_json(
        "/events/live",
        {
            "apiKey": key,
            "sport": SPORT,
        },
    )

    eventos = _lista_eventos(resposta)
    mapa = {}

    for evento in eventos:
        event_id = evento.get("id")
        if event_id is not None:
            mapa[str(event_id)] = evento

    ids_mantidos = [
        str(event_id)
        for event_id in _IDS_LIVE_SELECIONADOS
        if str(event_id) in mapa
    ]

    restantes = [
        evento
        for event_id, evento in mapa.items()
        if event_id not in ids_mantidos
    ]

    restantes.sort(key=_extrair_minuto)

    vagas = max(
        0,
        MAX_EVENTOS_POR_CONSULTA - len(ids_mantidos),
    )

    for evento in restantes[:vagas]:
        ids_mantidos.append(str(evento["id"]))

    _IDS_LIVE_SELECIONADOS = ids_mantidos[:MAX_EVENTOS_POR_CONSULTA]

    selecionados = [
        mapa[event_id]
        for event_id in _IDS_LIVE_SELECIONADOS
        if event_id in mapa
    ]

    print(
        "JOGOS AO VIVO ENCONTRADOS:",
        len(eventos),
        "| SELECIONADOS:",
        len(selecionados),
    )

    for evento in selecionados:
        print(
            "SELECIONADO | "
            f"{_extrair_minuto(evento)}' | "
            f"{evento.get('home', '')} x "
            f"{evento.get('away', '')} | "
            f"ID={evento.get('id')}"
        )

    return selecionados


# ============================================================
# BUSCAR JOGOS PRÉ-LIVE
# ============================================================

def buscar_jogos_pre_live():
    try:
        key = obter_api_key()
    except Exception as erro:
        print("ERRO API KEY:", erro)
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
    agora = datetime.now(timezone.utc)
    limite = agora.timestamp() + PRE_LIVE_JANELA_MINUTOS * 60
    proximos = []

    for evento in eventos:
        dt = _parse_data_evento(evento)
        if dt is None:
            continue

        timestamp = dt.timestamp()

        if agora.timestamp() <= timestamp <= limite:
            proximos.append(evento)

    proximos.sort(
        key=lambda e: _parse_data_evento(e) or agora
    )

    proximos = proximos[:MAX_EVENTOS_POR_CONSULTA]

    print(
        "JOGOS PRE-LIVE PROXIMOS:",
        len(proximos),
    )

    return proximos


# ============================================================
# BUSCAR ODDS MULTIPLOS
# ============================================================

def buscar_odds_multiplos(eventos):
    if not eventos:
        print("ODDS MULTI: nenhum evento recebido.")
        return []

    try:
        key = obter_api_key()
    except Exception as erro:
        print("ERRO API KEY:", erro)
        return []

    ids = [
        str(evento["id"])
        for evento in eventos
        if isinstance(evento, dict)
        and evento.get("id") is not None
    ]

    ids = list(dict.fromkeys(ids))
    ids = ids[:MAX_EVENTOS_POR_CONSULTA]

    if not ids:
        return []

    resultados = []

    for inicio in range(0, len(ids), 10):
        bloco = ids[inicio:inicio + 10]

        print(
            f"CONSULTA ODDS {inicio // 10 + 1}: "
            f"{len(bloco)} eventos | IDS={bloco}"
        )

        resposta = _request_json(
            "/odds/multi",
            {
                "apiKey": key,
                "eventIds": ",".join(bloco),
                "bookmakers": BOOKMAKER,
            },
        )

        eventos_odds = _lista_eventos(resposta)

        print(
            "EVENTOS COM ODDS RECEBIDOS:",
            len(eventos_odds),
        )

        resultados.extend(eventos_odds)

    return resultados


# ============================================================
# LOCALIZAR EVENTO DE ODDS
# ============================================================

def _evento_odds_por_id(odds, event_id):
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
# MERCADOS DO BOOKMAKER
# ============================================================

def _mercados_bet365(evento):
    if not isinstance(evento, dict):
        return []

    bookmakers = evento.get("bookmakers", {})

    if isinstance(bookmakers, dict):
        mercados = bookmakers.get(BOOKMAKER)

        if mercados is None:
            for nome, valor in bookmakers.items():
                if str(nome).strip().lower() == BOOKMAKER.strip().lower():
                    mercados = valor
                    break

        if isinstance(mercados, dict):
            mercados = mercados.get("markets", [])

        return mercados if isinstance(mercados, list) else []

    if isinstance(bookmakers, list):
        for bookmaker in bookmakers:
            if not isinstance(bookmaker, dict):
                continue

            nome = str(
                bookmaker.get("name")
                or bookmaker.get("title")
                or bookmaker.get("key")
                or ""
            ).strip().lower()

            if nome == BOOKMAKER.strip().lower():
                mercados = bookmaker.get("markets", [])
                return mercados if isinstance(mercados, list) else []

    return []


# ============================================================
# LINHAS DE ODDS
# ============================================================

def _linhas_odds(mercado):
    if not isinstance(mercado, dict):
        return []

    valores = mercado.get("odds")

    if isinstance(valores, list):
        return [item for item in valores if isinstance(item, dict)]

    if isinstance(valores, dict):
        return [valores]

    return []


# ============================================================
# PREÇO DE ITEM
# ============================================================

def _preco_item(item):
    if not isinstance(item, dict):
        return 0.0

    for chave in (
        "price",
        "value",
        "odd",
        "odds",
        "decimal",
    ):
        valor = item.get(chave)

        if isinstance(valor, (int, float, str)):
            numero = _numero(valor)
            if numero > 0:
                return numero

    return 0.0


# ============================================================
# EXTRAIR OUTCOME
# ============================================================

def _extrair_outcome(linha, nomes):
    if not isinstance(linha, dict):
        return 0.0

    alvo = {
        str(nome).strip().lower()
        for nome in nomes
    }

    for nome in nomes:
        valor = linha.get(nome)

        if valor not in (None, ""):
            if isinstance(valor, dict):
                preco = _preco_item(valor)
            else:
                preco = _numero(valor)

            if preco > 0:
                return preco

    for chave in (
        "outcomes",
        "selections",
        "items",
        "options",
    ):
        valor = linha.get(chave)

        if isinstance(valor, list):
            candidatos = [
                item for item in valor
                if isinstance(item, dict)
            ]
        elif isinstance(valor, dict):
            candidatos = [
                item for item in valor.values()
                if isinstance(item, dict)
            ]
        else:
            candidatos = []

        for item in candidatos:
            nome = str(
                item.get("name")
                or item.get("label")
                or item.get("selection")
                or item.get("key")
                or ""
            ).strip().lower()

            if nome in alvo:
                preco = _preco_item(item)
                if preco > 0:
                    return preco

    nome = str(
        linha.get("name")
        or linha.get("label")
        or linha.get("selection")
        or ""
    ).strip().lower()

    if nome in alvo:
        return _preco_item(linha)

    return 0.0


# ============================================================
# NOME DO MERCADO
# ============================================================

def _nome_mercado(mercado):
    return str(
        mercado.get("name")
        or mercado.get("key")
        or mercado.get("market")
        or ""
    ).strip().lower()


# ============================================================
# ENCONTRAR 1X2
# ============================================================

def _encontrar_1x2(mercados):
    nomes = (
        "ml",
        "moneyline",
        "1x2",
        "match winner",
        "match result",
        "full time result",
        "winner",
    )

    for mercado in mercados:
        nome = _nome_mercado(mercado)

        if nome in nomes:
            linhas = _linhas_odds(mercado)

            for linha in linhas:
                casa = _extrair_outcome(linha, ("home", "1"))
                empate = _extrair_outcome(linha, ("draw", "x", "tie"))
                fora = _extrair_outcome(linha, ("away", "2"))

                if casa > 0 or empate > 0 or fora > 0:
                    return casa, empate, fora

    return 0.0, 0.0, 0.0


# ============================================================
# CÁLCULO Q PRÉ-LIVE
# ============================================================

def calcular_q_pre_live(odd_casa, odd_visitante):
    """
    Q = 2 × (W1 × W2) / (W1 + W2)

    Fórmula alinhada ao scanner_pre_live.
    """

    w1 = _numero(odd_casa)
    w2 = _numero(odd_visitante)

    if w1 <= 0 or w2 <= 0:
        return 0.0

    soma = w1 + w2

    if soma <= 0:
        return 0.0

    return 2.0 * w1 * w2 / soma


# ============================================================
# CÁLCULO R PRÉ-LIVE
# ============================================================

def calcular_r_pre_live(odd_casa, odd_visitante):
    """
    R = maior odd / menor odd.

    R próximo de 1:
        maior equilíbrio.

    R maior:
        maior desequilíbrio entre as pontas.
    """

    w1 = _numero(odd_casa)
    w2 = _numero(odd_visitante)

    if w1 <= 0 or w2 <= 0:
        return 0.0

    menor = min(w1, w2)
    maior = max(w1, w2)

    if menor <= 0:
        return 0.0

    return maior / menor


# ============================================================
# DESEQUILÍBRIO
# ============================================================

def calcular_desequilibrio(odd_casa, odd_visitante):
    return calcular_r_pre_live(
        odd_casa,
        odd_visitante,
    )


# ============================================================
# CLASSIFICAÇÃO DO EQUILÍBRIO
# ============================================================

def classificar_equilibrio(r):
    r = _numero(r)

    if r <= 0:
        return "SEM DADOS"

    if r <= 1.20:
        return "MUITO EQUILIBRA
