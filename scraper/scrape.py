"""
ポケモンカード スクレイピングスクリプト（改良版）
HIJスタンダードのカードを公式サイトから集めて
data/cards.json に保存します。
"""

import json
import asyncio
from playwright.async_api import async_playwright

BASE = (
    "https://www.pokemon-card.com/card-search/index.php"
    "?keyword=&se_ta=&regulation_sidebar_form=XY"
    "&pg={page}&illust=&sort=&kanji=&num=&hp=&expansion_code="
)


async def scrape():
    cards = []
    seen = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        page_num = 1
        empty_streak = 0

        while page_num <= 60:
            url = BASE.format(page=page_num)
            print(f"ページ {page_num} 読み込み中")
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception as e:
                print(f"  読み込み失敗: {e}")
                break

            await asyncio.sleep(2)

            imgs = await page.query_selector_all("img")

            found = 0
            for img in imgs:
                src = await img.get_attribute("src")
                alt = await img.get_attribute("alt")

                if not src or "card_images" not in src:
                    continue
                if not alt or alt.strip() == "":
                    continue
                if src in seen:
                    continue
                seen.add(src)

                cards.append({"name": alt.strip(), "image": src})
                found += 1

            print(f"  → {found}枚、累計 {len(cards)}枚")

            if found == 0:
                empty_streak += 1
                if empty_streak >= 2:
                    print("終了します")
                    break
            else:
                empty_streak = 0

            page_num += 1
            await asyncio.sleep(1)

        await browser.close()

    return cards


async def main():
    cards = await scrape()
    with open("data/cards.json", "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    print(f"完了！ {len(cards)}枚を保存しました。")


if __name__ == "__main__":
    asyncio.run(main())
