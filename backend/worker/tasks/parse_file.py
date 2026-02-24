import asyncio
import json
import os
import pathlib

from dishka.integrations.taskiq import FromDishka, inject

import redis.asyncio as aredis

from backend.app.infrastructure.config import AppSettings
from backend.app.infrastructure.utils.channels import get_channel_name

from backend.app.infrastructure.persistent.chat import ChatRepository
from backend.app.infrastructure.storage import StorageWorker

from backend.app.domain.chat.value_objects.types import EventType, ParsingStatus
from backend.worker.broker import broker
from backend.worker.modules.parser.exceptions import ExtractorNotFound
from backend.worker.modules.parser.universal_parser import parse


@broker.task(task_name="parse_file")
@inject
async def parse_file_task(
        user_id: int,
        attachment_id: str,
        filename: str,
        config: FromDishka[AppSettings],
        chat_repo: FromDishka[ChatRepository],
        redis_client: FromDishka[aredis.Redis],
        storage: FromDishka[StorageWorker]
):
    root_path = pathlib.Path(__file__).resolve().parent.parent / "tmp"
    tmp_path = str(root_path / attachment_id)

    channel = get_channel_name(user_id)
    try:
        await redis_client.publish(
            channel,
            create_status_message(ParsingStatus.IN_PROCESS, attachment_id)
        )

        if not os.path.exists(root_path):
            os.mkdir(root_path)

        await storage.download_file(bucket=config.storage.BUCKET_NAME, key=attachment_id, path=tmp_path)

        parsed_data = parse(tmp_path, filename, True, "tiny")  # TODO: сделать выбор модели
        print(parsed_data)

        # TODO: складывать результат парсинга в БД/S3
        await redis_client.publish(
            channel,
            create_status_message(ParsingStatus.SUCCESSFULLY_ENDED, attachment_id)
        )

    except ExtractorNotFound:
        print(f"Cannot parse file with such extension: {filename}")
        await redis_client.publish(
            channel,
            create_status_message(ParsingStatus.FAILED, attachment_id)
        )
    except Exception as exc:
        # TODO: logging
        print(exc.with_traceback(exc.__traceback__))
        await redis_client.publish(
            channel,
            create_status_message(ParsingStatus.FAILED, attachment_id)
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def create_status_message(status: ParsingStatus, attachment_id: str):
    return json.dumps(
        {
            "type": EventType.PARSING_STATUS,
            "status": status,
            "attachment_id": attachment_id
        }
    )
