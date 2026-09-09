# ============================================================
# ENVIAR LISTA PRÉ-LIVE — NOVO PADRÃO
# ============================================================

def enviar_lista_pre_live(
    jogos,
    q_min=None,
    q_max=None
):

    if not jogos:

        print(
            "⚠️ NENHUM JOGO PRÉ-LIVE PARA ENVIAR."
        )

        return False

    if q_min is None:
        q_min = Q_MIN

    if q_max is None:
        q_max = Q_MAX

    mensagem = (
        "🧪 PRÉ-LIVE — IPM RADAR\n"
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

            try:

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

                r = float(
                    jogo.get(
                        "r",
                        0
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

                indice_equilibrio = float(
                    jogo.get(
                        "indice_equilibrio",
                        0
                    ) or 0
                )

            except (
                TypeError,
                ValueError
            ):

                continue

            # ------------------------------------------------
            # FILTRO Q
            # ------------------------------------------------

            if q < q_min or q > q_max:
                continue

            # ------------------------------------------------
            # EQUILÍBRIO / DESEQUILÍBRIO
            # ------------------------------------------------

            equilibrio = indice_equilibrio

            desequilibrio = (
                100.0
                - equilibrio
            )

            # Segurança numérica
            equilibrio = max(
                0.0,
                min(
                    100.0,
                    equilibrio
                )
            )

            desequilibrio = max(
                0.0,
                min(
                    100.0,
                    desequilibrio
                )
            )

            # ------------------------------------------------
            # CLASSIFICAÇÃO
            # ------------------------------------------------

            classificacao = jogo.get(
                "equilibrio",
                "SEM_DADOS"
            )

            padrao = jogo.get(
                "padrao",
                "SEM_DADOS"
            )

            # ------------------------------------------------
            # FORMATAÇÃO DO PADRÃO
            # ------------------------------------------------

            if padrao == "PADRÃO_EMPATE":
                icone_padrao = "🤝"
                texto_padrao = "PADRÃO EMPATE"

            elif padrao == "PADRÃO_GOL":
                icone_padrao = "⚽"
                texto_padrao = "PADRÃO GOL"

            else:
                icone_padrao = "🎯"
                texto_padrao = str(
                    padrao
                )

            # ------------------------------------------------
            # MENSAGEM DO JOGO
            # ------------------------------------------------

            mensagem += (
                f"⚽ {horario} | "
                f"{casa} x {fora}\n"
                "\n"

                f"🏠 Casa: "
                f"{odd_casa:.2f}\n"

                f"🤝 Empate: "
                f"{odd_empate:.2f}\n"

                f"🚌 Visitante: "
                f"{odd_visitante:.2f}\n"
                "\n"

                f"📐 Q: "
                f"{q:.2f}\n"

                f"📊 R: "
                f"{r:.2f}\n"
                "\n"

                f"⚖️ Equilíbrio: "
                f"{equilibrio:.2f}%\n"

                f"⚠️ Desequilíbrio: "
                f"{desequilibrio:.2f}%\n"

                f"🔎 Classificação: "
                f"{classificacao}\n"
                "\n"

                f"{icone_padrao} "
                f"Hipótese: "
                f"{texto_padrao}\n"
                "\n"

                f"📊 P(X): "
                f"{prob_x:.2f}%\n"

                f"📊 P(X) N: "
                f"{prob_x_normalizada:.2f}%\n"

                "\n"
            )

            quantidade += 1

    # --------------------------------------------------------
    # NENHUM JOGO
    # --------------------------------------------------------

    if quantidade == 0:

        print(
            "⚠️ Nenhum jogo dentro "
            "do intervalo Q."
        )

        return False

    # --------------------------------------------------------
    # RODAPÉ
    # --------------------------------------------------------

    mensagem += (
        "────────────────────\n"
        f"📋 Jogos selecionados: "
        f"{quantidade}\n"
        "\n"
        "📌 LEITURA DO RADAR\n"
        "⚖️ Equilíbrio = 100 ÷ R\n"
        "⚠️ Desequilíbrio = 100 − Equilíbrio\n"
        "\n"
        "📚 Monitoramento estatístico "
        "pré-live.\n"
        "\n"
        "🤖 IPM-RADAR-V3\n"
        "⚠️ Não realiza apostas automaticamente."
    )

    return enviar_mensagem(
        mensagem
                )
