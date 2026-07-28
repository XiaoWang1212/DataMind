import os
from huggingface_hub import snapshot_download

# 設定快取目錄
cache_dir = os.path.expanduser("~/.cache/huggingface")
model_name = "BAAI/bge-m3"

print(f"開始下載 {model_name}...")
print(f"下載位置: {cache_dir}")

try:
    model_path = snapshot_download(
        repo_id=model_name,
        cache_dir=cache_dir,
        local_dir_use_symlinks=False
    )
    print(f"✅ 下載完成！模型路徑: {model_path}")
except Exception as e:
    print(f"❌ 下載失敗: {e}")
