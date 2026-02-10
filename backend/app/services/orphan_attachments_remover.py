from datetime import datetime, timedelta

from prisma import Prisma
from prisma.types import AttachmentWhereInput, DateTimeFilter

from backend.app.infrastructure.config import AppSettings
from backend.app.infrastructure.storage import StorageWorker


async def cleanup_orphan_attachments(db: Prisma, storage: StorageWorker, config: AppSettings):
    # TODO: нужен рефактор - вынести получение orphans в репозиторий + сделать запуск каждые пару часов
    threshold = datetime.now() - timedelta(hours=1)

    orphans = await db.attachment.find_many(
        where=AttachmentWhereInput(
            message_id=None,
            created_at=DateTimeFilter(lt=threshold),
        )
    )

    for orphan in orphans:
        await storage.remove_object(config.storage.BUCKET_NAME, orphan.id)

    await db.attachment.delete_many(
        where=AttachmentWhereInput(
            message_id=None,
            created_at=DateTimeFilter(lt=threshold)
        )
    )
