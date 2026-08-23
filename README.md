# E-YOOSO Z88 109 LED制御

E-YOOSO（e元素）Z88 109キー日本語配列キーボードを、ファームウェアを書き換えずWindowsから24ビットRGB制御するプロジェクトです。単色・アニメーション・任意の126スロットRGBフレームに対応し、Codexの処理状態をキーボード全体の色で表示できます。

## 対象モデル

このリポジトリで実機検証した対象は、次のモデルです。

| 項目 | 実測値 |
| --- | --- |
| 製品 | E-YOOSO Z88 109キー日本語配列 |
| 販売型番 | `Z-88RGB109` / `Z88RGB109JP` |
| 接続 | USB Type-C有線 |
| USB VID/PID | `258A:0049` |
| Manufacturer | `BY Tech` |
| Product | `Gaming Keyboard` |
| 直接RGB | Interface 1 / `Col08` / Report ID 8 |
| Report 8全長 | 382バイト |

同じ`258A:0049`はRedragon K617など別機種でも使われます。本実装はVID/PIDだけでなく、Interface 1の`Col08`が一意に見つかった場合だけRGBデータを送信します。

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

## セットアップ

依存関係はリポジトリ内の`.deps`へ導入します。システムPythonへ直接追加する必要はありません。

```powershell
python -m pip install --target .\.deps -r .\requirements.txt
```

接続中の実機を変更せず確認します。

```powershell
python .\probe_device.py
python .\backup_firmware.py
python .\direct_rgb_probe.py
```

`backup_firmware.py`と`direct_rgb_probe.py`は、引数なしではdry-runだけを行います。

## LEDを光らせる

全キーを赤で5秒点灯します。

```powershell
python .\rgb_cli.py solid FF0000 --seconds 5
```

30FPSのレインボーを5秒表示します。

```powershell
python .\rgb_cli.py rainbow --seconds 5 --fps 30
```

CLIは終了時に消灯します。キーボード内蔵の発光モードへ戻す場合は`Fn+M`を押してください。

コードから任意の126スロットを制御する場合は、`z88_rgb.Z88RGBController.send_frame()`へ126個の`(R, G, B)`を渡します。JISキー名とスロット番号の完全対応表はまだ実測途中です。

## Codexとの連携

`install_codex_hooks.py`がユーザー共通の`~/.codex/hooks.json`へ[公式Codex lifecycle Hooks](https://learn.chatgpt.com/docs/hooks)を登録し、どのプロジェクトでも[esp32-codex-notifications](https://github.com/roflsunriz/esp32-codex-notifications)と同じ状態色へ変換します。OpenAI APIキーやPC側の常駐ブリッジは不要です。

| 色 | Codex状態 | 主なHook |
| --- | --- | --- |
| 白 | セッション待機中 | `SessionStart` |
| 青 | 処理中、ツール実行中 | `UserPromptSubmit`、`PreToolUse`、成功した`PostToolUse` |
| 緑 | ターン完了 | `Stop` |
| 黄 | 承認待ち | `PermissionRequest` |
| 赤 | ツール実行エラー | 失敗した`PostToolUse` |
| 消灯 | セッション終了 | `SessionEnd` |

ユーザー共通Hooksを登録するため、リポジトリ直下で次を実行します。

```powershell
python .\install_codex_hooks.py
```

1. Hooks画面で新しいユーザー共通フック定義を確認して信頼します。
2. 任意のプロジェクトで新しいタスクを開き、プロンプト送信時の青→緑を確認します。
3. Hooksが失敗した場合は`logs/codex-led-hook.log`を確認します。

ユーザー共通設定はこのリポジトリ内のスクリプトを絶対パスで参照します。リポジトリを移動した場合はインストーラーを再実行してください。フック定義を変更すると再確認が必要です。変更後の定義を再度信頼し、新しいタスクで確認してください。現在のタスクを開いた後でHooksを追加・変更した場合、そのタスクが設定を自動再読込すると仮定しないでください。

複数のCodexタスクが並列に動く場合は、全タスクの状態を`logs/codex-led-hook-state.json`へ集約し、最後に`SessionStart`または`UserPromptSubmit`を受けた前面タスクの色だけを表示します。バックグラウンドタスクのツール実行は前面色を上書きしません。Codex Hooksには画面フォーカス専用イベントがないため、タブを切り替えただけでは優先タスクは変わらず、切替先でプロンプトを送信した時点で表示対象が移ります。

## ファームウェアの退避と安全性

実測した現行ファームウェアは61,440バイトで、SHA-256は次の値です。

```text
0de319edb11a4a532bf27cc263a6491b4a98e666a627b0df6cd51a547f9fabe8
```

退避を実行する場合は、完了後にUSBケーブルを抜き差しできる状態で行います。

```powershell
python .\backup_firmware.py --read-firmware
```

この退避経路が許可するのは、ISP移行`0x75`、読出し開始`0x52`、再起動要求`0x5A`だけです。LJMP変更`0x55`、書込み`0x57`、消去`0x45`は`isp_protocol.py`が拒否します。Windows実機では退避後にUSBが切断状態となり、ケーブルの抜き差しで通常起動へ戻りました。

次は行わないでください。

- `258A:1006`用の旧Z88/CK104 X2000ファームを本機へ書き込む
- K617用Report 6テンプレートを本機へ送る
- 現行ファームと物理復旧手段を確認せず、別機種ファームや実験ファームを書き込む
- 通常の`sinowisp read`を完全な読取り専用とみなす

退避ファイルは`firmware-dumps/`、解析ツールは`.tools/`へ保存され、どちらもGit管理外です。

## 開発と検証

```powershell
python -m unittest discover -s .\tests -v
python .\probe_device.py
python .\backup_firmware.py
python .\direct_rgb_probe.py
pip-audit -r .\requirements.txt
```

実験履歴とプロトコル根拠は[プロトコル調査記録](docs/protocol-notes.md)、更新・復旧手順は[更新手順](how-to-update.md)を参照してください。

## 主要ファイル

- `z88_rgb.py`: RGBパケット生成とHID送信
- `rgb_cli.py`: 単色・レインボーCLI
- `codex_led_status.py`: Codex状態色変換
- `install_codex_hooks.py`: 全プロジェクト共通のCodex lifecycle Hooks設定
- `backup_firmware.py` / `isp_protocol.py`: 破壊的命令を拒否する退避経路
- `probe_device.py`: 読取り専用HIDプローブ
- `analyze_firmware.py`: 8051ファーム識別・比較
- `docs/protocol-notes.md`: 実測履歴

## 参考資料

- [OpenAI公式Codex Hooks](https://learn.chatgpt.com/docs/hooks)
- [esp32-codex-notifications](https://github.com/roflsunriz/esp32-codex-notifications)
- [Sinodragon](https://github.com/EvanSunde/Sinodragon)
- [fizz-rgb](https://github.com/MrSchrodingers/fizz-rgb)
- [旧Z88/CK104 Reddit投稿](https://www.reddit.com/r/MechanicalKeyboards/comments/7sghkk/eelement_z88_104_keys_lighting_and_macro_editor/)
