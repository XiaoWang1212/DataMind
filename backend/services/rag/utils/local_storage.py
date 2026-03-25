import logging
import time
import shutil
from pathlib import Path
from io import BytesIO
from src.rag import settings
from src.rag.utils import singleton


@singleton
class LocalFileStorage:
    def __init__(self):
        self.root = None
        self.__open__()

    def __open__(self):
        try:
            if self.root:
                self.__close__()
        except Exception:
            pass

        try:
            # 從 settings 讀取配置
            storage_path = getattr(settings, 'LOCAL_STORAGE_PATH', './storage')
            self.root = Path(storage_path).resolve()
            self.root.mkdir(parents=True, exist_ok=True)
            logging.info(f"Local storage initialized at: {self.root}")
        except Exception:
            logging.exception(f"Fail to initialize local storage")

    def __close__(self):
        self.root = None

    def health(self):
        """健康檢查 - 與 MinIO 介面一致"""
        bucket, fnm, binary = "txtxtxtxt1", "txtxtxtxt1", b"_t@@@1"
        if not self.bucket_exists(bucket):
            (self.root / bucket).mkdir(parents=True, exist_ok=True)

        file_path = self.root / bucket / fnm
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(binary)
        return True

    def put(self, bucket, fnm, binary):
        """上傳檔案 - 與 MinIO 介面一致"""
        for _ in range(3):
            try:
                # 確保 bucket 目錄存在
                bucket_path = self.root / bucket
                bucket_path.mkdir(parents=True, exist_ok=True)

                # 寫入檔案
                file_path = bucket_path / fnm
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(binary)

                logging.debug(f"Stored: {bucket}/{fnm} ({len(binary)} bytes)")
                return True
            except Exception:
                logging.exception(f"Fail to put {bucket}/{fnm}:")
                time.sleep(1)

    def rm(self, bucket, fnm):
        """刪除檔案 - 與 MinIO 介面一致"""
        try:
            file_path = self.root / bucket / fnm
            if file_path.exists():
                file_path.unlink()
                logging.debug(f"Removed: {bucket}/{fnm}")
        except Exception:
            logging.exception(f"Fail to remove {bucket}/{fnm}:")

    def get(self, bucket, filename):
        """讀取檔案 - 與 MinIO 介面一致"""
        for _ in range(1):
            try:
                file_path = self.root / bucket / filename
                if file_path.exists() and file_path.is_file():
                    data = file_path.read_bytes()
                    logging.debug(f"Retrieved: {bucket}/{filename} ({len(data)} bytes)")
                    return data
                else:
                    logging.warning(f"File not found: {bucket}/{filename}")
                    return None
            except Exception:
                logging.exception(f"Fail to get {bucket}/{filename}")
                time.sleep(1)
        return None

    def obj_exist(self, bucket, filename):
        """檢查檔案存在 - 與 MinIO 介面一致"""
        try:
            file_path = self.root / bucket / filename
            exists = file_path.exists() and file_path.is_file()
            return exists
        except Exception:
            logging.exception(f"obj_exist {bucket}/{filename} got exception")
            return False

    def bucket_exists(self, bucket):
        """檢查 bucket 存在 - 與 MinIO 介面一致"""
        try:
            bucket_path = self.root / bucket
            exists = bucket_path.exists() and bucket_path.is_dir()
            return exists
        except Exception:
            logging.exception(f"bucket_exist {bucket} got exception")
            return False

    def get_presigned_url(self, bucket, fnm, expires):
        """生成預簽名 URL - 與 MinIO 介面一致

        注意: 本地儲存返回檔案絕對路徑
        生產環境建議配合 FastAPI StaticFiles 提供 HTTP URL
        """
        for _ in range(10):
            try:
                file_path = self.root / bucket / fnm
                if file_path.exists():
                    # 返回絕對路徑（開發環境）
                    # 生產環境可返回: f"/storage/{bucket}/{fnm}"
                    return str(file_path.absolute())
                else:
                    logging.warning(f"File not found for presigned URL: {bucket}/{fnm}")
                    return None
            except Exception:
                logging.exception(f"Fail to get_presigned {bucket}/{fnm}:")
                time.sleep(1)
        return None

    def remove_bucket(self, bucket):
        """刪除整個 bucket - 與 MinIO 介面一致"""
        try:
            bucket_path = self.root / bucket
            if bucket_path.exists() and bucket_path.is_dir():
                shutil.rmtree(bucket_path)
                logging.info(f"Removed bucket: {bucket}")
        except Exception:
            logging.exception(f"Fail to remove bucket {bucket}")
