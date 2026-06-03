import os, sys, time, requests
from io import BytesIO
from urllib.parse import urlencode
from PIL import Image

QUERY = "органайзер для хранения"
MIN_RATING = 4.7
MIN_FEEDBACKS = 150
DEST = "-1257786"
SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v18/search"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "@nahodki_do_zp")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Origin": "https://www.wildberries.ru",
    "Referer": "https://www.wildberries.ru/",
}

def get_json(url, tries=4):
    r = None
    for i in range(tries):
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            return r.json()
        print(f"Try {i+1}: HTTP {r.status_code}")
        if r.status_code in (429, 403, 500, 502, 503):
            time.sleep(5 * (i + 1)); continue
        break
    r.raise_for_status()

def send_text(text):
    requests.post(f"{API}/sendMessage", data={"chat_id": CHAT_ID, "text": text}, timeout=30)

def send_photo(buf, caption):
    files = {"photo": ("p.jpg", buf, "image/jpeg")}
    requests.post(f"{API}/sendPhoto", data={"chat_id": CHAT_ID, "caption": caption}, files=files, timeout=60)

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

def get_image(nm):
    vol = nm // 100000
    part = nm // 1000
    for b in range(1, 41):
        url = f"https://basket-{b:02d}.wbbasket.ru/vol{vol}/part{part}/{nm}/images/big/1.webp"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200 and r.content:
                img = Image.open(BytesIO(r.content)).convert("RGB")
                buf = BytesIO(); img.save(buf, format="JPEG", quality=85); buf.seek(0)
                print("Image from:", url)
                return buf
        except Exception:
            continue
    print("No image for", nm)
    return None

def main():
    params = {
        "appType": "1", "curr": "rub", "dest": DEST, "lang": "ru",
        "page": "1", "query": QUERY, "resultset": "catalog",
        "sort": "popular", "spp": "30",
    }
    url = f"{SEARCH_URL}?{urlencode(params)}"
    print("Requesting:", url)
    try:
        data = get_json(url)
    except Exception as e:
        send_text(f"⚠️ WB не отвечает: {e}")
        print("ERROR:", e); sys.exit(1)

    root = data.get("data") or data
    products = root.get("products") or []
    print("Products returned:", len(products))
    if not products:
        send_text(f"⚠️ 0 товаров. Ключи: {list(data.keys())}")
        return

    for p in products:
        rating = p.get("reviewRating") or p.get("rating") or p.get("nmReviewRating") or 0
        fb = p.get("feedbacks") or 0
        if rating >= MIN_RATING and fb >= MIN_FEEDBACKS:
            nm = p.get("id"); name = p.get("name", "Без названия")
            brand = p.get("brand", ""); price = get_price(p)
            link = f"https://www.wildberries.ru/catalog/{nm}/detail.aspx"
            price_str = f"{price} ₽" if price else "цена уточняется"
            caption = f"🔎 {name}\n{brand}\n⭐ {rating} • отзывов: {fb}\n💰 {price_str}\n{link}"
            buf = get_image(nm)
            send_photo(buf, caption) if buf else send_text(caption)
            print("Posted nmId:", nm); return

    send_text("⚠️ Товары есть, но фильтр не прошёл.")

main()
