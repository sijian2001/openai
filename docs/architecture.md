# アーキテクチャ更新メモ

## 目的
- `src/` 直下に散在していた CLI・フェッチャー・サマライザーを `src/summary/` 配下へ再配置し、機能別パッケージ構成を明示する。
- バンドル済み設定 (`config.yaml`) を同じパッケージ配下へ移し、`importlib.resources` による解決を簡潔にする。
- テストおよびドキュメントを新しいモジュールパスに追従させる。

## モジュール構成
```
src/
  summary/
    __init__.py         # パッケージエクスポート
    cli.py              # メインエントリーポイント (main())
    fetcher.py          # PDF ダウンロード機能
    summarizer.py       # OpenAI Responses API を使った要約機能
    config.yaml         # CLI 既定値 (モデル・出力パスなど)
```

- `python -m src.summary.cli` で CLI が起動する。
- `load_config()` は `src.summary.config.yaml` を既定として読み込み、`config.yaml` (作業ディレクトリ) があれば上書きする。

## テスト戦略
- `tests/test_cli.py` を新しい名前空間（`src.summary`）に合わせて更新し、CLI の例外パスや成功パスを継続的にカバー。
- 既存のフェッチャー・サマライザーテストもインポート先を更新し、キャッシュやエラー判定などの分岐網羅を維持。
- `pytest`, `ruff`, `black` を使用したローカル検証手順を README と整合。

## OCR パッケージ追加
- `src/ocr/` を新設し、`cli.py` と `recognizer.py` に責務を分割。CLI は入出力と CSV 生成を担当し、`recognizer.py` は OpenAI Responses API への問い合わせと文字列抽出を担当する。
- PNG 画像を base64 エンコードして API に渡し、応答からテキストを抽出する共通ロジック（`_extract_text`）を実装。OCR エラーは `OCRProcessingError` にラップ。
- `process_images()` で複数画像を扱い、認識結果をラインごとの CSV として保存する。
- テストは `tests/ocr/` 配下に配置し、API クライアントをモックしてバイナリ読み込み・CSV 出力・エラーハンドリングを検証する。

## 今後の検討事項
- 追加モジュール（parser 等）が増える場合は `src/summary/` にサブパッケージを切り、テストもミラー構成で配置する。
- `DEFAULT_DIR` など設定値は将来的に設定ファイルへ集約することを検討。
