# ============================================================
# FORMATAR LISTA PRÉ-LIVE — NOVO PADRÃO
# ============================================================

def montar_mensagens(resultados):

    mensagens = []

    linhas = [
        "🧪 PRÉ-LIVE — IPM RADAR",
        "",
        "📡 MAPA ESTRUTURAL DO RADAR",
        "",
        f"📐 Q: {Q_MIN:.2f} até {Q_MAX:.2f}",
        "",
        "📊 R = relação entre as duas pontas",
        "⚖️ Equilíbrio = classificação do R",
        "📊 Índice = valor estrutural do equilíbrio",
        "🎯 Hipótese = padrão indicado pelo R",
        "",
    ]

    ultimo_dia = None

    for jogo in resultados:

        try:

            odd_casa = float(
                jogo.get("odd_casa", 0) or 0
            )

            odd_empate = float(
                jogo.get("odd_empate", 0) or 0
            )

            odd_visitante = float(
                jogo.get("odd_visitante", 0) or 0
            )

            q = float(
                jogo.get(
                    "q",
                    jogo.get("odd_pre_live", 0)
                ) or 0
            )

            r = float(
                jogo.get("r", 0) or 0
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

        # ----------------------------------------------------
        # DADOS ESTRUTURAIS
        # ----------------------------------------------------

        equilibrio = jogo.get(
            "equilibrio",
            "SEM_DADOS"
        )

        padrao = jogo.get(
            "padrao",
            "SEM_DADOS"
        )

        data = jogo.get(
            "data",
            ""
        )

        horario = jogo.get(
            "horario",
            "--:--"
        )

        casa = jogo.get(
            "casa",
            "Casa"
        )

        fora = jogo.get(
            "fora",
            "Fora"
        )

        # ----------------------------------------------------
        # INTERPRETAÇÃO VISUAL
        # ----------------------------------------------------

        if "DESEQUILÍBRIO" in equilibrio:

            indicador = "⚠️ DESEQUILIBRADO"

        else:

            indicador = "⚖️ EQUILIBRADO"

        # ----------------------------------------------------
        # DATA
        # ----------------------------------------------------

        if data != ultimo_dia:

            if ultimo_dia is not None:

                linhas.append("")

            linhas.append(
                f"📅 {data}"
            )

            ultimo_dia = data

        # ----------------------------------------------------
        # JOGO
        # ----------------------------------------------------

        bloco = [
            "",
            (
                f"⚽ {horario} | "
                f"{casa} x {fora}"
            ),
            "",
            (
                f"🏠 Casa: "
                f"{odd_casa:.2f}"
            ),
            (
                f"🤝 Empate (X): "
                f"{odd_empate:.2f}"
            ),
            (
                f"🚌 Visitante: "
                f"{odd_visitante:.2f}"
            ),
            "",
            (
                f"📐 Q: "
                f"{q:.2f}"
            ),
            (
                f"📊 R: "
                f"{r:.2f}"
            ),
            "",
            (
                f"⚖️ Equilíbrio: "
                f"{equilibrio}"
            ),
            (
                f"📊 Valor do equilíbrio: "
                f"{indice_equilibrio:.2f}/100"
            ),
            (
                f"⚠️ Desequilíbrio: "
                f"{indicador}"
            ),
            "",
            (
                f"🎯 Hipótese: "
                f"{padrao}"
            ),
            "",
            (
                f"📊 P(X): "
                f"{prob_x:.2f}%"
            ),
            (
                f"📊 P(X) N: "
                f"{prob_x_normalizada:.2f}%"
            ),
            "",
            "🧪 LEITURA IPM",
            (
                f"Q dentro da faixa "
                f"{Q_MIN:.2f}–{Q_MAX:.2f}."
            ),
            (
                f"R = {r:.2f} → "
                f"{equilibrio}."
            ),
            (
                f"Índice de equilíbrio = "
                f"{indice_equilibrio:.2f}/100."
            ),
            (
                "Este índice é estrutural "
                "e não representa probabilidade."
            ),
            "",
            "────────────────────",
        ]

        # ----------------------------------------------------
        # CONTROLE DO TAMANHO DO TELEGRAM
        # ----------------------------------------------------

        texto_bloco = "\n".join(
            bloco
        )

        texto_atual = "\n".join(
            linhas
        )

        if (
            len(texto_atual)
            + len(texto_bloco)
            > 3500
        ):

            mensagens.append(
                texto_atual
            )

            linhas = [
                "🧪 PRÉ-LIVE — IPM RADAR",
                "",
                f"📐 Q: "
                f"{Q_MIN:.2f} até "
                f"{Q_MAX:.2f}",
                "",
            ]

            linhas.extend(
                bloco
            )

        else:

            linhas.extend(
                bloco
            )

    # --------------------------------------------------------
    # FINALIZAR
    # --------------------------------------------------------

    if len(linhas) > 4:

        linhas.extend(
            [
                "",
                "📚 LABORATÓRIO IPM",
                "",
                "O pré-live identifica "
                "a estrutura estatística "
                "das partidas.",
                "",
                "⚠️ Não representa entrada "
                "e não realiza apostas "
                "automaticamente.",
                "",
                "🤖 IPM-RADAR-V5",
            ]
        )

        mensagens.append(
            "\n".join(linhas)
        )

    return mensagens
