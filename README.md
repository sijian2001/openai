# Earnings Report Summarizer

上場企業の決算報告書（PDF）を取得し、OpenAI API を用いて日本語で要約する CLI ツールです。  
`src/cli.py` の `main()` がエントリーポイントとなり、1 つの決算報告書 URL を受け取って処理を実行します。

## 必要要件
- Python 3.12 以上
- OpenAI API キー（環境変数 `OPENAI_API_KEY`）
- インターネット接続（決算報告書のダウンロードと OpenAI API 呼び出しに利用）

## セットアップ
```bash
python -m venv .venv
source .venv/bin/activate       # Windows PowerShell の場合: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 設定ファイル
`src/config.yaml` に CLI の既定値が同梱されています（モデル ID や出力先ディレクトリなど）。
リポジトリ直下に `config.yaml` を作成すれば、その内容で `src/config.yaml` の値を上書きできます。

```yaml
summarizer:
  model: "gpt-4o-mini"       # 要約に利用するモデル ID
  output_dir: "output/summaries"
fetcher:
  pdf_dir: "output/pdf"
```

OpenAI API キーは実行前に `export OPENAI_API_KEY="sk-..."` を行って設定します。

## 使い方
```bash
python -m src.cli <filing_url>
```

主なオプション（`python -m src.cli --help` でも確認可能）:
- `--model`: 要約に利用する OpenAI モデル（既定値は設定ファイルの `summarizer.model`）
- `--pdf-dir`: PDF を保存するディレクトリ（既定値は `fetcher.pdf_dir`）
- `--output-dir`: 要約テキスト／レスポンス JSON を出力するディレクトリ（既定値は `summarizer.output_dir`）

実行結果は標準出力とテキストファイルに保存され、API 応答の JSON は同じディレクトリに `_response.json` としてキャッシュされます。

## 開発とテスト
- ユニット／統合テスト: `pytest`
- 対象テストのみ実行: `pytest -k test_fetcher`
- カバレッジ確認: `pytest --cov=src --cov-report=term-missing`
- Lint: `ruff check src tests`
- フォーマット: `black src tests`

テスト用のサンプルデータは `tests/fixtures/` に配置します。  
一時的なダウンロードや生成物は `.cache/`（Git 追跡対象外）または `output/` 以下で扱ってください。

## ディレクトリ構成
```
src/
  cli.py           # CLI エントリーポイント。Config 読み込みと各モジュールのオーケストレーション
  fetcher.py       # HTTP 経由で PDF を取得し、ローカルに保存
  summarizer.py    # OpenAI Responses API を呼び出して要約（JSON キャッシュ対応）
tests/
  fixtures/        # サンプル決算報告書などのテスト用ファイル
  test_fetcher.py
  test_summarizer.py
src/config.yaml    # CLI の既定値を管理（変更可）
config.yaml        # 任意のローカル上書き設定
output/            # 既定設定での PDF と要約の保存先
```

今後、追加のリファレンス資料は `docs/` に、短期間のみ必要なダウンロードは `.cache/` に配置してください。

## トラブルシュート
- **OpenAI API キーが設定されていない**: 環境変数 `OPENAI_API_KEY` を設定してください。
- **PDF ダウンロードに失敗する**: ネットワーク設定を確認し、URL が PDF を指しているかを確かめてください。
- **要約結果が更新されない**: `_response.json` がキャッシュとして利用されます。再実行時に更新したい場合は該当ファイルを削除してください。
