def extrair_mercados(odds_event):
    """Extrai ML, Totals e Handicap da resposta da Odds-API.io."""

    resultado = {
        "resultado": [],
        "gols": [],
        "handicap": []
    }

    if not isinstance(odds_event, dict):
        print("[DIAGNOSTICO] odds_event não é dict")
        return resultado

    bookmakers = odds_event.get("bookmakers", {})

    if not isinstance(bookmakers, dict):
        print("[DIAGNOSTICO] bookmakers não é dict")
        return resultado

    print("[DIAGNOSTICO] Bookmakers recebidos:", list(bookmakers.keys()))

    mercados = bookmakers.get(BOOKMAKER)

    if mercados is None:
        for nome, valor in bookmakers.items():
            if str(nome).strip().lower() == BOOKMAKER.strip().lower():
                mercados = valor
                break

    if not isinstance(mercados, list):
        print("[DIAGNOSTICO] Nenhum mercado encontrado para:", BOOKMAKER)
        return resultado

    print("[DIAGNOSTICO] Quantidade de mercados:", len(mercados))

    for mercado in mercados:

        if not isinstance(mercado, dict):
            continue

        nome = str(mercado.get("name", "")).strip().lower()
        odds = mercado.get("odds", [])

        if not isinstance(odds, list):
            continue

        # RESULTADO 1X2
        if nome in ("ml", "moneyline", "match winner"):

            for odd in odds:
                if not isinstance(odd, dict):
                    continue

                if (
                    odd.get("home") is not None
                    or odd.get("draw") is not None
                    or odd.get("away") is not None
                ):
                    resultado["resultado"].append({
                        "home": odd.get("home"),
                        "draw": odd.get("draw"),
                        "away": odd.get("away")
                    })

        # TOTAL DE GOLS
        elif nome in ("totals", "total goals", "over/under"):

            for odd in odds:
                if not isinstance(odd, dict):
                    continue

                resultado["gols"].append({
                    "linha": odd.get("hdp"),
                    "over": odd.get("over"),
                    "under": odd.get("under")
                })

        # HANDICAP / SPREAD
        elif nome in (
            "spread",
            "asian handicap",
            "asian handicap - 3 way",
            "handicap"
        ):

            for odd in odds:
                if not isinstance(odd, dict):
                    continue

                resultado["handicap"].append({
                    "linha": odd.get("hdp"),
                    "home": odd.get("home"),
                    "away": odd.get("away")
                })

    print(
        "[DIAGNOSTICO] Odds extraídas:",
        "ML =", len(resultado["resultado"]),
        "GOLS =", len(resultado["gols"]),
        "HANDICAP =", len(resultado["handicap"])
    )

    return resultado
```0
