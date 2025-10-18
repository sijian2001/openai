# Earnings Report Summarizer

python program を作って、株式銘柄の決算報告書をサマライズしてください。
python programのパラメータ：決算報告書のurl

処理内容：
1. URLを使って決算報告書 (PDF) をダウンロードし、`pdf/` 配下に保存する  
2. OpenAI API を使って PDF の内容を解析し、要約結果を生成する  
3. 要約結果を整形して console に出力し、テキストファイルとして `summaries/` 配下へ保存する

pythonプロジェクトは仮想環境を利用します。

## Requirements
- Python 3.12 以上
- インターネット接続（決算報告書を取得するため）
- OpenAI API キー（環境変数 `OPENAI_API_KEY` で設定）

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage
```bash
export OPENAI_API_KEY="sk-..."
python -m src.cli <report-url>
```

主なオプション:
- `--model`: 使用する OpenAI モデル (デフォルト: `gpt-4o-mini`)
- `--pdf-dir`: PDF の保存ディレクトリ (デフォルト: `pdf/`)
- `--output-dir`: 要約結果を保存するディレクトリ (デフォルト: `summaries/`)

## Tests
```bash
python -m unittest
```

## Project Structure
```
src/
  cli.py          # エントリーポイント
  fetcher.py      # PDF ダウンロード処理
  summarizer.py   # OpenAI API を利用した要約ロジック
tests/
  test_*.py       # ユニットテスト
pdf/              # ダウンロードした決算報告書
summaries/        # 出力した要約テキスト
```
