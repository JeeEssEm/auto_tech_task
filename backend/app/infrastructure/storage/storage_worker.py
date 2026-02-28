from typing import BinaryIO, AsyncIterator
from contextlib import asynccontextmanager

import aioboto3
import structlog
from botocore.exceptions import ClientError, DataNotFoundError
from types_aiobotocore_s3 import S3Client

from backend.app.infrastructure.config import AppSettings
from backend.app.web.exceptions import AttachmentFileIsTooBig

logger = structlog.get_logger(__name__)


class StorageWorker:
    def __init__(self, config: AppSettings):
        self._endpoint_url = config.storage.connection_url
        self._access_key = config.storage.ACCESS_KEY
        self._secret_key = config.storage.SECRET_KEY
        self._region = config.storage.REGION
        self._session = aioboto3.Session()
        self._client: S3Client | None = None
        self._client_ctx = None

    async def start(self):
        self._client_ctx = self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            region_name=self._region,
        )
        self._client = await self._client_ctx.__aenter__()
        logger.info("s3_client_started", endpoint=self._endpoint_url)

    async def stop(self):
        if self._client_ctx:
            await self._client_ctx.__aexit__(None, None, None)
            self._client = None
            logger.info("s3_client_stopped")

    def _ensure_client(self) -> S3Client:
        if self._client is None:
            raise RuntimeError(
                "StorageWorker не запущен. Вызовите await storage.start() перед использованием."
            )
        return self._client

    async def create_bucket(self, bucket: str) -> bool:
        client = self._ensure_client()
        try:
            await client.create_bucket(Bucket=bucket)
            logger.info("bucket_created", bucket=bucket)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in (
                "BucketAlreadyExists",
                "BucketAlreadyOwnedByYou",
            ):
                logger.debug("bucket_already_exists", bucket=bucket)
                return False
            raise

    async def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str | None = None,
    ) -> str:
        client = self._ensure_client()
        kwargs = {"Bucket": bucket, "Key": key, "Body": data}
        if content_type:
            kwargs["ContentType"] = content_type

        response = await client.put_object(**kwargs)
        logger.debug("object_put", bucket=bucket, key=key, size=len(data))
        return response["ETag"]

    async def remove_object(self, bucket: str, key: str) -> bool:
        client = self._ensure_client()
        try:
            await client.delete_object(Bucket=bucket, Key=key)
            logger.info("object_removed", bucket=bucket, key=key)
            return True
        except DataNotFoundError:
            logger.warning("object_not_found_on_remove", bucket=bucket, key=key)
            return False

    async def upload_stream(
        self,
        bucket: str,
        key: str,
        stream: AsyncIterator[bytes],
        content_type: str | None = None,
        chunk_size: int = 5 * 1024 * 1024,
        max_file_size: int = 1 * 1024 * 1024 * 1024,
    ) -> tuple[str, int]:
        """Multipart upload из async-стрима. Возвращает (ETag, actual_size)."""
        client = self._ensure_client()

        create_resp = await client.create_multipart_upload(
            Bucket=bucket,
            Key=key,
            **({"ContentType": content_type} if content_type else {}),
        )
        upload_id = create_resp["UploadId"]

        parts = []
        part_number = 1
        buffer = b""
        total_bytes = 0

        try:
            async for chunk in stream:
                total_bytes += len(chunk)
                if total_bytes > max_file_size:
                    raise AttachmentFileIsTooBig(max_file_size)

                buffer += chunk

                while len(buffer) >= chunk_size:
                    part_data = buffer[:chunk_size]
                    buffer = buffer[chunk_size:]

                    resp = await client.upload_part(
                        Bucket=bucket,
                        Key=key,
                        UploadId=upload_id,
                        PartNumber=part_number,
                        Body=part_data,
                    )
                    parts.append({"PartNumber": part_number, "ETag": resp["ETag"]})
                    part_number += 1

            if buffer:
                resp = await client.upload_part(
                    Bucket=bucket,
                    Key=key,
                    UploadId=upload_id,
                    PartNumber=part_number,
                    Body=buffer,
                )
                parts.append({"PartNumber": part_number, "ETag": resp["ETag"]})

            elif len(parts) == 0:
                resp = await client.upload_part(
                    Bucket=bucket,
                    Key=key,
                    UploadId=upload_id,
                    PartNumber=part_number,
                    Body=b"",
                )
                parts.append({"PartNumber": part_number, "ETag": resp["ETag"]})

            complete_resp = await client.complete_multipart_upload(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )

            logger.info(
                "stream_upload_complete",
                bucket=bucket,
                key=key,
                total_bytes=total_bytes,
                parts_count=len(parts),
            )
            return complete_resp["ETag"], total_bytes

        except Exception:
            await client.abort_multipart_upload(
                Bucket=bucket, Key=key, UploadId=upload_id
            )
            logger.warning(
                "stream_upload_aborted",
                bucket=bucket,
                key=key,
                uploaded_bytes=total_bytes,
            )
            raise

    async def get_object_stream(
        self,
        bucket: str,
        key: str,
        chunk_size: int = 64 * 1024,
    ) -> AsyncIterator[bytes]:
        """Async iterator для стриминга файла из S3."""
        client = self._ensure_client()
        response = await client.get_object(Bucket=bucket, Key=key)
        async with response["Body"] as body:
            async for chunk in body.content.iter_chunked(chunk_size):
                yield chunk

    async def get_object_stream_with_meta(
        self,
        bucket: str,
        key: str,
        chunk_size: int = 64 * 1024,
    ) -> tuple[AsyncIterator[bytes], dict]:
        """Возвращает (async iterator, metadata)."""
        client = self._ensure_client()
        response = await client.head_object(Bucket=bucket, Key=key)

        metadata = {
            "content_type": response.get("ContentType"),
            "content_length": response.get("ContentLength"),
            "etag": response.get("ETag"),
            "last_modified": response.get("LastModified"),
        }

        return self.get_object_stream(bucket, key, chunk_size), metadata

    async def download_file(self, bucket: str, key: str, path: str):
        client = self._ensure_client()
        await client.download_file(Bucket=bucket, Key=key, Filename=path)
        logger.debug("file_downloaded", bucket=bucket, key=key, path=path)

    async def load_text(self, bucket: str, key: str, text: str):
        client = self._ensure_client()
        await client.put_object(
            Bucket=bucket, Key=key, Body=text, ContentType="text/plain"
        )
        logger.debug("text_loaded", bucket=bucket, key=key, length=len(text))
