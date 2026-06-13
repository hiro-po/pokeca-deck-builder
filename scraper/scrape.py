import json, re, asyncio
from playwright.async_api import async_playwright

LIST = "https://www.pokemon-card.com/card-search/index.php?keyword=&se_ta=&regulation_sidebar_form=XY&pg={p}"

async def fetch_page(page, p):
    for attempt in range(5):
        try:
            await page.goto(LIST.format(p=p), wait_until="networkidle", timeout=90000)
        except Exception:
            print(f"  page {p} goto retry {attempt+1}")
            await asyncio.sleep(4)
            continue
        try:
            await page.wait_for_function(
                "document.querySelectorAll(\"img[src*='card_images']\").length >= 5",
                timeout=25000
            )
        except Exception:
            pass
        await asyncio.sleep(5)
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
        print(f"  page {p} empty retry {attempt+1}")
        await asyncio.sleep(4)
    return []

async def main():
    cards = {}
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        page = await b.new_page()
        for p in range(1, 139):
            got = await fetch_page(page, p)
            new = sum(1 for c in got if c["id"] not in cards)
            for c in got:
                cards[c["id"]] = c
            print(f"page {p}: +{new} total {len(cards)}")
            await asyncio.sleep(0.3)
        await b.close()
    result = list(cards.values())
    with open("data/cards.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"done {len(result)}")

asyncio.run(main())
