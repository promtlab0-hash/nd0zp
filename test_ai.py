import os, json, urllib.request, urllib.parse

GH_TOKEN = os.environ["GH_MODELS_TOKEN"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "@nahodki_do_zp")

def ai(prompt):
    body = json.dumps({
        "model": "openai/gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }).encode()
    req = urllib.request.Request(
        "https://models.github.ai/inference/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())["choices"][0]["message"]["content"]

def tg(text):
    body = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=body)
    urllib.request.urlopen(req, timeout=30).read()

try:
    reply = ai("Напиши одно тёплое короткое предложение для теста: что ИИ-мозг канала о полезных товарах для дома подключён и готов к работе.")
    print("AI reply:", reply)
    tg("🧠 Тест ИИ: " + reply)
except Exception as e:
    print("ERROR:", e)
    tg(f"⚠️ ИИ не ответил: {e}")
    raise
