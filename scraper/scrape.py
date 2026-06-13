import json, re, asyncio
from playwright.async_api import async_playwright

LIST = "https://www.pokemon-card.com/card-search/index.php?keyword=&se_ta=&regulation_sidebar_form=XY&pg={p}"

async def fetch_page(page, p):
    for attempt in range(4):
        try:
            await page.goto(LIST.format(p=p), wait_until="networkidle", timeout=60000)
            await page.wait_for_selector("img[src*='card_images']", timeout=20000)
            await asyncio.sleep(2)
        except Exception:
            print(f"  page {p} retry {attempt+1}")
            await asyncio.sleep(3)
            continue
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
            })
        if got:
            return got
        print(f"  page {p} empty retry")
        await asyncio.sleep(3)
    return []

async def main():
    cards = {}
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        page = await b.new_page()
        TOTAL_PAGES = 138
        for p in range(1, TOTAL_PAGES + 1):
            got = await fetch_page(page, p)
            new = 0
            for c in got:
                if c["id"] not in cards:
                    cards[c["id"]] = c
                    new += 1
            print(f"page {p}: +{new} total {len(cards)}")
            await asyncio.sleep(0.3)
        await b.close()
    result = list(cards.values())
    with open("data/cards.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"done {len(result)}")

asyncio.run(main())
