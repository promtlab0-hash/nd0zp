import os, sys, json, time, random, requests, subprocess
from io import BytesIO
from urllib.parse import urlencode
from PIL import Image

MODE = os.environ.get("MODE", "single").strip() or "single"
MIN_RATING = 4.7
MIN_FB = 150
MAX_FB = 4000
MAX_PRICE = 2000
DEST = "-1257786"
SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v18/search"
POOL_QUERIES = 10
MAX_POOL = 28
PER_QUERY_CAP = 3
PER_THEME_POOL_CAP = 3
POSTED_FILE = "posted.json"
COOLDOWN_DAYS = 30

THEMES = {
    "хранение": ["органайзер для хранения мелочей","подвесные кармашки для хранения",
                 "разделители для ящиков комода","коробки для хранения вещей складные"],
    "под кроватью": ["ящик под кровать на колесах","вакуумные пакеты для одежды",
                     "кофр для хранения сезонных вещей"],
    "кухня хранение": ["контейнер для специй с дозатором","банки для сыпучих продуктов",
                       "органайзер для крышек от кастрюль"],
    "кухня помощь": ["многоразовые мешочки для овощей","силиконовые формы для заморозки",
                     "гаджеты для кухни экономящие время","измельчитель чеснока ручной"],
    "посуда": ["коврик для сушки посуды","подставка под горячее силиконовая",
               "контейнеры для еды с разделителями"],
    "уют свет": ["гирлянда теплый свет для спальни","ночник проектор звездное небо",
                 "лампа настольная с регулировкой"],
    "уют текстиль": ["коврик с длинным ворсом","плед с рукавами","декоративные наволочки"],
    "отдых": ["подставка для книг для чтения","столик для завтрака в кровать",
              "маска для сна с эффектом 3д"],
    "ароматы": ["аромадиффузор автоматический","саше ароматическое для дома","свеча ароматическая"],
    "красота волосы": ["массажер для кожи головы","силиконовые бигуди без нагрева",
                       "держатель для фена настенный"],
    "красота уход": ["органайзер для косметики вращающийся","зеркало с подсветкой настольное",
                     "роллер для лица","щетка для сухого массажа"],
    "уборка": ["щетка для чистки межплиточных швов","дозатор для моющего средства",
               "скребок для чистки сковород","салфетки из микрофибры набор"],
    "ванная": ["угловая полка в ванную без сверления","держатель для зубных щеток",
               "коврик в ванную быстросохнущий"],
    "дом мелочи": ["магнитная сетка от комаров на дверь","крючки для одежды без сверления",
                   "вещи для маленькой квартиры","органайзер для проводов"],
}
RUBRICS = ["решает мелкое бытовое раздражение","красиво и недорого","неожиданная находка",
           "для маленькой квартиры","экономит время на кухне","для уютного вечера дома"]

GH_TOKEN = os.environ["GH_MODELS_TOKEN"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "@nahodki_do_zp")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "*/*", "Accept-Language": "ru-RU,ru;q=0.9",
    "Origin": "https://www.wildberries.ru", "Referer": "https://www.wildberries.ru/",
}

def load_posted():
    try:
        with open(POSTED_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_posted(posted):
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(posted, f, ensure_ascii=False)
    for cmd in (["git","config","user.name","bot"], ["git","config","user.email","bot@local"],
                ["git","add",POSTED_FILE], ["git","commit","-m","update posted"], ["git","push"]):
        subprocess.run(cmd, check=False)

def is_fresh(nm, posted):
    ts = posted.get(str(nm))
    return True if not ts else (time.time() - ts) > COOLDOWN_DAYS * 86400

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

def collect(posted):
    pool = {}; theme_count = {}; plan = []
    themes = list(THEMES.keys()); random.shuffle(themes)
    iters = {t: iter(random.sample(THEMES[t], len(THEMES[t]))) for t in themes}
    active = list(themes)
    while len(plan) < POOL_QUERIES and active:
        for t in list(active):
            try:
                plan.append((t, next(iters[t])))
                if len(plan) >= POOL_QUERIES: break
            except StopIteration:
                active.remove(t)
    for theme, q in plan:
        added = 0
        for p in wb_search(q):
            rating = p.get("reviewRating") or p.get("rating") or 0
            fb = p.get("feedbacks") or 0
            nm = p.get("id"); price = get_price(p)
            if (rating>=MIN_RATING and MIN_FB<=fb<=MAX_FB and price and price<=MAX_PRICE
                    and nm and is_fresh(nm, posted) and nm not in pool
                    and theme_count.get(theme,0) < PER_THEME_POOL_CAP):
                pool[nm] = {"nmId":nm,"name":(p.get("name") or "")[:80],"brand":p.get("brand",""),
                            "theme":theme,"price":price,"rating":rating,"reviews":fb}
                theme_count[theme] = theme_count.get(theme,0)+1
                added += 1
                if added >= PER_QUERY_CAP: break
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
    return json.loads(txt.replace("```json","").replace("```","").strip())

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
        data={"chat_id":CHAT_ID,"media":json.dumps(media, ensure_ascii=False)}, files=files, timeout=120)

def do_single(cands, rubric, posted):
    sysp=("Ты — редактор уютного Telegram-канала о полезных недорогих товарах для дома, хранения, быта, "
          f"уюта и красоты. Тема: {rubric}. Выбери ОДИН самый цепляющий товар. "
          "Текст: 2-4 тёплых предложения о пользе, без капса и навязчивости, 2-3 эмодзи. "
          'Верни ТОЛЬКО JSON: {"nmId": <число>, "caption": "<текст>"}')
    pick=ai_json(sysp, cands)
    nm=int(pick["nmId"]); cap=(pick.get("caption") or "").strip()
    c={x["nmId"]:x for x in cands}.get(nm)
    if not c or not cap: tg_text("⚠️ ИИ вернул некорректный выбор."); return
    link=f"https://www.wildberries.ru/catalog/{nm}/detail.aspx"
    caption=f"{cap}\n\n💰 {c['price']} ₽ • ⭐ {c['rating']}\n{link}"
    buf=get_image(nm)
    tg_photo(buf, caption) if buf else tg_text(caption)
    posted[str(nm)] = time.time(); save_posted(posted)
    print("Posted single", nm)

def do_gallery(cands, rubric, posted):
    sysp=("Ты — редактор уютного Telegram-канала о полезных недорогих товарах для дома. "
          "У каждого товара есть поле theme. Выбери до 8 лучших товаров и ранжируй от самого интересного, "
          "стараясь охватить РАЗНЫЕ theme. Вступление НЕЙТРАЛЬНОЕ к набору: про подборку полезных находок "
          "для дома в целом, 1-2 предложения, 1-2 эмодзи. К каждому товару — одна короткая строка пользы "
          "(до 12 слов, с эмодзи). "
          'Верни ТОЛЬКО JSON: {"intro":"<текст>","items":[{"nmId":<число>,"line":"<строка>"}]}')
    res=ai_json(sysp, cands)
    by={x["nmId"]:x for x in cands}
    chosen=[]; used=set()
    for it in (res.get("items") or []):
        try: nm=int(it["nmId"])
        except Exception: continue
        c=by.get(nm)
        if not c or c["theme"] in used: continue
        used.add(c["theme"]); chosen.append((nm,(it.get("line") or "").strip(),c))
        if len(chosen)>=5: break
    if len(chosen)<5:
        for c in cands:
            if c["theme"] in used: continue
            used.add(c["theme"]); chosen.append((c["nmId"], c["name"], c))
            if len(chosen)>=5: break
    intro=(res.get("intro") or "Подборка полезных находок для дома 🏡").strip()
    lines=[intro, ""]; photos=[]; n=0; used_nm=[]
    for nm, line, c in chosen:
        buf=get_image(nm)
        if not buf: continue
        n+=1; photos.append(buf); used_nm.append(nm)
        link=f"https://www.wildberries.ru/catalog/{nm}/detail.aspx"
        lines.append(f"{n}. {line} — {c['price']} ₽\n{link}")
    caption="\n".join(lines)
    if len(photos)>=2: tg_album(photos, caption); print("Posted gallery", len(photos))
    elif len(photos)==1: tg_photo(photos[0], caption)
    else: tg_text(caption); return
    for nm in used_nm: posted[str(nm)] = time.time()
    save_posted(posted)

def main():
    posted = load_posted()
    cands=collect(posted)
    print("Candidates:", len(cands), "MODE:", MODE)
    need = 5 if MODE=="gallery" else 3
    if len(cands) < need:
        tg_text(f"⚠️ Мало свежих кандидатов ({len(cands)})."); return
    rubric=random.choice(RUBRICS); print("Rubric:", rubric)
    try:
        do_gallery(cands, rubric, posted) if MODE=="gallery" else do_single(cands, rubric, posted)
    except Exception as e:
        tg_text(f"⚠️ Сбой ({MODE}): {e}"); print("ERROR:", e); raise

main()


