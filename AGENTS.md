# AGENTS.md

## 作業開始前の必須手順（最優先・例外なし）

1. エージェントは、調査、計画、コマンド実行、スキル利用、ファイル編集、コミット、プッシュを始める前に、必ずリポジトリ直下の `.\COMMON-AGENTS.md` を開き、先頭から末尾まで全文を読む。
2. `COMMON-AGENTS.md` はGit管理外のシンボリックリンクである。`git`や既定のignore設定が有効な`rg --files`の検索結果だけで、ファイルが存在しないと判断してはならない。PowerShellでは最初に次を実行する。

```powershell
Get-Content -Raw -LiteralPath .\COMMON-AGENTS.md
```

3. 読み取りに失敗した場合、出力が省略された場合、または末尾まで読めたことを確認できない場合は、一切の作業を開始せず、パスとシンボリックリンク先を確認して全文を再取得する。必要なら分割して末尾まで読む。
4. 全文を読了するまで、ローカル `AGENTS.md` だけを根拠に作業を続けてはならない。読了後は `COMMON-AGENTS.md` を最優先の指針とし、読了直後の最初の進捗報告で全文を読了したことを明示する。
   このファイルでは `e-yooso-z88-109-keyboard` 固有の補足だけを記載する。

## 目的

- E-YOOSO（e元素）Z88 109キー日本語配列キーボードを、ファームウェアを書き換えずにWindowsからRGB制御する。
- Codexのエージェント状態をキーボード全体の色へ反映する。
- 現行ファームウェアを安全側の手順で退避し、別機種ファームの誤書込みを防ぐ。

## 確認済み対象モデル

- 製品: E-YOOSO Z88 109キー日本語配列、販売型番 `Z-88RGB109` / `Z88RGB109JP`
- 接続: USB Type-C有線
- USB VID/PID: `258A:0049`
- Manufacturer: `BY Tech`
- Product: `Gaming Keyboard`
- 通常キーボード: Interface 0
- ベンダーHID: Interface 1
- 直接RGB: Interface 1 / `Col08` / Report ID `8` / 全長382バイト
- ISPコマンド: Interface 1 / `Col05` / Report ID `5` / 全長6バイト
- ISP転送: Interface 1 / `Col06` / Report ID `6` / 全長1032バイト

VID/PIDはRedragon K617など別機種でも使われる。VID/PID一致だけで互換と判断せず、Interface、Collection、Report Descriptor、実機発色をすべて確認すること。

## 実測済みRGBプロトコル

- Report 8は`08 0A 7A 01`の4バイトヘッダーに、126スロット分のRGB各3バイトを続ける。
- パケット全長は382バイトで、色順はR-G-Bである。
- 動画モードへ入るには、全スロット0のReport 8を16ms間隔で3回送る初期化が必須である。
- 初期化なしの単発Report 8は、HID送信自体が成功しても実機では消灯だけを起こす。送信バイト数だけで成功と判定してはならない。
- 3回初期化後、全キーの赤、緑、青、消灯を実機目視で確認済み。
- 30FPSで150フレームのレインボー送信が完走済み。
- 終了時の消灯と、`Fn+M`によるキーボード内蔵発光モードへの復帰を確認済み。
- 主要実装は`z88_rgb.py`、利用者向けCLIは`rgb_cli.py`、再現用スモークテストは`direct_rgb_probe.py`である。

## Codex状態連携

- `install_codex_hooks.py`でユーザー共通の`~/.codex/hooks.json`へ公式Codex lifecycle Hooksを登録する。
- `.codex/hooks/codex_led_hook.py`がstdinのJSONを読み、`codex_led_status.py`で状態色へ変換する。
- 状態色は`roflsunriz/esp32-codex-notifications`の意味に合わせる。
  - 白: セッション待機中
  - 青: 処理中、ツール実行中
  - 緑: ターン完了
  - 黄: 承認待ち
  - 赤: ツール実行エラー
  - 消灯: セッション終了
- 手動のHook JSON経路で青、黄、赤、緑の送信成功を確認済み。
- ユーザー共通Hooksは、設定追加後に定義を確認して信頼し、新しく開いたCodexタスクで初回実行確認が必要である。現在のタスク開始後に追加したHooksが自動再読込されると仮定しない。
- LED連携失敗時もCodex本体は継続し、`logs/codex-led-hook.log`へエラーを残す。

## ファームウェア退避の実測結果

- ファームウェア領域: 61,440バイト
- SHA-256: `0de319edb11a4a532bf27cc263a6491b4a98e666a627b0df6cd51a547f9fabe8`
- 識別文字列: `CK 8907 3.0`、`CK 8907 5.0`
- `backup_firmware.py`は次の3コマンドだけを許可する。
  - `0x75`: ISPモードへ移行
  - `0x52`: 読出し開始
  - `0x5A`: 再起動要求
- 次の破壊的コマンドは`isp_protocol.py`で拒否し、送ってはならない。
  - `0x55`: LJMP変更
  - `0x57`: フラッシュ書込み
  - `0x45`: フラッシュ消去
- Windows実機では退避完了後の再起動要求でUSBが切断状態となり、ケーブルの抜き差しで通常モードへ復帰した。
- 退避ファイル、比較用ファームウェア、Rizin一時ツールはGit管理外とする。

## 使用禁止

- Redditの旧Z88/CK104向けX2000更新ファームは`258A:1006`用であり、本機`258A:0049`へ書き込まない。
- K617向けReport 6テンプレートを、本機へそのまま送らない。
- `sinowisp read`を安全な読取り専用とみなさない。公式実装は読出し前に`0x55`を送り得るため、本リポジトリでは使用しない。
- 現行ファームウェアと物理復旧手段を確認せず、SMK、QMK類似ファーム、他機種純正ファームを書き込まない。
- Report 8の単発送信結果、VID/PID一致、ビルド成功だけで実機能の完成としない。

## 検証済み環境

- Microsoft Windows 11 Pro x64 `10.0.26200`
- Python `3.14.6`
- hidapi `0.15.0`
- Codex Desktop `26.818.5229.0`
- Rizin `0.9.1`（8051静的解析用、一時ツール）

## セットアップと検証

依存関係はリポジトリ内`.deps`へ導入する。

```powershell
python -m pip install --target .\.deps -r .\requirements.txt
```

変更後は少なくとも次を実行する。

```powershell
python -m unittest discover -s .\tests -v
python .\probe_device.py
python .\backup_firmware.py
python .\direct_rgb_probe.py
python .\rgb_cli.py solid FF0000 --seconds 1
python .\rgb_cli.py rainbow --seconds 5 --fps 30
pip-audit -r .\requirements.txt
```

実機へ送信するテストは、対象が`258A:0049`かつInterface 1の`Col08`へ一意に解決された場合だけ行う。ファーム退避の実行時はUSB再接続が必要になる前提で、利用者へ事前に伝える。

## 主要ファイル

- `z88_rgb.py`: 126スロットRGBフレーム生成とHID送信
- `rgb_cli.py`: 単色・レインボーCLI
- `codex_led_status.py`: Codexイベントと色の対応
- `install_codex_hooks.py`: 全プロジェクト共通のCodex Hooks設定
- `backup_firmware.py` / `isp_protocol.py`: 非破壊コマンド限定の退避経路
- `probe_device.py`: 読取り専用HID列挙
- `analyze_firmware.py`: ファーム識別・比較
- `docs/protocol-notes.md`: 実験履歴と根拠
- `how-to-update.md`: 更新・検証・復旧手順

## 既知の制約

- Report 8の126スロットとJIS 109キー名の完全対応表は未確定である。
- 現在のCodex連携はキーボード全体を状態色へ変える。キー単位の状態表示は、スロット対応表を実測してから追加する。
- 自動Hook読込みの最終確認は、新しく開いた信頼済みCodexタスクで行う。

## 参考資料の扱い

- `roflsunriz/esp32-codex-notifications`: 状態色の意味とCodex連携設計の参考
- OpenAI公式Codex Hooks: lifecycleイベントとJSON入力仕様の正とする資料
- RedditのZ88/CK104投稿: 歴史的な調査入口。旧ファームを本機へ適用する根拠にはしない
- Sinodragon / fizz-rgb / BYK916関連実装: Report 8構造と動画モード調査の比較対象。実機確認を省略する根拠にはしない
