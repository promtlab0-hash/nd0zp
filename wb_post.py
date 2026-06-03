import os, sys, json, urllib.request, urllib.parse

QUERY = "органайзер для хранения"
MIN_RATING = 4.7
MIN_FEEDBACKS = 150
DEST = "-1257786"
SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v5/search"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "@nahodki_do_zp")
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def tg(text):
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def get_price(p):
    for s in (p.get("sizes") or []):
        pr = s.get("price") or {}
        for k in ("product", "total", "basic"):
            if pr.get(k):
                return int(pr[k]) // 100
    for k in ("salePriceU", "priceU"):
        if p.get(k):
            return int(p[k]) // 100
    return None

def main():
    params = urllib.parse.urlencode({
        "appType": "1", "curr": "rub", "dest": DEST,
        "query": QUERY, "resultset": "catalog", "sort": "popular", "spp": "30",
    })
    url = f"{SEARCH_URL}?{params}"
    print("Requesting:", url)
    try:
        data = get_json(url)
    except Exception as e:
        tg(f"⚠️ Не смог запросить WB: {e}")
        print("ERROR:", e); sys.exit(1)

    products = (data.get("data") or {}).get("products") or []
    print("Products returned:", len(products))
    if not products:
        tg("⚠️ WB вернул 0 товаров — возможно, изменился эндпоинт.")
        print("RAW:", json.dumps(data)[:1000]); return
    print("First product keys:", list(products[0].keys()))

    for p in products:
        rating = p.get("reviewRating") or p.get("rating") or p.get("nmReviewRating") or 0
        fb = p.get("feedbacks") or 0
        if rating >= MIN_RATING and fb >= MIN_FEEDBACKS:
            nm = p.get("id"); name = p.get("name", "Без названия")
            brand = p.get("brand", ""); price = get_price(p)
            link = f"https://www.wildberries.ru/catalog/{nm}/detail.aspx"
            price_str = f"{price} ₽" if price else "цена уточняется"
            tg(f"🔎 {name}\n{brand}\n⭐ {rating} • отзывов: {fb}\n💰 {price_str}\n{link}")
            print("Posted nmId:", nm); return

    tg("⚠️ Товары есть, но фильтр не прошёл никто — смягчим порог.")
    print("Sample:", json.dumps(products[0])[:800])

main()
