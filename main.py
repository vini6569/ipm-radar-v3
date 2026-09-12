# ============================================================
# MAIN - IPM RADAR V5.1 CORRIGIDO
# PRE-LIVE + MONITORAMENTO + MOTOR IPM
# ============================================================
#
# CORREÇÕES:
# 1) O radar NÃO para depois de encontrar um sinal.
# 2) Cada ciclo continua processando TODOS os jogos monitorados.
# 3) Jogo sem retorno LIVE não usa odds antigas como se fossem LIVE.
# 4) O alerta de +/-20% em 10 minutos é controlado por jogo/direção.
# 5) O mesmo sinal não fica sendo enviado a cada ciclo enquanto
#    permanecer igual; se voltar a NEUTRO e depois cruzar 20%,
#    pode alertar novamente.
# 6) Jogos finalizados são retirados do monitoramento.
# 7) Logs mostram quantos jogos foram lidos e quantos sinais ocorreram.
# ============================================================

import os
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from config import horario_ativo
from scanner_pre_live import escanear_pre_live

from odds_api import (
    buscar_jogos_ao_vivo_por_ids,
    buscar_odds_multiplos,
    extrair_mercados,
)

from telegram import enviar_mensagem

from motor_ipm import (
    analisar_ipm_com_memoria,
    avaliar_pre_entrada,
    jogo_finalizado,
    resultado_empate,
    formatar_radar,
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

INTERVALO_RADAR = int(
    os.getenv("INTERVALO_RADAR", "60")
)

Q_MIN = float(
    os.getenv("Q_PRE_LIVE_MINIMO", "2.30")
)

Q_MAX = float(
    os.getenv("Q_PRE_LIVE_MAXIMO", "3.00")
)

TELEGRAM_MAX_CARACTERES = 3800


# ============================================================
# MEMÓRIA DO MAIN
# ============================================================

ULTIMA_LISTA = None

JOGOS_MONITORADOS = {}

# Guarda o último estado de sinal enviado por jogo.
# Exemplo:
#   "ALTA_20"  -> não repete até mudar de estado
#   "NEUTRO"   -> permite novo alerta quando cruzar 20%
#   "QUEDA_20" -> não repete até mudar de estado
ULTIMO_SINAL_ENVIADO = {}


# ============================================================
# SERVIDOR DE SAÚDE
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

        self.end_headers()

        self.wfile.write(
            b"IPM RADAR V5.1 OK"
        )

    def log_message(
        self,
        format,
        *args
    ):
        return


def iniciar_servidor_saude():

    porta = int(
        os.getenv("PORT", "10000")
    )

    servidor = HTTPServer(
        ("0.0.0.0", porta),
        HealthHandler
    )

    threading.Thread(
        target=servidor.serve_forever,
        daemon=True
    ).start()

    print(
        f"SERVIDOR DE SAUDE ATIVO | PORTA={porta}"
    )


# ============================================================
# CONVERSÕES
# ============================================================

def numero(
    valor,
    padrao=0.0
):

    try:

        if valor in (
            None,
            ""
        ):
            return padrao

        return float(valor)

    except (
        TypeError,
        ValueError
    ):

        return padrao


# ============================================================
# EQUILÍBRIO
# ============================================================

def calcular_valores_equilibrio(r):

    r = numero(r)

    if r <= 0:

        return (
            0.0,
            0.0
        )

    equilibrio = 100.0 / r

    return (
        round(equilibrio, 2),
        round(
            100.0 - equilibrio,
            2
        )
    )


def obter_equilibrio_jogo(jogo):

    r = numero(
        jogo.get("r", 0)
    )

    equilibrio = numero(
        jogo.get(
            "equilibrio_percentual",
            0
        )
    )

    desequilibrio = numero(
        jogo.get(
            "desequilibrio_percentual",
            0
        )
    )

    if (
        equilibrio <= 0
        and desequilibrio <= 0
    ):

        equilibrio, desequilibrio = (
            calcular_valores_equilibrio(r)
        )

    return (
        equilibrio,
        desequilibrio
    )


# ============================================================
# FILTRO Q
# ============================================================

def filtrar_por_q(resultados):

    return [

        jogo

        for jogo in resultados

        if (
            Q_MIN
            <= numero(
                jogo.get(
                    "odd_pre_live",
                    jogo.get("q", 0)
                )
            )
            <= Q_MAX
        )

    ]


# ============================================================
# REGISTRAR JOGOS NO RADAR
# ============================================================

def registrar_jogos_monitorados(jogos):

    for jogo in jogos:

        event_id = jogo.get(
            "event_id"
        )

        if event_id is None:
            continue

        event_id = str(
            event_id
        )

        if event_id not in JOGOS_MONITORADOS:

            JOGOS_MONITORADOS[event_id] = {

                "event_id": event_id,

                "casa": jogo.get(
                    "casa",
                    "Casa"
                ),

                "fora": jogo.get(
                    "fora",
                    "Fora"
                ),

                "odd_casa": numero(
                    jogo.get(
                        "odd_casa",
                        0
                    )
                ),

                "odd_empate": numero(
                    jogo.get(
                        "odd_empate",
                        0
                    )
                ),

                "odd_visitante": numero(
                    jogo.get(
                        "odd_visitante",
                        0
                    )
                ),

                "q": numero(
                    jogo.get(
                        "q",
                        jogo.get(
                            "odd_pre_live",
                            0
                        )
                    )
                ),

                "odd_pre_live": numero(
                    jogo.get(
                        "odd_pre_live",
                        jogo.get(
                            "q",
                            0
                        )
                    )
                ),

                "criado_em": time.time(),

            }

        else:

            monitorado = (
                JOGOS_MONITORADOS[event_id]
            )

            monitorado["casa"] = jogo.get(
                "casa",
                monitorado["casa"]
            )

            monitorado["fora"] = jogo.get(
                "fora",
                monitorado["fora"]
            )

            if numero(
                jogo.get(
                    "odd_casa",
                    0
                )
            ) > 0:

                monitorado["odd_casa"] = (
                    numero(
                        jogo.get(
                            "odd_casa"
                        )
                    )
                )

            if numero(
                jogo.get(
                    "odd_empate",
                    0
                )
            ) > 0:

                monitorado["odd_empate"] = (
                    numero(
                        jogo.get(
                            "odd_empate"
                        )
                    )
                )

            if numero(
                jogo.get(
                    "odd_visitante",
                    0
                )
            ) > 0:

                monitorado["odd_visitante"] = (
                    numero(
                        jogo.get(
                            "odd_visitante"
                        )
                    )
                )


# ============================================================
# CONSTRUIR EVENTO PARA O MOTOR
# ============================================================

def construir_evento_motor(
    event_id,
    monitorado,
    jogo_live,
    mercados
):

    if not isinstance(
        jogo_live,
        dict
    ):
        jogo_live = {}

    if not isinstance(
        mercados,
        dict
    ):
        mercados = {}

    casa = (
        jogo_live.get("home")
        or jogo_live.get("homeTeam")
        or monitorado.get(
            "casa",
            "Casa"
        )
    )

    fora = (
        jogo_live.get("away")
        or jogo_live.get("awayTeam")
        or monitorado.get(
            "fora",
            "Fora"
        )
    )

    # --------------------------------------------------------
    # ODDS LIVE
    # --------------------------------------------------------

    odd_casa = numero(
        mercados.get(
            "odd_casa",
            mercados.get(
                "home",
                0
            )
        )
    )

    odd_empate = numero(
        mercados.get(
            "odd_empate",
            mercados.get(
                "odd_draw",
                mercados.get(
                    "draw",
                    0
                )
            )
        )
    )

    odd_visitante = numero(
        mercados.get(
            "odd_visitante",
            mercados.get(
                "away",
                0
            )
        )
    )

    # --------------------------------------------------------
    # FALLBACK SOMENTE SE O MERCADO NÃO TROUXER A ODD
    # --------------------------------------------------------

    if odd_casa <= 0:

        odd_casa = numero(
            monitorado.get(
                "odd_casa"
            )
        )

    if odd_empate <= 0:

        odd_empate = numero(
            monitorado.get(
                "odd_empate"
            )
        )

    if odd_visitante <= 0:

        odd_visitante = numero(
            monitorado.get(
                "odd_visitante"
            )
        )

    # --------------------------------------------------------
    # MINUTO
    # --------------------------------------------------------

    minuto = int(
        numero(
            mercados.get(
                "minuto",
                jogo_live.get(
                    "minute",
                    jogo_live.get(
                        "elapsed",
                        0
                    )
                )
            )
        )
    )

    # --------------------------------------------------------
    # PLACAR
    # --------------------------------------------------------

    gols = 0

    scores = jogo_live.get(
        "scores"
    )

    if isinstance(
        scores,
        dict
    ):

        gols_casa = int(
            numero(
                scores.get(
                    "home",
                    scores.get(
                        "homeScore",
                        0
                    )
                )
            )
        )

        gols_fora = int(
            numero(
                scores.get(
                    "away",
                    scores.get(
                        "awayScore",
                        0
                    )
                )
            )
        )

        gols = (
            gols_casa
            + gols_fora
        )

    else:

        gols = int(
            numero(
                jogo_live.get(
                    "goals",
                    0
                )
            )
        )

    # --------------------------------------------------------
    # ESTATÍSTICAS
    # --------------------------------------------------------

    escanteios = int(
        numero(
            mercados.get(
                "escanteios",
                jogo_live.get(
                    "corners",
                    0
                )
            )
        )
    )

    cartoes = int(
        numero(
            mercados.get(
                "cartoes",
                jogo_live.get(
                    "cards",
                    0
                )
            )
        )
    )

    finalizacoes = int(
        numero(
            mercados.get(
                "finalizacoes",
                jogo_live.get(
                    "shots",
                    0
                )
            )
        )
    )

    ataques_perigosos = int(
        numero(
            mercados.get(
                "ataques_perigosos",
                jogo_live.get(
                    "dangerous_attacks",
                    0
                )
            )
        )
    )

    # --------------------------------------------------------
    # PRÉ-LIVE
    # --------------------------------------------------------

    odd_pre_live = numero(
        monitorado.get(
            "odd_pre_live",
            monitorado.get(
                "odd_empate",
                0
            )
        )
    )

    odd_casa_pre_live = numero(
        monitorado.get(
            "odd_casa",
            0
        )
    )

    odd_visitante_pre_live = numero(
        monitorado.get(
            "odd_visitante",
            0
        )
    )

    return {

        "event_id": event_id,

        "home": casa,

        "away": fora,

        "minuto": minuto,

        "gols": gols,

        "escanteios": escanteios,

        "cartoes": cartoes,

        "finalizacoes": finalizacoes,

        "ataques_perigosos": ataques_perigosos,

        "odd_casa": odd_casa,

        "odd_empate": odd_empate,

        "odd_visitante": odd_visitante,

        "odd_pre_live": odd_pre_live,

        "odd_casa_pre_live": (
            odd_casa_pre_live
        ),

        "odd_visitante_pre_live": (
            odd_visitante_pre_live
        ),

    }


# ============================================================
# PROCESSAR MOTOR IPM
# ============================================================

def processar_motor_ipm(
    event_id,
    monitorado,
    jogo_live,
    mercados
):

    dados = construir_evento_motor(
        event_id,
        monitorado,
        jogo_live,
        mercados
    )

    # --------------------------------------------------------
    # VALIDAR ODD X
    # --------------------------------------------------------

    if dados["odd_empate"] <= 0:

        print(
            f"MOTOR IPM | ODD X INVALIDA | ID={event_id}"
        )

        return None

    # --------------------------------------------------------
    # CHAMADA DO MOTOR
    # --------------------------------------------------------

    resultado = analisar_ipm_com_memoria(

        chave_jogo=event_id,

        odd_atual=dados[
            "odd_empate"
        ],

        minuto=dados[
            "minuto"
        ],

        gols=dados[
            "gols"
        ],

        escanteios=dados[
            "escanteios"
        ],

        cartoes=dados[
            "cartoes"
        ],

        finalizacoes=dados[
            "finalizacoes"
        ],

        ataques_perigosos=dados[
            "ataques_perigosos"
        ],

        odd_pre_live=dados[
            "odd_pre_live"
        ],

        odd_casa=dados[
            "odd_casa"
        ],

        odd_visitante=dados[
            "odd_visitante"
        ],

        odd_casa_pre_live=dados[
            "odd_casa_pre_live"
        ],

        odd_visitante_pre_live=dados[
            "odd_visitante_pre_live"
        ],
    )

    # --------------------------------------------------------
    # LOG PRINCIPAL
    # --------------------------------------------------------

    var_10min = numero(
        resultado.get(
            "var_10min"
        )
    )

    sinal = resultado.get(
        "sinal_pre_entrada",
        "NEUTRO"
    )

    ipm = numero(
        resultado.get(
            "ipm"
        )
    )

    odd_x = numero(
        resultado.get(
            "odd_empate"
        )
    )

    odd_45 = numero(
        resultado.get(
            "odd_45"
        )
    )

    diferenca_45 = numero(
        resultado.get(
            "diferenca_45"
        )
    )

    print(
        "MOTOR IPM | "
        f"{dados['home']} x {dados['away']} | "
        f"{dados['minuto']}' | "
        f"X={odd_x:.2f} | "
        f"VAR10={var_10min:+.2f}% | "
        f"SINAL={sinal} | "
        f"IPM={ipm:.2f} | "
        f"45={odd_45:.2f} | "
        f"DIF45={diferenca_45:+.2f}%"
    )

    # --------------------------------------------------------
    # SINAL DE PRÉ-ENTRADA
    # --------------------------------------------------------

    if avaliar_pre_entrada(
        resultado
    ):

        ultimo_sinal = (
            ULTIMO_SINAL_ENVIADO.get(
                event_id
            )
        )

        # Só envia quando:
        # - é o primeiro sinal;
        # - mudou ALTA <-> QUEDA;
        # - ou voltou a NEUTRO antes de cruzar novamente.
        novo_sinal = (
            sinal != ultimo_sinal
        )

        if novo_sinal:

            print(
                "🚨 SINAL PRÉ-ENTRADA | "
                f"{dados['home']} x {dados['away']} | "
                f"{sinal} | "
                f"{var_10min:+.2f}%"
            )

            mensagem = formatar_radar(
                dados,
                resultado,
                mercados
            )

            if mensagem:

                enviado = enviar_mensagem(
                    mensagem
                )

                if enviado:

                    ULTIMO_SINAL_ENVIADO[
                        event_id
                    ] = sinal

                    print(
                        "ALERTA TELEGRAM ENVIADO | "
                        f"ID={event_id}"
                    )

        else:

            print(
                "SINAL JÁ ENVIADO NESTE ESTADO | "
                f"ID={event_id} | "
                f"{sinal}"
            )

    else:

        # Ao voltar para NEUTRO, libera um próximo cruzamento.
        if ULTIMO_SINAL_ENVIADO.get(
            event_id
        ) is not None:

            ULTIMO_SINAL_ENVIADO[
                event_id
            ] = "NEUTRO"

    return resultado


# ============================================================
# PROCESSAMENTO LIVE
# ============================================================

def processar_live():

    ids = list(
        JOGOS_MONITORADOS.keys()
    )

    if not ids:

        print(
            "LIVE | Nenhum jogo no radar."
        )

        return

    print(
        f"LIVE | Consultando {len(ids)} jogos monitorados."
    )

    # --------------------------------------------------------
    # BUSCAR JOGOS LIVE
    # --------------------------------------------------------

    try:

        jogos_live = (
            buscar_jogos_ao_vivo_por_ids(
                ids
            )
            or []
        )

    except Exception as erro:

        print(
            "ERRO BUSCANDO JOGOS LIVE:",
            type(erro).__name__,
            erro
        )

        return

    mapa_live = {

        str(
            j.get("id")
        ): j

        for j in jogos_live

        if (
            isinstance(j, dict)
            and j.get("id") is not None
        )

    }

    # --------------------------------------------------------
    # RETIRAR JOGOS FINALIZADOS
    # --------------------------------------------------------

    finalizados = []

    for event_id, jogo_live in mapa_live.items():

        if jogo_finalizado(jogo_live):

            finalizados.append(
                event_id
            )

    for event_id in finalizados:

        JOGOS_MONITORADOS.pop(
            event_id,
            None
        )

        ULTIMO_SINAL_ENVIADO.pop(
            event_id,
            None
        )

        print(
            f"LIVE | JOGO FINALIZADO REMOVIDO | ID={event_id}"
        )

    # Recalcula os IDs depois da limpeza.
    ids = list(
        JOGOS_MONITORADOS.keys()
    )

    if not ids:

        print(
            "LIVE | Nenhum jogo ativo após limpeza."
        )

        return

    # --------------------------------------------------------
    # PREPARAR EVENTOS PARA ODDS
    # --------------------------------------------------------

    eventos_para_odds = []

    for event_id in ids:

        evento = mapa_live.get(
            str(event_id)
        )

        # Não mandamos jogo inexistente no LIVE
        # para o módulo de odds como se estivesse ao vivo.
        if evento is None:

            print(
                f"LIVE | JOGO NÃO RETORNADO | ID={event_id}"
            )

            continue

        eventos_para_odds.append(
            evento
        )

    if not eventos_para_odds:

        print(
            "LIVE | Nenhum evento LIVE disponível neste ciclo."
        )

        return

    # --------------------------------------------------------
    # BUSCAR ODDS
    # --------------------------------------------------------

    try:

        odds = (
            buscar_odds_multiplos(
                eventos_para_odds
            )
            or []
        )

    except Exception as erro:

        print(
            "ERRO BUSCANDO ODDS:",
            type(erro).__name__,
            erro
        )

        return

    if not odds:

        print(
            "ODDS MONITORAMENTO: "
            "nenhuma odds recebida neste ciclo. "
            "O radar continua no próximo ciclo."
        )

        return

    # --------------------------------------------------------
    # PROCESSAR CADA JOGO
    # --------------------------------------------------------

    processados = 0
    sinais = 0

    for event_id in ids:

        event_id = str(
            event_id
        )

        monitorado = (
            JOGOS_MONITORADOS.get(
                event_id
            )
        )

        if not monitorado:
            continue

        jogo_live = (
            mapa_live.get(
                event_id
            )
        )

        # Se a partida não veio no retorno LIVE,
        # não inventamos uma leitura.
        if jogo_live is None:

            continue

        # ----------------------------------------------------
        # EXTRAIR MERCADOS
        # ----------------------------------------------------

        try:

            mercados = (
                extrair_mercados(
                    jogo_live,
                    odds
                )
                or {}
            )

        except Exception as erro:

            print(
                "ERRO EXTRAINDO MERCADOS | "
                f"ID={event_id} | "
                f"{type(erro).__name__}: {erro}"
            )

            continue

        # ----------------------------------------------------
        # MOTOR
        # ----------------------------------------------------

        resultado = processar_motor_ipm(

            event_id,

            monitorado,

            jogo_live,

            mercados

        )

        if resultado is None:
            continue

        processados += 1

        if avaliar_pre_entrada(
            resultado
        ):

            sinais += 1

    print(
        f"MONITORAMENTO CONCLUIDO | "
        f"LEITURAS={processados} | "
        f"SINAIS_ATIVOS={sinais} | "
        f"JOGOS_MONITORADOS={len(JOGOS_MONITORADOS)}"
    )


# ============================================================
# MENSAGEM PRÉ-LIVE
# ============================================================

def montar_mensagens(
    resultados
):

    mensagens = []

    def novo_bloco():

        return [

            "⚽ PRE-LIVE - IPM RADAR",

            "",

            f"📐 Q: {Q_MIN:.2f} ate {Q_MAX:.2f}",

            "📊 R = desequilibrio entre as pontas",

            "⚖️ Equilibrio = 100 / R",

            "⚠️ Desequilibrio = 100 - Equilibrio",

            "",

        ]

    linhas = novo_bloco()

    ultimo_dia = None

    for jogo in resultados:

        data = jogo.get(
            "data",
            ""
        )

        if data != ultimo_dia:

            if ultimo_dia is not None:

                linhas.append("")

            linhas.append(
                f"📅 Data: {data}"
            )

            ultimo_dia = data

        odd_casa = numero(
            jogo.get(
                "odd_casa",
                0
            )
        )

        odd_empate = numero(
            jogo.get(
                "odd_empate",
                0
            )
        )

        odd_visitante = numero(
            jogo.get(
                "odd_visitante",
                0
            )
        )

        q = numero(
            jogo.get(
                "q",
                0
            )
        )

        r = numero(
            jogo.get(
                "r",
                0
            )
        )

        prob_x = numero(
            jogo.get(
                "probabilidade_x",
                0
            )
        )

        prob_x_normalizada = numero(
            jogo.get(
                "probabilidade_x_normalizada",
                0
            )
        )

        equilibrio, desequilibrio = (
            obter_equilibrio_jogo(
                jogo
            )
        )

        classificacao = jogo.get(
            "equilibrio",
            ""
        )

        padrao = jogo.get(
            "padrao",
            ""
        )

        linhas.extend([

            f"⚽ {jogo.get('horario', '--:--')} | "
            f"{jogo.get('casa', 'Casa')} x "
            f"{jogo.get('fora', 'Fora')}",

            f"🏠 Casa {odd_casa:.2f} | "
            f"🤝 X {odd_empate:.2f} | "
            f"🚌 Visitante {odd_visitante:.2f}",

            f"📐 Q: {q:.2f}",

            f"📊 R: {r:.2f}",

            f"⚖️ Equilibrio: "
            f"{equilibrio:.2f}%",

            f"⚠️ Desequilibrio: "
            f"{desequilibrio:.2f}%",

            f"🎯 Estrutura: "
            f"{classificacao or 'NAO CLASSIFICADO'}",

            f"🧭 Padrao: "
            f"{padrao or 'NAO CLASSIFICADO'}",

            f"📊 P(X): "
            f"{prob_x:.2f}% | "
            f"P(X) N: "
            f"{prob_x_normalizada:.2f}%",

            "",

        ])

        if (
            len(
                "\n".join(linhas)
            )
            > TELEGRAM_MAX_CARACTERES
        ):

            mensagens.append(
                "\n".join(
                    linhas[:-10]
                )
            )

            linhas = novo_bloco()

            linhas.extend([

                f"📅 Data: {data}",

                f"⚽ {jogo.get('horario', '--:--')} | "
                f"{jogo.get('casa', 'Casa')} x "
                f"{jogo.get('fora', 'Fora')}",

                f"🏠 Casa {odd_casa:.2f} | "
                f"🤝 X {odd_empate:.2f} | "
                f"🚌 Visitante {odd_visitante:.2f}",

                f"📐 Q: {q:.2f}",

                f"📊 R: {r:.2f}",

                f"⚖️ Equilibrio: "
                f"{equilibrio:.2f}%",

                f"⚠️ Desequilibrio: "
                f"{desequilibrio:.2f}%",

                f"🎯 Estrutura: "
                f"{classificacao or 'NAO CLASSIFICADO'}",

                f"🧭 Padrao: "
                f"{padrao or 'NAO CLASSIFICADO'}",

                f"📊 P(X): "
                f"{prob_x:.2f}% | "
                f"P(X) N: "
                f"{prob_x_normalizada:.2f}%",

                "",

            ])

    if len(linhas) > 7:

        linhas.extend([

            "--------------------",

            f"📋 Jogos selecionados: "
            f"{len(resultados)}",

            "",

            "🤖 IPM-RADAR-V5.1",

            "🧪 Monitoramento estatistico pre-live.",

            "⚠️ Nao realiza apostas automaticamente.",

        ])

        mensagens.append(
            "\n".join(linhas)
        )

    return mensagens


# ============================================================
# EXECUTAR PRÉ-LIVE
# ============================================================

def executar_pre_live():

    print(
        "\n" + "=" * 72
    )

    print(
        "PRE-LIVE | IPM RADAR V5.1"
    )

    print(
        f"Q: {Q_MIN:.2f} -> {Q_MAX:.2f}"
    )

    print(
        "=" * 72
    )

    try:

        resultados = (
            escanear_pre_live()
            or []
        )

    except Exception as erro:

        print(
            "ERRO NO SCANNER:",
            type(erro).__name__,
            erro
        )

        return

    aprovados = filtrar_por_q(
        resultados
    )

    print(
        "JOGOS APROVADOS:",
        len(aprovados)
    )

    if not aprovados:

        print(
            "Nenhum jogo dentro da faixa Q."
        )

        return

    registrar_jogos_monitorados(
        aprovados
    )

    global ULTIMA_LISTA

    assinatura = tuple(

        (

            j.get("event_id"),

            j.get("odd_empate"),

            j.get("q"),

            j.get("r"),

        )

        for j in aprovados

    )

    if assinatura == ULTIMA_LISTA:

        print(
            "Lista igual a anterior."
        )

        return

    for mensagem in montar_mensagens(
        aprovados
    ):

        if enviar_mensagem(
            mensagem
        ):

            print(
                "LISTA PRE-LIVE ENVIADA."
            )

    ULTIMA_LISTA = assinatura


# ============================================================
# LOOP PRINCIPAL
# ============================================================

def loop_consulta():

    print(
        "IPM RADAR V5.1 INICIADO"
    )

    print(
        f"Q: {Q_MIN:.2f} -> {Q_MAX:.2f}"
    )

    print(
        f"INTERVALO: {INTERVALO_RADAR}s"
    )

    print(
        "SINAL PRÉ-ENTRADA: "
        "+/-20% EM 10 MINUTOS"
    )

    while True:

        inicio = time.time()

        try:

            if horario_ativo():

                executar_pre_live()

                processar_live()

            else:

                print(
                    "Radar em periodo de pausa."
                )

        except Exception as erro:

            print(
                "ERRO NO LOOP:",
                type(erro).__name__,
                erro
            )

        agora = time.time()

        proximo_ciclo = (
            (
                int(agora)
                // INTERVALO_RADAR
            )
            + 1
        ) * INTERVALO_RADAR

        espera = max(
            1,
            proximo_ciclo - agora
        )

        print(

            f"CICLO TERMINADO EM "
            f"{agora - inicio:.1f}s | "

            f"PROXIMO CICLO EM "
            f"{espera:.0f}s"

        )

        time.sleep(
            espera
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    iniciar_servidor_saude()

    loop_consulta()
