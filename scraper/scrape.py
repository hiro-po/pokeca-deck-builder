import json, re, asyncio
from playwright.async_api import async_playwright

LIST = "https://www.pokemon-card.com/card-search/index.php?keyword=&se_ta=&regulation_sidebar_form=XY&pg={p}"

async def get_cards_from_list(page):
    cards = {}
    p, empty = 1, 0
    while p <= 60:
        print(f"list {p}")
        try:
            await page.goto(LIST.format(p=p), wait_until="networkidle", timeout=40000)
        except Exception:
            break
        await asyncio.sleep(2)
        found = 0
        for img in await page.query_selector_all("img"):
            src = await img.get_attribute("src")
            alt = await img.get_attribute("alt")
            if not src or "card_images" not in src:
                continue
            if not alt or not alt.strip():
                continue
            m = re.search(r"/(\d+)_([PTE])_", src)
            if not m:
                continue
            cid, code = m.group(1), m.group(2)
            if cid in cards:
                continue
            cards[cid] = {"id": cid, "name": alt.strip(), "code": code,
                          "image": src if src.startswith("http") else "https://www.pokemon-card.com" + src}
            found += 1
        print(f"  {found} total {len(cards)}")
        if found == 0:
            empty += 1
            if empty >= 2:
                break
        else:
            empty = 0
        p += 1
        await asyncio.sleep(1)
    return list(cards.values())

async def add_detail(page, card):
    url = f"https://www.pokemon-card.com/card-search/details.php/card/{card['id']}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_selector("h1", timeout=10000)
    except Exception:
        return
    body = await page.inner_text("body")
    if card["code"] == "P":
        card["type"] = "ポケモン"
        card["stage"] = "2進化" if "2 進化" in body else "1進化" if "1 進化" in body else "たね"
        m = re.search(r"HP\s*(\d+)", body)
        card["hp"] = m.group(1) if m else None
    elif card["code"] == "E":
        card["type"] = "エネルギー"
        card["stage"] = "-"
    else:
        card["type"] = "サポート" if "サポート" in body else "スタジアム" if "スタジアム" in body else "グッズ"
        card["stage"] = "-"
    name = card["name"]
    card["is_ex"] = "ex" in name.lower()
    card["is_mega"] = ("メガ" in name or name.startswith("M"))

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        page = await b.new_page()
        cards = await get_cards_from_list(page)
        print(f"{len(cards)} cards found. getting details")
        for i, c in enumerate(cards, 1):
            await add_detail(page, c)
            if i % 20 == 0:
                print(f"{i}/{len(cards)}")
            await asyncio.sleep(0.3)
        await b.close()
    with open("data/cards.json", "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    print(f"done {len(cards)}")

asyncio.run(main())
