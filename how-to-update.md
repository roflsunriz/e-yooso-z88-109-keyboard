# 更新手順

## 前提

- Windows
- Python 3.14以降
- USB接続されたE-YOOSO Z88 109 (`VID 258A / PID 0049`)

## 依存関係の更新

仮想環境を有効にした上で、次を実行する。

```powershell
python -m pip install -r .\requirements.txt
```

## 検証

単体テストと読み取り専用の実機プローブを実行する。

```powershell
python -m unittest discover -s .\tests -v
python .\probe_device.py
```

プローブはHID feature reportの送信やファームウェア変更を行わない。K617向けReport 8は本機で消灯のみを起こすため、再送信しない。詳細は`docs/protocol-notes.md`を参照する。

## ロールバック

コードだけを戻す場合は、直前の正常なGitコミットへ戻す。過去のReport 8試験後は`Fn+M`による発光モード切替で通常状態へ復帰できることを確認済みである。
