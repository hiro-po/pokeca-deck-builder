import json, re, asyncio
from playwright.async_api import async_playwright

START = "https://www.pokemon-card.com/card-search/index.php?se_ta=&keyword=&regulation_sidebar_form=XY&pg=&illust=&sm_and_keyword=true"

async def extract(page):
    got = []
    for li in await page.query_selector_all("li"):
        img = await li.query_selector("img[src*='card_images']")
        if not img:
            continue
        src = await img.get_attribute("src")
        alt = await img.get_attribute("alt")
        if not src or not alt or not alt.strip():
            continue
        m = re.search(r"/(\d+)_([PTE])_", src)
        if not m:
            continue
        got.append({
            "id": m.group(1), "name": alt.strip(), "code": m.group(2),
            "image": src if src.startswith("http") else "https://www.pokemon-card.com" + src,
            "type": "ポケモン" if m.group(2)=="P" else "エネルギー" if m.group(2)=="E" else "トレーナーズ",
            "stage": "-", "hp": None,
            "is_ex": "ex" in alt.strip().lower(),
            "is_mega": ("メガ" in alt.strip() or alt.strip().startswith("M")),
            "evolvesFrom": None,
        })
    return got

async def fill_pokemon_detail(page, card):
    url = f"https://www.pokemon-card.com/card-search/details.php/card/{card['id']}/regu/XY"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_selector("h1", timeout=10000)
    except Exception:
        return
    body = await page.inner_text("body")
    if "2 進化" in body:
        card["stage"] = "2進化"
    elif "1 進化" in body:
        card["stage"] = "1進化"
    elif "たね" in body:
        card["stage"] = "たね"
    hpm = re.search(r"HP\s*(\d+)", body)
    if hpm:
        card["hp"] = hpm.group(1)
    evos = await page.query_selector_all("div.evolution")
    if evos:
        names, on_index = [], -1
        for i, ev in enumerate(evos):
            a = await ev.query_selector("a")
            names.append((await a.inner_text()).strip() if a else "")
            cls = await ev.get_attribute("class") or ""
            if "ev_on" in cls:
                on_index = i
        if on_index > 0:
            card["evolvesFrom"] = names[on_index - 1]

async def main():
    cards = {}
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        page = await b.new_page()
        await page.goto(START, wait_until="networkidle", timeout=90000)
        await page.wait_for_selector("img[src*='card_images']", timeout=30000)
        await asyncio.sleep(3)
        try:
            max_page = await page.evaluate("window.vueApp ? window.vueApp.maxPage : 0")
        except Exception:
            max_page = 0
        if not max_page or max_page < 1:
            max_page = 140
        print(f"maxPage = {max_page}")
        for pno in range(1, int(max_page) + 1):
            if pno > 1:
                try:
                    await page.evaluate(f"PTC.paginationRequest({pno})")
                except Exception:
                    pass
                await asyncio.sleep(2.5)
                try:
                    await page.wait_for_selector("img[src*='card_images']", timeout=15000)
                except Exception:
                    pass
            for c in await extract(page):
                if c["id"] not in cards:
                    cards[c["id"]] = c
            if pno % 20 == 0:
                print(f"list {pno}/{int(max_page)} total {len(cards)}")
        print(f"list done {len(cards)}")
        pokes = [c for c in cards.values() if c["code"] == "P"]
        print(f"pokemon detail targets {len(pokes)}")
        for i, c in enumerate(pokes, 1):
            await fill_pokemon_detail(page, c)
            if i % 25 == 0:
                print(f"  detail {i}/{len(pokes)}")
            await asyncio.sleep(0.25)
        await b.close()
    result = list(cards.values())
    with open("data/cards.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"done {len(result)}")

asyncio.run(main())
