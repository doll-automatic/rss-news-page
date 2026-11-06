# rss-news-page

Claude Code の定期実行（6時間ごと）で Web 検索してニュースを集め、RSS 2.0 として公開するリポジトリ。
[AndroidRSS](https://github.com/doll-automatic/AndroidRSS) の RSS ソースとして登録して使う。

## フィード

| トピック | URL |
|---|---|
| テクノロジー・AI | `https://raw.githubusercontent.com/doll-automatic/rss-news-page/main/feeds/tech.xml` |
| 経済・マーケット | `https://raw.githubusercontent.com/doll-automatic/rss-news-page/main/feeds/economy.xml` |
| 国内の主要ニュース | `https://raw.githubusercontent.com/doll-automatic/rss-news-page/main/feeds/domestic.xml` |

## 仕組み

- `TASK.md` … 定期実行セッションが従う収集手順
- `topics.json` … 収集トピックと保持期間（`retention_hours`、既定48時間＝2日）
- `scripts/update_feed.py` … 記事のマージ・重複排除・期限切れ削除・RSS 生成（標準ライブラリのみ）
- `data/<slug>.json` … 保持中の記事データ
- `feeds/<slug>.xml` … 公開する RSS

トピックを増やす・変えるときは `topics.json` を編集する（`slug` ごとに `feeds/<slug>.xml` ができる）。

このリポジトリは公開のため、ニュースの見出し・リンク・要約以外（個人情報・APIキー等）は置かないこと。
