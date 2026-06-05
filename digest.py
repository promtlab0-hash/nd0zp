 os, sys, json, time, random, requests
from io import BytesIO
from urllib.parse import urlencode
from PIL import Image

MODE = os.environ.get("MODE", "single").strip() or "single"
MIN_RATING = 4.7
MIN_FB = 150
MAX_FB = 4000
DEST = "-1257786"
SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v18/search"
POOL_QUERIES = 6
MAX_POOL = 24

QUERY_BANK = [
    "органайзер для хранения мелочей", "подвесные кармашки для хранения",
    "вакуумные пакеты для одежды", "контейнер для специй с дозатором",
    "ящик под кровать на колесах", "разделители для ящиков комода",
    "гирлянда теплый свет для спальни", "аромадиффузор автоматический",
    "ночник проектор звездное небо", "коврик с длинным ворсом",
    "магнитная сетка от комаров на дверь", "угловая полка в ванную без сверления",
    "коврик для сушки посуды", "крючки для одежды без сверления",
    "массажер для кожи головы", "силиконовые бигуди без нагрева",
    "органайзер для косметики вращающийся", "зеркало с подсветкой настольное",
    "щетка для чистки межплиточных швов", "многоразовые мешочки для овощей",
    "силиконовые формы для заморозки", "дозатор для моющего средства",
    "гаджеты для кухни экономящие время", "вещи для маленькой квартиры",
]
RUBRICS = [
    "решает мелкое бытовое раздражение", "красиво и недорого",
    "неожиданная находка, 'а так можно было'", "для маленькой квартиры",
    "экономит время на кухне", "для уютного вечера дома",
]

GH_TOKEN = os.environ["GH_MODELS_TOKEN"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "@nahodki_do_zp")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "*/*", "Accept-Language": "ru-RU,ru;q=0.9",
    "Origin": "https://www.wildberries.ru", "Referer": "https://www.wildberries.ru/",
}

def wb_search(query, tries=3):
    params = {"appType":"1","curr":"rub","dest":DEST,"lang":"ru","page":"1",
              "query":query,"resultset":"catalog","sort":"popular","spp":"30"}
    url = f"{SEARCH_URL}?{urlencode(params)}"
    for i in range(tries):
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            j = r.json(); root = j.get("data") or j
            return root.get("products") or []
        time.sleep(3*(i+1))
    return []

def get_price(p):
    for s in (p.get("sizes") or []):
        pr = s.get("price") or {}
        for k in ("product","total","basic"):
            if pr.get(k): return int(pr[k])//100
    for k in ("salePriceU","priceU"):
        if p.get(k): return int(p[k])//100
    return None

def collect():
    pool = {}
    for q in random.sample(QUERY_BANK, min(POOL_QUERIES, len(QUERY_BANK))):
        for p in wb_search(q):
            rating = p.get("reviewRating") or p.get("rating") or 0
            fb = p.get("feedbacks") or 0
            nm = p.get("id"); price = get_price(p)
            if rating>=MIN_RATING and MIN_FB<=fb<=MAX_FB and nm and price:
                pool[nm] = {"nmId":nm,"name":(p.get("name") or "")[:80],
                            "brand":p.get("brand",""),"subcat":q,
                            "price":price,"rating":rating,"reviews":fb}
        if len(pool) >= MAX_POOL: break
    return list(pool.values())[:MAX_POOL]

def get_image(nm):
    vol = nm//100000; part = nm//1000
    for b in range(1,41):
        url = f"https://basket-{b:02d}.wbbasket.ru/vol{vol}/part{part}/{nm}/images/big/1.webp"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code==200 and r.content:
                img = Image.open(BytesIO(r.content)).convert("RGB")
                buf = BytesIO(); img.save(buf,"JPEG",quality=85); buf.seek(0)
                return buf
        except Exception:
            continue
    return None

def ai_json(system, user_obj):
    body = {"model":"openai/gpt-4o","temperature":0.8,
        "messages":[{"role":"system","content":system},
                    {"role":"user","content":json.dumps(user_obj, ensure_ascii=False)}]}
    r = requests.post("https://models.github.ai/inference/chat/completions",
        headers={"Authorization":f"Bearer {GH_TOKEN}","Content-Type":"application/json",
                 "Accept":"application/vnd.github+json"},
        data=json.dumps(body).encode(), timeout=90)
    r.raise_for_status()
    txt = r.json()["choices"][0]["message"]["content"].strip()
    txt = txt.replace("```json","").replace("```","").strip()
    return json.loads(txt)

def tg_text(t):
    requests.post(f"{API}/sendMessage", data={"chat_id":CHAT_ID,"text":t}, timeout=30)

def tg_photo(buf, caption):
    requests.post(f"{API}/sendPhoto", data={"chat_id":CHAT_ID,"caption":caption[:1000]},
        files={"photo":("p.jpg",buf,"image/jpeg")}, timeout=60)

def tg_album(photos, caption):
    media=[]; files={}
    for i,buf in enumerate(photos):
        key=f"p{i}"; files[key]=(f"{key}.jpg",buf,"image/jpeg")
        m={"type":"photo","media":f"attach://{key}"}
        if i==0: m["caption"]=caption[:1024]
        media.append(m)
    requests.post(f"{API}/sendMediaGroup",
        data={"chat_id":CHAT_ID,"media":json.dumps(media, ensure_ascii=False)},
        files=files, timeout=120)

def do_single(cands, rubric):
    sysp=("Ты — редактор уютного Telegram-канала о полезных товарах для дома, хранения, быта, "
          f"уюта и красоты. Тема: {rubric}. Выбери ОДИН самый цепляющий товар из списка. "
          "Напиши тёплый живой текст 2-4 предложения о пользе в жизни, без капса и навязчивости, 2-3 эмодзи. "
          'Верни ТОЛЬКО JSON без markdown: {"nmId": <число>, "caption": "<текст>"}')
    pick=ai_json(sysp, cands)
    nm=int(pick["nmId"]); cap=(pick.get("caption") or "").strip()
    c={x["nmId"]:x for x in cands}.get(nm)
    if not c or not cap: tg_text("⚠️ ИИ вернул некорректный выбор."); return
    link=f"https://www.wildberries.ru/catalog/{nm}/detail.aspx"
    caption=f"{cap}\n\n💰 {c['price']} ₽ • ⭐ {c['rating']}\n{link}"
    buf=get_image(nm)
    tg_photo(buf, caption) if buf else tg_text(caption)
    print("Posted single", nm)

def do_gallery(cands, rubric):
    sysp=("Ты — редактор уютного Telegram-канала о полезных товарах для дома, хранения, быта, "
          f"уюта и красоты. Тема подборки: {rubric}. Выбери 5 ПО-НАСТОЯЩЕМУ РАЗНЫХ товара "
          "(не больше одного на одну subcat). Напиши короткое тёплое вступление (1-2 предложения, 1-2 эмодзи) "
          "и к каждому товару одну короткую строку пользы (до 12 слов, с эмодзи). "
          'Верни ТОЛЬКО JSON без markdown: {"intro":"<текст>","items":[{"nmId":<число>,"line":"<строка>"}]}')
    res=ai_json(sysp, cands)
    by={x["nmId"]:x for x in cands}
    lines=[(res.get("intro") or "").strip(), ""]
    photos=[]; n=0
    for it in (res.get("items") or [])[:5]:
        try: nm=int(it["nmId"])
        except Exception: continue
        c=by.get(nm)
        if not c: continue
        buf=get_image(nm)
        if not buf: continue
        n+=1; photos.append(buf)
        link=f"https://www.wildberries.ru/catalog/{nm}/detail.aspx"
        lines.append(f"{n}. {(it.get('line') or '').strip()} — {c['price']} ₽\n{link}")
    caption="\n".join(lines)
    if len(photos)>=2: tg_album(photos, caption); print("Posted gallery", len(photos))
    elif len(photos)==1: tg_photo(photos[0], caption)
    else: tg_text(caption)

def main():
    cands=collect()
    print("Candidates:", len(cands), "MODE:", MODE)
    need = 5 if MODE=="gallery" else 3
    if len(cands) < need:
        tg_text(f"⚠️ Мало кандидатов ({len(cands)})."); return
    rubric=random.choice(RUBRICS); print("Rubric:", rubric)
    try:
        do_gallery(cands, rubric) if MODE=="gallery" else do_single(cands, rubric)
    except Exception as e:
        tg_text(f"⚠️ Сбой ({MODE}): {e}"); print("ERROR:", e); raise

main()
