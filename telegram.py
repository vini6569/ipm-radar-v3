import os,json,urllib.request,urllib.parse,urllib.error
from config import Q_MIN,Q_MAX
TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","").strip()
CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","").strip()

def n(v,d=0.0):
    try:return d if v in (None,"") else float(v)
    except:return d
def enviar_mensagem(msg):
    if not TOKEN:return False
    cid=CHAT_ID
    if not cid:
        u=f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        try:
            r=json.loads(urllib.request.urlopen(u,timeout=20).read().decode())
            for x in reversed(r.get("result",[])):
                c=x.get("message",{}).get("chat",{}).get("id")
                if c:cid=str(c);break
        except Exception as e:print("ERRO TELEGRAM:",e)
    if not cid:return False
    try:
        u=f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        d=urllib.parse.urlencode({"chat_id":cid,"text":str(msg),"disable_web_page_preview":True}).encode()
        r=urllib.request.urlopen(urllib.request.Request(u,data=d,method="POST"),timeout=20)
        return json.loads(r.read().decode()).get("ok",False)
    except Exception as e:print("ERRO TELEGRAM:",e);return False

def enviar_entrada(casa,fora,placar,minuto,mercado,linha,odd_anterior,odd_atual,variacao,forca,ipm,sinal):
    return enviar_mensagem(f"🚨 IPM RADAR — ENTRADA\n\n⚽ {casa} x {fora}\n📊 Placar: {placar}\n⏱️ Minuto: {minuto}\n\n🎯 Mercado: {mercado}\n📏 Linha: {linha}\n📉 Odd: {odd_anterior:.2f} → {odd_atual:.2f}\n📈 Variação: {variacao:+.2f}%\n🔥 Força: {forca}\n🧠 IPM: {ipm:.0f}/100\n🚦 {sinal}\n\n🤖 IPM-RADAR-V3\n⚠️ Informação estatística — não realiza apostas automaticamente.")

def enviar_ciclo(casa,fora,placar_final,resultado,gols_total,dados=None):
    m=f"🏁 CICLO FINALIZADO\n\n⚽ {casa} x {fora}\n🏆 Placar final: {placar_final}\n🎯 Resultado: {resultado}\n⚽ Total de gols: {gols_total}"
    if isinstance(dados,dict):
        if dados.get("ipm") is not None:m+=f"\n\n🧠 IPM registrado: {dados['ipm']}"
        if dados.get("mercado"):m+=f"\n🎯 Mercado: {dados['mercado']}"
        if dados.get("odd"):m+=f"\n💰 Odd: {dados['odd']}"
    return enviar_mensagem(m+"\n\n📚 Resultado enviado para o laboratório IPM.\n🤖 IPM-RADAR-V3")

def enviar_relatorio(texto):return enviar_mensagem(f"📊 RELATÓRIO — LABORATÓRIO IPM\n\n{texto}\n\n🤖 IPM-RADAR-V3")

def enviar_lista_pre_live(jogos,q_min=None,q_max=None):
    if not jogos:return False
    q_min=Q_MIN if q_min is None else q_min;q_max=Q_MAX if q_max is None else q_max
    m=f"🧪 PRÉ-LIVE — IPM RADAR\n\n📐 Q: {q_min:.2f} até {q_max:.2f}\n📊 R = maior odd / menor odd\n⚖️ Equilíbrio = 100 / R\n\n"
    qtd=0
    for p in ("06:00 - 12:00","12:00 - 18:00","18:00 - 00:00"):
        grupo=[j for j in jogos if j.get("periodo")==p and q_min<=n(j.get("q"))<=q_max]
        if not grupo:continue
        m+=f"🕐 {p}\n────────────────────\n"
        for j in grupo:
            r=n(j.get("r"));eq=100/r if r else 0;de=100-eq
            m+=f"⚽ {j.get('horario','--:--')} | {j.get('casa','Casa')} x {j.get('fora','Fora')}\n🏠 {n(j.get('odd_casa')):.2f} | 🤝 X {n(j.get('odd_empate')):.2f} | 🚌 {n(j.get('odd_visitante')):.2f}\n📐 Q: {n(j.get('q')):.2f} | 📊 R: {r:.2f}\n⚖️ Equilíbrio: {eq:.2f}% | ⚠️ Desequilíbrio: {de:.2f}%\n🎯 Estrutura: {j.get('equilibrio','NÃO CLASSIFICADO')}\n🧭 Padrão: {j.get('padrao','NÃO CLASSIFICADO')}\n📊 P(X): {n(j.get('probabilidade_x')):.2f}% | P(X) N: {n(j.get('probabilidade_x_normalizada')):.2f}%\n\n";qtd+=1
    return enviar_mensagem(m+f"────────────────────\n📋 Jogos selecionados: {qtd}\n\n🤖 IPM-RADAR-V3\n📚 Monitoramento estatístico pré-live.\n⚠️ Não realiza apostas automaticamente.")

def teste_telegram():return enviar_mensagem("🧪 TESTE DO TELEGRAM — IPM RADAR V3\n\n✅ Robô conectado ao Telegram.\n📡 Comunicação funcionando.\n📊 Radar IPM V3 online.\n\nAguardando as entradas do Radar.")

if __name__=="__main__":print("TELEGRAM:", "OK" if teste_telegram() else "FALHOU")
