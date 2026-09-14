# ============================================================
# CONFIG.PY — Q PRÉ-LIVE AJUSTÁVEL
# ============================================================
#
# COLOQUE estas duas linhas no config.py.
#
# Futuramente, para alterar o filtro Q, basta mudar no Render:
#
# Q_PRE_LIVE_MINIMO
# Q_PRE_LIVE_MAXIMO
#
# Exemplo:
#
# Q_PRE_LIVE_MINIMO = 2.00
# Q_PRE_LIVE_MAXIMO = 3.00
#
# O scanner_pre_live.py, pre_live.py e telegram.py
# passam a usar os mesmos valores.
# ============================================================

Q_MIN = float(
    os.getenv("Q_PRE_LIVE_MINIMO", "2.00")
)

Q_MAX = float(
    os.getenv("Q_PRE_LIVE_MAXIMO", "3.00")
)
