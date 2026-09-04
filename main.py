# ============================================================
# MAIN - IPM RADAR V5.1
# ============================================================

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from config import (
    NOME_BOT,
    VERSAO,
    INTERVALO_RADAR,
    MAX_JOGOS_RADAR,
    IPM_MINIMO_OBSERVACAO,
    IPM_MINIMO_FORTE,
    IPM_MINIMO_MUITO_FORTE,
    VARIACAO_MINIMA_ODD,
    IPM_MINIMO_ENTRADA,
    MINUTO_MINIMO_ENTRADA,
    MINUTO_MAXIMO_ENTRADA,
    MAX_ENTRADAS_POR_JOGO,
    horario_ativo,
    horario_atual,
)

from odds_api import (
    buscar_jogos_ao_vivo,
    buscar_jogos_pre_live,
    buscar_odds_multiplos,
    extrair_mercados,
)

from motor_ipm import (
    analisar_ipm_com_memoria,
    formatar_radar,
    avaliar_entrada,
    jogo_finalizado,
    resultado_empate,
)

from telegram import enviar_mensagem


# ============================================================
# PAINEL DE AJUSTE - MIN 45 E PRE-ENTRADA
# ============================================================

PRE_ENTRADA_ATIVADA = True

# A pré-entrada começa a ser avaliada a partir de 10 minutos.
PRE_ENTRADA_MINUTO = 10

# ============================================================
# LIMITE DO SINAL DE PRÉ-ENTRADA
#
# +20% ou mais = ALTA_20
# -20% ou menos = QUEDA_20
#
# IMPORTANTE:
# Esta regra usa a variação da odd do EMPATE
# em aproximadamente 10 minutos.
# ============================================================

PRE_ENTRADA_POSITIVO = 20.0
PRE_ENTRADA_NEGATIVO = 20.0


# ============================================================
# MIN 45!!!!!
# ============================================================

MIN45_PROB_BASE = 40.0


# ============================================================
# SERVIDOR DE SAÚDE
# ============================================================

PORTA_SAUDE = int(
    os.environ.get(
        "PORT",
        "10000"
    )
)

ARQUIVO_CONTROLE = Path(
    os.getenv(
        "ARQUIVO_CONTROLE",
        "ipm_controle.json"
    )
)


# ============================================================
# MEMÓRIA DO MAIN
# ============================================================

_lock = threading.Lock()

_controle_jogos = {}


# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(texto):
    return enviar_mensagem(texto)


# ============================================================
# SALVAR CONTROLE
# ============================================================

def salvar_controle():

    try:

        temporario = ARQUIVO_CONTROLE.with_suffix(
            ".tmp"
        )

        with temporario.open(
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                _controle_jogos,
                arquivo,
                ensure_ascii=False,
                indent=2
            )

        temporario.replace(
            ARQUIVO_CONTROLE
        )

    except Exception as erro:

        print(
            "ERRO AO SALVAR CONTROLE:",
            type(erro).__name__,
            erro
        )


# ============================================================
# CARREGAR CONTROLE
# ============================================================

def carregar_controle():

    global _controle_jogos

    try:

        if not ARQUIVO_CONTROLE.exists():

            print(
                "INFO: Arquivo de controle ainda nao existe."
            )

            return

        with ARQUIVO_CONTROLE.open(
            "r",
            encoding="utf-8"
        ) as arquivo:

            dados = json.load(
                arquivo
            )

        if isinstance(
            dados,
            dict
        ):

            _controle_jogos = dados

        print(
            "Controle carregado:",
            len(_controle_jogos),
            "jogos"
        )

    except Exception as erro:

        print(
            "ERRO AO CARREGAR CONTROLE:",
            type(erro).__name__,
            erro
        )


# ============================================================
# OBTER CONTROLE DO JOGO
# ============================================================

def obter_controle(event_id):

    chave = str(
        event_id
    )

    with _lock:

        controle = _controle_jogos.setdefault(
            chave,
            {
                # ------------------------------------------------
                # PRÉ-LIVE
                # ------------------------------------------------

                "odd_pre_live": None,

                "odd_casa_pre_live": None,

                "odd_visitante_pre_live": None,

                "pre_live_capturada_em": None,

                "pre_live_fallback": False,

                # ------------------------------------------------
                # PRÉ-ENTRADA
                # ------------------------------------------------

                "pre_entrada_emitida": False,

                # ------------------------------------------------
                # ENTRADAS OFICIAIS
                # ------------------------------------------------

                "entradas": [],

                "entrada_ativa": False,

                "padrao_mantido": False,

                # ------------------------------------------------
                # RESULTADO
                # ------------------------------------------------

                "finalizado": False,

                "resultado": None,

                # ------------------------------------------------
                # TRAJETÓRIA
                # ------------------------------------------------

                "trajetoria": [],

                # ------------------------------------------------
                # ÚLTIMO ESTADO
                # ------------------------------------------------

                "ultimo_minuto": 0,

                "ultima_odd": None,

                "ultimo_ipm": 0.0,

                "ultima_variacao_ciclo": 0.0,

                "ultima_variacao_pre_live": 0.0,

                # ------------------------------------------------
                # MIN 45
                # ------------------------------------------------

                "acompanhamento_45": False,

                "ipm_45": None,

                "odd_45": None,

                "variacao_pre_live_45": None,

                "variacao_ciclo_45": None,

                "probabilidade_empate_45": None,

                "min45_sinal": None,
            }
        )

    if not isinstance(
        controle.get("entradas"),
        list
    ):

        controle["entradas"] = []

    if not isinstance(
        controle.get("trajetoria"),
        list
    ):

        controle["trajetoria"] = []

    return controle


# ============================================================
# CLASSIFICAR SINAL IPM
# ============================================================

def classificar_sinal(ipm):

    try:

        valor = float(
            ipm
        )

    except (
        TypeError,
        ValueError
    ):

        valor = 0.0

    if valor >= IPM_MINIMO_MUITO_FORTE:

        return "SINAL MUITO FORTE"

    if valor >= IPM_MINIMO_FORTE:

        return "SINAL FORTE"

    if valor >= IPM_MINIMO_OBSERVACAO:

        return "OBSERVAR"

    return "SEM SINAL"


# ============================================================
# SERVIDOR DE SAÚDE
# ============================================================

class HealthHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        try:

            agora = horario_atual()

            corpo = (
                f"{NOME_BOT} ONLINE | "
                f"Brasil: "
                f"{agora.strftime('%d/%m/%Y %H:%M:%S')} | "
                f"Versao: {VERSAO}"
            ).encode(
                "utf-8"
            )

            self.send_response(
                200
            )

            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(corpo))
            )

            self.end_headers()

            self.wfile.write(
                corpo
            )

        except Exception:

            try:

                self.send_response(
                    500
                )

                self.end_headers()

            except Exception:
                pass

    def log_message(
        self,
        formato,
        *args
    ):

        return


# ============================================================
# INICIAR SERVIDOR DE SAÚDE
# ============================================================

def iniciar_servidor_saude():

    try:

        servidor = HTTPServer(
            (
                "0.0.0.0",
                PORTA_SAUDE
            ),
            HealthHandler
        )

        print(
            "Servidor de saude iniciado na porta",
            PORTA_SAUDE
        )

        servidor.serve_forever()

    except Exception as erro:

        print(
            "ERRO SERVIDOR DE SAUDE:",
            type(erro).__name__,
            erro
        )


# ============================================================
# CAPTURAR REFERÊNCIA PRÉ-LIVE
# ============================================================

def capturar_referencia_pre_live():

    try:

        jogos = (
            buscar_jogos_pre_live()
            or []
        )

        print(
            f"PRE-LIVE ENCONTRADOS: {len(jogos)}"
        )

        if not jogos:
            return

        odds = (
            buscar_odds_multiplos(
                jogos
            )
            or []
        )

        print(
            f"PRE-LIVE ODDS RECEBIDAS: {len(odds)}"
        )

        for jogo in jogos:

            if (
                not isinstance(
                    jogo,
                    dict
                )
                or jogo.get("id") is None
            ):
                continue

            mercados = (
                extrair_mercados(
                    jogo,
                    odds
                )
                or {}
            )

            try:

                odd_casa = float(
                    mercados.get(
                        "odd_casa",
                        0.0
                    )
                    or 0.0
                )

                odd_draw = float(
                    mercados.get(
                        "odd_draw",
                        0.0
                    )
                    or mercados.get(
                        "odd_empate",
                        0.0
                    )
                    or 0.0
                )

                odd_visitante = float(
                    mercados.get(
                        "odd_visitante",
                        0.0
                    )
                    or 0.0
                )

            except (
                TypeError,
                ValueError
            ):
                continue

            if (
                odd_casa <= 0
                and odd_draw <= 0
                and odd_visitante <= 0
            ):

                print(
                    "PRE-LIVE SEM ODDS | "
                    f"{jogo.get('home', '')} x "
                    f"{jogo.get('away', '')}"
                )

                continue

            controle = obter_controle(
                jogo["id"]
            )

            if (
                controle.get(
                    "odd_casa_pre_live"
                ) is None
                and odd_casa > 0
            ):

                controle[
                    "odd_casa_pre_live"
                ] = odd_casa

            if (
                controle.get(
                    "odd_pre_live"
                ) is None
                and odd_draw > 0
            ):

                controle[
                    "odd_pre_live"
                ] = odd_draw

                controle[
                    "pre_live_capturada_em"
                ] = horario_atual().isoformat()

                controle[
                    "pre_live_fallback"
                ] = False

            if (
                controle.get(
                    "odd_visitante_pre_live"
                ) is None
                and odd_visitante > 0
            ):

                controle[
                    "odd_visitante_pre_live"
                ] = odd_visitante

            print(
                "PRE-LIVE | "
                f"{jogo.get('home', '')} x "
                f"{jogo.get('away', '')} | "
                f"CASA={controle.get('odd_casa_pre_live')} | "
                f"EMPATE={controle.get('odd_pre_live')} | "
                f"VISITANTE={controle.get('odd_visitante_pre_live')}"
            )

        salvar_controle()

    except Exception as erro:

        print(
            "ERRO CAPTURA PRE-LIVE:",
            type(erro).__name__,
            erro
                    )



# ============================================================
# REGISTRAR TRAJETÓRIA
# ============================================================

def registrar_trajetoria(
    controle,
    resultado
):

    ponto = {

        "minuto": resultado.get(
            "minuto",
            0
        ),

        "ipm": resultado.get(
            "ipm",
            0.0
        ),

        "odd_casa": resultado.get(
            "odd_casa",
            0.0
        ),

        "odd_empate": resultado.get(
            "odd_empate",
            0.0
        ),

        "odd_visitante": resultado.get(
            "odd_visitante",
            0.0
        ),

        "variacao_casa": resultado.get(
            "variacao_casa",
            0.0
        ),

        "variacao_empate": resultado.get(
            "variacao_empate",
            0.0
        ),

        "variacao_visitante": resultado.get(
            "variacao_visitante",
            0.0
        ),

        "variacao_pre_live": resultado.get(
            "variacao_pre_live",
            0.0
        ),

        "variacao_ciclo": resultado.get(
            "variacao_ciclo",
            0.0
        ),

        # ----------------------------------------------------
        # NOVO
        # ----------------------------------------------------

        "var_10min": resultado.get(
            "var_10min",
            0.0
        ),

        "sinal_pre_entrada": resultado.get(
            "sinal_pre_entrada",
            "NEUTRO"
        ),

        "gols": resultado.get(
            "gols",
            0
        ),
    }

    trajetoria = controle.get(
        "trajetoria",
        []
    )

    if not isinstance(
        trajetoria,
        list
    ):

        trajetoria = []

    # --------------------------------------------------------
    # Se já existe registro do mesmo minuto,
    # substitui pelo mais recente.
    # --------------------------------------------------------

    if (
        trajetoria
        and isinstance(
            trajetoria[-1],
            dict
        )
        and trajetoria[-1].get(
            "minuto"
        ) == ponto["minuto"]
    ):

        trajetoria[-1] = ponto

    else:

        trajetoria.append(
            ponto
        )

    controle[
        "trajetoria"
    ] = trajetoria[-100:]

    # ========================================================
    # MIN 45!!!!!
    # ========================================================

    try:

        minuto = int(
            ponto["minuto"]
        )

    except (
        TypeError,
        ValueError
    ):

        minuto = 0

    if (
        minuto >= 45
        and not controle.get(
            "acompanhamento_45",
            False
        )
    ):

        controle[
            "acompanhamento_45"
        ] = True

        controle[
            "ipm_45"
        ] = ponto[
            "ipm"
        ]

        controle[
            "odd_45"
        ] = ponto[
            "odd_empate"
        ]

        controle[
            "variacao_pre_live_45"
        ] = ponto[
            "variacao_pre_live"
        ]

        controle[
            "variacao_ciclo_45"
        ] = ponto[
            "variacao_ciclo"
        ]

        try:

            odd_45 = float(
                ponto.get(
                    "odd_empate",
                    0.0
                )
                or 0.0
            )

            if odd_45 > 0:

                prob_45 = (
                    100.0
                    / odd_45
                )

            else:

                prob_45 = 0.0

        except (
            TypeError,
            ValueError,
            ZeroDivisionError
        ):

            prob_45 = 0.0

        controle[
            "probabilidade_empate_45"
        ] = prob_45

        if (
            prob_45
            >= MIN45_PROB_BASE
        ):

            controle[
                "min45_sinal"
            ] = "ACIMA_DA_BASE"

        else:

            controle[
                "min45_sinal"
            ] = "ABAIXO_DA_BASE"

        print(
            "MIN 45!!!!! | "
            f"ODD={odd_45:.3f} | "
            f"PROB={prob_45:.2f}% | "
            f"BASE={MIN45_PROB_BASE:.2f}% | "
            f"{controle['min45_sinal']} | "
            f"IPM={ponto.get('ipm', 0.0):.2f} | "
            f"PRE={ponto.get('variacao_pre_live', 0.0):+.2f}% | "
            f"CICLO={ponto.get('variacao_ciclo', 0.0):+.2f}%"
        )


# ============================================================
# PROCESSAR JOGO
# ============================================================

def processar_jogo(
    jogo,
    mercados,
    resultado
):

    event_id = jogo.get(
        "id"
    )

    if event_id is None:
        return

    controle = obter_controle(
        event_id
    )

    # ========================================================
    # DADOS NUMÉRICOS
    # ========================================================

    try:

        minuto = int(
            resultado.get(
                "minuto",
                0
            )
            or 0
        )

    except (
        TypeError,
        ValueError
    ):

        minuto = 0

    try:

        ipm = float(
            resultado.get(
                "ipm",
                0.0
            )
            or 0.0
        )

    except (
        TypeError,
        ValueError
    ):

        ipm = 0.0

    try:

        var_pre = float(
            resultado.get(
                "variacao_pre_live",
                0.0
            )
            or 0.0
        )

    except (
        TypeError,
        ValueError
    ):

        var_pre = 0.0

    try:

        var_ciclo = float(
            resultado.get(
                "variacao_ciclo",
                0.0
            )
            or 0.0
        )

    except (
        TypeError,
        ValueError
    ):

        var_ciclo = 0.0

    try:

        var_10min = float(
            resultado.get(
                "var_10min",
                0.0
            )
            or 0.0
        )

    except (
        TypeError,
        ValueError
    ):

        var_10min = 0.0

    sinal_10min = str(
        resultado.get(
            "sinal_pre_entrada",
            "NEUTRO"
        )
        or "NEUTRO"
    )

    # ========================================================
    # PRÉ-ENTRADA
    #
    # REGRA:
    #
    # odd atual comparada com a odd aproximadamente
    # 10 minutos antes.
    #
    # +20% = ALTA_20
    # -20% = QUEDA_20
    #
    # ISSO NÃO É ENTRADA OFICIAL.
    # ========================================================

    if (
        PRE_ENTRADA_ATIVADA
        and minuto <= PRE_ENTRADA_MINUTO
        and not controle.get(
            "pre_entrada_emitida",
            False
        )
        and (
            var_10min >= PRE_ENTRADA_POSITIVO
            or var_10min <= -PRE_ENTRADA_NEGATIVO
        )
    ):

        controle[
            "pre_entrada_emitida"
        ] = True

        if (
            var_10min
            >= PRE_ENTRADA_POSITIVO
        ):

            direcao_pre = "ALTA"

        else:

            direcao_pre = "QUEDA"

    # ========================================================
    # PRÉ-ENTRADA
    #
    # REGRA:
    #
    # odd atual comparada com a odd aproximadamente
    # 10 minutos antes.
    #
    # +20% = ALTA_20
    # -20% = QUEDA_20
    #
    # ISSO NÃO É ENTRADA OFICIAL.
    # ========================================================

        var_10min = float(
        resultado.get("var_10min", 0.0) or 0.0
    )

    if (
        PRE_ENTRADA_ATIVADA
        and minuto <= PRE_ENTRADA_MINUTO
        and not controle.get("pre_entrada_emitida", False)
        and (
            var_10min >= PRE_ENTRADA_POSITIVO
            or var_10min <= -PRE_ENTRADA_NEGATIVO
        )
        ):

        controle[
            "pre_entrada_emitida"
        ] = True

        if (
            var_10min
            >= PRE_ENTRADA_POSITIVO
        ):

            direcao_pre = "ALTA"

        else:

            direcao_pre = "QUEDA"

        odd_10min = resultado.get(
            "odd_10min"
        )

        if odd_10min is None:
            odd_10min = "N/D"

        enviar_telegram(

            "⚠️ PRÉ-ENTRADA DETECTADA\n\n"

            f"⚽ {jogo.get('home', 'Casa')} x "
            f"{jogo.get('away', 'Fora')}\n"

            f"⏱️ Minuto: {minuto}\n"

            f"💰 Odd 10 min atrás: "
            f"{odd_10min}\n"

            f"💰 Odd atual: "
            f"{resultado.get('odd_atual', 0)}\n"

            f"📊 Variação 10 min: "
            f"{var_10min:+.2f}%\n"

            f"🚨 Movimento: "
            f"{direcao_pre}\n"

            f"📡 Sinal: "
            f"{sinal_10min}\n"

            f"🎯 IPM: "
            f"{ipm:.2f}\n\n"

            "🔎 SINAL DE PRÉ-ENTRADA"
        )

        salvar_controle()

    # ========================================================
    # FINALIZAÇÃO
    # ========================================================

    try:

        if (
            not controle.get(
                "finalizado",
                False
            )
            and jogo_finalizado(
                jogo
            )
        ):

            empate = resultado_empate(
                jogo,
                mercados
            )

            if empate is not None:

                controle[
                    "finalizado"
                ] = True

                controle[
                    "resultado"
                ] = (
                    "VERDE"
                    if empate
                    else "VERMELHO"
                )

                controle[
                    "entrada_ativa"
                ] = False

                for entrada in controle.get(
                    "entradas",
                    []
                ):

                    entrada[
                        "status"
                    ] = controle[
                        "resultado"
                    ]

                placar_casa = 0
                placar_fora = 0

                scores = jogo.get(
                    "scores"
                )

                if isinstance(
                    scores,
                    dict
                ):

                    placar_casa = scores.get(
                        "home",
                        0
                    )

                    placar_fora = scores.get(
                        "away",
                        0
                    )

                enviar_telegram(

                    f"{'🟢' if empate else '🔴'} "
                    "RESULTADO FINAL\n\n"

                    f"⚽ {jogo.get('home', 'Casa')} x "
                    f"{jogo.get('away', 'Fora')}\n"

                    f"📊 Placar: "
                    f"{placar_casa} x "
                    f"{placar_fora}\n"

                    f"📌 "
                    f"{'EMPATE' if empate else 'NAO EMPATE'}"
                )

                salvar_controle()

            return

    except Exception as erro:

        print(
            "ERRO AO FINALIZAR JOGO:",
            type(erro).__name__,
            erro
        )

    # ========================================================
    # TRAJETÓRIA
    # ========================================================

    registrar_trajetoria(
        controle,
        resultado
    )

    controle[
        "ultimo_minuto"
    ] = minuto

    controle[
        "ultima_odd"
    ] = resultado.get(
        "odd_atual"
    )

    controle[
        "ultimo_ipm"
    ] = ipm

    controle[
        "ultima_variacao_ciclo"
    ] = var_ciclo

    controle[
        "ultima_variacao_pre_live"
    ] = var_pre

    # ========================================================
    # ENTRADA OFICIAL
    #
    # ATENÇÃO:
    # Continua independente da pré-entrada.
    # ========================================================

    try:

        pode_entrar = avaliar_entrada(
            resultado,
            minuto,
            IPM_MINIMO_ENTRADA,
            VARIACAO_MINIMA_ODD,
            MINUTO_MINIMO_ENTRADA,
            MINUTO_MAXIMO_ENTRADA
        )

    except Exception as erro:

        print(
            "ERRO AO AVALIAR ENTRADA:",
            type(erro).__name__,
            erro
        )

        pode_entrar = False

    quantidade = len(
        controle.get(
            "entradas",
            []
        )
    )

    if (
        not controle.get(
            "finalizado",
            False
        )
        and quantidade
        < MAX_ENTRADAS_POR_JOGO
        and pode_entrar
    ):

        entrada = {

            "numero":
                quantidade + 1,

            "minuto":
                minuto,

            "odd":
                resultado.get(
                    "odd_atual"
                ),

            "odd_pre_live":
                resultado.get(
                    "odd_pre_live"
                ),

            "ipm":
                ipm,

            "variacao_pre_live":
                var_pre,

            "variacao_ciclo":
                var_ciclo,

            "var_10min":
                var_10min,

            "status":
                "ATIVA",
        }

        controle[
            "entradas"
        ].append(
            entrada
        )

        controle[
            "entrada_ativa"
        ] = True

        controle[
            "padrao_mantido"
        ] = True

        enviar_telegram(

            "🚨 ENTRADA EMPATE\n\n"

            f"⚽ {jogo.get('home', 'Casa')} x "
            f"{jogo.get('away', 'Fora')}\n"

            f"⏱️ Minuto: {minuto}'\n"

            f"💰 Odd pre-live: "
            f"{resultado.get('odd_pre_live')}\n"

            f"💰 Odd atual: "
            f"{resultado.get('odd_atual')}\n"

            f"📉 Pre-live -> atual: "
            f"{var_pre:+.2f}%\n"

            f"🔄 Ultimo ciclo: "
            f"{var_ciclo:+.2f}%\n"

            f"📈 10 min: "
            f"{var_10min:+.2f}%\n"

            f"🎯 IPM: "
            f"{ipm:.2f}\n"

            "🟢 PADRAO CONFIRMADO"
        )

    # ========================================================
    # MARCO 45
    # ========================================================

    if minuto >= 45:

        print(

            "MARCO 45 | "

            f"{jogo.get('home', '')} x "
            f"{jogo.get('away', '')} | "

            f"IPM={ipm:.2f} | "

            f"ODD={resultado.get('odd_atual')} | "

            f"PRE={var_pre:+.2f}% | "

            f"CICLO={var_ciclo:+.2f}% | "

            f"10MIN={var_10min:+.2f}%"
        )

    salvar_controle()


# ============================================================
# EXECUTAR CONSULTA
# ============================================================

def executar_consulta():

    print()

    print(
        "=" * 72
    )

    print(
        "IPM RADAR V5.1 | "
        + horario_atual().strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    )

    print(
        "=" * 72
    )

    # --------------------------------------------------------
    # PRIMEIRO: CAPTURA PRÉ-LIVE
    # --------------------------------------------------------

    capturar_referencia_pre_live()

    # --------------------------------------------------------
    # BUSCAR JOGOS AO VIVO
    # --------------------------------------------------------

    try:

        jogos = (
            buscar_jogos_ao_vivo()
            or []
        )

    except Exception as erro:

        print(
            "ERRO AO BUSCAR JOGOS AO VIVO:",
            type(erro).__name__,
            erro
        )

        return

    print(
        "JOGOS AO VIVO:",
        len(jogos)
    )

    if not jogos:

        print(
            "Nenhum jogo ao vivo neste ciclo."
        )

        return

    jogos = jogos[
        :MAX_JOGOS_RADAR
    ]

    # --------------------------------------------------------
    # BUSCAR ODDS
    # --------------------------------------------------------

    try:

        odds = (
            buscar_odds_multiplos(
                jogos
            )
            or []
        )

    except Exception as erro:

        print(
            "ERRO AO BUSCAR ODDS:",
            type(erro).__name__,
            erro
        )

        odds = []

    print(
        "EVENTOS COM ODDS RECEBIDOS:",
        len(odds)
    )

    # ========================================================
    # PROCESSAR CADA JOGO
    # ========================================================

    for jogo in jogos:

        try:

            if (
                not isinstance(
                    jogo,
                    dict
                )
                or jogo.get("id") is None
            ):

                continue

            event_id = jogo[
                "id"
            ]

            # ------------------------------------------------
            # MERCADOS
            # ------------------------------------------------

            mercados = (
                extrair_mercados(
                    jogo,
                    odds
                )
                or {}
            )

            try:

                odd_casa = float(
                    mercados.get(
                        "odd_casa",
                        0.0
                    )
                    or 0.0
                )

                odd_empate = float(
                    mercados.get(
                        "odd_empate",
                        0.0
                    )
                    or mercados.get(
                        "odd_atual",
                        0.0
                    )
                    or 0.0
                )

                odd_visitante = float(
                    mercados.get(
                        "odd_visitante",
                        0.0
                    )
                    or 0.0
                )

                minuto = int(
                    mercados.get(
                        "minuto",
                        0
                    )
                    or 0
                )

                gols = int(
                    mercados.get(
                        "gols",
                        0
                    )
                    or 0
                )

                escanteios = int(
                    mercados.get(
                        "escanteios",
                        0
                    )
                    or 0
                )

                cartoes = int(
                    mercados.get(
                        "cartoes",
                        0
                    )
                    or 0
                )

                finalizacoes = int(
                    mercados.get(
                        "finalizacoes",
                        0
                    )
                    or 0
                )

                ataques = int(
                    mercados.get(
                        "ataques_perigosos",
                        0
                    )
                    or 0
                )

            except (
                TypeError,
                ValueError
            ):

                print(
                    "ERRO AO CONVERTER DADOS DO JOGO:",
                    event_id
                )

                continue

            # ------------------------------------------------
            # CONTROLE
            # ------------------------------------------------

            controle = obter_controle(
                event_id
            )

            # ------------------------------------------------
            # REFERÊNCIA PRÉ-LIVE
            # ------------------------------------------------

            odd_pre_live = controle.get(
                "odd_pre_live"
            )

            # ------------------------------------------------
            # FALLBACK
            #
            # Só usa a odd atual se realmente não houver
            # referência pré-live capturada.
            # ------------------------------------------------

            if (
                not odd_pre_live
                and odd_empate > 0
            ):

                controle[
                    "odd_pre_live"
                ] = odd_empate

                controle[
                    "pre_live_fallback"
                ] = True

                odd_pre_live = odd_empate

            # =================================================
            # MOTOR IPM
            # =================================================

            resultado = analisar_ipm_com_memoria(

                chave_jogo=event_id,

                odd_atual=odd_empate,

                minuto=minuto,

                gols=gols,

                escanteios=escanteios,

                cartoes=cartoes,

                finalizacoes=finalizacoes,

                ataques_perigosos=ataques,

                odd_pre_live=odd_pre_live,

                odd_casa=odd_casa,

                odd_visitante=odd_visitante,

                odd_casa_pre_live=(
                    controle.get(
                        "odd_casa_pre_live"
                    )
                ),

                odd_visitante_pre_live=(
                    controle.get(
                        "odd_visitante_pre_live"
                    )
                ),
            )

            # =================================================
            # GARANTIR ODDS NO RESULTADO
            # =================================================

            resultado[
                "odd_casa"
            ] = odd_casa

            resultado[
                "odd_empate"
            ] = odd_empate

            resultado[
                "odd_visitante"
            ] = odd_visitante

            resultado[
                "odd_atual"
            ] = odd_empate

            resultado[
                "odd_pre_live"
            ] = odd_pre_live

    # ============================================================
    # DESCOBRIR ODD DE 10 MINUTOS
    # ============================================================

    historico = resultado.get(
        "historico_odds",
        []
    )

    odd_10min = None

    if (
        isinstance(historico, list)
        and minuto >= 10
    ):

        minuto_referencia = (
            minuto - 10
        )

        # Procurar o registro mais próximo
        # dos 10 minutos anteriores
        for registro in reversed(
            historico[:-1]
        ):

            if not isinstance(
                registro,
                dict
            ):
                continue

            try:
                minuto_registro = registro.get(
                    "minuto",
                    -1
                )
            except (
                TypeError,
                ValueError
            ):
                continue

            if (
                minuto_registro <=
                minuto_referencia
            ):

                odd_10min = registro.get(
                    "odd_empate"
                )

                break

    resultado[
        "odd_10min"
    ] = odd_10min


    # ============================================================
    # VARIAÇÃO DA ODD DO EMPATE EM 10 MINUTOS
    # ============================================================

    variacao_10min = 0.0
    sinal_pre_entrada = None

    if (
        odd_10min is not None
        and odd_10min > 0
        and odd_empate > 0
    ):

        variacao_10min = (
            (
                odd_empate - odd_10min
            )
            / odd_10min
        ) * 100

        # ========================================================
        # SINAL DE PRÉ-ENTRADA
        # ========================================================

        if variacao_10min >= 20:
            sinal_pre_entrada = "ALTA_20"

        elif variacao_10min <= -20:
            sinal_pre_entrada = "BAIXA_20"

    resultado[
        "variacao_10min"
    ] = variacao_10min

    resultado[
        "sinal_pre_entrada"
    ] = sinal_pre_entrada

            # =================================================
            # TRAJETÓRIA NO CONSOLE
            # =================================================

            print(

                "TRAJETORIA | "

                f"{jogo.get('home', 'Casa')} x "
                f"{jogo.get('away', 'Fora')} | "

                f"{minuto}' | "

                f"CASA={odd_casa:.3f} | "

                f"EMPATE={odd_empate:.3f} | "

                f"VISITANTE={odd_visitante:.3f} | "

                f"IPM={float(resultado.get('ipm', 0)):.2f} | "

                f"10MIN={float(resultado.get('var_10min', 0)):+.2f}%"
            )

            # =================================================
            # FORMATAR RADAR
            # =================================================

            try:

                texto = formatar_radar(
                    jogo,
                    resultado,
                    mercados
                )

                if texto:

                    print(
                        texto
                    )

                    enviar_telegram(
                        texto
                    )

            except Exception as erro:

                print(
                    "ERRO AO FORMATAR RADAR:",
                    type(erro).__name__,
                    erro
                )

            # =================================================
            # CLASSIFICAÇÃO
            # =================================================

            print(
                "SINAL:",
                classificar_sinal(
                    resultado.get(
                        "ipm",
                        0
                    )
                )
            )

            # =================================================
            # PROCESSAMENTO
            # =================================================

            processar_jogo(
                jogo,
                mercados,
                resultado
            )

        except Exception as erro:

            print(
                "ERRO AO PROCESSAR JOGO:",
                type(erro).__name__,
                erro
            )


# ============================================================
# LOOP PRINCIPAL
# ============================================================

def loop_consulta():

    carregar_controle()

    print(
        f"ROBO INICIADO | "
        f"{NOME_BOT} | "
        f"VERSAO {VERSAO}"
    )

    while True:

        inicio = time.time()

        try:

            if horario_ativo():

                executar_consulta()

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

        decorrido = (
            time.time()
            - inicio
        )

        espera = max(
            1,
            INTERVALO_RADAR
            - decorrido
        )

        print(
            f"PROXIMO CICLO EM "
            f"{espera:.0f}s"
        )

        time.sleep(
            espera
        )


# ============================================================
# INÍCIO
# ============================================================

if __name__ == "__main__":

    print(
        f"INICIANDO "
        f"{NOME_BOT} "
        f"VERSAO {VERSAO}"
    )

    thread_saude = threading.Thread(
        target=iniciar_servidor_saude,
        daemon=True
    )

    thread_saude.start()

    loop_consulta()
