_memoria = {}

def _num(v, default=0.0):
    try:
        return default if v in (None, "") else float(v)
    except (TypeError, ValueError):
        return default

def calcular_variacao_odd(anterior, atual):
    anterior, atual = _num(anterior), _num(atual)
    if anterior <= 0 or atual <= 0:
        return 0.0
    return ((atual - anterior) / anterior) * 100.0

def classificar_forca(v):
    v = abs(_num(v))
    if v >= 10: return "MUITO FORTE"
    if v >= 5: return "FORTE"
    if v >= 2: return "MODERADO"
    if v >= 0.5: return "FRACO"
    return "ESTAVEL"

def classificar_direcao(v):
    v = _num(v)
    if v < -0.05: return "QUEDA"
    if v > 0.05: return "ALTA"
    return "ESTAVEL"

def analisar_movimento(evento_id, periodo, mercado, linha, selecao, odd_atual):
    atual = _num(odd_atual)
    chave = (str(evento_id), str(periodo), str(mercado), str(linha), str(selecao))
    anterior = _memoria.get(chave)
    if atual <= 0:
        return {"odd_anterior": anterior, "odd_atual": atual, "variacao": 0.0,
                "primeira_consulta": False, "direcao": "ESTAVEL", "forca": "ESTAVEL"}
    if anterior is None:
        _memoria[chave] = atual
        return {"odd_anterior": None, "odd_atual": atual, "variacao": 0.0,
                "primeira_consulta": True, "direcao": "REFERENCIA", "forca": "ESTAVEL"}
    variacao = calcular_variacao_odd(anterior, atual)
    _memoria[chave] = atual
    return {"odd_anterior": anterior, "odd_atual": atual,
            "variacao": round(variacao, 4), "primeira_consulta": False,
            "direcao": classificar_direcao(variacao),
            "forca": classificar_forca(variacao)}

def calcular_ipm(movimentacao=0, minuto=0, gols=0, escanteios=0, cartoes=0,
                 finalizacoes=0, ataques_perigosos=0, **kwargs):
    movimento = min(abs(_num(movimentacao)) * 5, 60)
    gols = min(max(int(_num(gols)), 0) * 5, 10)
    esc = min(max(int(_num(escanteios)), 0) * 1.5, 10)
    cart = min(max(int(_num(cartoes)), 0), 10)
    fin = min(max(int(_num(finalizacoes)), 0) * 0.5, 10)
    ata = min(max(int(_num(ataques_perigosos)), 0) * 0.2, 10)
    return {"ipm": round(min(100, movimento + gols + esc + cart + fin + ata), 2),
            "movimento": round(movimento, 2),
            "forca": classificar_forca(movimentacao),
            "direcao": classificar_direcao(movimentacao)}
