import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from dishka.integrations.fastapi import FromDishka, DishkaRoute

from backend.app.domain.ports import TaskDispatcher
from backend.app.infrastructure.auth.typed_roles import AuthenticatedUser
from backend.app.infrastructure.config import AppSettings
from backend.app.infrastructure.persistent.chat import ChatRepository
from backend.app.infrastructure.persistent.generation import GenerationRepository
from backend.app.infrastructure.storage import StorageWorker
from backend.app.services import ChatService
from backend.app.web.schemas.tz_generation import (
    ExportTZRequest,
    GenerateCustomBlockRequest,
    ManualEditBlockRequest,
    RegenerateBlockRequest,
    RunFullPipelineRequest,
    UpdateCustomSectionsRequest,
    UpdateTZRequest,
)

router = APIRouter(
    prefix="/tz",
    route_class=DishkaRoute,
    tags=["tz-generation"],
)


async def _ensure_user_owns_chat(
    chat_repo: ChatRepository,
    user_id: int,
    chat_id: int,
) -> None:
    if not await chat_repo.check_user_has_chat_async(user_id, chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")


async def _collect_parsed_sources(
    chat_service: ChatService,
    user_id: int,
    chat_id: int,
    attachment_ids: list[str],
) -> list[dict[str, str]]:
    """Загружает транскрипты указанных вложений и возвращает список DataSource-совместимых словарей."""
    if not attachment_ids:
        return []

    all_parsed = await chat_service.get_parsed_attachments_async(user_id, chat_id)
    parsed_by_key = {p["key"]: p for p in all_parsed}

    sources: list[dict[str, str]] = []
    for aid in attachment_ids:
        parsed = parsed_by_key.get(aid)
        if parsed is None or not parsed.get("transcript"):
            raise HTTPException(
                status_code=400,
                detail=f"Attachment {aid} is not parsed or has no transcript",
            )
        sources.append({
            "id": aid,
            "type": parsed["file_type"],
            "content": parsed["transcript"],
        })

    return sources


@router.post("/{chat_id}/generate")
async def run_full_pipeline(
    chat_id: int,
    body: RunFullPipelineRequest,
    user: FromDishka[AuthenticatedUser],
    chat_repo: FromDishka[ChatRepository],
    chat_service: FromDishka[ChatService],
    dispatcher: FromDishka[TaskDispatcher],
) -> dict[str, str]:
    """Запуск полного пайплайна первичной генерации ТЗ."""
    await _ensure_user_owns_chat(chat_repo, user.id, chat_id)

    parsed_files = await _collect_parsed_sources(
        chat_service, user.id, chat_id, body.attachment_ids,
    )
    if not parsed_files:
        raise HTTPException(status_code=400, detail="No parsed files provided")

    await dispatcher.dispatch_run_full_pipeline(
        chat_id=chat_id,
        user_id=user.id,
        parsed_files=parsed_files,
    )

    return {"status": "accepted"}


@router.post("/{chat_id}/update")
async def update_tz(
    chat_id: int,
    body: UpdateTZRequest,
    user: FromDishka[AuthenticatedUser],
    chat_repo: FromDishka[ChatRepository],
    chat_service: FromDishka[ChatService],
    dispatcher: FromDishka[TaskDispatcher],
) -> dict[str, str]:
    """Обновление ТЗ: догрузка файлов и/или глобальный комментарий."""
    await _ensure_user_owns_chat(chat_repo, user.id, chat_id)

    if not body.new_attachment_ids and not body.comment:
        raise HTTPException(
            status_code=400,
            detail="At least one of new_attachment_ids or comment must be provided",
        )

    new_parsed_files = await _collect_parsed_sources(
        chat_service, user.id, chat_id, body.new_attachment_ids,
    )

    await dispatcher.dispatch_update_tz(
        chat_id=chat_id,
        user_id=user.id,
        new_parsed_files=new_parsed_files or None,
        comment=body.comment,
    )

    return {"status": "accepted"}


@router.post("/{chat_id}/regenerate-block")
async def regenerate_block(
    chat_id: int,
    body: RegenerateBlockRequest,
    user: FromDishka[AuthenticatedUser],
    chat_repo: FromDishka[ChatRepository],
    dispatcher: FromDishka[TaskDispatcher],
) -> dict[str, str]:
    """Перегенерация конкретного блока ТЗ."""
    await _ensure_user_owns_chat(chat_repo, user.id, chat_id)

    await dispatcher.dispatch_regenerate_block(
        chat_id=chat_id,
        user_id=user.id,
        field_path=body.field_path,
        instruction=body.instruction,
    )

    return {"status": "accepted"}


@router.post("/{chat_id}/generate-block")
async def generate_custom_block(
    chat_id: int,
    body: GenerateCustomBlockRequest,
    user: FromDishka[AuthenticatedUser],
    chat_repo: FromDishka[ChatRepository],
    dispatcher: FromDishka[TaskDispatcher],
) -> dict[str, str]:
    """Генерация/заполнение кастомного или пустого блока."""
    await _ensure_user_owns_chat(chat_repo, user.id, chat_id)

    await dispatcher.dispatch_generate_custom_block(
        chat_id=chat_id,
        user_id=user.id,
        field_path=body.field_path,
        custom_topic=body.custom_topic,
    )

    return {"status": "accepted"}


def _set_nested_field(data: dict, field_path: str, value: object) -> None:
    """Устанавливает значение по dot-notation пути в словаре."""
    keys = field_path.split(".")
    obj = data
    for key in keys[:-1]:
        if key not in obj or not isinstance(obj[key], dict):
            obj[key] = {}
        obj = obj[key]
    obj[keys[-1]] = value


@router.post("/{chat_id}/manual-edit")
async def manual_edit_block(
    chat_id: int,
    body: ManualEditBlockRequest,
    user: FromDishka[AuthenticatedUser],
    chat_repo: FromDishka[ChatRepository],
    gen_repo: FromDishka[GenerationRepository],
    storage: FromDishka[StorageWorker],
    config: FromDishka[AppSettings],
) -> dict[str, str]:
    """Ручное редактирование блока ТЗ пользователем."""
    await _ensure_user_owns_chat(chat_repo, user.id, chat_id)

    run = await gen_repo.get_latest_run(chat_id)
    if not run or not run.result_key:
        raise HTTPException(status_code=404, detail="No generation found")

    try:
        content_str = await storage.get_text(config.storage.BUCKET_NAME, run.result_key)
        content = json.loads(content_str)
    except Exception:
        raise HTTPException(status_code=404, detail="Generation content not found")

    _set_nested_field(content["document"], body.field_path, body.value)

    await storage.put_object(
        bucket=config.storage.BUCKET_NAME,
        key=run.result_key,
        data=json.dumps(content, ensure_ascii=False).encode("utf-8"),
        content_type="application/json",
    )

    if run.state_json:
        state = json.loads(run.state_json)
        internal = state.get("internal_state", {})
        internal[f"manual:{body.field_path}"] = body.value
        state["internal_state"] = internal
        await gen_repo.save_state(run.id, json.dumps(state))

    return {"status": "ok"}


def _validate_depth(nodes: list, current_depth: int = 1, max_depth: int = 3) -> None:
    """Проверяет, что глубина дерева подпунктов не превышает max_depth."""
    if current_depth > max_depth:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum subsection nesting depth is {max_depth}",
        )
    for node in nodes:
        children = node.children if hasattr(node, "children") else node.get("children", [])
        if children:
            _validate_depth(children, current_depth + 1, max_depth)


@router.post("/{chat_id}/update-custom-sections")
async def update_custom_sections(
    chat_id: int,
    body: UpdateCustomSectionsRequest,
    user: FromDishka[AuthenticatedUser],
    chat_repo: FromDishka[ChatRepository],
    gen_repo: FromDishka[GenerationRepository],
    storage: FromDishka[StorageWorker],
    config: FromDishka[AppSettings],
) -> dict[str, str]:
    """Сохранение пользовательских подпунктов секции ТЗ."""
    await _ensure_user_owns_chat(chat_repo, user.id, chat_id)

    _validate_depth(body.sections)

    run = await gen_repo.get_latest_run(chat_id)
    if not run or not run.result_key:
        raise HTTPException(status_code=404, detail="No generation found")

    try:
        content_str = await storage.get_text(config.storage.BUCKET_NAME, run.result_key)
        content = json.loads(content_str)
    except Exception:
        raise HTTPException(status_code=404, detail="Generation content not found")

    if "custom_sections" not in content:
        content["custom_sections"] = {}

    content["custom_sections"][body.section_key] = [
        s.model_dump() for s in body.sections
    ]

    await storage.put_object(
        bucket=config.storage.BUCKET_NAME,
        key=run.result_key,
        data=json.dumps(content, ensure_ascii=False).encode("utf-8"),
        content_type="application/json",
    )

    return {"status": "ok"}


@router.post("/{chat_id}/export")
async def export_tz(
    chat_id: int,
    body: ExportTZRequest,
    user: FromDishka[AuthenticatedUser],
    chat_repo: FromDishka[ChatRepository],
    dispatcher: FromDishka[TaskDispatcher],
) -> dict[str, str]:
    """Запуск экспорта ТЗ в файл."""
    await _ensure_user_owns_chat(chat_repo, user.id, chat_id)

    if body.format not in ("markdown", "word", "pdf"):
        raise HTTPException(status_code=400, detail="Unsupported format")

    await dispatcher.dispatch_export_tz(
        chat_id=chat_id,
        user_id=user.id,
        result_key=body.result_key,
        format=body.format,
    )

    return {"status": "accepted"}


@router.get("/{chat_id}/export-download")
async def download_export(
    chat_id: int,
    key: str,
    user: FromDishka[AuthenticatedUser],
    chat_repo: FromDishka[ChatRepository],
    storage: FromDishka[StorageWorker],
    config: FromDishka[AppSettings],
):
    """Скачивание экспортированного файла."""
    await _ensure_user_owns_chat(chat_repo, user.id, chat_id)

    if not key.startswith(f"exports/{chat_id}/"):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        stream, meta = await storage.get_object_stream_with_meta(
            bucket=config.storage.BUCKET_NAME, key=key,
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Export file not found")

    filename = key.rsplit("/", 1)[-1]
    return StreamingResponse(
        stream,
        media_type=meta.get("content_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(meta.get("content_length", 0)),
        },
    )


@router.get("/{chat_id}/generation-status")
async def get_generation_status(
        chat_id: int,
        user: FromDishka[AuthenticatedUser],
        chat_repo: FromDishka[ChatRepository],
        gen_repo: FromDishka[GenerationRepository],
):
    if not await chat_repo.check_user_has_chat_async(user.id, chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")

    run = await gen_repo.get_latest_run(chat_id)
    if run is None:
        return {"status": None}

    return {
        "run_id": run.id,
        "chat_id": run.chat_id,
        "status": run.status,
        "step": run.step,
        "progress": run.progress,
        "result_key": run.result_key,
        "error": run.error,
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
    }


@router.get("/{chat_id}/generation-content")
async def get_generation_content(
        chat_id: int,
        result_key: str,
        user: FromDishka[AuthenticatedUser],
        chat_repo: FromDishka[ChatRepository],
        storage: FromDishka[StorageWorker],
        config: FromDishka[AppSettings]
):
    if not await chat_repo.check_user_has_chat_async(user.id, chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")

    try:
        content = await storage.get_text(config.storage.BUCKET_NAME, result_key)
        return {"content": json.loads(content)}

    except Exception:
        raise HTTPException(status_code=404, detail="Generation content not found")


@router.get("/{chat_id}/generations")
async def get_generations(
        chat_id: int,
        user: FromDishka[AuthenticatedUser],
        chat_repo: FromDishka[ChatRepository],
        gen_repo: FromDishka[GenerationRepository]
):
    if not await chat_repo.check_user_has_chat_async(user.id, chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")

    runs = await gen_repo.get_completed_runs(chat_id)
    return [
        {
            "id": int(run.id),
            "status": run.status,
            "step": run.step,
            "progress": run.progress,
            "result_key": run.result_key,
            "created_at": run.created_at.isoformat(),
        }
        for run in runs
    ]
