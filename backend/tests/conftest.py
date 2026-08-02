"""讓測試可以直接 import backend 底下的模組（services.xxx、routes.xxx）。

backend/ 不是安裝成套件（pyproject 設了 package = false），所以
測試執行時要自己把 backend/ 加進 sys.path。
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
