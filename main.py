# ============================================================
# MAIN - IPM RADAR | PRÉ-LIVE REDUZIDO
# ============================================================
#
# Objetivo:
#   - Trabalhar somente a PRÉ-LIVE por enquanto.
#   - Janela mínima: 180 minutos.
#   - Janela configurável para cima.
#   - Q configurável.
#   - Consulta a cada 300 segundos.
#   - Envia a lista aprovada para o Telegram.
#
# O IPM LIVE fica preservado nos demais módulos/projeto.
# Este arquivo não gera entrada e não realiza apostas.
# ============================================================

import os
import time

from config import (
    horario_ativo,
)

from scanner_pre_live import (
    escanear_pre_live,
)

from telegram import (
    enviar_mensagem,
)


# ============================================================
# CONFIGURAÇÕES AJUSTÁVEIS
# ============================================================

INTERVALO_RADAR = int(
    os.getenv(
        "INTERVALO_RADAR",
        "300",
    )
)

PRE_LIVE_JANELA_MINUTOS = max(
    180,
    int(
        os.getenv(
            "PRE_LIVE_JANELA_MINUTOS",
            "180",
        )
    ),
)

Q_MIN = float(
    os.getenv(
        "Q_PRE_LIVE_MINIMO",
        "2.50",
    )
)

Q_MAX = float(
    os.getenv(
        "Q_PRE_LIVE_MAXIMO",
        "3.00",
    )
)

# Telegram aceita mensagens de até 4096 caracteres.
# Usamos uma margem para evitar rejeição.
TELEGRAM_MAX_CARACTERES = 3800


# ============================================================
# MEMÓRIA
# ============================================================

ULTIMA_LISTA = None


# ============================================================
# FILTRAR Q
# ============================================================

def filtrar_por_q(resultados):

    aprovados = []

    for jogo in resultados:

        try:
            q = float(
                jogo.get(
                    "odd_pre_live",
                    jogo.get("q", 0),
                )
                or 0
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if Q_MIN <= q <= Q_MAX:
            aprovados.append(jogo)

    return aprovados


# ============================================================
# FORMATAR UM JOGO
# ============================================================

def formatar_jogo(jogo):

    data = jogo.get(
        "data",
        "",
    )

    casa = jogo.get(
        "casa",
        "Casa",
    )

    fora = jogo.get(
        "fora",
        "Fora",
    )

    horario = jogo.get(
        "horario",
        "--:--",
    )

    odd_casa = float(
        jogo.get(
            "odd_casa",
            0,
        )
        or 0
    )

    odd_empate = float(
        jogo.get(
            "odd_empate",
            0,
        )
        or 0
    )

    odd_visitante = float(
        jogo.get(
            "odd_visitante",
            0,
        )
        or 0
    )

    q = float(
        jogo.get(
            "odd_pre_live",
            jogo.get("q", 0),
        )
        or 0
    )

    prob_x = float(
        jogo.get(
            "probabilidade_x",
            0,
        )
        or 0
    )

    prob_norm = float(
        jogo.get(
            "probabilidade_x_normalizada",
            0,
        )
        or 0
    )

    return [
        data,
        "",
        (
            f"⚽ {horario} | "
            f"{casa} x {fora}"
        ),
        (
            f"🏠 {odd_casa:.2f} | "
            f"🤝 X {odd_empate:.2f} | "
            f"🚌 {odd_visitante:.2f}"
        ),
        f"📐 Q: {q:.2f}",
        f"📊 P(X): {prob_x:.2f}%",
        (
            f"📊 P(X) normalizada: "
            f"{prob_norm:.2f}%"
        ),
    ]


# ============================================================
# MONTAR CABEÇALHO
# ============================================================

def cabecalho_mensagem():

    return [
        "🧪 PRÉ-LIVE — IPM RADAR",
        "",
        (
            f"⏱️ Janela: agora → "
            f"+{PRE_LIVE_JANELA_MINUTOS} min"
        ),
        (
            f"📐 Q: {Q_MIN:.2f} até "
            f"{Q_MAX:.2f}"
        ),
        "",
    ]


# ============================================================
# MONTAR RODAPÉ
# ============================================================

def rodape_mensagem():

    return [
        "",
        "────────────────────",
        (
            "🤖 IPM-RADAR | "
            "OBSERVAÇÃO PRÉ-LIVE"
        ),
        (
            "⚠️ Informação estatística — "
            "não realiza apostas automaticamente."
        ),
    ]


# ============================================================
# DIVIDIR LISTA EM MENSAGENS
# ============================================================

def montar_mensagens(resultados):

    mensagens = []

    linhas = cabecalho_mensagem()
    ultimo_dia = None

    for jogo in resultados:

        bloco = formatar_jogo(jogo)
        data = bloco[0]

        if data != ultimo_dia:

            if ultimo_dia is not None:
                linhas.append("")

            linhas.append(
                f"📅 {data}"
            )

            ultimo_dia = data

        linhas_jogo = bloco[1:]

        candidato = "\n".join(
            linhas + linhas_jogo
        )

        if (
            len(candidato)
            + 250
            > TELEGRAM_MAX_CARACTERES
            and len(linhas) > len(
                cabecalho_mensagem()
            )
        ):

            linhas.extend(
                rodape_mensagem()
            )

            mensagens.append(
                "\n".join(linhas)
            )

            linhas = (
                cabecalho_mensagem()
                + [f"📅 {data}"]
                + linhas_jogo
            )

        else:

            linhas.extend(
                linhas_jogo
            )

    if len(linhas) > len(
        cabecalho_mensagem()
    ):

        linhas.extend(
            rodape_mensagem()
        )

        mensagens.append(
            "\n".join(linhas)
        )

    return mensagens


# ============================================================
# EXECUTAR PRÉ-LIVE
# ============================================================

def executar_pre_live():

    print()
    print("=" * 72)
    print("🧪 PRÉ-LIVE | IPM RADAR")
    print(
        f"JANELA: {PRE_LIVE_JANELA_MINUTOS} MIN"
    )
    print(
        f"Q: {Q_MIN:.2f} → {Q_MAX:.2f}"
    )
    print("=" * 72)

    try:
        resultados = (
            escanear_pre_live()
            or []
        )

    except Exception as erro:

        print(
            "ERRO NO SCANNER PRÉ-LIVE:",
            type(erro).__name__,
            erro,
        )

        return

    aprovados = filtrar_por_q(
        resultados
    )

    print(
        "PRÉ-LIVE ANALISADOS:",
        len(resultados),
    )

    print(
        "PRÉ-LIVE NO Q:",
        len(aprovados),
    )

    if not aprovados:

        print(
            "Nenhum jogo dentro da faixa Q."
        )

        return

    global ULTIMA_LISTA

    assinatura = tuple(
        (
            jogo.get("event_id"),
            jogo.get(
                "odd_pre_live",
                jogo.get("q"),
            ),
            jogo.get("odd_empate"),
        )
        for jogo in aprovados
    )

    if assinatura == ULTIMA_LISTA:

        print(
            "Lista igual à anterior. "
            "Telegram não reenviado."
        )

        return

    mensagens = montar_mensagens(
        aprovados
    )

    print(
        "MENSAGENS TELEGRAM A ENVIAR:",
        len(mensagens),
    )

    enviados = 0

    for numero, mensagem in enumerate(
        mensagens,
        start=1,
    ):

        print(
            f"ENVIANDO TELEGRAM "
            f"{numero}/{len(mensagens)} | "
            f"{len(mensagem)} caracteres"
        )

        sucesso = enviar_mensagem(
            mensagem
        )

        if not sucesso:

            print(
                f"❌ FALHA NA MENSAGEM "
                f"{numero}/{len(mensagens)}."
            )

            return

        enviados += 1

    if enviados == len(mensagens):

        ULTIMA_LISTA = assinatura

        print(
            "✅ LISTA PRÉ-LIVE ENVIADA "
            "COMPLETAMENTE."
        )


# ============================================================
# LOOP
# ============================================================

def loop_consulta():

    print(
        "ROBO INICIADO | "
        "IPM RADAR | PRÉ-LIVE"
    )

    print(
        f"JANELA MÍNIMA: "
        f"{PRE_LIVE_JANELA_MINUTOS} MIN"
    )

    print(
        f"INTERVALO: "
        f"{INTERVALO_RADAR} S"
    )

    while True:

        inicio = time.time()

        try:

            if horario_ativo():
                executar_pre_live()

            else:
                print(
                    "Radar em período de pausa."
                )

        except Exception as erro:

            print(
                "ERRO NO LOOP:",
                type(erro).__name__,
                erro,
            )

        decorrido = (
            time.time() - inicio
        )

        espera = max(
            1,
            INTERVALO_RADAR - decorrido,
        )

        print(
            f"PRÓXIMO CICLO EM "
            f"{espera:.0f}s"
        )

        time.sleep(
            espera
        )


# ============================================================
# INÍCIO
# ============================================================

if __name__ == "__main__":
    loop_consulta()
    
