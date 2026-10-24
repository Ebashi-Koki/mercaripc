# メルカリPC利益チェッカー

メルカリで販売中のゲーミングデスクトップPCを集め、搭載 GPU / CPU を
[ドスパラ買取](https://www.dospara.co.jp/used-buy) の買取上限価格と照らし合わせて、
「パーツをドスパラに売ったら利益が出そうな出品」をスマホで一覧できるようにするツールです。

- GitHub Actions が 3 時間ごとにデータを取得し、GitHub Pages に公開します
- スマホのブラウザで開き「ホーム画面に追加」するとアプリのように使えます
- 査定率・送料・最低利益などの計算条件は画面上で変更でき、端末に保存されます

## 仕組み

1. `scraper/dospara.py` — ドスパラ買取の CPU / ビデオカード一覧から、型番ごとの買取上限価格（中央値）を取得（1日1回）
2. `scraper/mercari.py` — メルカリ「ゲーミングデスクトップ」カテゴリの販売中出品を取得
3. `scraper/parts.py` — 商品名（不足時は説明文）から `RTX4070SUPER` や `RYZEN 5700X` などの型番を抽出
4. `scraper/build.py` — 突き合わせて `docs/data/deals.json` を出力
5. `docs/index.html` — スマホ向けの一覧画面。利益は画面側で計算

推定買取額 ＝ GPU価格 × GPU査定率 ＋ CPU価格 × CPU査定率 ＋ その他パーツ（固定額）

## セットアップ（最初の1回だけ）

1. このブランチを `main` にマージ
2. GitHub のリポジトリ → **Settings → Pages → Build and deployment → Source** を **GitHub Actions** にする
3. **Actions → update → Run workflow** で手動実行
4. 数分後 `https://ebashi-koki.github.io/mercaripc/` をスマホで開く

## ローカルで動かす

```sh
pip install -r requirements.txt
python -m scraper.build
python -m http.server -d docs 8000   # http://localhost:8000
```

## 注意

- ドスパラの価格は「買取上限価格」（美品・付属品完備時）です。実際の査定額は下がることが多いので、購入前に必ず見積もりを確認してください。
- 型番は文字列から自動抽出しているため誤判定があります。「GPU複数記載」「CPU不明」の表示がある出品は特に説明文を確認してください。
- ジャンク・故障・パーツ欠品らしい出品はキーワードで除外していますが完全ではありません。
