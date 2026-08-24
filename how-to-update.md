# 更新手順

## 安定版への更新

[GitHub Releases](https://github.com/roflsunriz/e-yooso-z88-109-keyboard/releases)から対象バージョンのZIPと`.sha256`を同じフォルダーへダウンロードする。展開前にPowerShellでSHA-256を照合する。

```powershell
$archive = ".\e-yooso-z88-109-keyboard-v1.0.0.zip"
$expected = ((Get-Content "$archive.sha256") -split '\s+')[0]
$actual = (Get-FileHash -Algorithm SHA256 $archive).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "SHA-256が一致しません" }
```

照合後に別フォルダーへ展開し、既存の`logs/`、`.deps/`、`firmware-dumps/`を上書きしない。下記の依存関係導入と検証を行ってから、必要に応じてCodex Hooksを再登録する。

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

`install_codex_hooks.py`はユーザー共通の`~/.codex/hooks.json`へ設定を登録し、全プロジェクトのCodexライフサイクルを次の色へ割り当てる。

- 白: セッション待機中
- 青: ユーザープロンプトを受けて処理中、またはツール実行中
- 緑: ターン完了
- 黄: 承認待ち
- 赤: ツール実行エラー
- 消灯: セッション終了

初回利用前に`.deps`へ依存関係を導入し、ユーザー共通Hooksを登録する。

```powershell
python -m pip install --target .\.deps -r .\requirements.txt
python .\install_codex_hooks.py
```

CodexのHooks画面で新しいユーザー共通フック定義を確認して信頼する。Codexはフック定義のハッシュ単位で信頼状態を記録するため、設定を変更した場合も再度確認して信頼する。

HooksのLED連携に失敗してもCodex本体は継続し、エラーは`logs/codex-led-hook.log`へ記録される。

複数タスクの状態は`logs/codex-led-hook-state.json`へ集約され、最後に`SessionStart`または`UserPromptSubmit`を受けたタスクだけが表示を占有する。画面フォーカスだけを通知するHookはないため、別タスクへタブを切り替えた場合は、そのタスクでプロンプトを送信して表示対象を切り替える。

Hooks設定を追加・変更した場合は、変更後のフック定義を再度信頼する。既存タスクで自動再読込されると仮定せず、任意のプロジェクトで新しく開いたCodexタスクの青→緑を確認する。ユーザー共通設定はこのリポジトリ内のスクリプトを絶対パスで参照するため、リポジトリを移動した場合はインストーラーを再実行する。

## ロールバック

コードだけを戻す場合は、直前の正常なGitコミットへ戻す。Report 8動画モードからは`Fn+M`で内蔵発光へ復帰できる。ファーム退避後にUSBデバイスが消えた場合は、ケーブルを抜き差しする。

## メンテナー向けリリース手順

1. `CHANGELOG.md`の`Unreleased`を`## [MAJOR.MINOR.PATCH] - YYYY-MM-DD`へ確定し、比較リンクを更新する。
2. 本書の検証、実機RGB確認、`pip-audit -r .\requirements.txt`を完走する。
3. `main`へ日本語Conventional Commits形式でコミットしてプッシュし、GitHub Actionsの`Windows検証`が成功するまで待つ。
4. 同じコミットへ注釈付きタグを作成し、タグだけをプッシュする。

```powershell
git tag -a v1.0.0 -m "v1.0.0"
git push origin v1.0.0
```

`.github/workflows/release.yml`はタグを`vMAJOR.MINOR.PATCH`として検証し、Windows上のテストと依存監査に成功した場合だけ、配布ZIP、SHA-256、`CHANGELOG.md`から抽出したリリースノートを公開する。公開済みタグは付け替えない。公開後に修正が必要な場合は次のパッチバージョンでリリースし、ワークフロー自体の一時障害だけであれば同じ実行を再実行する。
