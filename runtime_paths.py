"""リポジトリ内へ導入した実行時依存をPython検索パスへ追加する。"""

from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent
LOCAL_DEPENDENCIES = REPOSITORY_ROOT / ".deps"


def activate_local_dependencies() -> None:
    dependency_path = str(LOCAL_DEPENDENCIES)
    if LOCAL_DEPENDENCIES.is_dir() and dependency_path not in sys.path:
        sys.path.insert(0, dependency_path)
