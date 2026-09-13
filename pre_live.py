# ============================================================
# IPM RADAR - PRE LIVE
# SOMENTE PRÉ-LIVE
# ============================================================

import os
import time
from config import horario_ativo
from scanner_pre_live import escanear_pre_live
from telegram import enviar_mensagem


INTERVALO = int(
    os.getenv("INTERVALO_PRE_LIVE", "60")
)

Q_MIN = float(
    os.getenv("Q_PRE_LIVE_MINIMO", "2.30")
)

Q_MAX = float(
    os.getenv("Q_PRE_LIVE_MAXIMO", "3.00")
)

MAX_TELEGRAM = 3800

ULTIMA_LISTA = None


# ============================================================
# CONVERSÃO
# ============================================================

def numero(valor, padrao=0.0):

    try:
        if valor in (None, ""):
            return padrao

        return float(valor)

    except (TypeError, ValueError):
        return padrao


# ============================================================
# EQUILÍBRIO
# ============================================================

def equilibrio(r):

    r = numero(r)

    if r <= 0:
        return 0.0, 0.0

    eq = 100.0 / r

    return (
        round(eq, 2),
        round(100.0 - eq, 2)
    )


# ============================================================
# FILTRO Q
# ============================================================

def filtrar(resultados):

    return [

        jogo

        for jogo in resultados

        if Q_MIN
        <= numero(
            jogo.get(
                "odd_pre_live",
                jogo.get("q", 0)
            )
        )
        <= Q_MAX

    ]


# ============================================================
# MENSAGENS
# ============================================================

def montar_mensagens(resultados):

    mensagens = []

    linhas = [

        "⚽ PRE-LIVE - IPM RADAR",

        "",

        f"📐 Q: {Q_MIN:.2f} ate {Q_MAX:.2f}",

        "📊 R = desequilibrio entre as pontas",

        "⚖️ Equilibrio = 100 / R",

        "⚠️ Desequilibrio = 100 - Equilibrio",

        "",

    ]

    ultimo_dia = None

    for jogo in resultados:

        data = jogo.get("data", "")

        if data != ultimo_dia:

            if ultimo_dia is not None:
                linhas.append("")

            linhas.append(
                f"📅 Data: {data}"
            )

            ultimo_dia = data

        casa = numero(
            jogo.get("odd_casa")
        )

        empate = numero(
            jogo.get("odd_empate")
        )

        fora = numero(
            jogo.get("odd_visitante")
        )

        q = numero(
            jogo.get("q")
        )

        r = numero(
            jogo.get("r")
        )

        prob = numero(
            jogo.get("probabilidade_x")
        )

        prob_n = numero(
            jogo.get(
                "probabilidade_x_normalizada"
            )
        )

        eq, deseq = equilibrio(r)

        linhas.extend([

            f"⚽ {jogo.get('horario', '--:--')} | "
            f"{jogo.get('casa', 'Casa')} x "
            f"{jogo.get('fora', 'Fora')}",

            f"🏠 Casa {casa:.2f} | "
            f"🤝 X {empate:.2f} | "
            f"🚌 Visitante {fora:.2f}",

            f"📐 Q: {q:.2f}",

            f"📊 R: {r:.2f}",

            f"⚖️ Equilibrio: {eq:.2f}%",

            f"⚠️ Desequilibrio: {deseq:.2f}%",

            f"🎯 Estrutura: "
            f"{jogo.get('equilibrio', 'NAO CLASSIFICADO')}",

            f"🧭 Padrao: "
            f"{jogo.get('padrao', 'NAO CLASSIFICADO')}",

            f"📊 P(X): {prob:.2f}% | "
            f"P(X) N: {prob_n:.2f}%",

            "",

        ])

        if len("\n".join(linhas)) > MAX_TELEGRAM:

            mensagens.append(
                "\n".join(linhas[:-10])
            )

            linhas = [
                "⚽ PRE-LIVE - IPM RADAR",
                "",
                f"📐 Q: {Q_MIN:.2f} ate {Q_MAX:.2f}",
                "",
                f"📅 Data: {data}",
            ]

            linhas.extend([

                f"⚽ {jogo.get('horario', '--:--')} | "
                f"{jogo.get('casa', 'Casa')} x "
                f"{jogo.get('fora', 'Fora')}",

                f"🏠 Casa {casa:.2f} | "
                f"🤝 X {empate:.2f} | "
                f"🚌 Visitante {fora:.2f}",

                f"📐 Q: {q:.2f}",
                f"📊 R: {r:.2f}",
                f"⚖️ Equilibrio: {eq:.2f}%",
                f"⚠️ Desequilibrio: {deseq:.2f}%",

                f"🎯 Estrutura: "
                f"{jogo.get('equilibrio', 'NAO CLASSIFICADO')}",

                f"🧭 Padrao: "
                f"{jogo.get('padrao', 'NAO CLASSIFICADO')}",

                f"📊 P(X): {prob:.2f}% | "
                f"P(X) N: {prob_n:.2f}%",

                "",

            ])

    if len(linhas) > 7:

        linhas.extend([

            "--------------------",

            f"📋 Jogos selecionados: "
            f"{len(resultados)}",

            "",

            "🤖 IPM-RADAR",

            "🧪 Monitoramento estatistico pre-live.",

        ])

        mensagens.append(
            "\n".join(linhas)
        )

    return mensagens


# ============================================================
# CICLO PRÉ-LIVE
# ============================================================

def executar():

    global ULTIMA_LISTA

    print("\n" + "=" * 60)
    print("PRE-LIVE | IPM RADAR")
    print(f"Q: {Q_MIN:.2f} -> {Q_MAX:.2f}")
    print("=" * 60)

    try:
        resultados = escanear_pre_live() or []

    except Exception as erro:

        print(
            "ERRO SCANNER:",
            type(erro).__name__,
            erro
        )

        return

    aprovados = filtrar(resultados)

    print(
        "JOGOS APROVADOS:",
        len(aprovados)
    )

    if not aprovados:
        return

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
            "PRE-LIVE | LISTA SEM ALTERACAO"
        )

        return

    for mensagem in montar_mensagens(aprovados):

        if enviar_mensagem(mensagem):

            print(
                "PRE-LIVE | LISTA ENVIADA"
            )

    ULTIMA_LISTA = assinatura


# ============================================================
# LOOP
# ============================================================

def main():

    print("IPM RADAR - PRE-LIVE INICIADO")
    print(f"INTERVALO: {INTERVALO}s")

    while True:

        inicio = time.time()

        try:

            if horario_ativo():
                executar()
            else:
                print(
                    "PRE-LIVE | Periodo de pausa."
                )

        except Exception as erro:

            print(
                "ERRO PRE-LIVE:",
                type(erro).__name__,
                erro
            )

        espera = max(
            1,
            INTERVALO - (
                time.time() - inicio
            )
        )

        time.sleep(espera)


if __name__ == "__main__":
    main()
