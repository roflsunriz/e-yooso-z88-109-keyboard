# 更新手順

## 前提

- Windows x64（実機検証: Windows 11 Pro `10.0.26200`）
- Python（実機検証: `3.14.6`）
- USB接続されたE-YOOSO Z88 109日本語配列 (`VID 258A / PID 0049`)

## 依存関係の更新

依存関係はリポジトリ内`.deps`へ導入する。CLIとHooksはこのパスを自動で読み込む。

```powershell
python -m pip install --target .\.deps -r .\requirements.txt
```

## 検証

単体テストと読み取り専用の実機プローブを実行する。

```powershell
python -m unittest discover -s .\tests -v
python .\probe_device.py
python .\backup_firmware.py
python .\direct_rgb_probe.py
```

`probe_device.py`、引数なしの`backup_firmware.py`、引数なしの`direct_rgb_probe.py`はdry-runであり、実機の状態を変更しない。Report 8は3回のゼロ色初期化後に本機でRGB制御できることを確認済みである。詳細は`docs/protocol-notes.md`を参照する。

`backup_firmware.py`は引数なしではdry-runのみを行う。実機バックアップ時は次を実行する。

```powershell
python .\backup_firmware.py --read-firmware
```

バックアップ処理はISP移行`0x75`、読出し開始`0x52`、再起動`0x5A`だけを使用し、LJMP変更`0x55`、書込み`0x57`、消去`0x45`を拒否する。Windows実機では退避後にUSBが切断状態となったため、完了後にケーブルを抜き差しする。生成される`firmware-dumps/`はGit管理外とする。

単色とレインボーの動作確認は次で行う。どちらも終了時に消灯する。キーボード内蔵の発光モードへ戻す場合は`Fn+M`を押す。

```powershell
python .\rgb_cli.py solid FF0000 --seconds 5
python .\rgb_cli.py rainbow --seconds 5 --fps 30
```

## Codex状態連携

プロジェクトの`.codex/hooks.json`は、Codexのライフサイクルを次の色へ割り当てる。

- 白: セッション待機中
- 青: ユーザープロンプトを受けて処理中、またはツール実行中
- 緑: ターン完了
- 黄: 承認待ち
- 赤: ツール実行エラー
- 消灯: セッション終了

Codexでこのプロジェクトを信頼し、Hooksの実行確認を承認する。初回利用前に`.deps`へ依存関係を導入しておく。

```powershell
python -m pip install --target .\.deps -r .\requirements.txt
```

HooksのLED連携に失敗してもCodex本体は継続し、エラーは`logs/codex-led-hook.log`へ記録される。

Hooks設定を追加・変更した場合は、既存タスクで自動再読込されると仮定せず、新しく開いた信頼済みCodexタスクで青→緑の状態変化を確認する。

## ロールバック

コードだけを戻す場合は、直前の正常なGitコミットへ戻す。Report 8動画モードからは`Fn+M`で内蔵発光へ復帰できる。ファーム退避後にUSBデバイスが消えた場合は、ケーブルを抜き差しする。
