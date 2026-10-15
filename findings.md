# findings.md

このリポジトリ固有の実現手段と調査知見の正本です。作業前に全文を読み、行動規範は [AGENTS.md](AGENTS.md) と [COMMON-AGENTS.md](COMMON-AGENTS.md) に従ってください。移動元の本文は以下に保持しています。

## 共通方針の適用と具体的な例外

| 項目 | このリポジトリでの扱い |
| --- | --- |
| 対象の共通ルール | 検証の言語別適用と実機条件 |
| 理由と適用範囲 | Python/HIDのWindowsツールとして、Bun向け検証の代わりに既存Python検査を用いる。実機送信は識別条件と利用者へのUSB再接続案内を満たす場合に限る。 |
| 同等の品質を保つ手段・検証 | unittest・構文検査・pip監査と、対象機器を識別した上での手動確認を分ける。HID送信成功だけでは発色成功としない。根拠: `requirements.txt`、`tests/`、[更新手順](how-to-update.md)、[検証記録](verification.md)。 |

## 文書の役割と適用範囲

- 共通ルールの対象は「ローカル AGENTS.md との関係」「設計と実装方針」「検証」「ドキュメント」。この文書は本リポジトリの構成と既存運用に適用し、共通の行動規範を弱めません。
- ファイル配置・ツール・環境をここに集約する理由は、作業規範と実装上の事実を分け、次の作業者が根拠を確認できるようにするためです。下記の既存手段は同じ対象の設定・CI・検証記録と照合して使います。
- README は利用開始・操作、更新手順は更新と復旧、verification.md は検証手順と実測証跡、専門の設計・研究文書は詳細な根拠を担います。これらの用途は維持し、この文書から参照します。
- 更新・検証の代替は一律のBunコマンドに固定せず、下記の採用技術と既存CIに対応する検査を使います。実行不能や未検証の条件は成功扱いせず verification.md に残します。

<a id="agents-1"></a>

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

移動元: `AGENTS.md`。

<a id="agents-2"></a>

## 実測済みRGBプロトコル

- Report 8は`08 0A 7A 01`の4バイトヘッダーに、126スロット分のRGB各3バイトを続ける。
- パケット全長は382バイトで、色順はR-G-Bである。
- 動画モードへ入るには、全スロット0のReport 8を16ms間隔で3回送る初期化が必須である。
- 初期化なしの単発Report 8は、HID送信自体が成功しても実機では消灯だけを起こす。送信バイト数だけで成功と判定してはならない。
- 3回初期化後、全キーの赤、緑、青、消灯を実機目視で確認済み。
- 30FPSで150フレームのレインボー送信が完走済み。
- 終了時の消灯と、`Fn+M`によるキーボード内蔵発光モードへの復帰を確認済み。
- 主要実装は`z88_rgb.py`、利用者向けCLIは`rgb_cli.py`、再現用スモークテストは`direct_rgb_probe.py`である。

移動元: `AGENTS.md`。

<a id="agents-3"></a>

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

移動元: `AGENTS.md`。

<a id="agents-4"></a>

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

移動元: `AGENTS.md`。

<a id="agents-5"></a>

## 検証済み環境

- Microsoft Windows 11 Pro x64 `10.0.26200`
- Python `3.14.6`
- hidapi `0.15.0`
- Codex Desktop `26.818.5229.0`
- Rizin `0.9.1`（8051静的解析用、一時ツール）

移動元: `AGENTS.md`。

<a id="agents-6"></a>

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

移動元: `AGENTS.md`。

<a id="agents-7"></a>

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
- `build_release.py`: 再現可能な配布ZIP・SHA-256・リリースノート生成
- `.github/workflows/release.yml`: Windows検証とタグ駆動のGitHub Release公開

移動元: `AGENTS.md`。

<a id="agents-8"></a>

## 既知の制約

- Report 8の126スロットとJIS 109キー名の完全対応表は未確定である。
- 現在のCodex連携はキーボード全体を状態色へ変える。キー単位の状態表示は、スロット対応表を実測してから追加する。
- 複数タスクでは最後に`SessionStart`または`UserPromptSubmit`を受けたタスクを前面として優先する。Hooksに画面フォーカス専用イベントはないため、タブ切替だけでは表示対象は変わらない。
- 自動Hook読込みの最終確認は、新しく開いた信頼済みCodexタスクで行う。

移動元: `AGENTS.md`。

<a id="readme-1"></a>

## 実機検証結果

Windows 11 Pro x64環境で、次を確認しました。

| 検証項目 | 結果 |
| --- | --- |
| 初期化なしの単発Report 8 | HID送信は成功するが実機は消灯のみ |
| ゼロ色Report 8を16ms間隔で3回送信 | 動画モード初期化に成功 |
| 全キー赤→緑→青→消灯 | 実機目視で成功 |
| 単色CLI | 成功 |
| 30FPSレインボー、5秒、150フレーム | 全フレーム送信完走 |
| `Fn+M`による内蔵発光への復帰 | 成功 |
| 61,440バイトのファーム退避 | 成功、書込み・消去命令は未使用 |
| Codex Hook JSONの青・黄・赤・緑変換 | 手動のend-to-end経路で送信成功 |

Report 8は`08 0A 7A 01`の4バイトヘッダーと、126スロット分のR-G-B各3バイトで構成します。動画モードの3回初期化を省略すると、送信バイト数が正しくても発色しません。

### 検証環境

- Microsoft Windows 11 Pro x64 `10.0.26200`
- Python `3.14.6`
- hidapi `0.15.0`
- Codex Desktop `26.818.5229.0`
- Rizin `0.9.1`（8051ファームの静的解析に使用）

移動元: `README.md`。

<a id="readme-2"></a>

## 開発と検証

```powershell
python -m unittest discover -s .\tests -v
python .\probe_device.py
python .\backup_firmware.py
python .\direct_rgb_probe.py
pip-audit -r .\requirements.txt
```

実験履歴とプロトコル根拠は[プロトコル調査記録](docs/protocol-notes.md)、更新・復旧手順は[更新手順](how-to-update.md)を参照してください。

移動元: `README.md`。

<a id="readme-3"></a>

## 主要ファイル

- `z88_rgb.py`: RGBパケット生成とHID送信
- `rgb_cli.py`: 単色・レインボーCLI
- `codex_led_status.py`: Codex状態色変換
- `install_codex_hooks.py`: 全プロジェクト共通のCodex lifecycle Hooks設定
- `backup_firmware.py` / `isp_protocol.py`: 破壊的命令を拒否する退避経路
- `probe_device.py`: 読取り専用HIDプローブ
- `analyze_firmware.py`: 8051ファーム識別・比較
- `docs/protocol-notes.md`: 実測履歴

移動元: `README.md`。

<a id="readme-4"></a>

## 依存更新の自動処理

Dependabot は対象の依存関係を毎週確認します。patch／minor 更新は PR のチェック（検証とリリース）が成功した後に自動で squash merge されます。CI の失敗ジョブは 1 回だけ再実行します。再失敗した PR は残して手動で修正します。major 更新は手動で確認します。

移動元: `README.md`。

## 根拠と検証記録

- [README.md](README.md): 利用者向けの導入と操作。
- [verification.md](verification.md): 検証手順、実測結果、未確認事項。
- [how-to-update.md](how-to-update.md): 更新・復旧の実手順。

## 文書配置を検査するテストと配布経路

`tests/test_documentation.py` は機器の識別値・RGB初期化条件・復帰操作とfirmware hashを正本 `findings.md` で検査し、AGENTSとREADMEから正本へ到達できることを別に確認する。配置変更時は期待する機器情報やhashを緩めず、読み取り先と参照を合わせる。READMEから分離した情報が配布ZIPでも読めるよう、`build_release.py` の `RELEASE_METADATA` に `findings.md` を含める。`tests/test_build_release.py` が同梱対象と再現可能なZIP生成を検証する。
