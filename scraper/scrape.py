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
        txt = await li.inner_text()
        stage = "2進化" if "2 進化" in txt else "1進化" if "1 進化" in txt else "たね" if "たね" in txt else "-"
        hpm = re.search(r"HP\s*(\d+)", txt)
        got.append({
            "id": m.group(1), "name": alt.strip(), "code": m.group(2),
            "image": src if src.startswith("http") else "https://www.pokemon-card.com" + src,
            "type": "ポケモン" if m.group(2)=="P" else "エネルギー" if m.group(2)=="E" else "トレーナーズ",
            "stage": stage if m.group(2)=="P" else "-",
            "hp": hpm.group(1) if hpm else None,
            "is_ex": "ex" in alt.strip().lower(),
            "is_mega": ("メガ" in alt.strip() or alt.strip().startswith("M")),
            "evolvesFrom": None,
        })
    return got

async def get_evolves_from(page, card_id):
    url = f"https://www.pokemon-card.com/card-search/details.php/card/{card_id}/regu/XY"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_selector("h1", timeout=10000)
    except Exception:
        return None
    evos = await page.query_selector_all("div.evolution")
    if not evos:
        return None
    names = []
    on_index = -1
    for i, ev in enumerate(evos):
        a = await ev.query_selector("a")
        nm = (await a.inner_text()).strip() if a else ""
        cls = await ev.get_attribute("class") or ""
        names.append(nm)
        if "ev_on" in cls:
            on_index = i
    if on_index > 0:
        return names[on_index - 1]
    return None

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
        evo_targets = [c for c in cards.values() if c["stage"] in ("1進化", "2進化")]
        print(f"evo targets {len(evo_targets)}")
        for i, c in enumerate(evo_targets, 1):
            ef = await get_evolves_from(page, c["id"])
            if ef:
                c["evolvesFrom"] = ef
            if i % 20 == 0:
                print(f"  evo {i}/{len(evo_targets)}")
            await asyncio.sleep(0.3)
        await b.close()
    result = list(cards.values())
    with open("data/cards.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"done {len(result)}")

asyncio.run(main())
