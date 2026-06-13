import json
import re
import asyncio
from playwright.async_api import async_playwright

LIST_URL = (
    "https://www.pokemon-card.com/card-search/index.php"
    "?keyword=&se_ta=&regulation_sidebar_form=XY"
    "&pg={page}&illust=&sort=&kanji=&num=&hp=&expansion_code="
)


async def collect_card_links(page):
    links = []
    seen = set()
    page_num = 1
    empty = 0
    while page_num <= 60:
        url = LIST_URL.format(page=page_num)
        print(f"一覧ページ {page_num}")
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"  失敗: {e}")
            break
        await asyncio.sleep(2)
        anchors = await page.query_selector_all("a")
        found = 0
        for a in anchors:
            href = await a.get_attribute("href")
            if not href or "details.php/card/" not in href:
                continue
            m = re.search(r"/card/(\d+)", href)
            if not m:
                continue
            cid = m.group(1)
            if cid in seen:
                continue
            seen.add(cid)
            if href.startswith("/"):
                href = "https://www.pokemon-card.com" + href
            links.append({"id": cid, "url": href})
            found += 1
        print(f"  {found}件 累計{len(links)}")
        if found == 0:
            empty += 1
            if empty >= 2:
                break
        else:
            empty = 0
        page_num += 1
        await asyncio.sleep(1)
    return links


async def scrape_detail(page, link):
    try:
        await page.goto(link["url"], wait_until="networkidle", timeout=30000)
    except Exception:
        return None
    await asyncio.sleep(0.5)
    name = None
    h1 = await page.query_selector("h1")
    if h1:
        name = (await h1.inner_text()).strip()
    body = await page.inner_text("body")
    stage = "-"
    if "2 進化" in body or "2進化" in body:
        stage = "2進化"
    elif "1 進化" in body or "1進化" in body:
        stage = "1進化"
    elif "たね" in body:
        stage = "たね"
    hp = None
    m = re.search(r"HP\s*(\d+)", body)
    if m:
        hp = m.group(1)
    ctype = "ポケモン"
    if stage == "-":
        if "サポート" in body:
            ctype = "サポート"
        elif "スタジアム" in body:
            ctype = "スタジアム"
        elif "グッズ" in body or "どうぐ" in body:
            ctype = "グッズ"
        elif "エネルギー" in body:
            ctype = "エネルギー"
    is_ex = bool(name and "ex" in name.lower())
    is_mega = bool(name and ("メガ" in name or name.startswith("M")))
    image = None
    img = await page.query_selector("img.fit")
    if not img:
        img = await page.query_selector("div.LeftBox img")
    if img:
        src = await img.get_attribute("src")
        if src and src.startswith("/"):
            src = "https://www.pokemon-card.com" + src
        image = src
    return {
        "id": link["id"], "name": name, "type": ctype,
        "stage": stage, "hp": hp, "is_ex": is_ex,
        "is_mega": is_mega, "image": image,
    }


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        links = await collect_card_links(page)
        print(f"\n{len(links)}枚のリンク取得。詳細取得開始\n")
        cards = []
        for i, link in enumerate(links, 1):
            card = await scrape_detail(page, link)
            if card and card["name"]:
                cards.append(card)
            if i % 20 == 0:
                print(f"  {i}/{len(links)}")
            await asyncio.sleep(0.5)
        await browser.close()
    with open("data/cards.json", "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    print(f"\n完了！ {len(cards)}枚を保存。")


if __name__ == "__main__":
    asyncio.run(main())
