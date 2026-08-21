def extrair_mercados(odds_evento):

    resultado = {
        "resultado": [],
        "gols": [],
        "handicap": []
    }

    if not isinstance(odds_evento, dict):
        return resultado

    bookmakers = odds_evento.get("bookmakers", [])

    if not isinstance(bookmakers, list):
        return resultado

    for bookmaker in bookmakers:

        mercados = bookmaker.get("markets", [])

        if not isinstance(mercados, list):
            continue

        for mercado in mercados:

            nome = mercado.get("name")

            # TESTE: mostra exatamente o que a API está retornando
            print("MERCADO ENCONTRADO:", nome)
            print("DADOS DO MERCADO:", mercado)

            outcomes = mercado.get("odds", [])

            if not isinstance(outcomes, list):
                continue

            # ================================
            # RESULTADO 1X2
            # ================================

            if nome == "ML":

                resultado["resultado"].extend(
                    outcomes
                )

            # ================================
            # TOTAL GOALS
            # ================================

            elif nome == "Totals":

                for odd in outcomes:

                    resultado["gols"].append({
                        "linha": odd.get("hdp"),
                        "over": odd.get("over"),
                        "under": odd.get("under")
                    })

            # ================================
            # ASIAN HANDICAP
            # ================================

            elif nome == "Spread":

                for odd in outcomes:

                    resultado["handicap"].append({
                        "linha": odd.get("hdp"),
                        "home": odd.get("home"),
                        "away": odd.get("away")
                    })

    return resultado
    
