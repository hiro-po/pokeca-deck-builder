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
        })
    return got

async def main():
    cards = {}
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        page = await b.new_page()
        await page.goto(START, wait_until="networkidle", timeout=90000)
        await page.wait_for_selector("img[src*='card_images']", timeout=30000)
        await asyncio.sleep(3)
        page_no = 1
        while page_no <= 140:
            got = await extract(page)
            new = sum(1 for c in got if c["id"] not in cards)
            for c in got:
                cards[c["id"]] = c
            print(f"page {page_no}: +{new} total {len(cards)}")
            nextlink = await page.query_selector("a.next, a:has-text('次のページ')")
            if not nextlink:
                print("no next. end")
                break
            try:
                await nextlink.click()
            except Exception:
                print("click fail. end")
                break
            await asyncio.sleep(3)
            try:
                await page.wait_for_selector("img[src*='card_images']", timeout=20000)
            except Exception:
                pass
            page_no += 1
        await b.close()
    result = list(cards.values())
    with open("data/cards.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"done {len(result)}")

asyncio.run(main())
