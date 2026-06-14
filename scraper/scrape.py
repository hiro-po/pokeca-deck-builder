import json, re, asyncio, os
from playwright.async_api import async_playwright

TEST = os.environ.get("TEST") == "1"
TEST_PAGES = 3
TEST_DETAILS = 10

START = "https://www.pokemon-card.com/card-search/index.php?se_ta=&keyword=&regulation_sidebar_form=XY&pg=&illust=&sm_and_keyword=true"

async def extract(page):
    try:
        for _ in range(10):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(0.4)
        await asyncio.sleep(1)
    except Exception:
        pass
    got = []
    for img in await page.query_selector_all("img[src*='card_images']"):
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

def valid_evolves_from(self_name, evo_name):
    if not evo_name:
        return None
    if evo_name == self_name:
        return None
    if evo_name in self_name or self_name in evo_name:
        return None
    return evo_name

async def fill_pokemon_detail(page, card):
    url = f"https://www.pokemon-card.com/card-search/details.php/card/{card['id']}/regu/XY"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_selector("h1", timeout=10000)
    except Exception:
        return
    try:
        t = await page.query_selector("span.type")
        if t:
            txt = (await t.inner_text()).strip()
            if "2" in txt and "進化" in txt:
                card["stage"] = "2進化"
            elif "1" in txt and "進化" in txt:
                card["stage"] = "1進化"
            elif "たね" in txt:
                card["stage"] = "たね"
    except Exception:
        pass
    try:
        h = await page.query_selector("span.hp-num")
        if h:
            hv = (await h.inner_text()).strip()
            if hv.isdigit():
                card["hp"] = hv
    except Exception:
        pass
    line = []
    for ev in await page.query_selector_all("div.evolution"):
        cls = await ev.get_attribute("class") or ""
        if "evbox" in cls:
            continue
        a = await ev.query_selector("a")
        nm = (await a.inner_text()).strip() if a else ""
        line.append((nm, "ev_on" in cls))
    on_idx = next((i for i, (nm, on) in enumerate(line) if on), -1)
    cand = None
    if on_idx >= 0 and on_idx + 1 < len(line):
        cand = line[on_idx + 1][0]
    elif on_idx < 0 and line:
        cand = line[0][0]
    card["evolvesFrom"] = valid_evolves_from(card["name"], cand)

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
        if TEST:
            max_page = TEST_PAGES
            print(f"[TESTモード] 最初の{TEST_PAGES}ページだけ取得")
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
            before = len(cards)
            for c in await extract(page):
                if c["id"] not in cards:
                    cards[c["id"]] = c
            if pno % 10 == 0 or pno <= 3:
                print(f"page {pno}/{int(max_page)}: +{len(cards)-before} total {len(cards)}")
        print(f"list done {len(cards)}")
        pokes = [c for c in cards.values() if c["code"] == "P"]
        if TEST:
            pokes = pokes[:TEST_DETAILS]
            print(f"[TESTモード] 詳細は{len(pokes)}枚だけ")
        print(f"pokemon detail targets {len(pokes)}")
        for i, c in enumerate(pokes, 1):
            await fill_pokemon_detail(page, c)
            if i % 50 == 0:
                print(f"  detail {i}/{len(pokes)}")
            await asyncio.sleep(0.2)
        await b.close()
    result = list(cards.values())
    outfile = "data/cards_test.json" if TEST else "data/cards.json"
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"done {len(result)} -> {outfile}")
    if TEST:
        for c in result[:5]:
            print(f"  例: {c['name']} ({c['type']}/{c['stage']}) evo={c['evolvesFrom']}")

asyncio.run(main())