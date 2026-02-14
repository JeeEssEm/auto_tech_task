from typing import BinaryIO, AsyncIterator
from contextlib import asynccontextmanager

from aiobotocore.session import get_session, AioSession
from botocore.exceptions import ClientError, DataNotFoundError
from types_aiobotocore_s3 import S3Client

from backend.app.infrastructure.config import AppSettings
from backend.app.web.exceptions import AttachmentFileIsTooBig


class StorageWorker:
    def __init__(self, config: AppSettings):
        self._endpoint_url = config.storage.connection_url
        self._access_key = config.storage.ACCESS_KEY
        self._secret_key = config.storage.SECRET_KEY
        self._region = config.storage.REGION
        self._session: AioSession = get_session()

    @asynccontextmanager
    async def _get_client(self) -> AsyncIterator[S3Client]:
        async with self._session.create_client(
                "s3",
                endpoint_url=self._endpoint_url,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                region_name=self._region,
        ) as client:
            yield client

    async def create_bucket(self, bucket: str) -> bool:
        async with self._get_client() as client:
            try:
                await client.create_bucket(Bucket=bucket)
                return True
            except ClientError as e:
                if e.response["Error"]["Code"] in (
                        "BucketAlreadyExists",
                        "BucketAlreadyOwnedByYou",
                ):
                    return False
                raise

    async def put_object(
            self,
            bucket: str,
            key: str,
            data: bytes,
            content_type: str | None = None,
    ) -> str:
        async with self._get_client() as client:
            kwargs = {"Bucket": bucket, "Key": key, "Body": data}
            if content_type:
                kwargs["ContentType"] = content_type

            response = await client.put_object(**kwargs)
            return response["ETag"]

    async def remove_object(self, bucket: str, key: str) -> bool:
        async with self._get_client() as client:
            try:
                await client.delete_object(Bucket=bucket, Key=key)
                return True
            except DataNotFoundError:
                return False

    async def upload_stream(
            self,
            bucket: str,
            key: str,
            stream: AsyncIterator[bytes],
            content_type: str | None = None,
            chunk_size: int = 5 * 1024 * 1024,
            max_file_size: int = 1 * 1024 * 1024 * 1024
    ) -> tuple[str, int]:
        """
        Возвращает (ETag, actual_size)
        """
        async with self._get_client() as client:
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

                async for _ in stream:
                    pass

                complete_resp = await client.complete_multipart_upload(
                    Bucket=bucket,
                    Key=key,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                )
                return complete_resp["ETag"], total_bytes

            except Exception:
                await client.abort_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id)
                raise

    async def get_object_stream(
            self,
            bucket: str,
            key: str,
            chunk_size: int = 64 * 1024,  # 64KB
    ) -> AsyncIterator[bytes]:
        """
        Возвращает async iterator для стриминга файла.
        """
        async with self._get_client() as client:
            response = await client.get_object(Bucket=bucket, Key=key)
            async with response["Body"] as stream:
                async for chunk in stream.content.iter_chunked(chunk_size):
                    yield chunk

    async def get_object_stream_with_meta(
            self,
            bucket: str,
            key: str,
            chunk_size: int = 64 * 1024,
    ) -> tuple[AsyncIterator[bytes], dict]:
        """
        Возвращает (async iterator, metadata).
        Metadata содержит content_type, content_length, etag и др.
        """
        async with self._get_client() as client:
            response = await client.get_object(Bucket=bucket, Key=key)

            metadata = {
                "content_type": response.get("ContentType"),
                "content_length": response.get("ContentLength"),
                "etag": response.get("ETag"),
                "last_modified": response.get("LastModified"),
            }

            async def stream_generator():
                async with response["Body"] as stream:
                    async for chunk in stream.content.iter_chunked(chunk_size):
                        yield chunk

            return stream_generator(), metadata
