from abc import ABC, abstractmethod


class BaseS3Storage(ABC):
    @abstractmethod
    async def upload_file(self, file: bytes, file_name: str, content_type: str = "image/jpeg") -> str: ...

    @abstractmethod
    async def download_file(self, file_name: str) -> bytes: ...

    @abstractmethod
    async def get_presigned_url(self, file_name: str, expires: int = 3600) -> str: ...
