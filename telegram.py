# ============================================================
# TELEGRAM - IPM RADAR V5.2
# ============================================================
import os, json, urllib.request, urllib.parse, urllib.error
from config import Q_MIN, Q_MAX

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","").strip()

def enviar_mensagem(mensagem):
    if not TOKEN:
        print("TELEGRAM_BOT_TOKEN não configurado.")
        return False
    chat_id = CHAT_ID
    if not chat_id:
        print("TELEGRAM_CHAT_ID não configurado.")
        return False
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    dados = urllib.parse.urlencode({
        "chat_id":chat_id, "text":str(mensagem), "disable_web_page_preview":True
    }).encode()
    try:
        req = urllib.request.Request(url,data=dados,method="POST")
        req.add_header("Content-Type","application/x-www-form-urlencoded")
        with urllib.request.urlopen(req,timeout=20) as r:
            ok = json.loads(r.read().decode()).get("ok",False)
        print("TELEGRAM | mensagem enviada." if ok else "TELEGRAM | envio recusado.")
        return ok
    except Exception as e:
        print("ERRO TELEGRAM:",type(e).__name__,e)
        return False
