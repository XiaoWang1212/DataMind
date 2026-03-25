import random
import sys
import threading
import time

from src.utils import get_uuid
from src.utils import timeout
from src.utils import init_root_logger, get_project_base_directory
from src.rag.prompts.generator import keyword_extraction, question_proposal, content_tagging

import logging
import os
from datetime import datetime
import json
import xxhash
import copy
import re
from functools import partial
from io import BytesIO
from multiprocessing.context import TimeoutError
from timeit import default_timer as timer
import tracemalloc
import signal
import trio
import exceptiongroup
import faulthandler

import numpy as np
from src.constants import LLMType, ParserType
from src.services import DocumentService
from src.services.llm_service import LLMBundle
from src.services import TaskService, has_canceled
from src.services import File2DocumentService
from src.rag import settings
from src.utils import get_aioters_rag_version
from src.core.database import get_sync_session
from sqlalchemy.orm import Session

from src.rag.app import laws, paper, presentation, manual, qa, table, book, resume, picture, naive, one, audio, \
    email, tag
from src.rag.nlp import search, rag_tokenizer
from src.rag.raptor import RecursiveAbstractiveProcessing4TreeOrganizedRetrieval as Raptor
from src.rag.settings import DOC_MAXIMUM_SIZE, DOC_BULK_SIZE, EMBEDDING_BATCH_SIZE, SVR_CONSUMER_GROUP_NAME, get_svr_queue_name, get_svr_queue_names, print_rag_settings, TAG_FLD, PAGERANK_FLD
from src.rag.utils import num_tokens_from_string, truncate
from src.rag.utils.redis_conn import REDIS_CONN, RedisDistributedLock
from src.rag.utils.storage_factory import STORAGE_IMPL

BATCH_SIZE = 64

FACTORY = {
    "general": naive,
    ParserType.NAIVE.value: naive,
    ParserType.PAPER.value: paper,
    ParserType.BOOK.value: book,
    ParserType.PRESENTATION.value: presentation,
    ParserType.MANUAL.value: manual,
    ParserType.LAWS.value: laws,
    ParserType.QA.value: qa,
    ParserType.TABLE.value: table,
    ParserType.RESUME.value: resume,
    ParserType.PICTURE.value: picture,
    ParserType.ONE.value: one,
    ParserType.AUDIO.value: audio,
    ParserType.EMAIL.value: email,
    ParserType.KG.value: naive,
    ParserType.TAG.value: tag
}

UNACKED_ITERATOR = None

CONSUMER_NO = "0" if len(sys.argv) < 2 else sys.argv[1]
CONSUMER_NAME = "task_executor_" + CONSUMER_NO
BOOT_AT = datetime.now().astimezone().isoformat(timespec="milliseconds")
PENDING_TASKS = 0
LAG_TASKS = 0
DONE_TASKS = 0
FAILED_TASKS = 0

CURRENT_TASKS = {}

MAX_CONCURRENT_TASKS = int(os.environ.get('MAX_CONCURRENT_TASKS', "5"))
MAX_CONCURRENT_CHUNK_BUILDERS = int(os.environ.get('MAX_CONCURRENT_CHUNK_BUILDERS', "1"))
MAX_CONCURRENT_MINIO = int(os.environ.get('MAX_CONCURRENT_MINIO', '10'))
MAX_CONCURRENT_CHAT = int(os.environ.get('MAX_CONCURRENT_CHAT', '10'))
task_limiter = trio.Semaphore(MAX_CONCURRENT_TASKS)
chunk_limiter = trio.CapacityLimiter(MAX_CONCURRENT_CHUNK_BUILDERS)
embed_limiter = trio.CapacityLimiter(MAX_CONCURRENT_CHUNK_BUILDERS)
minio_limiter = trio.CapacityLimiter(MAX_CONCURRENT_MINIO)
kg_limiter = trio.CapacityLimiter(2)
chat_limiter = trio.CapacityLimiter(MAX_CONCURRENT_CHAT)
WORKER_HEARTBEAT_TIMEOUT = int(os.environ.get('WORKER_HEARTBEAT_TIMEOUT', '120'))
stop_event = threading.Event()


def signal_handler(sig, frame):
    logging.info("Received interrupt signal, shutting down...")
    stop_event.set()
    time.sleep(1)
    sys.exit(0)


# SIGUSR1 handler: start tracemalloc and take snapshot
def start_tracemalloc_and_snapshot(signum, frame):
    if not tracemalloc.is_tracing():
        logging.info("start tracemalloc")
        tracemalloc.start()
    else:
        logging.info("tracemalloc is already running")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_file = f"snapshot_{timestamp}.trace"
    snapshot_file = os.path.abspath(os.path.join(get_project_base_directory(), "logs", f"{os.getpid()}_snapshot_{timestamp}.trace"))

    snapshot = tracemalloc.take_snapshot()
    snapshot.dump(snapshot_file)
    current, peak = tracemalloc.get_traced_memory()
    if sys.platform == "win32":
        import  psutil
        process = psutil.Process()
        max_rss = process.memory_info().rss / 1024
    else:
        import resource
        max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    logging.info(f"taken snapshot {snapshot_file}. max RSS={max_rss / 1000:.2f} MB, current memory usage: {current / 10**6:.2f} MB, Peak memory usage: {peak / 10**6:.2f} MB")

# SIGUSR2 handler: stop tracemalloc
def stop_tracemalloc(signum, frame):
    if tracemalloc.is_tracing():
        logging.info("stop tracemalloc")
        tracemalloc.stop()
    else:
        logging.info("tracemalloc not running")

# Cache helper functions (replacement for removed graphrag.utils)
def get_llm_cache(llm_name, *args, **kwargs):
    """Get cached LLM response from Redis"""
    if not REDIS_CONN.is_alive():
        return None
    try:
        cache_key = f"llm_cache:{llm_name}:{xxhash.xxh64(json.dumps([args, kwargs], ensure_ascii=False).encode()).hexdigest()}"
        cached = REDIS_CONN.get(cache_key)
        if cached:
            return json.loads(cached) if cached.startswith('{') or cached.startswith('[') else cached
    except Exception as e:
        logging.warning(f"get_llm_cache error: {e}")
    return None


def set_llm_cache(llm_name, *args, value=None, **kwargs):
    """Set LLM response cache in Redis"""
    if not REDIS_CONN.is_alive():
        return False
    try:
        # Handle both positional value and kwargs
        if value is None and args:
            # If called like set_llm_cache(llm_name, input, output, type, params)
            # We need to extract the value from args
            if len(args) >= 2:
                value = args[1]
                args = (args[0],) + args[2:]

        cache_key = f"llm_cache:{llm_name}:{xxhash.xxh64(json.dumps([args, kwargs], ensure_ascii=False).encode()).hexdigest()}"
        cache_value = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
        return REDIS_CONN.set(cache_key, cache_value, 3600 * 24 * 7)  # 7 days cache
    except Exception as e:
        logging.warning(f"set_llm_cache error: {e}")
    return False


def get_tags_from_cache(kb_ids):
    """Get tags from Redis cache"""
    if not REDIS_CONN.is_alive():
        return None
    try:
        cache_key = f"tags_cache:{','.join(sorted([str(k) for k in kb_ids]))}"
        return REDIS_CONN.get(cache_key)
    except Exception as e:
        logging.warning(f"get_tags_from_cache error: {e}")
    return None


def set_tags_to_cache(kb_ids, tags):
    """Set tags to Redis cache"""
    if not REDIS_CONN.is_alive():
        return False
    try:
        cache_key = f"tags_cache:{','.join(sorted([str(k) for k in kb_ids]))}"
        cache_value = json.dumps(tags, ensure_ascii=False) if isinstance(tags, (dict, list)) else str(tags)
        return REDIS_CONN.set(cache_key, cache_value, 3600 * 24)  # 24 hours cache
    except Exception as e:
        logging.warning(f"set_tags_to_cache error: {e}")
    return False


class TaskCanceledException(Exception):
    def __init__(self, msg):
        self.msg = msg


# Database session helper for task_executor (sync version for Trio)
def get_db_session():
    """獲取同步數據庫 session（在 Trio 環境下使用）"""
    return next(get_sync_session())


# 同步 Service 包裝函數（在 Trio 環境下使用）
def sync_get_task(task_id: str):
    """同步版本的 get_task - JOIN Task, Document, Knowledgebase 獲取完整信息"""
    from src.models.document import Task, Document
    from src.models.knowledgebase import Knowledgebase
    from sqlalchemy import select

    db = get_db_session()
    try:
        # JOIN Task, Document, Knowledgebase 來獲取所有需要的字段
        query = (
            select(Task, Document, Knowledgebase)
            .join(Document, Task.doc_id == Document.id)
            .join(Knowledgebase, Document.kb_id == Knowledgebase.id)
            .where(Task.id == task_id)
        )
        result = db.execute(query)
        row = result.first()

        if row is None:
            return None

        task_obj, doc_obj, kb_obj = row

        # 將 Task, Document, Knowledgebase 對象合併為完整字典
        return {
            # From Task
            "id": task_obj.id,
            "doc_id": task_obj.doc_id,
            "from_page": task_obj.from_page,
            "to_page": task_obj.to_page,
            "task_type": task_obj.task_type,
            "retry_count": task_obj.retry_count,
            "progress": task_obj.progress,
            "progress_msg": task_obj.progress_msg,
            # From Document
            "parser_id": doc_obj.parser_id,
            "parser_config": doc_obj.parser_config,
            "name": doc_obj.name,
            "location": doc_obj.location,
            "size": doc_obj.size,
            "type": doc_obj.type,
            # From Knowledgebase
            "tenant_id": kb_obj.tenant_id,
            "kb_id": kb_obj.id,
            "embd_id": kb_obj.embd_id,
            "language": kb_obj.language or "English",
            "llm_id": "",  # llm_id 不在 Knowledgebase 模型中，使用空字符串
        }
    finally:
        db.close()


def sync_update_progress(task_id: str, info: dict):
    """同步版本的 update_progress"""
    from src.models import Task
    from sqlalchemy import select, update

    db = get_db_session()
    try:
        stmt = update(Task).where(Task.id == task_id).values(**info)
        db.execute(stmt)
        db.commit()
    finally:
        db.close()


def sync_get_storage_address(doc_id: str):
    """同步版本的 get_storage_address

    模仿參考專案 api/db/services/file2document_service.py 的邏輯：
    1. 先查詢 File2Document 關聯表
    2. 如果有關聯，則從 File 表取得 location (parent_id 作為 bucket, location 作為 name)
    3. 如果沒有關聯，則從 Document 表取得 location (kb_id 作為 bucket, location 作為 name)
    """
    from src.models import File2Document, File, Document
    from sqlalchemy import select

    db = get_db_session()
    try:
        # 先查詢 File2Document 關聯
        query = select(File2Document).where(File2Document.document_id == doc_id)
        result = db.execute(query)
        f2d = result.scalar_one_or_none()

        if f2d and f2d.file_id:
            # 如果有關聯的 File，從 File 表取得
            file_query = select(File).where(File.id == f2d.file_id)
            file_result = db.execute(file_query)
            file = file_result.scalar_one_or_none()
            if file:
                # parent_id 作為 bucket, location 作為 name
                return file.parent_id, file.location

        # 如果沒有關聯的 File，從 Document 表取得
        doc_query = select(Document).where(Document.id == doc_id)
        doc_result = db.execute(doc_query)
        doc = doc_result.scalar_one_or_none()
        if doc:
            # kb_id 作為 bucket, location 作為 name
            return doc.kb_id, doc.location

        return None, None
    finally:
        db.close()


def sync_update_chunk_ids(task_id: str, chunk_ids: str):
    """同步版本的 update_chunk_ids"""
    from src.models import Task
    from sqlalchemy import update

    db = get_db_session()
    try:
        stmt = update(Task).where(Task.id == task_id).values(chunk_ids=chunk_ids)
        db.execute(stmt)
        db.commit()
    finally:
        db.close()


def sync_increment_chunk_num(doc_id: str, dataset_id: str, token_count: int, chunk_count: int, dupe_count: int):
    """同步版本的 increment_chunk_num"""
    from src.models import Document
    from sqlalchemy import select, update

    db = get_db_session()
    try:
        # 獲取當前值
        query = select(Document).where(Document.id == doc_id)
        result = db.execute(query)
        doc = result.scalar_one_or_none()

        if doc:
            # 更新值
            stmt = update(Document).where(Document.id == doc_id).values(
                token_num=(doc.token_num or 0) + token_count,
                chunk_num=(doc.chunk_num or 0) + chunk_count,
            )
            db.execute(stmt)
            db.commit()
    finally:
        db.close()


def sync_update_document_progress(doc_id: str, progress: float, msg: str = ""):
    """同步版本的 update_document_progress - 更新文檔進度"""
    from src.models import Document
    from sqlalchemy import update

    db = get_db_session()
    try:
        stmt = update(Document).where(Document.id == doc_id).values(
            progress=progress,
            progress_msg=msg
        )
        db.execute(stmt)
        db.commit()
    finally:
        db.close()


async def notify_insight_file_status(
    doc_id: str,
    status: str,
    chunk_count: int = 0,
    error: str = None
):
    """通知 Insight 更新檔案處理狀態

    從 Document 的 meta_fields 中讀取 insight_file_id,
    如果存在則呼叫 Insight 的 webhook 更新檔案狀態

    Args:
        doc_id: 文檔 ID
        status: 處理狀態 (processing, completed, failed)
        chunk_count: 分塊數量
        error: 錯誤訊息 (可選)
    """
    try:
        from src.models import Document
        from src.clients.insight_client import InsightClient

        # 查詢 Document 的 meta_fields
        db = get_db_session()
        try:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                logging.warning(f"Document not found: {doc_id}")
                return

            meta_fields = doc.meta_fields or {}
            insight_file_id = meta_fields.get("insight_file_id")

            if not insight_file_id:
                # 沒有 insight_file_id,不需要回呼
                logging.debug(f"Document {doc_id} 沒有 insight_file_id,跳過 Insight 通知")
                return

            logging.info(f"通知 Insight 檔案狀態: file_id={insight_file_id}, status={status}")

            # 呼叫 InsightClient 更新狀態
            insight_client = InsightClient()
            await insight_client.update_file_status(
                file_id=int(insight_file_id),
                status=status,
                chunk_count=chunk_count if status == "completed" else None,
                error=error if status == "failed" else None,
                rag_document_id=doc_id
            )

            logging.info(f"成功通知 Insight 檔案狀態: file_id={insight_file_id}")

        finally:
            db.close()

    except Exception as e:
        # 通知失敗不應影響主流程,只記錄錯誤
        logging.error(f"通知 Insight 檔案狀態失敗: {e}", exc_info=True)


async def set_progress(task_id, from_page=0, to_page=-1, prog=None, msg="Processing..."):
    """Progress update function - 在 Trio 環境下使用同步數據庫操作

    Note: 雖然是 async 函數，但內部使用 trio.to_thread.run_sync 執行同步數據庫操作
    """
    try:
        if prog is not None and prog < 0:
            msg = "[ERROR]" + msg

        # has_canceled 是同步函數，直接調用
        cancel = has_canceled(task_id)

        if cancel:
            msg += " [Canceled]"
            prog = -1

        if to_page > 0:
            if msg:
                if from_page < to_page:
                    msg = f"Page({from_page + 1}~{to_page + 1}): " + msg
        if msg:
            msg = datetime.now().strftime("%H:%M:%S") + " " + msg
        d = {"progress_msg": msg}
        if prog is not None:
            d["progress"] = prog

        # 使用 trio.to_thread.run_sync 執行同步數據庫操作
        await trio.to_thread.run_sync(sync_update_progress, task_id, d)

        if cancel:
            raise TaskCanceledException(msg)
        logging.info(f"set_progress({task_id}), progress: {prog}, progress_msg: {msg}")
    except TaskCanceledException:
        # Re-raise TaskCanceledException
        raise
    except Exception as e:
        # Handle task not found
        if "not found" in str(e).lower() or isinstance(e, (KeyError, AttributeError)):
            logging.warning(f"set_progress({task_id}) got exception: Task not found")
            return
        logging.exception(f"set_progress({task_id}), progress: {prog}, progress_msg: {msg}, got exception")


async def collect():
    global CONSUMER_NAME, DONE_TASKS, FAILED_TASKS
    global UNACKED_ITERATOR

    svr_queue_names = get_svr_queue_names()
    try:
        if not UNACKED_ITERATOR:
            UNACKED_ITERATOR = REDIS_CONN.get_unacked_iterator(svr_queue_names, SVR_CONSUMER_GROUP_NAME, CONSUMER_NAME)
        try:
            redis_msg = next(UNACKED_ITERATOR)
        except StopIteration:
            for svr_queue_name in svr_queue_names:
                redis_msg = REDIS_CONN.queue_consumer(svr_queue_name, SVR_CONSUMER_GROUP_NAME, CONSUMER_NAME)
                if redis_msg:
                    break
    except Exception:
        logging.exception("collect got exception")
        return None, None

    if not redis_msg:
        return None, None
    msg = redis_msg.get_message()
    if not msg:
        logging.error(f"collect got empty message of {redis_msg.get_msg_id()}")
        redis_msg.ack()
        return None, None

    canceled = False
    # 獲取任務信息（使用同步數據庫操作）
    task = await trio.to_thread.run_sync(sync_get_task, msg["id"])

    if task:
        canceled = has_canceled(task["id"])
    if not task or canceled:
        state = "is unknown" if not task else "has been cancelled"
        FAILED_TASKS += 1
        logging.warning(f"collect task {msg['id']} {state}")
        redis_msg.ack()
        return None, None

    task_type = msg.get("task_type", "")
    task["task_type"] = task_type
    if task_type == "dataflow":
        task["tenant_id"]=msg.get("tenant_id", "")
        task["dsl"] = msg.get("dsl", "")
        task["dataflow_id"] = msg.get("dataflow_id", get_uuid())
        task["kb_id"] = msg.get("kb_id", "")
    return redis_msg, task


async def get_storage_binary(bucket, name):
    return await trio.to_thread.run_sync(lambda: STORAGE_IMPL.get(bucket, name))


def sync_progress_callback(task_id, from_page, to_page):
    """創建一個同步的 progress callback，供 chunk() 等同步函數使用

    因為 chunk() 是同步函數，但被 trio.to_thread.run_sync 調用，
    所以我們不能直接使用異步的 set_progress。
    這個 wrapper 直接調用同步的數據庫更新函數。
    """
    def callback(prog=None, msg=""):
        try:
            if prog is not None and prog < 0:
                msg = "[ERROR]" + msg

            cancel = has_canceled(task_id)

            if cancel:
                msg += " [Canceled]"
                prog = -1

            if to_page > 0:
                if msg:
                    if from_page < to_page:
                        msg = f"Page({from_page + 1}~{to_page + 1}): " + msg
            if msg:
                msg = datetime.now().strftime("%H:%M:%S") + " " + msg
            d = {"progress_msg": msg}
            if prog is not None:
                d["progress"] = prog

            # 直接調用同步數據庫更新
            sync_update_progress(task_id, d)

            if cancel:
                raise TaskCanceledException(msg)
            logging.info(f"sync_progress_callback({task_id}), progress: {prog}, progress_msg: {msg}")
        except TaskCanceledException:
            raise
        except Exception as e:
            logging.warning(f"sync_progress_callback({task_id}) got exception: {e}")

    return callback


@timeout(60*80, 1)
async def build_chunks(task, progress_callback):
    if task["size"] > DOC_MAXIMUM_SIZE:
        await set_progress(task["id"], prog=-1, msg="File size exceeds( <= %dMb )" %
                                              (int(DOC_MAXIMUM_SIZE / 1024 / 1024)))
        return []

    chunker = FACTORY[task["parser_id"].lower()]
    try:
        st = timer()
        # 獲取文檔存儲地址（使用同步數據庫操作）
        bucket, name = await trio.to_thread.run_sync(sync_get_storage_address, task["doc_id"])

        binary = await get_storage_binary(bucket, name)
        logging.info("From minio({}) {}/{}".format(timer() - st, task["location"], task["name"]))
    except TimeoutError:
        await progress_callback(-1, "Internal server error: Fetch file from minio timeout. Could you try it again.")
        logging.exception(
            "Minio {}/{} got timeout: Fetch file from minio timeout.".format(task["location"], task["name"]))
        raise
    except Exception as e:
        if re.search("(No such file|not found)", str(e)):
            await progress_callback(-1, "Can not find file <%s> from minio. Could you try it again?" % task["name"])
        else:
            await progress_callback(-1, "Get file from minio: %s" % str(e).replace("'", ""))
        logging.exception("Chunking {}/{} got exception".format(task["location"], task["name"]))
        raise

    try:
        async with chunk_limiter:
            # 創建同步的 progress callback 供 chunk() 使用
            sync_callback = sync_progress_callback(task["id"], task["from_page"], task["to_page"])
            cks = await trio.to_thread.run_sync(lambda: chunker.chunk(task["name"], binary=binary, from_page=task["from_page"],
                                to_page=task["to_page"], lang=task["language"], callback=sync_callback,
                                kb_id=task["kb_id"], parser_config=task["parser_config"], tenant_id=task["tenant_id"]))
        logging.info("Chunking({}) {}/{} done".format(timer() - st, task["location"], task["name"]))
    except TaskCanceledException:
        raise
    except Exception as e:
        await progress_callback(-1, "Internal server error while chunking: %s" % str(e).replace("'", ""))
        logging.exception("Chunking {}/{} got exception".format(task["location"], task["name"]))
        raise

    docs = []
    doc = {
        "doc_id": task["doc_id"],
        "kb_id": str(task["kb_id"])
    }
    if task.get("pagerank"):
        doc[PAGERANK_FLD] = int(task["pagerank"])
    st = timer()

    @timeout(60)
    async def upload_to_minio(document, chunk):
        try:
            d = copy.deepcopy(document)
            d.update(chunk)
            d["id"] = xxhash.xxh64((chunk["content_with_weight"] + str(d["doc_id"])).encode("utf-8", "surrogatepass")).hexdigest()
            d["create_time"] = str(datetime.now()).replace("T", " ")[:19]
            d["create_timestamp_flt"] = datetime.now().timestamp()
            if not d.get("image"):
                _ = d.pop("image", None)
                d["img_id"] = ""
                docs.append(d)
                return

            with BytesIO() as output_buffer:
                if isinstance(d["image"], bytes):
                    output_buffer.write(d["image"])
                    output_buffer.seek(0)
                else:
                    # If the image is in RGBA mode, convert it to RGB mode before saving it in JPEG format.
                    if d["image"].mode in ("RGBA", "P"):
                        converted_image = d["image"].convert("RGB")
                        #d["image"].close()  # Close original image
                        d["image"] = converted_image
                    try:
                        d["image"].save(output_buffer, format='JPEG')
                    except OSError as e:
                        logging.warning(
                            "Saving image of chunk {}/{}/{} got exception, ignore: {}".format(task["location"], task["name"], d["id"], str(e)))

                async with minio_limiter:
                    await trio.to_thread.run_sync(lambda: STORAGE_IMPL.put(task["kb_id"], d["id"], output_buffer.getvalue()))
                d["img_id"] = "{}-{}".format(task["kb_id"], d["id"])
                if not isinstance(d["image"], bytes):
                    d["image"].close()
                del d["image"]  # Remove image reference
                docs.append(d)
        except Exception:
            logging.exception(
                "Saving image of chunk {}/{}/{} got exception".format(task["location"], task["name"], d["id"]))
            raise

    async with trio.open_nursery() as nursery:
        for ck in cks:
            nursery.start_soon(upload_to_minio, doc, ck)

    el = timer() - st
    logging.info("MINIO PUT({}) cost {:.3f} s".format(task["name"], el))

    if task["parser_config"].get("auto_keywords", 0):
        st = timer()
        await progress_callback(msg="Start to generate keywords for every chunk ...")
        chat_mdl = LLMBundle(task["tenant_id"], LLMType.CHAT, llm_name=task["llm_id"], lang=task["language"])

        async def doc_keyword_extraction(chat_mdl, d, topn):
            cached = get_llm_cache(chat_mdl.llm_name, d["content_with_weight"], "keywords", {"topn": topn})
            if not cached:
                async with chat_limiter:
                    cached = await trio.to_thread.run_sync(lambda: keyword_extraction(chat_mdl, d["content_with_weight"], topn))
                set_llm_cache(chat_mdl.llm_name, d["content_with_weight"], cached, "keywords", {"topn": topn})
            if cached:
                d["important_kwd"] = cached.split(",")
                d["important_tks"] = rag_tokenizer.tokenize(" ".join(d["important_kwd"]))
            return
        async with trio.open_nursery() as nursery:
            for d in docs:
                nursery.start_soon(doc_keyword_extraction, chat_mdl, d, task["parser_config"]["auto_keywords"])
        await progress_callback(msg="Keywords generation {} chunks completed in {:.2f}s".format(len(docs), timer() - st))

    if task["parser_config"].get("auto_questions", 0):
        st = timer()
        await progress_callback(msg="Start to generate questions for every chunk ...")
        chat_mdl = LLMBundle(task["tenant_id"], LLMType.CHAT, llm_name=task["llm_id"], lang=task["language"])

        async def doc_question_proposal(chat_mdl, d, topn):
            cached = get_llm_cache(chat_mdl.llm_name, d["content_with_weight"], "question", {"topn": topn})
            if not cached:
                async with chat_limiter:
                    cached = await trio.to_thread.run_sync(lambda: question_proposal(chat_mdl, d["content_with_weight"], topn))
                set_llm_cache(chat_mdl.llm_name, d["content_with_weight"], cached, "question", {"topn": topn})
            if cached:
                d["question_kwd"] = cached.split("\n")
                d["question_tks"] = rag_tokenizer.tokenize("\n".join(d["question_kwd"]))
        async with trio.open_nursery() as nursery:
            for d in docs:
                nursery.start_soon(doc_question_proposal, chat_mdl, d, task["parser_config"]["auto_questions"])
        await progress_callback(msg="Question generation {} chunks completed in {:.2f}s".format(len(docs), timer() - st))

    if task.get("kb_parser_config", {}).get("tag_kb_ids", []):
        await progress_callback(msg="Start to tag for every chunk ...")
        kb_ids = task["kb_parser_config"]["tag_kb_ids"]
        tenant_id = task["tenant_id"]
        topn_tags = task["kb_parser_config"].get("topn_tags", 3)
        S = 1000
        st = timer()
        examples = []
        all_tags = get_tags_from_cache(kb_ids)
        if not all_tags:
            all_tags = settings.retrievaler.all_tags_in_portion(tenant_id, kb_ids, S)
            set_tags_to_cache(kb_ids, all_tags)
        else:
            all_tags = json.loads(all_tags)

        chat_mdl = LLMBundle(task["tenant_id"], LLMType.CHAT, llm_name=task["llm_id"], lang=task["language"])

        docs_to_tag = []
        for d in docs:
            task_canceled = has_canceled(task["id"])
            if task_canceled:
                await progress_callback(-1, msg="Task has been canceled.")
                return
            if settings.retrievaler.tag_content(tenant_id, kb_ids, d, all_tags, topn_tags=topn_tags, S=S) and len(d[TAG_FLD]) > 0:
                examples.append({"content": d["content_with_weight"], TAG_FLD: d[TAG_FLD]})
            else:
                docs_to_tag.append(d)

        async def doc_content_tagging(chat_mdl, d, topn_tags):
            cached = get_llm_cache(chat_mdl.llm_name, d["content_with_weight"], all_tags, {"topn": topn_tags})
            if not cached:
                picked_examples = random.choices(examples, k=2) if len(examples)>2 else examples
                if not picked_examples:
                    picked_examples.append({"content": "This is an example", TAG_FLD: {'example': 1}})
                async with chat_limiter:
                    cached = await trio.to_thread.run_sync(lambda: content_tagging(chat_mdl, d["content_with_weight"], all_tags, picked_examples, topn=topn_tags))
                if cached:
                    cached = json.dumps(cached)
            if cached:
                set_llm_cache(chat_mdl.llm_name, d["content_with_weight"], cached, all_tags, {"topn": topn_tags})
                d[TAG_FLD] = json.loads(cached)
        async with trio.open_nursery() as nursery:
            for d in docs_to_tag:
                nursery.start_soon(doc_content_tagging, chat_mdl, d, topn_tags)
        await progress_callback(msg="Tagging {} chunks completed in {:.2f}s".format(len(docs), timer() - st))

    return docs


def init_kb(row, vector_size: int):
    idxnm = search.index_name(row["tenant_id"])
    return settings.docStoreConn.createIdx(idxnm, row.get("kb_id", ""), vector_size)


async def embedding(docs, mdl, parser_config=None, callback=None):
    if parser_config is None:
        parser_config = {}
    tts, cnts = [], []
    for d in docs:
        tts.append(d.get("docnm_kwd", "Title"))
        c = "\n".join(d.get("question_kwd", []))
        if not c:
            c = d["content_with_weight"]
        c = re.sub(r"</?(table|td|caption|tr|th)( [^<>]{0,12})?>", " ", c)
        if not c:
            c = "None"
        cnts.append(c)

    tk_count = 0
    if len(tts) == len(cnts):
        vts, c = await trio.to_thread.run_sync(lambda: mdl.encode(tts[0: 1]))
        tts = np.concatenate([vts for _ in range(len(tts))], axis=0)
        tk_count += c

    @timeout(60)
    def batch_encode(txts):
        nonlocal mdl
        return mdl.encode([truncate(c, mdl.max_length-10) for c in txts])

    cnts_ = np.array([])
    for i in range(0, len(cnts), EMBEDDING_BATCH_SIZE):
        async with embed_limiter:
            vts, c = await trio.to_thread.run_sync(lambda: batch_encode(cnts[i: i + EMBEDDING_BATCH_SIZE]))
        if len(cnts_) == 0:
            cnts_ = vts
        else:
            cnts_ = np.concatenate((cnts_, vts), axis=0)
        tk_count += c
        if callback:
            await callback(prog=0.7 + 0.2 * (i + 1) / len(cnts), msg="")
    cnts = cnts_
    filename_embd_weight = parser_config.get("filename_embd_weight", 0.1) # due to the db support none value
    if not filename_embd_weight:
        filename_embd_weight = 0.1
    title_w = float(filename_embd_weight)
    vects = (title_w * tts + (1 - title_w) *
             cnts) if len(tts) == len(cnts) else cnts

    assert len(vects) == len(docs)
    vector_size = 0
    for i, d in enumerate(docs):
        v = vects[i].tolist()
        vector_size = len(v)
        d["q_%d_vec" % len(v)] = v
    return tk_count, vector_size

@timeout(3600)
async def run_raptor(row, chat_mdl, embd_mdl, vector_size, callback=None):
    chunks = []
    vctr_nm = "q_%d_vec"%vector_size
    for d in settings.retrievaler.chunk_list(row["doc_id"], row["tenant_id"], [str(row["kb_id"])],
                                             fields=["content_with_weight", vctr_nm]):
        chunks.append((d["content_with_weight"], np.array(d[vctr_nm])))

    raptor = Raptor(
        row["parser_config"]["raptor"].get("max_cluster", 64),
        chat_mdl,
        embd_mdl,
        row["parser_config"]["raptor"]["prompt"],
        row["parser_config"]["raptor"]["max_token"],
        row["parser_config"]["raptor"]["threshold"]
    )
    original_length = len(chunks)
    chunks = await raptor(chunks, row["parser_config"]["raptor"]["random_seed"], callback)
    doc = {
        "doc_id": row["doc_id"],
        "kb_id": [str(row["kb_id"])],
        "docnm_kwd": row["name"],
        "title_tks": rag_tokenizer.tokenize(row["name"])
    }
    if row["pagerank"]:
        doc[PAGERANK_FLD] = int(row["pagerank"])
    res = []
    tk_count = 0
    for content, vctr in chunks[original_length:]:
        d = copy.deepcopy(doc)
        d["id"] = xxhash.xxh64((content + str(d["doc_id"])).encode("utf-8")).hexdigest()
        d["create_time"] = str(datetime.now()).replace("T", " ")[:19]
        d["create_timestamp_flt"] = datetime.now().timestamp()
        d[vctr_nm] = vctr.tolist()
        d["content_with_weight"] = content
        d["content_ltks"] = rag_tokenizer.tokenize(content)
        d["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(d["content_ltks"])
        res.append(d)
        tk_count += num_tokens_from_string(content)
    return res, tk_count


@timeout(60*60*2, 1)
async def do_handle_task(task):
    task_id = task["id"]
    task_from_page = task["from_page"]
    task_to_page = task["to_page"]
    task_tenant_id = task["tenant_id"]
    task_embedding_id = task["embd_id"]
    task_language = task["language"]
    task_llm_id = task["llm_id"]
    task_dataset_id = task["kb_id"]
    task_doc_id = task["doc_id"]
    task_document_name = task["name"]
    task_parser_config = task["parser_config"]
    task_start_ts = timer()

    # prepare the progress callback function
    progress_callback = partial(set_progress, task_id, task_from_page, task_to_page)

    task_canceled = has_canceled(task_id)
    if task_canceled:
        await progress_callback(-1, msg="Task has been canceled.")
        return

    try:
        # bind embedding model
        embedding_model = LLMBundle(task_tenant_id, LLMType.EMBEDDING, llm_name=task_embedding_id, lang=task_language)
        vts, _ = embedding_model.encode(["ok"])
        vector_size = len(vts[0])
    except Exception as e:
        error_message = f'Fail to bind embedding model: {str(e)}'
        await progress_callback(-1, msg=error_message)
        logging.exception(error_message)
        raise

    init_kb(task, vector_size)

    task_type = task.get("task_type", "")
    if task_type == "raptor":
        # bind LLM for raptor
        chat_model = LLMBundle(task_tenant_id, LLMType.CHAT, llm_name=task_llm_id, lang=task_language)
        # run RAPTOR
        async with kg_limiter:
            chunks, token_count = await run_raptor(task, chat_model, embedding_model, vector_size, progress_callback)
    # Either using graphrag or Standard chunking methods
    elif task_type == "graphrag":
        # NOTE: graphrag module has been removed, this feature is no longer available
        error_message = "GraphRAG feature has been removed from this system. Please use standard chunking methods instead."
        await progress_callback(prog=-1.0, msg=error_message)
        logging.error(f"GraphRAG task requested but feature is removed: {task_id}")
        raise Exception(error_message)
        # if not task_parser_config.get("graphrag", {}).get("use_graphrag", False):
        #     progress_callback(prog=-1.0, msg="Internal configuration error.")
        #     return
        # graphrag_conf = task["kb_parser_config"].get("graphrag", {})
        # start_ts = timer()
        # chat_model = LLMBundle(task_tenant_id, LLMType.CHAT, llm_name=task_llm_id, lang=task_language)
        # with_resolution = graphrag_conf.get("resolution", False)
        # with_community = graphrag_conf.get("community", False)
        # async with kg_limiter:
        #     await run_graphrag(task, task_language, with_resolution, with_community, chat_model, embedding_model, progress_callback)
        # progress_callback(prog=1.0, msg="Knowledge Graph done ({:.2f}s)".format(timer() - start_ts))
        # return
    else:
        # Standard chunking methods
        start_ts = timer()
        chunks = await build_chunks(task, progress_callback)
        logging.info("Build document {}: {:.2f}s".format(task_document_name, timer() - start_ts))
        if not chunks:
            no_chunk_msg = f"No chunk built from {task_document_name}"
            await progress_callback(1., msg=no_chunk_msg)
            # 更新文檔進度到 100%（即使沒有 chunk）
            await trio.to_thread.run_sync(sync_update_document_progress, task_doc_id, 1.0, no_chunk_msg)
            return

        await progress_callback(msg="Generate {} chunks".format(len(chunks)))
        start_ts = timer()
        try:
            token_count, vector_size = await embedding(chunks, embedding_model, task_parser_config, progress_callback)
        except Exception as e:
            error_message = "Generate embedding error:{}".format(str(e))
            await progress_callback(-1, error_message)
            logging.exception(error_message)
            token_count = 0
            raise
        progress_message = "Embedding chunks ({:.2f}s)".format(timer() - start_ts)
        logging.info(progress_message)
        await progress_callback(msg=progress_message)

    chunk_count = len(set([chunk["id"] for chunk in chunks]))
    start_ts = timer()
    doc_store_result = ""

    async def delete_image(kb_id, chunk_id):
        try:
            async with minio_limiter:
                STORAGE_IMPL.delete(kb_id, chunk_id)
        except Exception:
            logging.exception(
                "Deleting image of chunk {}/{}/{} got exception".format(task["location"], task["name"], chunk_id))
            raise

    for b in range(0, len(chunks), DOC_BULK_SIZE):
        doc_store_result = await trio.to_thread.run_sync(lambda: settings.docStoreConn.insert(chunks[b:b + DOC_BULK_SIZE], search.index_name(task_tenant_id), task_dataset_id))
        task_canceled = has_canceled(task_id)
        if task_canceled:
            await progress_callback(-1, msg="Task has been canceled.")
            return
        if b % 128 == 0:
            await progress_callback(prog=0.8 + 0.1 * (b + 1) / len(chunks), msg="")
        if doc_store_result:
            error_message = f"Insert chunk error: {doc_store_result}, please check log file and Elasticsearch status!"
            await progress_callback(-1, msg=error_message)
            raise Exception(error_message)
        chunk_ids = [chunk["id"] for chunk in chunks[:b + DOC_BULK_SIZE]]
        chunk_ids_str = " ".join(chunk_ids)
        try:
            # 更新任務的 chunk_ids（使用同步數據庫操作）
            await trio.to_thread.run_sync(sync_update_chunk_ids, task["id"], chunk_ids_str)
        except Exception as e:
            # Task not found
            logging.warning(f"do_handle_task update_chunk_ids failed since task {task['id']} is unknown: {e}")
            doc_store_result = await trio.to_thread.run_sync(lambda: settings.docStoreConn.delete({"id": chunk_ids}, search.index_name(task_tenant_id), task_dataset_id))
            async with trio.open_nursery() as nursery:
                for chunk_id in chunk_ids:
                    nursery.start_soon(delete_image, task_dataset_id, chunk_id)
            await progress_callback(-1, msg=f"Chunk updates failed since task {task['id']} is unknown.")
            return

    logging.info("Indexing doc({}), page({}-{}), chunks({}), elapsed: {:.2f}".format(task_document_name, task_from_page,
                                                                                     task_to_page, len(chunks),
                                                                                     timer() - start_ts))

    # 更新文檔的 chunk 統計（使用同步數據庫操作）
    await trio.to_thread.run_sync(sync_increment_chunk_num, task_doc_id, task_dataset_id, token_count, chunk_count, 0)

    time_cost = timer() - start_ts
    task_time_cost = timer() - task_start_ts
    completion_msg = "Indexing done ({:.2f}s). Task done ({:.2f}s)".format(time_cost, task_time_cost)

    # 更新任務進度到 100%
    await progress_callback(prog=1.0, msg=completion_msg)

    # 更新文檔進度到 100%（使用同步數據庫操作）
    await trio.to_thread.run_sync(sync_update_document_progress, task_doc_id, 1.0, completion_msg)

    # 回呼 Insight 更新檔案狀態 (如果有 insight_file_id)
    try:
        await notify_insight_file_status(task_doc_id, "completed", chunk_count)
    except Exception as notify_error:
        # 回呼失敗不影響主流程
        logging.warning(f"通知 Insight 檔案狀態失敗: {notify_error}")

    logging.info(
        "Chunk doc({}), page({}-{}), chunks({}), token({}), elapsed:{:.2f}".format(task_document_name, task_from_page,
                                                                                   task_to_page, len(chunks),
                                                                                   token_count, task_time_cost))


async def handle_task():
    global DONE_TASKS, FAILED_TASKS
    redis_msg, task = await collect()
    if not task:
        await trio.sleep(5)
        return
    try:
        logging.info(f"handle_task begin for task {json.dumps(task)}")
        CURRENT_TASKS[task["id"]] = copy.deepcopy(task)
        await do_handle_task(task)
        DONE_TASKS += 1
        CURRENT_TASKS.pop(task["id"], None)
        logging.info(f"handle_task done for task {json.dumps(task)}")
    except Exception as e:
        FAILED_TASKS += 1
        CURRENT_TASKS.pop(task["id"], None)
        try:
            err_msg = str(e)
            while isinstance(e, exceptiongroup.ExceptionGroup):
                e = e.exceptions[0]
                err_msg += ' -- ' + str(e)
            error_msg = f"[Exception]: {err_msg}"
            await set_progress(task["id"], prog=-1, msg=error_msg)
            # 更新文檔進度為錯誤狀態（使用同步數據庫操作）
            await trio.to_thread.run_sync(sync_update_document_progress, task["doc_id"], -1, error_msg)

            # 回呼 Insight 更新檔案狀態為失敗 (如果有 insight_file_id)
            try:
                await notify_insight_file_status(task["doc_id"], "failed", 0, err_msg)
            except Exception as notify_error:
                # 回呼失敗不影響主流程
                logging.warning(f"通知 Insight 檔案失敗狀態失敗: {notify_error}")
        except Exception:
            pass
        logging.exception(f"handle_task got exception for task {json.dumps(task)}")
    redis_msg.ack()


async def report_status():
    global CONSUMER_NAME, BOOT_AT, PENDING_TASKS, LAG_TASKS, DONE_TASKS, FAILED_TASKS
    REDIS_CONN.sadd("TASKEXE", CONSUMER_NAME)
    redis_lock = RedisDistributedLock("clean_task_executor", lock_value=CONSUMER_NAME, timeout=60)
    while True:
        try:
            now = datetime.now()
            group_info = REDIS_CONN.queue_info(get_svr_queue_name(0), SVR_CONSUMER_GROUP_NAME)
            if group_info is not None:
                PENDING_TASKS = int(group_info.get("pending", 0))
                LAG_TASKS = int(group_info.get("lag", 0))

            current = copy.deepcopy(CURRENT_TASKS)
            heartbeat = json.dumps({
                "name": CONSUMER_NAME,
                "now": now.astimezone().isoformat(timespec="milliseconds"),
                "boot_at": BOOT_AT,
                "pending": PENDING_TASKS,
                "lag": LAG_TASKS,
                "done": DONE_TASKS,
                "failed": FAILED_TASKS,
                "current": current,
            })
            REDIS_CONN.zadd(CONSUMER_NAME, heartbeat, now.timestamp())
            logging.info(f"{CONSUMER_NAME} reported heartbeat: {heartbeat}")

            expired = REDIS_CONN.zcount(CONSUMER_NAME, 0, now.timestamp() - 60 * 30)
            if expired > 0:
                REDIS_CONN.zpopmin(CONSUMER_NAME, expired)

            # clean task executor
            if redis_lock.acquire():
                task_executors = REDIS_CONN.smembers("TASKEXE")
                for consumer_name in task_executors:
                    if consumer_name == CONSUMER_NAME:
                        continue
                    expired = REDIS_CONN.zcount(
                        consumer_name, now.timestamp() - WORKER_HEARTBEAT_TIMEOUT, now.timestamp() + 10
                    )
                    if expired == 0:
                        logging.info(f"{consumer_name} expired, removed")
                        REDIS_CONN.srem("TASKEXE", consumer_name)
                        REDIS_CONN.delete(consumer_name)
        except Exception:
            logging.exception("report_status got exception")
        finally:
            redis_lock.release()
        await trio.sleep(30)


async def task_manager():
    try:
        await handle_task()
    finally:
        task_limiter.release()


async def main():
    logging.info(f'TaskExecutor: AIoTersRAG version: {get_aioters_rag_version()}')
    settings.init_settings()
    print_rag_settings()

    # 重新初始化 Redis 連接（因為 REDIS_CONN 單例在 init_settings() 之前就創建了）
    from src.rag.utils import redis_conn
    redis_conn.REDIS_CONN = redis_conn.RedisDB()
    logging.info(f"Redis reconnected: is_alive={redis_conn.REDIS_CONN.is_alive()}")
    if sys.platform != "win32":
        signal.signal(signal.SIGUSR1, start_tracemalloc_and_snapshot)
        signal.signal(signal.SIGUSR2, stop_tracemalloc)
    TRACE_MALLOC_ENABLED = int(os.environ.get('TRACE_MALLOC_ENABLED', "0"))
    if TRACE_MALLOC_ENABLED:
        start_tracemalloc_and_snapshot(None, None)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    async with trio.open_nursery() as nursery:
        nursery.start_soon(report_status)
        while not stop_event.is_set():
            await task_limiter.acquire()
            nursery.start_soon(task_manager)
    logging.error("BUG!!! You should not reach here!!!")

if __name__ == "__main__":
    faulthandler.enable()
    init_root_logger(CONSUMER_NAME)
    trio.run(main)
