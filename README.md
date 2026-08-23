# E-YOOSO Z88 109 LED制御

E-YOOSO（e元素）Z88 109キー日本語配列キーボードを、ファームウェアを書き換えずWindowsから24ビットRGB制御するプロジェクトです。Codexの処理状態をキーボード全体の色で表示できます。

## 確認済み実機

- USB VID/PID: `258A:0049`
- Manufacturer: `BY Tech`
- Product: `Gaming Keyboard`
- Report 8: 382バイト

VID/PIDは他機種でも再利用されているため、スクリプトはInterface 1の`Col08`を一意に確認してから送信します。

## セットアップ

```powershell
python -m pip install --target .\.deps -r .\requirements.txt
```

## LED動作確認

```powershell
python .\rgb_cli.py solid FF0000 --seconds 5
python .\rgb_cli.py rainbow --seconds 5 --fps 30
```

終了時は消灯します。キーボード内蔵の発光モードへ戻す場合は`Fn+M`を押します。

## Codex状態連携

プロジェクト同梱の`.codex/hooks.json`が[公式Codex lifecycle Hooks](https://learn.chatgpt.com/docs/hooks)を受け取り、[esp32-codex-notifications](https://github.com/roflsunriz/esp32-codex-notifications)と同じ状態色へ変換します。

| 色 | 状態 |
| --- | --- |
| 白 | セッション待機中 |
| 青 | 処理中 |
| 緑 | ターン完了 |
| 黄 | 承認待ち |
| 赤 | ツール実行エラー |
| 消灯 | セッション終了 |

Codexでこのプロジェクトを信頼し、初回のHooks実行確認を承認してください。APIキーやPC側の常駐ブリッジは不要です。

## 安全性

- 通常のLED制御はRAM上の動画モードへReport 8を送り、フラッシュを変更しません。
- 現行ファームウェアの退避ツールは、LJMP変更、書込み、消去コマンドを実装上拒否します。
- ファームウェア本体と解析ツールはGit管理外です。

実機試験結果は[プロトコル調査記録](docs/protocol-notes.md)、更新・復旧手順は[更新手順](how-to-update.md)を参照してください。
