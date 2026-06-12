
"""
ポケモンカード スクレイピングスクリプト
================================================
このプログラムは、ポケモンカード公式サイトから
HIJスタンダードのカード情報を自動で集めて、
cards.json というファイルに保存します。

GitHub Actions（クラウド）の上で自動実行されるので、
あなたのPCやiPhoneで動かす必要はありません。
"""

import json
import asyncio
from playwright.async_api import async_playwright

# 検索のベースURL（HIJスタンダード = regulation_sidebar_form=XY）
BASE_URL = (
    "https://www.pokemon-card.com/card-search/index.php"
    "?keyword=&se_ta=&regulation_sidebar_form=XY"
    "&pg={page}&illust=&sort=&page={page}"
)


async def scrape_all_cards():
    """全ページをめぐってカード情報を集める関数"""
    cards = []

    async with async_playwright() as p:
        # ブラウザを起動（画面は表示しない＝headless）
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        page_num = 1
        while True:
            url = BASE_URL.format(page=page_num)
            print(f"ページ {page_num} を読み込み中...")
            await page.goto(url, wait_until="networkidle")

            # カード一覧が出てくるまで待つ（最大10秒）
            try:
                await page.wait_for_selector("ul.List_card li", timeout=10000)
            except Exception:
                print("カードが見つかりません。終了します。")
                break

            # ページ内のカードをすべて取得
            items = await page.query_selector_all("ul.List_card li")
            if not items:
                break

            for item in items:
                # カード名
                name_el = await item.query_selector("img")
                name = await name_el.get_attribute("alt") if name_el else None

                # カード画像URL
                img_el = await item.query_selector("img")
                img = await img_el.get_attribute("src") if img_el else None

                # カード詳細ページへのリンク
                link_el = await item.query_selector("a")
                link = await link_el.get_attribute("href") if link_el else None

                if name:
                    cards.append({
                        "name": name,
                        "image": img,
                        "detail_url": link,
                    })

            print(f"  → ここまで合計 {len(cards)} 枚")

            # 「次へ」ボタンがあるか確認。なければ終了
            next_btn = await page.query_selector("a.next")
            if not next_btn:
                print("最後のページに到達しました。")
                break

            page_num += 1
            # サーバーに優しく：1秒待つ
            await asyncio.sleep(1)

        await browser.close()

    return cards


async def main():
    cards = await scrape_all_cards()

    # cards.json に保存（日本語が文字化けしないよう ensure_ascii=False）
    with open("data/cards.json", "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)

    print(f"\n完了！ 合計 {len(cards)} 枚を data/cards.json に保存しました。")


if __name__ == "__main__":
    asyncio.run(main())
