# ============================================================
# EVENTO ODDS POR ID
# ============================================================

def _evento_odds_por_id(
    odds,
    event_id
):

    if event_id is None:
        return None

    alvo = str(event_id).strip()

    # --------------------------------------------------------
    # LISTA
    # --------------------------------------------------------

    if isinstance(odds, list):

        for item in odds:

            if not isinstance(item, dict):
                continue

            item_id = item.get("id")

            if item_id is not None:

                if str(item_id).strip() == alvo:

                    return item

    # --------------------------------------------------------
    # DICIONÁRIO
    # --------------------------------------------------------

    if isinstance(odds, dict):

        # O próprio objeto é o evento
        if odds.get("id") is not None:

            if str(
                odds.get("id")
            ).strip() == alvo:

                return odds

        # Evento indexado pelo ID
        for chave, valor in odds.items():

            if str(chave).strip() == alvo:

                if isinstance(valor, dict):

                    return valor

    return None
