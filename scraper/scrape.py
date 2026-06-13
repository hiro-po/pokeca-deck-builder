import json, re, asyncio
from playwright.async_api import async_playwright

LIST = "https://www.pokemon-card.com/card-search/index.php?keyword=&se_ta=&regulation_sidebar_form=XY&pg={p}"

async def get_links(page):
    links, seen, p, empty = [], set(), 1, 0
    while p <= 60:
        print(f"list {p}")
        try:
            await page.goto(LIST.format(p=p), timeout=40000)
        except Exception:
            break
        try:
            await page.wait_for_selector("a[href*='details.php/card/']", timeout=15000)
        except Exception:
            pass
        found = 0
        for a in await page.query_selector_all("a[href*='details.php/card/']"):
            href = await a.get_attribute("href")
            if not href:
                continue
            m = re.search(r"/card/(\d+)", href)
            if not m or m.group(1) in seen:
                continue
            seen.add(m.group(1))
            if href.startswith("/"):
                href = "https://www.pokemon-card.com" + href
            links.append({"id": m.group(1), "url": href})
            found += 1
        print(f"  {found} total {len(links)}")
        if found == 0:
            empty += 1
            if empty >= 2:
                break
        else:
            empty = 0
        p += 1
        await asyncio.sleep(1)
    return links

async def get_detail(page, link):
    try:
        await page.goto(link["url"], timeout=40000)
        await page.wait_for_selector("h1", timeout=15000)
    except Exception:
        return None
    h1 = await page.query_selector("h1")
    name = (await h1.inner_text()).strip() if h1 else None
    if not name:
        return None
    body = await page.inner_text("body")
    stage = "2進化" if "2 進化" in body else "1進化" if "1 進化" in body else "たね" if "たね" in body else "-"
    m = re.search(r"HP\s*(\d+)", body)
    hp = m.group(1) if m else None
    ctype = "ポケモン"
    if stage == "-":
        ctype = "サポート" if "サポート" in body else "スタジアム" if "スタジアム" in body else "グッズ" if ("どうぐ" in body or "グッズ" in body) else "エネルギー" if "エネルギー" in body else "トレーナーズ"
    img = await page.query_selector("img[src*='card_images']")
    image = None
    if img:
        src = await img.get_attribute("src")
        image = ("https://www.pokemon-card.com" + src) if src and src.startswith("/") else src
    return {"id": link["id"], "name": name, "type": ctype, "stage": stage, "hp": hp,
            "is_ex": "ex" in name.lower(), "is_mega": ("メガ" in name or name.startswith("M")), "image": image}

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        page = await b.new_page()
        links = await get_links(page)
        print(f"{len(links)} links")
        cards = []
        for i, link in enumerate(links, 1):
            c = await get_detail(page, link)
            if c:
                cards.append(c)
            if i % 20 == 0:
                print(f"{i}/{len(links)}")
            await asyncio.sleep(0.4)
        await b.close()
    with open("data/cards.json", "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    print(f"done {len(cards)}")

asyncio.run(main())
