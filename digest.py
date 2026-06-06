import os, sys, json, time, random, requests, subprocess, re
from io import BytesIO
from urllib.parse import urlencode
from PIL import Image

MIN_RATING = 4.7
MIN_FB = 150
MAX_FB = 4000
MAX_PRICE = 3000
DEST = "-1257786"
SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v18/search"
POOL_QUERIES = 14
MAX_POOL = 28
PER_QUERY_CAP = 2
PER_THEME_POOL_CAP = 1
POSTED_FILE = "posted.json"
DONE_FILE = "done.json"
STATE_FILE = "state.json"
COOLDOWN_DAYS = 30
MODELS = ["openai/gpt-4o", "openai/gpt-4o-mini"]
LAST_ATTEMPT = 4
STYLE_MEMORY = 3

SCHEDULE_MAP = {
    "30 5 * * *": ("morning","single",1), "50 5 * * *": ("morning","single",2),
    "10 6 * * *": ("morning","single",3), "30 6 * * *": ("morning","single",4),
    "0 10 * * *": ("noon","single",1), "20 10 * * *": ("noon","single",2),
    "40 10 * * *": ("noon","single",3), "0 11 * * *": ("noon","single",4),
    "0 18 * * *": ("evening","gallery",1), "20 18 * * *": ("evening","gallery",2),
    "40 18 * * *": ("evening","gallery",3), "0 19 * * *": ("evening","gallery",4),
}

THEMES = {
    "органайзеры": ["органайзер для хранения мелочей","разделители для ящиков комода"],
    "коробки": ["коробки для хранения вещей складные","корзина для белья складная"],
    "под кроватью": ["ящик под кровать на колесах","кофр для хранения сезонных вещей"],
    "вакуум": ["вакуумные пакеты для одежды"],
    "вешалки": ["вешалки плечики бархатные","органайзер для сумок в шкаф"],
    "обувь хранение": ["органайзер для обуви","коробки для обуви прозрачные"],
    "специи": ["контейнер для специй с дозатором","банки для сыпучих продуктов"],
    "кухонные гаджеты": ["измельчитель чеснока ручной","овощечистка экономка","открывашка для банок"],
    "нарезка": ["доска разделочная с контейнерами","терка многофункциональная"],
    "заморозка": ["силиконовые формы для заморозки","контейнеры для еды с разделителями"],
    "выпечка": ["силиконовый коврик для выпечки","форма для кексов силиконовая"],
    "посуда уход": ["коврик для сушки посуды","подставка под горячее силиконовая"],
    "ланч": ["ланч бокс с разделами","термокружка с крышкой"],
    "напитки": ["бутылка для воды мотивационная","заварочный чайник стеклянный"],
    "свет": ["гирлянда теплый свет для спальни","ночник проектор звездное небо","лампа настольная"],
    "текстиль": ["коврик с длинным ворсом","плед с рукавами","декоративные наволочки"],
    "шторы декор": ["шторы блэкаут для спальни","подхваты для штор магнитные"],
    "сон отдых": ["подставка для книг для чтения","столик для завтрака в кровать","маска для сна 3д"],
    "ароматы": ["аромадиффузор автоматический","свеча ароматическая","саше для шкафа"],
    "уход за одеждой": ["отпариватель ручной для одежды","машинка для удаления катышков"],
    "стирка": ["мешки для стирки белья набор","сортер для белья трехсекционный"],
    "волосы": ["массажер для кожи головы","силиконовые бигуди без нагрева","расческа массажная"],
    "укладка": ["заколки крабики набор","резинки для волос спиральные","повязка для умывания"],
    "косметика хранение": ["органайзер для косметики вращающийся","зеркало с подсветкой настольное"],
    "кисти уход": ["держатель для кистей макияжа","спонж для макияжа набор"],
    "уход тело": ["роллер для лица","щетка для сухого массажа","массажер для ног"],
    "маникюр": ["набор для маникюра","лампа для сушки ногтей"],
    "уборка кухня": ["скребок для чистки сковород","щетка для чистки межплиточных швов"],
    "уборка тряпки": ["салфетки из микрофибры набор","швабра с отжимом"],
    "уборка ванной": ["щетка для унитаза силиконовая","спрей для чистки сантехники"],
    "пыль": ["щетка для пыли гибкая","набор для мытья окон со сгоном"],
    "ванная": ["угловая полка в ванную без сверления","коврик в ванную быстросохнущий","держатель для зубных щеток"],
    "ванная мелочи": ["дозатор для мыла автоматический","стакан для зубных щеток настенный"],
    "крючки": ["крючки для одежды без сверления","вешалка органайзер для шарфов"],
    "провода": ["органайзер для проводов","держатель для телефона настольный"],
    "от насекомых": ["магнитная сетка от комаров на дверь","ловушка для мошек"],
    "эко": ["многоразовые мешочки для овощей","экомешочки для хранения"],
    "растения": ["кашпо для цветов подвесное","лейка для комнатных растений"],
    "прихожая": ["ключница настенная органайзер","полка для обуви узкая"],
    "рабочее место": ["подставка для ноутбука складная","органайзер для канцелярии"],
    "документы": ["папка органайзер для документов","шкатулка для мелочей"],
    "питомцы": ["лежанка для кошки мягкая","коврик под миску для животных"],
    "дети уют": ["ночник детский силиконовый","корзина для игрушек складная"],
    "праздник": ["свечи для торта тонкие","подарочная упаковка набор"],
    "путешествия": ["органайзеры для чемодана набор","косметичка дорожная подвесная"],
    "авто уют": ["органайзер в машину между сиденьями","держатель для телефона в авто"],
    "погода": ["сушилка для белья складная","зонт автомат компактный"],
    "тепло": ["грелка для рук электрическая","теплые носки домашние"],
    "технологии быт": ["увлажнитель воздуха для дома","ручной пылесос беспроводной"],
    "мелочи кухни": ["держатель для бумажных полотенец","подставка для крышек"],
}
RUBRICS = ["решает мелкое бытовое раздражение","красиво и недорого","неожиданная находка","для маленькой квартиры","экономит время на кухне","для уютного вечера дома"]
STYLES = [
    "тёплый и по-домашнему, как добрый совет подруги",
    "с лёгким юмором и доброй иронией",
    "коротко и по-деловому, по существу, без воды",
    "восторженно, будто делишься классной находкой",
    "спокойно и уютно, с акцентом на комфорт и ощущения",
    "практично, с упором на конкретную пользу и экономию",
    "вдохновляюще, про красоту и эстетику дома",
    "доверительно, будто рассказываешь секрет",
    "живо и энергично, с лёгкостью и улыбкой",
]

GH_TOKEN = os.environ["GH_MODELS_TOKEN"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "@nahodki_do_zp")
ALERT_CHAT_ID = os.environ.get("ALERT_CHAT_ID", "")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "*/*", "Accept-Language": "ru-RU,ru;q=0.9",
    "Origin": "https://www.wildberries.ru", "Referer": "https://www.wildberries.ru/",
}

def load_json(path):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except Exception: return {}

def prune_done(done):
    cut = time.strftime("%Y-%m-%d", time.gmtime(time.time()-5*86400))
    return {k:v for k,v in done.items() if k.split(":")[0] >= cut}

def persist(posted, done, state):
    with open(POSTED_FILE,"w",encoding="utf-8") as f: json.dump(posted,f,ensure_ascii=False)
    with open(DONE_FILE,"w",encoding="utf-8") as f: json.dump(done,f,ensure_ascii=False)
    with open(STATE_FILE,"w",encoding="utf-8") as f: json.dump(state,f,ensure_ascii=False)
    for cmd in (["git","config","user.name","bot"],["git","config","user.email","bot@local"],
                ["git","add",POSTED_FILE,DONE_FILE,STATE_FILE],["git","commit","-m","state"],["git","push"]):
        subprocess.run(cmd, check=False)

def is_fresh(nm, posted):
    ts = posted.get(str(nm))
    return True if not ts else (time.time()-ts) > COOLDOWN_DAYS*86400

def wb_search(query, tries=3):
    params = {"appType":"1","curr":"rub","dest":DEST,"lang":"ru","page":"1",
              "query":query,"resultset":"catalog","sort":"popular","spp":"30"}
    url = f"{SEARCH_URL}?{urlencode(params)}"
    for i in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                j = r.json(); root = j.get("data") or j
                return root.get("products") or []
        except Exception as e:
            print("wb err:", e)
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

def collect(posted, relaxed=False):
    max_fb = 50000 if relaxed else MAX_FB
    max_price = 4000 if relaxed else MAX_PRICE
    pool_queries = len(THEMES) if relaxed else POOL_QUERIES
    pool = {}; theme_count = {}; plan = []
    themes = list(THEMES.keys()); random.shuffle(themes)
    iters = {t: iter(random.sample(THEMES[t], len(THEMES[t]))) for t in themes}
    active = list(themes)
    while len(plan) < pool_queries and active:
        for t in list(active):
            try:
                plan.append((t, next(iters[t])))
                if len(plan) >= pool_queries: break
            except StopIteration:
                active.remove(t)
    for theme, q in plan:
        if theme_count.get(theme,0) >= PER_THEME_POOL_CAP: continue
        added = 0
        for p in wb_search(q):
            rating = p.get("reviewRating") or p.get("rating") or 0
            fb = p.get("feedbacks") or 0
            nm = p.get("id"); price = get_price(p)
            if (rating>=MIN_RATING and MIN_FB<=fb<=max_fb and price and price<=max_price
                    and nm and is_fresh(nm,posted) and nm not in pool
                    and theme_count.get(theme,0) < PER_THEME_POOL_CAP):
                pool[nm] = {"nmId":nm,"name":(p.get("name") or "")[:80],"brand":p.get("brand",""),
                            "theme":theme,"price":price,"rating":rating,"reviews":fb}
                theme_count[theme] = theme_count.get(theme,0)+1
                added += 1
                if added >= PER_QUERY_CAP or theme_count.get(theme,0) >= PER_THEME_POOL_CAP: break
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
    last=None
    for model in MODELS:
        for attempt in range(2):
            try:
                body = {"model":model,"temperature":0.9,
                    "messages":[{"role":"system","content":system},
                                {"role":"user","content":json.dumps(user_obj, ensure_ascii=False)}]}
                r = requests.post("https://models.github.ai/inference/chat/completions",
                    headers={"Authorization":f"Bearer {GH_TOKEN}","Content-Type":"application/json",
                             "Accept":"application/vnd.github+json"},
                    data=json.dumps(body).encode(), timeout=90)
                r.raise_for_status()
                txt = r.json()["choices"][0]["message"]["content"].strip()
                return json.loads(txt.replace("```json","").replace("```","").strip())
            except Exception as e:
                last=e; print(f"AI fail {model} #{attempt+1}:", e); time.sleep(3)
    raise last

def esc(t):
    return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def clean(t):
    t = t.strip()
    t = re.sub(r"\.\s*([^\w\s.,!?]+)\s*$", r" \1", t)
    while t and t[-1] in " .":
        t = t[:-1]
    return t.strip()

def link(nm):
    return f'<a href="https://www.wildberries.ru/catalog/{nm}/detail.aspx">смотреть</a>'

def tg_text(t):
    requests.post(f"{API}/sendMessage",
        data={"chat_id":CHAT_ID,"text":t,"parse_mode":"HTML","disable_web_page_preview":"true"}, timeout=30)

def alert(t):
    target = ALERT_CHAT_ID or CHAT_ID
    requests.post(f"{API}/sendMessage", data={"chat_id":target,"text":t}, timeout=30)

def tg_photo(buf, caption):
    requests.post(f"{API}/sendPhoto",
        data={"chat_id":CHAT_ID,"caption":caption[:1000],"parse_mode":"HTML"},
        files={"photo":("p.jpg",buf,"image/jpeg")}, timeout=60)

def tg_album(photos, caption):
    media=[]; files={}
    for i,buf in enumerate(photos):
        key=f"p{i}"; files[key]=(f"{key}.jpg",buf,"image/jpeg")
        m={"type":"photo","media":f"attach://{key}"}
        if i==0: m["caption"]=caption[:1024]; m["parse_mode"]="HTML"
        media.append(m)
    requests.post(f"{API}/sendMediaGroup",
        data={"chat_id":CHAT_ID,"media":json.dumps(media, ensure_ascii=False)}, files=files, timeout=120)

def post_single(nm, cap, c, posted):
    caption=f"{esc(clean(cap))}\n\n💰 {c['price']} ₽ → {link(nm)}"
    buf=get_image(nm)
    tg_photo(buf, caption) if buf else tg_text(caption)
    posted[str(nm)] = time.time()
    return True

def post_gallery(intro, items, posted):
    lines=[esc(clean(intro)),""]; photos=[]; n=0
    for nm, line, c in items:
        buf=get_image(nm)
        if not buf: continue
        n+=1; photos.append(buf)
        lines.append(f"{n}. {esc(clean(line))} — {c['price']} ₽ → {link(nm)}")
        posted[str(nm)] = time.time()
    caption="\n".join(lines)
    if len(photos)>=2: tg_album(photos, caption); return True
    if len(photos)==1: tg_photo(photos[0], caption); return True
    return False

def do_single(cands, rubric, style, posted):
    sysp=("Ты — редактор уютного Telegram-канала о полезных недорогих товарах для дома, хранения, быта, "
          f"уюта и красоты. Аудитория: женщины 25-40 лет. Тема: {rubric}. Стиль подачи: {style}. "
          "Выбери ОДИН самый цепляющий товар. Текст: 2-4 предложения о пользе в жизни, без капса и навязчивости, 2-3 эмодзи. "
          "Каждый раз формулируй ПО-НОВОМУ, избегай шаблонных фраз вроде 'находка для тех, кто', "
          "'идеально подойдёт', 'сделает ваш дом уютнее', 'незаменимый помощник'. "
          "Точки между предложениями ставь как обычно, но НЕ ставь точку в самом конце и перед финальным эмодзи. "
          'Верни ТОЛЬКО JSON: {"nmId": <число>, "caption": "<текст>"}')
    pick=ai_json(sysp, cands)
    nm=int(pick["nmId"]); cap=(pick.get("caption") or "").strip()
    c={x["nmId"]:x for x in cands}.get(nm)
    if not c or not cap: return False
    return post_single(nm, cap, c, posted)

def do_gallery(cands, rubric, style, posted):
    sysp=("Ты — редактор уютного Telegram-канала о полезных недорогих товарах для дома. Аудитория: женщины 25-40 лет. "
          f"Стиль подачи: {style}. У каждого товара есть поле theme. Выбери 5 товаров из РАЗНЫХ theme, "
          "максимально разные по виду и назначению. Вступление каждый раз формулируй ПО-РАЗНОМУ, "
          "НЕ начинай со слова 'Подборка', 1-2 предложения, 1-2 эмодзи. К каждому товару — короткая строка "
          "пользы (до 12 слов, с эмодзи), без шаблонных и повторяющихся оборотов. "
          "Точки между предложениями ставь как обычно, но НЕ ставь точку в конце строки и перед финальным эмодзи. "
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
    if len(chosen)<2: return False
    intro=(res.get("intro") or "Полезные находки для дома 🏡").strip()
    return post_gallery(intro, chosen, posted)

def simple_single(cands, posted):
    c=max(cands, key=lambda x: x["reviews"])
    return post_single(c["nmId"], c["name"], c, posted)

def simple_gallery(cands, posted):
    chosen=[]; used=set()
    for c in cands:
        if c["theme"] in used: continue
        used.add(c["theme"]); chosen.append((c["nmId"], c["name"], c))
        if len(chosen)>=5: break
    return post_gallery("Полезные находки для дома 🏡", chosen, posted)

def resolve_slot():
    m=os.environ.get("EVENT_INPUT_MODE","").strip()
    if m: return ("manual", m, LAST_ATTEMPT)
    sched=os.environ.get("EVENT_SCHEDULE","").strip()
    return SCHEDULE_MAP.get(sched, ("manual","single",LAST_ATTEMPT))

def pick_style(state):
    recent = state.get("recent_styles", [])
    choices = [s for s in STYLES if s not in recent] or STYLES
    return random.choice(choices)

def remember_style(state, style):
    recent = state.get("recent_styles", [])
    recent.append(style)
    state["recent_styles"] = recent[-STYLE_MEMORY:]

def main():
    posted = load_json(POSTED_FILE)
    done = prune_done(load_json(DONE_FILE))
    state = load_json(STATE_FILE)
    slot, mode, attempt = resolve_slot()
    is_last = attempt >= LAST_ATTEMPT
    today = time.strftime("%Y-%m-%d", time.gmtime())
    key = f"{today}:{slot}"
    print("slot:", slot, "mode:", mode, "attempt:", attempt)
    if slot != "manual" and done.get(key):
        print("already done:", key); return

    cands = collect(posted, relaxed=False)
    need = 5 if mode=="gallery" else 3
    if len(cands) < need:
        cands = collect(posted, relaxed=True)
    print("Candidates:", len(cands))
    if len(cands) < (2 if mode=="gallery" else 1):
        if is_last: alert(f"⚠️ Слот «{slot}»: нет товаров, пост пропущен.")
        else: print("not enough, retry later")
        return

    rubric = random.choice(RUBRICS)
    style = pick_style(state)
    print("rubric:", rubric, "| style:", style)
    ok = False
    try:
        ok = do_gallery(cands, rubric, style, posted) if mode=="gallery" else do_single(cands, rubric, style, posted)
    except Exception as e:
        print("quality path failed:", e); ok = False

    if ok:
        remember_style(state, style)
        done[key] = time.time(); persist(posted, done, state); print("posted:", key); return

    if not is_last:
        print("quality failed, will retry next slot"); return

    try:
        (simple_gallery if mode=="gallery" else simple_single)(cands, posted)
        done[key] = time.time(); persist(posted, done, state)
        alert(f"ℹ️ Слот «{slot}»: ИИ не ответил, вышел резервный пост без живого текста.")
    except Exception as e:
        alert(f"⚠️ Слот «{slot}»: не удалось выпустить пост ({e}).")

main()
