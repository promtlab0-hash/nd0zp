import os, sys, json, time, random, requests, subprocess, re
from io import BytesIO
from urllib.parse import urlencode
from PIL import Image

MIN_RATING = 4.7
MIN_FB = 150
MAX_FB = 4000
MIN_PRICE = 100
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
THEME_MEMORY = 70
WOW_IN_POOL = 4

SCHEDULE_MAP = {
    "25 5 * * *": ("morning","single",1), "45 5 * * *": ("morning","single",2),
    "5 6 * * *": ("morning","single",3), "25 6 * * *": ("morning","single",4),
    "55 9 * * *": ("noon","single",1), "15 10 * * *": ("noon","single",2),
    "35 10 * * *": ("noon","single",3), "55 10 * * *": ("noon","single",4),
    "55 17 * * *": ("evening","gallery",1), "15 18 * * *": ("evening","gallery",2),
    "35 18 * * *": ("evening","gallery",3), "55 18 * * *": ("evening","gallery",4),
}

# обычные темы (быт/дом/красота/организация/дорожный органайзинг)
THEMES = {
    "органайзеры мелочей": ["органайзер для хранения мелочей","разделители для ящиков комода"],
    "коробки": ["коробки для хранения вещей складные"],
    "корзина белья": ["корзина для белья складная"],
    "под кроватью": ["ящик под кровать на колесах","кофр для хранения сезонных вещей"],
    "вакуум": ["вакуумные пакеты для одежды"],
    "вешалки": ["вешалки плечики бархатные"],
    "органайзер сумок": ["органайзер для сумок в шкаф"],
    "обувь хранение": ["органайзер для обуви","коробки для обуви прозрачные"],
    "органайзер белья": ["органайзер для нижнего белья","разделители для носков"],
    "шкатулка украшений": ["шкатулка для украшений","органайзер для украшений"],
    "специи": ["контейнер для специй с дозатором","банки для сыпучих продуктов"],
    "измельчитель": ["измельчитель чеснока ручной"],
    "овощечистка": ["овощечистка экономка"],
    "открывашка": ["открывашка для банок"],
    "доска нарезка": ["доска разделочная с контейнерами"],
    "терка": ["терка многофункциональная"],
    "заморозка": ["силиконовые формы для заморозки"],
    "контейнеры еды": ["контейнеры для еды с разделителями"],
    "коврик выпечки": ["силиконовый коврик для выпечки"],
    "форма кексов": ["форма для кексов силиконовая"],
    "коврик сушки": ["коврик для сушки посуды"],
    "подставка горячее": ["подставка под горячее силиконовая"],
    "ланч бокс": ["ланч бокс с разделами"],
    "термокружка": ["термокружка с крышкой"],
    "бутылка воды": ["бутылка для воды мотивационная"],
    "заварочный чайник": ["заварочный чайник стеклянный"],
    "держатель полотенец": ["держатель для бумажных полотенец"],
    "подставка крышек": ["подставка для крышек"],
    "кухонные весы": ["кухонные весы электронные"],
    "мерные ложки": ["мерные ложки набор"],
    "силиконовые лопатки": ["силиконовые лопатки для кухни"],
    "крышка от брызг": ["крышка от брызг для сковороды"],
    "банки чай кофе": ["банки для чая и кофе"],
    "диспенсер напитков": ["диспенсер для напитков"],
    "контейнер холодильник": ["контейнеры для холодильника"],
    "свет гирлянда": ["гирлянда теплый свет для спальни"],
    "ночник проектор": ["ночник проектор звездное небо"],
    "лампа настольная": ["лампа настольная с регулировкой"],
    "светильник датчик": ["светильник с датчиком движения"],
    "соляная лампа": ["соляная лампа ночник"],
    "текстиль коврик": ["коврик с длинным ворсом"],
    "плед": ["плед с рукавами"],
    "наволочки": ["декоративные наволочки"],
    "шторы": ["шторы блэкаут для спальни"],
    "подхваты штор": ["подхваты для штор магнитные"],
    "покрывало": ["покрывало на кровать стеганое"],
    "чехлы стульев": ["чехлы на стулья"],
    "скатерть": ["скатерть водоотталкивающая"],
    "подставка книг": ["подставка для книг для чтения"],
    "столик завтрак": ["столик для завтрака в кровать"],
    "маска сна": ["маска для сна 3д"],
    "подушка шея": ["подушка для шеи дорожная"],
    "ароматы диффузор": ["аромадиффузор автоматический"],
    "свеча": ["свеча ароматическая"],
    "саше": ["саше для шкафа ароматическое"],
    "отпариватель": ["отпариватель ручной для одежды"],
    "машинка катышков": ["машинка для удаления катышков"],
    "мешки стирки": ["мешки для стирки белья набор"],
    "сортер белья": ["сортер для белья трехсекционный"],
    "сушилка белья": ["сушилка для белья складная"],
    "ролик одежды": ["ролик для чистки одежды"],
    "волосы массажер": ["массажер для кожи головы"],
    "бигуди": ["силиконовые бигуди без нагрева"],
    "расческа": ["расческа массажная"],
    "заколки": ["заколки крабики набор"],
    "резинки": ["резинки для волос спиральные"],
    "повязка умывание": ["повязка для умывания"],
    "косметика органайзер": ["органайзер для косметики вращающийся"],
    "зеркало подсветка": ["зеркало с подсветкой настольное"],
    "держатель кистей": ["держатель для кистей макияжа"],
    "спонж": ["спонж для макияжа набор"],
    "роллер лица": ["роллер для лица"],
    "щетка массаж": ["щетка для сухого массажа"],
    "массажер ног": ["массажер для ног"],
    "маникюр набор": ["набор для маникюра"],
    "лампа ногтей": ["лампа для сушки ногтей"],
    "уборка скребок": ["скребок для чистки сковород"],
    "щетка швы": ["щетка для чистки межплиточных швов"],
    "салфетки микрофибра": ["салфетки из микрофибры набор"],
    "швабра": ["швабра с отжимом"],
    "щетка унитаз": ["щетка для унитаза силиконовая"],
    "спрей сантехника": ["спрей для чистки сантехники"],
    "щетка пыли": ["щетка для пыли гибкая"],
    "сгон окон": ["набор для мытья окон со сгоном"],
    "перчатки уборка": ["перчатки для уборки хозяйственные"],
    "губки": ["губки для посуды набор"],
    "средство накипи": ["средство от накипи"],
    "водосгон": ["водосгон для пола с ручкой"],
    "ванная полка": ["угловая полка в ванную без сверления"],
    "ванная коврик": ["коврик в ванную быстросохнущий"],
    "держатель щеток": ["держатель для зубных щеток"],
    "дозатор мыла": ["дозатор для мыла автоматический"],
    "стакан настенный": ["стакан для зубных щеток настенный"],
    "штора ванная": ["штора для ванной тканевая"],
    "органайзер душ": ["органайзер для ванной подвесной"],
    "коврик диатомит": ["коврик диатомитовый для ванной"],
    "крючки": ["крючки для одежды без сверления"],
    "вешалка шарфов": ["вешалка органайзер для шарфов"],
    "провода органайзер": ["органайзер для проводов"],
    "сетка от насекомых": ["магнитная сетка от комаров на дверь"],
    "ловушка мошек": ["ловушка для мошек"],
    "эко мешочки": ["многоразовые мешочки для овощей"],
    "кашпо": ["кашпо для цветов подвесное"],
    "лейка": ["лейка для комнатных растений"],
    "опрыскиватель": ["опрыскиватель для растений"],
    "ключница": ["ключница настенная органайзер"],
    "полка обуви": ["полка для обуви узкая"],
    "подставка ноутбук": ["подставка для ноутбука складная"],
    "органайзер канцелярии": ["органайзер для канцелярии настольный"],
    "папка документов": ["папка органайзер для документов"],
    "шкатулка мелочей": ["шкатулка для мелочей"],
    "питомцы лежанка": ["лежанка для кошки мягкая"],
    "питомцы коврик": ["коврик под миску для животных"],
    "когтеточка": ["когтеточка настенная"],
    "миска подставка": ["миска для животных на подставке"],
    "дети ночник": ["ночник детский силиконовый"],
    "дети игрушки": ["корзина для игрушек складная"],
    "праздник свечи": ["свечи для торта тонкие"],
    "упаковка подарок": ["подарочная упаковка набор"],
    "путешествия чемодан": ["органайзеры для чемодана набор"],
    "косметичка": ["косметичка дорожная подвесная"],
    "дорожные бутылочки": ["дорожные бутылочки для косметики"],
    "авто органайзер": ["органайзер в машину между сиденьями"],
    "зонт": ["зонт автомат компактный"],
    "грелка рук": ["грелка для рук электрическая"],
    "теплые носки": ["теплые носки домашние"],
    "увлажнитель": ["увлажнитель воздуха для дома"],
    "пылесос ручной": ["ручной пылесос беспроводной"],
    "термометр гигрометр": ["термометр гигрометр комнатный"],
    "органайзер лекарств": ["органайзер для лекарств"],
    "контейнер крупы": ["контейнер для круп с крышкой"],
    "подставка планшет": ["подставка для планшета кухонная"],
    "фартук": ["фартук кухонный водонепроницаемый"],
    "прихватки": ["прихватки силиконовые для кухни"],
    "под раковину": ["органайзер под раковину выдвижной"],
    "рейлинг кухня": ["рейлинг для кухни с крючками"],
    "держатель ножей": ["магнитный держатель для ножей"],
    "термос еды": ["термос для еды с ложкой"],
    "грелка солевая": ["грелка солевая многоразовая"],
    "коврик придверный": ["коврик придверный грязезащитный"],
    "вкладыш сумку": ["органайзер вкладыш в сумку"],
    "зеркало увеличение": ["зеркало косметическое с увеличением"],
    "точилка ножей": ["точилка для ножей механическая"],
    "хлебница": ["хлебница металлическая"],
    "подставка зонтов": ["подставка для зонтов в прихожую"],
    "полка специй": ["полка для специй настенная"],
    "сушилка фруктов": ["сушилка для овощей и фруктов"],
    "формы печенья": ["формы для печенья набор"],
    "контейнер торта": ["контейнер для торта с крышкой"],
    "поднос": ["поднос для завтрака бамбуковый"],
    "обувница": ["обувница узкая в прихожую"],
    "короб игрушек": ["короб для игрушек с крышкой"],
}

# вау-находки: хитрые мелочи, о которых обычно не догадываются
WOW_THEMES = {
    "wow крышка кружки": ["силиконовая крышка для кружки от проливания"],
    "wow чистка клавиатуры": ["щетка для чистки клавиатуры мелкая"],
    "wow гель для пыли": ["чистящий гель лизун для клавиатуры и пыли"],
    "wow протекторы углов": ["силиконовые накладки на углы мебели"],
    "wow кольцо для банок": ["открыватель крышек кольцо силиконовый"],
    "wow фиксаторы ковра": ["держатели ковра от скольжения уголки"],
    "wow карман холодильник": ["подвесной карман органайзер на холодильник"],
    "wow разделитель тарелки": ["силиконовые разделители для тарелки"],
    "wow антискользящие плечики": ["силиконовые полоски на плечики от скольжения"],
    "wow щетка жалюзи": ["щетка для чистки жалюзи с зажимами"],
    "wow слив для раковины": ["силиконовая сетка фильтр для слива раковины"],
    "wow держатель пакетов": ["держатель мусорных пакетов под раковину"],
    "wow клипсы пакетов": ["клипсы зажимы для пакетов с продуктами"],
    "wow подставка губки": ["держатель для губки на присоске в раковину"],
    "wow магнитные стяжки": ["магнитные стяжки для проводов многоразовые"],
    "wow наклейки выключатель": ["светящиеся наклейки на выключатель"],
    "wow крючок под стол": ["крючок для сумки под стол самоклеящийся"],
    "wow защита плиты": ["силиконовые накладки между плитой и столешницей"],
    "wow воронка складная": ["складная силиконовая воронка для кухни"],
    "wow щетка для пуговиц": ["щетка для чистки труднодоступных мест"],
    "wow стоп-дверь": ["силиконовый фиксатор стоппер для двери"],
    "wow антиопрокидыватель": ["держатель крышки кастрюли антивыкипание"],
    "wow дренаж подоконник": ["поддон лоток для рассады на подоконник"],
    "wow ремувка катышки": ["камень пемза для удаления катышков"],
    "wow органайзер зарядок": ["бокс органайзер для зарядных устройств"],
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
        for k in ("total","product"):
            if pr.get(k): return int(pr[k])//100
    for s in (p.get("sizes") or []):
        pr = s.get("price") or {}
        if pr.get("basic"): return int(pr["basic"])//100
    for k in ("salePriceU","priceU"):
        if p.get(k): return int(p[k])//100
    return None

def price_from(price):
    floor = (price // 50) * 50
    if floor < MIN_PRICE: floor = MIN_PRICE
    return f"от {floor} ₽"

def search_themes(theme_map, plan, posted, pool, theme_count, max_fb, max_price, wow):
    for theme, q in plan:
        if theme_count.get(theme,0) >= PER_THEME_POOL_CAP: continue
        added = 0
        for p in wb_search(q):
            rating = p.get("reviewRating") or p.get("rating") or 0
            fb = p.get("feedbacks") or 0
            nm = p.get("id"); price = get_price(p)
            if (rating>=MIN_RATING and MIN_FB<=fb<=max_fb and price and MIN_PRICE<=price<=max_price
                    and nm and is_fresh(nm,posted) and nm not in pool
                    and theme_count.get(theme,0) < PER_THEME_POOL_CAP):
                pool[nm] = {"nmId":nm,"name":(p.get("name") or "")[:80],"brand":p.get("brand",""),
                            "theme":theme,"price":price,"rating":rating,"reviews":fb,"wow":wow}
                theme_count[theme] = theme_count.get(theme,0)+1
                added += 1
                if added >= PER_QUERY_CAP or theme_count.get(theme,0) >= PER_THEME_POOL_CAP: break
        if len(pool) >= MAX_POOL: break

def build_plan(theme_map, exclude, count):
    avail = [t for t in theme_map.keys() if t not in exclude] or list(theme_map.keys())
    random.shuffle(avail)
    iters = {t: iter(random.sample(theme_map[t], len(theme_map[t]))) for t in avail}
    active = list(avail); plan = []
    while len(plan) < count and active:
        for t in list(active):
            try:
                plan.append((t, next(iters[t])))
                if len(plan) >= count: break
            except StopIteration:
                active.remove(t)
    return plan

def collect(posted, recent_themes, relaxed=False):
    max_fb = 50000 if relaxed else MAX_FB
    max_price = 4000 if relaxed else MAX_PRICE
    pool = {}; theme_count = {}
    wow_n = min(WOW_IN_POOL, len(WOW_THEMES))
    main_n = (min(len(THEMES),30) if relaxed else POOL_QUERIES)
    wow_plan = build_plan(WOW_THEMES, recent_themes, wow_n)
    search_themes(WOW_THEMES, wow_plan, posted, pool, theme_count, max_fb, max_price, True)
    main_plan = build_plan(THEMES, recent_themes, main_n)
    search_themes(THEMES, main_plan, posted, pool, theme_count, max_fb, max_price, False)
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
    caption=f"{esc(clean(cap))}\n\n💰 {price_from(c['price'])} → {link(nm)}"
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
        lines.append(f"{n}. {esc(clean(line))} — {price_from(c['price'])} → {link(nm)}")
        posted[str(nm)] = time.time()
    caption="\n".join(lines)
    if len(photos)>=2: tg_album(photos, caption); return True
    if len(photos)==1: tg_photo(photos[0], caption); return True
    return False

def do_single(cands, rubric, style, posted):
    wow = [c for c in cands if c.get("wow")]
    pref = wow if wow else cands
    sysp=("Ты — редактор уютного Telegram-канала о полезных недорогих товарах для дома, хранения, быта, "
          f"уюта и красоты. Аудитория: женщины 25-40 лет. Тема: {rubric}. Стиль подачи: {style}. "
          "Выбери ОДИН самый цепляющий товар, отдавай предпочтение неочевидным находкам, решающим мелкую бытовую проблему. "
          "Текст: 2-4 предложения о пользе в жизни, без капса и навязчивости, 2-3 эмодзи. "
          "Каждый раз формулируй ПО-НОВОМУ, избегай шаблонных фраз вроде 'находка для тех, кто', "
          "'идеально подойдёт', 'сделает ваш дом уютнее', 'незаменимый помощник'. "
          "Точки между предложениями ставь как обычно, но НЕ ставь точку в самом конце и перед финальным эмодзи. "
          'Верни ТОЛЬКО JSON: {"nmId": <число>, "caption": "<текст>"}')
    pick=ai_json(sysp, pref)
    nm=int(pick["nmId"]); cap=(pick.get("caption") or "").strip()
    c={x["nmId"]:x for x in cands}.get(nm)
    if not c or not cap: return None
    post_single(nm, cap, c, posted)
    return [c["theme"]]

def do_gallery(cands, rubric, style, posted):
    sysp=("Ты — редактор уютного Telegram-канала о полезных недорогих товарах для дома. Аудитория: женщины 25-40 лет. "
          f"Стиль подачи: {style}. У каждого товара есть поле theme. Выбери 5 товаров из РАЗНЫХ theme, "
          "максимально разные по виду и назначению. Если среди товаров есть неочевидные находки, обязательно включи хотя бы одну. "
          "Вступление каждый раз формулируй ПО-РАЗНОМУ, НЕ начинай со слова 'Подборка', 1-2 предложения, 1-2 эмодзи. "
          "К каждому товару — короткая строка пользы (до 12 слов, с эмодзи), без шаблонных оборотов. "
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
    if not any(c.get("wow") for _,_,c in chosen):
        wow_c = next((c for c in cands if c.get("wow") and c["theme"] not in used), None)
        if wow_c:
            if len(chosen)>=5: chosen.pop()
            used.add(wow_c["theme"]); chosen.insert(0,(wow_c["nmId"], wow_c["name"], wow_c))
    if len(chosen)<5:
        for c in cands:
            if c["theme"] in used: continue
            used.add(c["theme"]); chosen.append((c["nmId"], c["name"], c))
            if len(chosen)>=5: break
    if len(chosen)<2: return None
    intro=(res.get("intro") or "Полезные находки для дома 🏡").strip()
    if post_gallery(intro, chosen, posted):
        return [c["theme"] for _,_,c in chosen]
    return None

def simple_single(cands, posted):
    c=max(cands, key=lambda x: x["reviews"])
    post_single(c["nmId"], c["name"], c, posted)
    return [c["theme"]]

def simple_gallery(cands, posted):
    chosen=[]; used=set()
    wow_c = next((c for c in cands if c.get("wow")), None)
    if wow_c:
        used.add(wow_c["theme"]); chosen.append((wow_c["nmId"], wow_c["name"], wow_c))
    for c in cands:
        if c["theme"] in used: continue
        used.add(c["theme"]); chosen.append((c["nmId"], c["name"], c))
        if len(chosen)>=5: break
    if post_gallery("Полезные находки для дома 🏡", chosen, posted):
        return [c["theme"] for _,_,c in chosen]
    return None

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

def remember_themes(state, themes):
    recent = state.get("recent_themes", [])
    recent.extend(themes)
    state["recent_themes"] = recent[-THEME_MEMORY:]

def main():
    posted = load_json(POSTED_FILE)
    done = prune_done(load_json(DONE_FILE))
    state = load_json(STATE_FILE)
    recent_themes = state.get("recent_themes", [])
    slot, mode, attempt = resolve_slot()
    is_last = attempt >= LAST_ATTEMPT
    today = time.strftime("%Y-%m-%d", time.gmtime())
    key = f"{today}:{slot}"
    print("slot:", slot, "mode:", mode, "attempt:", attempt)
    if slot != "manual" and done.get(key):
        print("already done:", key); return

    cands = collect(posted, recent_themes, relaxed=False)
    need = 5 if mode=="gallery" else 3
    if len(cands) < need:
        cands = collect(posted, recent_themes, relaxed=True)
    print("Candidates:", len(cands))
    if len(cands) < (2 if mode=="gallery" else 1):
        if is_last: alert(f"⚠️ Слот «{slot}»: нет товаров, пост пропущен.")
        else: print("not enough, retry later")
        return

    rubric = random.choice(RUBRICS)
    style = pick_style(state)
    print("rubric:", rubric, "| style:", style)
    used_themes = None
    try:
        used_themes = do_gallery(cands, rubric, style, posted) if mode=="gallery" else do_single(cands, rubric, style, posted)
    except Exception as e:
        print("quality path failed:", e); used_themes = None

    if used_themes:
        remember_style(state, style); remember_themes(state, used_themes)
        done[key] = time.time(); persist(posted, done, state); print("posted:", key); return

    if not is_last:
        print("quality failed, will retry next slot"); return

    try:
        ut = (simple_gallery if mode=="gallery" else simple_single)(cands, posted)
        if ut: remember_themes(state, ut)
        done[key] = time.time(); persist(posted, done, state)
        alert(f"ℹ️ Слот «{slot}»: ИИ не ответил, вышел резервный пост без живого текста.")
    except Exception as e:
        alert(f"⚠️ Слот «{slot}»: не удалось выпустить пост ({e}).")

main()
