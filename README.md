# Earnings Report Summarizer

python program を作って、株式銘柄の決算報告をサマライズしてください。  
python programのパラメータは決算報告書のURLです。  
サマライズの結果は整形して、consoleに出力してください。

このリポジトリは、決算報告書 (HTML) を取得して要約を生成する簡易CLIツールです。
外部ライブラリに依存せず、標準ライブラリのみで動作します。

## Requirements
- Python 3.12 以上
- インターネット接続（決算報告書を取得するため）

## Setup
```bash
python3 -m venv .venv --without-pip
source .venv/bin/activate
```

## Installation
依存パッケージはありません。標準ライブラリのみで動作します。

## Usage
```bash
python -m src.cli <report-url>
```

オプション:
- `--max-sentences`: 出力する要約文の最大数 (デフォルト: 5)

## Tests
```bash
python -m unittest
```

## Project Structure
```
src/
  cli.py          # エントリーポイント
  fetcher.py      # レポートのダウンロード処理
  summarizer.py   # 要約ロジック
  parser/
    html_text.py  # HTMLからテキストを抽出
tests/
  test_*.py       # ユニットテスト
```
