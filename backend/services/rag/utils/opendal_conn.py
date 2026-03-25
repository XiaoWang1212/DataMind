import opendal
import logging
import os

from src.rag.utils import singleton


def get_opendal_config():
    """
    獲取 OpenDAL 配置

    TODO: 從 .env 配置替代 YAML
    目前使用環境變數或返回空配置
    """
    try:
        # 從環境變數讀取 OpenDAL 配置
        scheme = os.getenv("OPENDAL_SCHEME", "")
        if not scheme:
            logging.warning("OPENDAL_SCHEME not set, returning empty config")
            return {}

        kwargs = {"scheme": scheme}
        logging.info("Loaded OpenDAL configuration from env: %s", kwargs)
        return kwargs
    except Exception as e:
        logging.error("Failed to load OpenDAL configuration: %s", str(e))
        raise


@singleton
class OpenDALStorage:
    def __init__(self):
        self._kwargs = get_opendal_config()
        self._scheme = self._kwargs.get('scheme')
        self._operator = opendal.Operator(**self._kwargs)

        logging.info("OpenDALStorage initialized successfully")

    def health(self):
        bucket, fnm, binary = "txtxtxtxt1", "txtxtxtxt1", b"_t@@@1"
        r = self._operator.write(f"{bucket}/{fnm}", binary)
        return r

    def put(self, bucket, fnm, binary):
        self._operator.write(f"{bucket}/{fnm}", binary)

    def get(self, bucket, fnm):
        return self._operator.read(f"{bucket}/{fnm}")

    def rm(self, bucket, fnm):
        self._operator.delete(f"{bucket}/{fnm}")
        self._operator.__init__()

    def scan(self, bucket, fnm):
        return self._operator.scan(f"{bucket}/{fnm}")

    def obj_exist(self, bucket, fnm):
        return self._operator.exists(f"{bucket}/{fnm}")
