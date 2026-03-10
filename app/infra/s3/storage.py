import logging
from abc import ABC
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from aiobotocore.session import get_session

from app.infra.s3.base import BaseS3Storage

logger = logging.getLogger(__name__)


@dataclass
class BaseS3Client(ABC):
    aws_access_key_id: str
    aws_secret_access_key: str
    bucket_name: str
    region_name: str
    endpoint_url: str = ""
    session: object = field(default_factory=get_session, init=False, repr=False)

    @asynccontextmanager
    async def get_client(self):
        kwargs = dict(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name,
        )
        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url

        # Backblaze B2 требует path-style адресацию (не virtual-hosted)
        # Без этого GET-запросы могут падать с ошибкой соединения
        try:
            from aiobotocore.config import AioConfig
            kwargs["config"] = AioConfig(
                s3={"addressing_style": "path"},
                connect_timeout=10,
                read_timeout=20,
                retries={"max_attempts": 2},
            )
        except ImportError:
            pass

        async with self.session.create_client("s3", **kwargs) as client:
            yield client


class S3Storage(BaseS3Storage, BaseS3Client):
    async def upload_file(self, file: bytes, file_name: str, content_type: str = "image/jpeg") -> str:
        """Загружает файл в S3 и возвращает S3-ключ (не presigned URL)."""
        logger.info(f"S3 upload: bucket={self.bucket_name}, key={file_name}, size={len(file)}")
        try:
            async with self.get_client() as client:
                await client.put_object(
                    Bucket=self.bucket_name,
                    Key=file_name,
                    Body=file,
                    ContentType=content_type,
                )
            logger.info(f"S3 upload OK: {file_name}")
            return file_name  # возвращаем ключ, а не URL
        except Exception as e:
            logger.error(f"S3 upload FAILED: key={file_name}, error={e}")
            raise

    async def download_file(self, file_name: str) -> bytes:
        """Скачивает файл из S3 и возвращает байты."""
        logger.info(f"S3 download: bucket={self.bucket_name}, key={file_name}")
        try:
            async with self.get_client() as client:
                resp = await client.get_object(Bucket=self.bucket_name, Key=file_name)
                body = await resp["Body"].read()
            if not body:
                raise ValueError("Empty S3 response")
            logger.info(f"S3 download OK: {file_name}, size={len(body)}")
            return body
        except Exception as e:
            logger.error(f"S3 download FAILED: key={file_name}, bucket={self.bucket_name}, "
                         f"endpoint={self.endpoint_url}, error={type(e).__name__}: {e}")
            raise

    async def get_presigned_url(self, file_name: str, expires: int = 3600) -> str:
        """Генерирует presigned URL для скачивания файла."""
        async with self.get_client() as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_name},
                ExpiresIn=expires,
            )
        return url
