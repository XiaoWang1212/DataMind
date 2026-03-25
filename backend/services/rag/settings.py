"""RAG 設定模組 - 使用 src/config.py 替代 YAML 配置

完整重構自 api/settings.py，使用 .env 和 src/config.py 替代 YAML 配置
"""

import json
import os
import secrets
import logging
from datetime import date
from enum import Enum, IntEnum

from src.utils import get_project_base_directory
from src.configs import get_settings

# 載入統一配置
settings = get_settings()

# Server
RAG_CONF_PATH = os.path.join(get_project_base_directory(), "conf")

# 從 settings 獲取儲存和文檔引擎類型
STORAGE_IMPL_TYPE = settings.STORAGE_IMPL
DOC_ENGINE = os.environ.get("DOC_ENGINE", settings.DOC_ENGINE)

# 初始化配置字典（從 settings 屬性獲取）
ES = settings.ELASTICSEARCH_URL if DOC_ENGINE.lower() == 'elasticsearch' else {}
MINIO = settings.minio_config if STORAGE_IMPL_TYPE == 'MINIO' else {}
REDIS = {
    "host": f"{settings.REDIS_HOST}:{settings.REDIS_PORT}",
    "password": settings.REDIS_PASSWORD,
    "db": settings.REDIS_DB
}

# RAG 常數
DOC_MAXIMUM_SIZE = int(os.environ.get("MAX_CONTENT_LENGTH", 128 * 1024 * 1024))
DOC_BULK_SIZE = int(os.environ.get("DOC_BULK_SIZE", 4))
EMBEDDING_BATCH_SIZE = int(os.environ.get("EMBEDDING_BATCH_SIZE", 16))
SVR_QUEUE_NAME = "aioters_rag_svr_queue"
SVR_CONSUMER_GROUP_NAME = "aioters_rag_svr_task_broker"
PAGERANK_FLD = "pagerank_fea"
TAG_FLD = "tag_feas"

# GPU 並行設備檢測
PARALLEL_DEVICES = 0
try:
    import torch.cuda
    PARALLEL_DEVICES = torch.cuda.device_count()
    logging.info(f"found {PARALLEL_DEVICES} gpus")
except Exception:
    logging.info("can't import package 'torch'")

# ============ 全局變量（參考 api/settings.py）============
LIGHTEN = int(os.environ.get("LIGHTEN", "0"))

# LLM 配置
LLM = None
LLM_FACTORY = None
LLM_BASE_URL = None
CHAT_MDL = ""
EMBEDDING_MDL = ""
RERANK_MDL = ""
ASR_MDL = ""
IMAGE2TEXT_MDL = ""
CHAT_CFG = ""
EMBEDDING_CFG = ""
RERANK_CFG = ""
ASR_CFG = ""
IMAGE2TEXT_CFG = ""
API_KEY = None
PARSERS = None
HOST_IP = None
HOST_PORT = None
SECRET_KEY = None
FACTORY_LLM_INFOS = None

# 數據庫配置（已在 src/config.py 中處理）
DATABASE_TYPE = os.getenv("DB_TYPE", "postgres")
DATABASE = None

# 認證配置
AUTHENTICATION_CONF = None
CLIENT_AUTHENTICATION = None
HTTP_APP_KEY = None
GITHUB_OAUTH = None
FEISHU_OAUTH = None
OAUTH_CONFIG = None

# 文檔存儲連接
docStoreConn = None
retrievaler = None

# 用戶註冊開關
REGISTER_ENABLED = 1

# 沙箱配置
SANDBOX_ENABLED = 0
SANDBOX_HOST = None
STRONG_TEST_COUNT = int(os.environ.get("STRONG_TEST_COUNT", "8"))

# 內建模型
BUILTIN_EMBEDDING_MODELS = ["BAAI/bge-large-zh-v1.5@BAAI"]

# SMTP 配置
SMTP_CONF = None
MAIL_SERVER = ""
MAIL_PORT = 000
MAIL_USE_SSL = True
MAIL_USE_TLS = False
MAIL_USERNAME = ""
MAIL_PASSWORD = ""
MAIL_DEFAULT_SENDER = ()
MAIL_FRONTEND_URL = ""


# ============ 輔助函數 ============

def get_or_create_secret_key():
    """獲取或創建 SECRET_KEY

    參考: api/settings.py:77-92
    """
    secret_key = os.environ.get("aioters_rag_SECRET_KEY")
    if secret_key and len(secret_key) >= 32:
        return secret_key

    # 檢查環境變量中的配置
    configured_key = os.environ.get("SECRET_KEY")
    if configured_key and configured_key != str(date.today()) and len(configured_key) >= 32:
        return configured_key

    # 生成新的安全密鑰並警告
    new_key = secrets.token_hex(32)
    logging.warning(f"SECURITY WARNING: Using auto-generated SECRET_KEY. Generated key: {new_key}")
    return new_key


def _parse_model_entry(entry):
    """解析模型條目

    參考: api/settings.py:228-239

    Args:
        entry: 字符串或字典形式的模型配置

    Returns:
        標準化的模型配置字典
    """
    if isinstance(entry, str):
        return {"name": entry, "factory": None, "api_key": None, "base_url": None}
    if isinstance(entry, dict):
        name = entry.get("name") or entry.get("model") or ""
        return {
            "name": name,
            "factory": entry.get("factory"),
            "api_key": entry.get("api_key"),
            "base_url": entry.get("base_url"),
        }
    return {"name": "", "factory": None, "api_key": None, "base_url": None}


def _resolve_per_model_config(entry_dict, backup_factory, backup_api_key, backup_base_url):
    """解析每個模型的配置

    參考: api/settings.py:242-256

    Args:
        entry_dict: 模型配置字典
        backup_factory: 備用工廠名稱
        backup_api_key: 備用 API 密鑰
        backup_base_url: 備用基礎 URL

    Returns:
        完整的模型配置字典
    """
    name = (entry_dict.get("name") or "").strip()
    m_factory = entry_dict.get("factory") or backup_factory or ""
    m_api_key = entry_dict.get("api_key") or backup_api_key or ""
    m_base_url = entry_dict.get("base_url") or backup_base_url or ""

    if name and "@" not in name and m_factory:
        name = f"{name}@{m_factory}"

    return {
        "model": name,
        "factory": m_factory,
        "api_key": m_api_key,
        "base_url": m_base_url,
    }


def init_settings():
    """初始化所有設定

    完整重構自 api/settings.py:95-191
    使用環境變量和 conf/llm_factories.json 替代 YAML 配置
    """
    global LLM, LLM_FACTORY, LLM_BASE_URL, LIGHTEN, DATABASE_TYPE, DATABASE, FACTORY_LLM_INFOS, REGISTER_ENABLED

    LIGHTEN = int(os.environ.get("LIGHTEN", "0"))

    # 數據庫配置從 src/config.py 的 db_config 屬性獲取
    DATABASE = settings.db_config
    DATABASE_TYPE = DATABASE["type"]

    # LLM 配置從環境變量讀取
    LLM_FACTORY = os.environ.get("LLM_FACTORY", "")
    LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")
    LLM = {
        "factory": LLM_FACTORY,
        "base_url": LLM_BASE_URL,
        "api_key": os.environ.get("LLM_API_KEY", ""),
        "default_models": {}
    }

    try:
        REGISTER_ENABLED = int(os.environ.get("REGISTER_ENABLED", "1"))
    except Exception:
        pass

    # 載入 LLM 工廠信息
    try:
        with open(os.path.join(get_project_base_directory(), "conf", "llm_factories.json"), "r") as f:
            FACTORY_LLM_INFOS = json.load(f)["factory_llm_infos"]
    except Exception:
        FACTORY_LLM_INFOS = []

    global CHAT_MDL, EMBEDDING_MDL, RERANK_MDL, ASR_MDL, IMAGE2TEXT_MDL
    global CHAT_CFG, EMBEDDING_CFG, RERANK_CFG, ASR_CFG, IMAGE2TEXT_CFG

    if not LIGHTEN:
        EMBEDDING_MDL = BUILTIN_EMBEDDING_MODELS[0]

    global API_KEY, PARSERS, HOST_IP, HOST_PORT, SECRET_KEY

    API_KEY = os.environ.get("LLM_API_KEY", "")
    PARSERS = os.environ.get(
        "PARSERS",
        "naive:General,qa:Q&A,resume:Resume,manual:Manual,table:Table,paper:Paper,book:Book,laws:Laws,presentation:Presentation,picture:Picture,one:One,audio:Audio,email:Email,tag:Tag"
    )

    # 解析模型配置
    LLM_DEFAULT_MODELS = LLM.get("default_models", {}) or {}

    chat_entry = _parse_model_entry(os.environ.get("CHAT_MODEL", LLM_DEFAULT_MODELS.get("chat_model", CHAT_MDL)))
    embedding_entry = _parse_model_entry(os.environ.get("EMBEDDING_MODEL", LLM_DEFAULT_MODELS.get("embedding_model", EMBEDDING_MDL)))
    rerank_entry = _parse_model_entry(os.environ.get("RERANK_MODEL", LLM_DEFAULT_MODELS.get("rerank_model", RERANK_MDL)))
    asr_entry = _parse_model_entry(os.environ.get("ASR_MODEL", LLM_DEFAULT_MODELS.get("asr_model", ASR_MDL)))
    image2text_entry = _parse_model_entry(os.environ.get("IMAGE2TEXT_MODEL", LLM_DEFAULT_MODELS.get("image2text_model", IMAGE2TEXT_MDL)))

    CHAT_CFG = _resolve_per_model_config(chat_entry, LLM_FACTORY, API_KEY, LLM_BASE_URL)
    EMBEDDING_CFG = _resolve_per_model_config(embedding_entry, LLM_FACTORY, API_KEY, LLM_BASE_URL)
    RERANK_CFG = _resolve_per_model_config(rerank_entry, LLM_FACTORY, API_KEY, LLM_BASE_URL)
    ASR_CFG = _resolve_per_model_config(asr_entry, LLM_FACTORY, API_KEY, LLM_BASE_URL)
    IMAGE2TEXT_CFG = _resolve_per_model_config(image2text_entry, LLM_FACTORY, API_KEY, LLM_BASE_URL)

    CHAT_MDL = CHAT_CFG.get("model", "") or ""
    EMBEDDING_MDL = EMBEDDING_CFG.get("model", "") or ""
    RERANK_MDL = RERANK_CFG.get("model", "") or ""
    ASR_MDL = ASR_CFG.get("model", "") or ""
    IMAGE2TEXT_MDL = IMAGE2TEXT_CFG.get("model", "") or ""

    HOST_IP = os.environ.get("HOST", "127.0.0.1")
    HOST_PORT = os.environ.get("HOST_PORT")

    SECRET_KEY = get_or_create_secret_key()

    global AUTHENTICATION_CONF, CLIENT_AUTHENTICATION, HTTP_APP_KEY, GITHUB_OAUTH, FEISHU_OAUTH, OAUTH_CONFIG

    # 認證配置從環境變量讀取
    AUTHENTICATION_CONF = {}
    CLIENT_AUTHENTICATION = os.environ.get("CLIENT_AUTHENTICATION", "false").lower() == "true"
    HTTP_APP_KEY = os.environ.get("HTTP_APP_KEY")

    # OAuth 配置
    GITHUB_OAUTH = {}
    FEISHU_OAUTH = {}
    OAUTH_CONFIG = {}

    global docStoreConn, retrievaler

    # 初始化文檔存儲連接
    lower_case_doc_engine = DOC_ENGINE.lower()
    if lower_case_doc_engine == "elasticsearch":
        import src.rag.utils.es_conn
        docStoreConn = src.rag.utils.es_conn.ESConnection()
    else:
        raise Exception(f"Not supported doc engine: {DOC_ENGINE}")

    # 初始化檢索器
    from src.rag.nlp import search
    retrievaler = search.Dealer(docStoreConn)

    if int(os.environ.get("SANDBOX_ENABLED", "0")):
        global SANDBOX_HOST
        SANDBOX_HOST = os.environ.get("SANDBOX_HOST", "sandbox-executor-manager")

    global SMTP_CONF, MAIL_SERVER, MAIL_PORT, MAIL_USE_SSL, MAIL_USE_TLS
    global MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER, MAIL_FRONTEND_URL

    # SMTP 配置從環境變量讀取
    SMTP_CONF = {}
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "465"))
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "true").lower() == "true"
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "false").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")

    # MAIL_DEFAULT_SENDER 格式：name,email
    sender_str = os.environ.get("MAIL_DEFAULT_SENDER", "")
    if sender_str and "," in sender_str:
        parts = sender_str.split(",", 1)
        if len(parts) >= 2:
            MAIL_DEFAULT_SENDER = (parts[0].strip(), parts[1].strip())

    MAIL_FRONTEND_URL = os.environ.get("MAIL_FRONTEND_URL", "")


# ============ 枚舉類 ============

class CustomEnum(Enum):
    """自定義枚舉基類

    參考: api/settings.py:193-208
    """
    @classmethod
    def valid(cls, value):
        try:
            cls(value)
            return True
        except BaseException:
            return False

    @classmethod
    def values(cls):
        return [member.value for member in cls.__members__.values()]

    @classmethod
    def names(cls):
        return [member.name for member in cls.__members__.values()]


class RetCode(IntEnum, CustomEnum):
    """返回碼枚舉

    參考: api/settings.py:211-225
    """
    SUCCESS = 0
    NOT_EFFECTIVE = 10
    EXCEPTION_ERROR = 100
    ARGUMENT_ERROR = 101
    DATA_ERROR = 102
    OPERATING_ERROR = 103
    CONNECTION_ERROR = 105
    RUNNING = 106
    PERMISSION_ERROR = 108
    AUTHENTICATION_ERROR = 109
    UNAUTHORIZED = 401
    SERVER_ERROR = 500
    FORBIDDEN = 403
    NOT_FOUND = 404


# ============ 原有函數保持不變 ============

def print_rag_settings():
    """列印 RAG 設定"""
    logging.info(f"MAX_CONTENT_LENGTH: {DOC_MAXIMUM_SIZE}")
    logging.info(f"MAX_FILE_COUNT_PER_USER: {int(os.environ.get('MAX_FILE_NUM_PER_USER', 0))}")


def get_svr_queue_name(priority: int) -> str:
    """獲取服務佇列名稱"""
    if priority == 0:
        return SVR_QUEUE_NAME
    return f"{SVR_QUEUE_NAME}_{priority}"


def get_svr_queue_names():
    """獲取所有服務佇列名稱"""
    return [get_svr_queue_name(priority) for priority in [1, 0]]
