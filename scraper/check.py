import asyncio
from playwright.async_api import async_playwright

START = "https://www.pokemon-card.com/card-search/index.php?se_ta=&keyword=&regulation_sidebar_form=XY&pg=&illust=&sm_and_keyword=true"

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=False)
        page = await b.new_page()
        await page.goto(START, wait_until="networkidle", timeout=90000)
        await page.wait_for_selector("img[src*='card_images']", timeout=30000)
        await asyncio.sleep(3)
        n1 = len(await page.query_selector_all("img[src*='card_images']"))
        print(f"スクロール前: {n1}枚")
        for i in range(10):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(0.5)
        await asyncio.sleep(2)
        n2 = len(await page.query_selector_all("img[src*='card_images']"))
        print(f"スクロール後: {n2}枚")
        li = len(await page.query_selector_all("li"))
        print(f"li要素: {li}個")
        print("ブラウザは10秒後に閉じます")
        await asyncio.sleep(10)
        await b.close()

asyncio.run(main())