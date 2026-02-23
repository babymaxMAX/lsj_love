from abc import ABC
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from aiobotocore.session import get_session

from app.infra.s3.base import BaseS3Storage


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

        async with self.session.create_client("s3", **kwargs) as client:
            yield client


class S3Storage(BaseS3Storage, BaseS3Client):
    async def upload_file(self, file: bytes, file_name: str) -> str:
        async with self.get_client() as client:
            await client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=file,
                ContentType="image/jpeg",
            )
            # Генерируем presigned URL (действует 7 дней) для приватного бакета
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_name},
                ExpiresIn=604800,  # 7 дней в секундах
            )
            return url
