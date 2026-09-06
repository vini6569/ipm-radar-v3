# ============================================================
# ENVIAR LISTA PRÉ-LIVE
# ============================================================

def enviar_lista_pre_live(
    jogos,
    q_min=2.50,
    q_max=3.00
):

    if not jogos:
        print(
            "⚠️ NENHUM JOGO PRÉ-LIVE PARA ENVIAR."
        )

        return False

    mensagem = (
        "🧪 IPM RADAR — PRÉ-LIVE\n"
        "\n"
        f"📐 Q: {q_min:.2f} até {q_max:.2f}\n"
        "\n"
    )

    periodos = (
        "06:00 - 12:00",
        "12:00 - 18:00",
        "18:00 - 00:00",
    )

    quantidade = 0

    for periodo in periodos:

        jogos_periodo = [
            jogo
            for jogo in jogos
            if jogo.get("periodo") == periodo
        ]

        if not jogos_periodo:
            continue

        mensagem += (
            f"🕐 {periodo}\n"
            "────────────────────\n"
        )

        for jogo in jogos_periodo:

            casa = jogo.get(
                "casa",
                "Casa"
            )

            fora = jogo.get(
                "fora",
                "Fora"
            )

            horario = jogo.get(
                "horario",
                "--:--"
            )

            odd_casa = float(
                jogo.get(
                    "odd_casa",
                    0
                ) or 0
            )

            odd_empate = float(
                jogo.get(
                    "odd_empate",
                    0
                ) or 0
            )

            odd_visitante = float(
                jogo.get(
                    "odd_visitante",
                    0
                ) or 0
            )

            q = float(
                jogo.get(
                    "q",
                    jogo.get(
                        "odd_pre_live",
                        0
                    )
                ) or 0
            )

            prob_x = float(
                jogo.get(
                    "probabilidade_x",
                    0
                ) or 0
            )

            prob_x_normalizada = float(
                jogo.get(
                    "probabilidade_x_normalizada",
                    0
                ) or 0
            )

            mensagem += (
                f"⚽ {horario} | "
                f"{casa} x {fora}\n"
                f"🏠 {odd_casa:.2f} | "
                f"🤝 X {odd_empate:.2f} | "
                f"🚌 {odd_visitante:.2f}\n"
                f"📐 Q: {q:.2f}\n"
                f"📊 P(X): {prob_x:.2f}% | "
                f"P(X) N: "
                f"{prob_x_normalizada:.2f}%\n"
                "\n"
            )

            quantidade += 1

    mensagem += (
        "────────────────────\n"
        f"📋 Jogos selecionados: "
        f"{quantidade}\n"
        "\n"
        "🤖 IPM-RADAR-V3\n"
        "📚 Monitoramento estatístico "
        "pré-live.\n"
        "⚠️ Não realiza apostas automaticamente."
    )

    return enviar_mensagem(
        mensagem
    )
