import os
from enum import Enum

from src.rag.utils.minio_conn import AIoTersRAGMinio
from src.rag.utils.opendal_conn import OpenDALStorage
from src.rag.utils.s3_conn import AIoTersRAGS3
from src.rag.utils.local_storage import LocalFileStorage


class Storage(Enum):
    MINIO = 1
    AWS_S3 = 2
    OSS = 3
    OPENDAL = 4
    LOCAL_FS = 5


class StorageFactory:
    storage_mapping = {
        Storage.MINIO: AIoTersRAGMinio,
        Storage.AWS_S3: AIoTersRAGS3,
        Storage.OPENDAL: OpenDALStorage,
        Storage.LOCAL_FS: LocalFileStorage,
    }

    @classmethod
    def create(cls, storage: Storage):
        return cls.storage_mapping[storage]()


STORAGE_IMPL_TYPE = os.getenv('STORAGE_IMPL', 'LOCAL_FS')
STORAGE_IMPL = StorageFactory.create(Storage[STORAGE_IMPL_TYPE])
