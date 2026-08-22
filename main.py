# ============================================================
# IPM-RADAR-V3
# MAIN.PY
# ROBÔ 2 - RADAR DE MOVIMENTAÇÃO / IPM
# ============================================================
#
# NOVO PADRÃO
#   ATIVO: 06:00 até 00:00
#   PAUSA: 00:00 até 06:00
#   CONSULTA: a cada 300 segundos (5 minutos)
#
# O robô:
#   - consulta jogos ao vivo;
#   - consulta odds;
#   - acompanha movimentação das odds;
#   - calcula IPM;
#   - registra sinais no histórico;
#   - envia sinais ao Telegram;
#   - NÃO realiza apostas.
#
# ============================================================

import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from config import (
    NOME_BOT,
    VERSAO,
    INTERVALO_COLETA,
    INTERVALO_RADAR,
    MAX_JOGOS_RADAR,
    IPM_MINIMO_OBSERVACAO,
    IPM_MINIMO_FORTE,
    IPM_MINIMO_MUITO_FORTE,
    VARIACAO_MINIMA_ODD,
    horario_ativo,
    horario_atual
)

from odds_api import (
    buscar_jogos_ao_vivo,
    buscar_odds_multiplos,
    extrair_mercados
)

from historico import (
    quantidade_jogos,
    registrar_jogo
)

from motor_ipm import (
    calcular_variacao_odd,
    calcular_ipm,
    classificar_forca
)

from telegram import enviar_mensagem


# ============================================================
# MEMÓRIA DAS ODDS
# ============================================================

memoria_odds = {}


# ============================================================
# MEMÓRIA DOS SINAIS ENVIADOS
# ============================================================
#
# Evita mandar a mesma entrada repetidamente em cada ciclo.
#
# ============================================================

sinais_enviados = {}


# ============================================================
# SERVIDOR DE SAÚDE DO RENDER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-type",
            "text/plain; charset=utf-8"
        )

        self.end_headers()

        self.wfile.write(
            b"IPM RADAR V3 ONLINE"
        )

    def log_message(
        self,
        format,
        *args
    ):
        return


def iniciar_servidor():

    porta = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    servidor = HTTPServer(
        (
            "0.0.0.0",
            porta
        ),
        HealthHandler
    )

    print(
        f"Servidor de saúde iniciado na porta {porta}"
    )

    servidor.serve_forever()


# ============================================================
# CLASSIFICAR SINAL
# ============================================================

def classificar_sinal(ipm):

    if ipm >= IPM_MINIMO_MUITO_FORTE:

        return "SINAL MUITO FORTE"

    if ipm >= IPM_MINIMO_FORTE:

        return "SINAL FORTE"

    if ipm >= IPM_MINIMO_OBSERVACAO:

        return "OBSERVAR"

    return "SEM SINAL"


# ============================================================
# ENVIAR ENTRADA PARA TELEGRAM
# ============================================================

def enviar_entrada_telegram(
    jogo,
    mercado,
    linha,
    odd_anterior,
    odd_atual,
    variacao,
    ipm,
    forca,
    sinal
):

    evento_id = jogo.get(
        "id"
    )

    chave = (
        str(evento_id),
        str(mercado),
        str(linha)
    )

    # Só envia sinais considerados relevantes.
    if ipm < IPM_MINIMO_OBSERVACAO:

        return False

    # Não repetir exatamente o mesmo sinal.
    assinatura = (
        round(float(odd_atual), 3),
        round(float(variacao), 2),
        round(float(ipm), 2),
        sinal
    )

    if sinais_enviados.get(
        chave
    ) == assinatura:

        return False

    sinais_enviados[
        chave
    ] = assinatura

    casa = jogo.get(
        "home",
        "Casa"
    )

    fora = jogo.get(
        "away",
        "Fora"
    )

    placar = jogo.get(
        "scores",
        "?"
    )

    campeonato = jogo.get(
        "league",
        ""
    )

    minuto = jogo.get(
        "minute",
        jogo.get(
            "elapsed",
            ""
        )
    )

    mensagem = (
        "🤖 IPM-RADAR V3\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🚨 ENTRADA / SINAL\n\n"
        f"⚽ {casa} x {fora}\n"
        f"🏆 {campeonato}\n"
        f"⏱️ Minuto: {minuto}\n"
        f"📊 Placar: {placar}\n\n"
        f"📌 Mercado: {mercado}\n"
        f"📏 Linha: {linha}\n"
        f"📉 Odd anterior: {odd_anterior:.2f}\n"
        f"📉 Odd atual: {odd_atual:.2f}\n"
        f"📈 Variação: {variacao:+.2f}%\n"
        f"💪 Força: {forca}\n"
        f"🔥 IPM: {ipm:.0f}/100\n"
        f"🎯 {sinal}\n\n"
        "⚠️ Sinal estatístico do radar. "
        "Não realiza aposta automática.\n"
        "━━━━━━━━━━━━━━━━━━"
    )

    sucesso = enviar_mensagem(
        mensagem
    )

    if sucesso:

        print(
            "✅ ENTRADA ENVIADA PARA TELEGRAM"
        )

    return sucesso


# ============================================================
# PROCESSAR MOVIMENTAÇÃO DE UMA ODD
# ============================================================

def processar_movimentacao(
    jogo,
    mercado,
    linha,
    odd_atual
):

    try:

        odd_atual = float(
            odd_atual
        )

    except (
        TypeError,
        ValueError
    ):

        return None

    if odd_atual <= 0:

        return None

    evento_id = jogo.get(
        "id"
    )

    if not evento_id:

        return None

    chave = (
        str(evento_id),
        str(mercado),
        str(linha)
    )

    # Primeira observação.
    if chave not in memoria_odds:

        memoria_odds[
            chave
        ] = odd_atual

        print(
            f"  NOVA ODD | {mercado} | "
            f"Linha: {linha} | "
            f"Odd: {odd_atual:.2f}"
        )

        return None

    odd_anterior = memoria_odds[
        chave
    ]

    memoria_odds[
        chave
    ] = odd_atual

    variacao = calcular_variacao_odd(
        odd_anterior,
        odd_atual
    )

    forca = classificar_forca(
        variacao
    )

    # Para o IPM atual ainda não temos estatísticas
    # adicionais de escanteios/finalizações.
    # Portanto, a movimentação da odd é a confirmação
    # disponível nesta etapa.
    ipm = calcular_ipm(
        variacao_odd=variacao,
        minuto=0,
        gols=0,
        escanteios=0,
        finalizacoes=0,
        ataques_perigosos=0
    )

    sinal = classificar_sinal(
        ipm
    )

    print(
        f"  MOVIMENTO | {mercado} | "
        f"Linha: {linha} | "
        f"{odd_anterior:.2f} -> {odd_atual:.2f} | "
        f"{variacao:+.2f}% | "
        f"IPM {ipm:.2f} | "
        f"{forca}"
    )

    # A variação mínima continua sendo um filtro.
    if abs(variacao) >= VARIACAO_MINIMA_ODD:

        registrar_jogo(
            evento_id=evento_id,
            campeonato=jogo.get(
                "league",
                ""
            ),
            casa=jogo.get(
                "home",
                ""
            ),
            fora=jogo.get(
                "away",
                ""
            ),
            placar=jogo.get(
                "scores",
                ""
            ),
            minuto=jogo.get(
                "minute",
                jogo.get(
                    "elapsed",
                    ""
                )
            ),
            ipm=ipm,
            mercado=mercado,
            odd=odd_atual,
            sinal=sinal,
            linha=linha,
            odd_anterior=odd_anterior,
            variacao_pct=round(
                variacao,
                2
            ),
            direcao=(
                "QUEDA"
                if variacao < -0.05
                else "ALTA"
                if variacao > 0.05
                else "ESTAVEL"
            ),
            forca=forca,
            status=sinal
        )

    # Envia para Telegram somente a partir do nível
    # de observação definido no config.py.
    enviar_entrada_telegram(
        jogo=jogo,
        mercado=mercado,
        linha=linha,
        odd_anterior=odd_anterior,
        odd_atual=odd_atual,
        variacao=variacao,
        ipm=ipm,
        forca=forca,
        sinal=sinal
    )

    return {
        "mercado": mercado,
        "linha": linha,
        "odd_anterior": odd_anterior,
        "odd_atual": odd_atual,
        "variacao_pct": round(
            variacao,
            2
        ),
        "forca": forca,
        "ipm": ipm,
        "sinal": sinal
    }


# ============================================================
# ANALISAR MERCADOS DO JOGO
# ============================================================

def analisar_movimentacao(
    jogo
):

    evento_id = jogo.get(
        "id"
    )

    if not evento_id:

        return

    print()
    print(
        "MOVIMENTAÇÃO DE ODDS"
    )

    # TOTAL GOALS
    for odd in jogo.get(
        "gols",
        []
    ):

        linha = odd.get(
            "linha"
        )

        processar_movimentacao(
            jogo,
            "OVER",
            linha,
            odd.get(
                "over"
            )
        )

        processar_movimentacao(
            jogo,
            "UNDER",
            linha,
            odd.get(
                "under"
            )
        )

    # ASIAN HANDICAP
    for odd in jogo.get(
        "handicap",
        []
    ):

        linha = odd.get(
            "linha"
        )

        processar_movimentacao(
            jogo,
            "HANDICAP_HOME",
            linha,
            odd.get(
                "home"
            )
        )

        processar_movimentacao(
            jogo,
            "HANDICAP_AWAY",
            linha,
            odd.get(
                "away"
            )
        )

    # RESULTADO 1X2
    for odd in jogo.get(
        "resultado",
        []
    ):

        processar_movimentacao(
            jogo,
            "HOME",
            "1X2",
            odd.get(
                "home"
            )
        )

        processar_movimentacao(
            jogo,
            "DRAW",
            "1X2",
            odd.get(
                "draw"
            )
        )

        processar_movimentacao(
            jogo,
            "AWAY",
            "1X2",
            odd.get(
                "away"
            )
        )


# ============================================================
# INICIAR RADAR
# ============================================================

def iniciar():

    print("=" * 60)
    print(NOME_BOT)
    print("VERSÃO:", VERSAO)
    print("=" * 60)

    print(
        "🤖 IPM-RADAR-V3 iniciado."
    )

    print(
        "Histórico registrado:",
        quantidade_jogos()
    )

    print(
        "Funcionamento: 06:00 até 00:00"
    )

    print(
        "Consulta: a cada",
        INTERVALO_COLETA,
        "segundos"
    )

    print()

    while True:

        try:

            # =================================================
            # HORÁRIO
            # =================================================

            if not horario_ativo():

                print(
                    f"🌙 RADAR PAUSADO | "
                    f"{horario_atual().strftime('%H:%M:%S')} | "
                    f"Retorna às 06:00"
                )

                time.sleep(
                    60
                )

                continue

            print()
            print(
                "=" * 60
            )

            print(
                "📡 RADAR ATIVO |",
                horario_atual().strftime(
                    "%d/%m/%Y %H:%M:%S"
                )
            )

            print(
                "=" * 60
            )

            # =================================================
            # 1. JOGOS AO VIVO
            # =================================================

            jogos = buscar_jogos_ao_vivo()

            print(
                "Jogos ao vivo encontrados:",
                len(jogos)
            )

            # Respeita limite configurado.
            if len(jogos) > MAX_JOGOS_RADAR:

                jogos = jogos[
                    :MAX_JOGOS_RADAR
                ]

                print(
                    "Jogos processados:",
                    len(jogos)
                )

            # =================================================
            # 2. ODDS EM LOTE
            # =================================================

            odds_eventos = []

            if jogos:

                odds_eventos = (
                    buscar_odds_multiplos(
                        jogos
                    )
                )

            print(
                "Eventos com odds recebidos:",
                len(odds_eventos)
            )

            # =================================================
            # 3. INDEXAR ODDS POR ID
            # =================================================

            odds_por_id = {}

            for odds_evento in odds_eventos:

                if not isinstance(
                    odds_evento,
                    dict
                ):

                    continue

                evento_id = odds_evento.get(
                    "id"
                )

                if evento_id:

                    odds_por_id[
                        str(evento_id)
                    ] = odds_evento

            # =================================================
            # 4. PROCESSAR JOGOS
            # =================================================

            for jogo in jogos:

                if not isinstance(
                    jogo,
                    dict
                ):

                    continue

                print(
                    "-" * 60
                )

                print(
                    jogo.get("home"),
                    "x",
                    jogo.get("away")
                )

                print(
                    "ID:",
                    jogo.get("id")
                )

                print(
                    "PLACAR:",
                    jogo.get("scores")
                )

                jogo_id = jogo.get(
                    "id"
                )

                odds_evento = odds_por_id.get(
                    str(jogo_id)
                )

                if odds_evento:

                    mercados = (
                        extrair_mercados(
                            odds_evento
                        )
                    )

                    jogo["gols"] = mercados.get(
                        "gols",
                        []
                    )

                    jogo["handicap"] = mercados.get(
                        "handicap",
                        []
                    )

                    jogo["resultado"] = mercados.get(
                        "resultado",
                        []
                    )

                else:

                    jogo["gols"] = []
                    jogo["handicap"] = []
                    jogo["resultado"] = []

                    print(
                        "Nenhuma resposta de odds "
                        "encontrada para este ID."
                    )

                analisar_movimentacao(
                    jogo
                )

            # =================================================
            # DIAGNÓSTICO
            # =================================================

            print()
            print(
                "ODDS NA MEMÓRIA:",
                len(memoria_odds)
            )

            print(
                "SINAIS NA MEMÓRIA:",
                len(sinais_enviados)
            )

            print(
                "HISTÓRICO REGISTRADO:",
                quantidade_jogos()
            )

            print()
            print(
                f"⏳ Nova consulta em "
                f"{INTERVALO_COLETA} segundos..."
            )

            time.sleep(
                INTERVALO_RADAR
            )

        except Exception as erro:

            print()
            print(
                "❌ ERRO NO RADAR:"
            )

            print(
                type(erro).__name__
            )

            print(
                erro
            )

            print(
                "Tentando novamente em 60 segundos..."
            )

            time.sleep(
                60
            )


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    threading.Thread(
        target=iniciar_servidor,
        daemon=True
    ).start()

    iniciar()
    
