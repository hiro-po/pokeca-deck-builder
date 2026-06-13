import json, re, asyncio
from playwright.async_api import async_playwright

LIST = "https://www.pokemon-card.com/card-search/index.php?keyword=&se_ta=&regulation_sidebar_form=XY&pg={p}"

async def main():
    cards = {}
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        page = await b.new_page()
        p = 1
        max_pages = 200
        consecutive_empty = 0
        while p <= max_pages:
            ok = False
            for attempt in range(3):
                try:
                    await page.goto(LIST.format(p=p), wait_until="networkidle", timeout=60000)
                    await page.wait_for_selector("img[src*='card_images']", timeout=15000)
                    ok = True
                    break
                except Exception:
                    print(f"page {p} retry {attempt+1}")
                    await asyncio.sleep(2)
            if not ok:
                consecutive_empty += 1
                print(f"page {p}: load fail")
                if consecutive_empty >= 5:
                    break
                p += 1
                continue
            items = await page.query_selector_all("li")
            found = 0
            for li in items:
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
                cid, code = m.group(1), m.group(2)
                if cid in cards:
                    continue
                txt = await li.inner_text()
                stage = "2進化" if "2 進化" in txt else "1進化" if "1 進化" in txt else "たね" if "たね" in txt else "-"
                hpm = re.search(r"HP\s*(\d+)", txt)
                hp = hpm.group(1) if hpm else None
                ctype = "ポケモン" if code == "P" else "エネルギー" if code == "E" else "トレーナーズ"
                name = alt.strip()
                cards[cid] = {
                    "id": cid, "name": name, "code": code,
                    "image": src if src.startswith("http") else "https://www.pokemon-card.com" + src,
                    "type": ctype, "stage": stage if code == "P" else "-", "hp": hp,
                    "is_ex": "ex" in name.lower(),
                    "is_mega": ("メガ" in name or name.startswith("M")),
                }
                found += 1
            print(f"page {p}: {found} total {len(cards)}")
            if found == 0:
                consecutive_empty += 1
                if consecutive_empty >= 5:
                    break
            else:
                consecutive_empty = 0
            p += 1
            await asyncio.sleep(0.5)
        await b.close()
    result = list(cards.values())
    with open("data/cards.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"done {len(result)}")

asyncio.run(main())
