import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from dishka.integrations.fastapi import FromDishka, DishkaRoute

from backend.app.domain.ports import TaskDispatcher
from backend.app.infrastructure.auth.typed_roles import AuthenticatedUser
from backend.app.infrastructure.config import AppSettings
from backend.app.infrastructure.persistent.chat import ChatRepository
from backend.app.infrastructure.persistent.generation import GenerationRepository
from backend.app.infrastructure.persistent.llm_pipeline import GKGRepository, PendingActionsRepository
from backend.app.infrastructure.storage import StorageWorker
from backend.app.services import ChatService
from backend.app.web.schemas.tz_generation import (
    DocumentSectionPayload,
    ExportTZRequest,
    GenerateCustomBlockRequest,
    ManualEditBlockRequest,
    RegenerateBlockRequest,
    ResolveConflictRequest,
    RunFullPipelineRequest,
    UpdateSectionsRequest,
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
            "name": parsed["file_name"],
            "content": parsed["transcript"],
        })

    return sources


@router.post("/{chat_id}/generate")
async def run_full_pipeline(
    chat_id: int,
    body: RunFullPipelineRequest,
    user: FromDishka[AuthenticatedUser],
    chat_repo: FromDishka[ChatRepository],
    gen_repo: FromDishka[GenerationRepository],
    chat_service: FromDishka[ChatService],
    dispatcher: FromDishka[TaskDispatcher],
) -> dict[str, str]:
    """Запуск полного пайплайна первичной генерации ТЗ."""
    await _ensure_user_owns_chat(chat_repo, user.id, chat_id)
    if await gen_repo.has_active_run(chat_id):
        raise HTTPException(status_code=409, detail="Generation is already running")

    parsed_files = await _collect_parsed_sources(
        chat_service, user.id, chat_id, body.attachment_ids,
    )
    if not parsed_files:
        raise HTTPException(status_code=400, detail="No parsed files provided")

    template = body.template_type
    if not template:
        template = (await chat_repo.get_chat_template_async(chat_id)).value

    await dispatcher.dispatch_run_full_pipeline(
        chat_id=chat_id,
        user_id=user.id,
        parsed_files=parsed_files,
        template_type=template,
        comment=body.comment,
    )

    return {"status": "accepted"}


@router.post("/{chat_id}/update")
async def update_tz(
    chat_id: int,
    body: UpdateTZRequest,
    user: FromDishka[AuthenticatedUser],
    chat_repo: FromDishka[ChatRepository],
    gen_repo: FromDishka[GenerationRepository],
    chat_service: FromDishka[ChatService],
    dispatcher: FromDishka[TaskDispatcher],
) -> dict[str, str]:
    """Обновление ТЗ: догрузка файлов и/или глобальный комментарий."""
    await _ensure_user_owns_chat(chat_repo, user.id, chat_id)
    if await gen_repo.has_active_run(chat_id):
        raise HTTPException(status_code=409, detail="Generation is already running")

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

    block_id = body.block_id or body.field_path
    if not block_id:
        raise HTTPException(status_code=400, detail="block_id is required")

    await dispatcher.dispatch_regenerate_block(
        chat_id=chat_id,
        user_id=user.id,
        block_id=block_id,
        instruction=body.instruction,
    )

    return {"status": "accepted"}


@router.post("/{chat_id}/resolve-conflict")
async def resolve_conflict(
    chat_id: int,
    body: ResolveConflictRequest,
    user: FromDishka[AuthenticatedUser],
    chat_repo: FromDishka[ChatRepository],
    dispatcher: FromDishka[TaskDispatcher],
) -> dict[str, str]:
    """Разрешение pending-конфликта и запуск связанных обновлений."""
    await _ensure_user_owns_chat(chat_repo, user.id, chat_id)

    await dispatcher.dispatch_resolve_conflict(
        chat_id=chat_id,
        user_id=user.id,
        action_id=body.action_id,
        resolution=body.resolution,
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


@router.post("/{chat_id}/manual-edit")
async def manual_edit_block(
    chat_id: int,
    body: ManualEditBlockRequest,
    user: FromDishka[AuthenticatedUser],
    chat_repo: FromDishka[ChatRepository],
    gen_repo: FromDishka[GenerationRepository],
    gkg_repo: FromDishka[GKGRepository],
) -> dict[str, str]:
    """Ручное редактирование блока ТЗ пользователем."""
    await _ensure_user_owns_chat(chat_repo, user.id, chat_id)

    run = await gen_repo.get_latest_run(chat_id)
    if not run:
        raise HTTPException(status_code=404, detail="No generation found")

    block_id = await gkg_repo.resolve_section_id(chat_id, body.field_path)
    if not block_id:
        raise HTTPException(status_code=400, detail=f"Section for field_path '{body.field_path}' not found")

    if isinstance(body.value, str):
        content_md = body.value
    else:
        content_md = json.dumps(body.value, ensure_ascii=False)

    await gkg_repo.mark_block_manual(chat_id, block_id, content_md)

    if run.state_json:
        state = json.loads(run.state_json)
        internal = state.get("internal_state", {})
        internal[f"manual:{body.field_path}"] = body.value
        state["internal_state"] = internal
        await gen_repo.save_state(run.id, json.dumps(state))

    return {"status": "ok"}


def _validate_sections(sections: list[DocumentSectionPayload]) -> None:
    """MVP: проверяет плоский список секций, где level используется как порядок."""
    if not sections:
        raise HTTPException(status_code=400, detail="At least one section is required")

    for section in sections:
        if int(section.level) < 0:
            raise HTTPException(status_code=400, detail="Section level must be >= 0")
        if not section.title.strip():
            raise HTTPException(status_code=400, detail="Section title cannot be empty")


@router.post("/{chat_id}/update-sections")
async def update_sections(
    chat_id: int,
    body: UpdateSectionsRequest,
    user: FromDishka[AuthenticatedUser],
    chat_repo: FromDishka[ChatRepository],
    gkg_repo: FromDishka[GKGRepository],
) -> dict[str, str]:
    """Полное сохранение структуры секций ТЗ."""
    await _ensure_user_owns_chat(chat_repo, user.id, chat_id)

    _validate_sections(body.sections)

    await gkg_repo.replace_document_sections(
        chat_id,
        [section.model_dump() for section in body.sections],
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

    try:
        await dispatcher.dispatch_export_tz(
            chat_id=chat_id,
            user_id=user.id,
            result_key=body.result_key,
            format=body.format,
        )
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))

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
        gen_repo: FromDishka[GenerationRepository],
    gkg_repo: FromDishka[GKGRepository],
):
    if not await chat_repo.check_user_has_chat_async(user.id, chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")

    run = await gen_repo.get_run_by_result_key(chat_id, result_key)
    if run is None:
        raise HTTPException(status_code=404, detail="Generation content not found")

    payload = await gkg_repo.build_tz_result_payload(chat_id)

    return {"content": payload}


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


@router.get("/{chat_id}/actions")
async def get_pending_actions_and_conflicts(
        chat_id: int,
        user: FromDishka[AuthenticatedUser],
        chat_repo: FromDishka[ChatRepository],
        gkg_repo: FromDishka[GKGRepository],
        pending_repo: FromDishka[PendingActionsRepository],
):
    if not await chat_repo.check_user_has_chat_async(user.id, chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")

    conflicts = await gkg_repo.get_pending_conflicts(chat_id)
    actions = await pending_repo.get_waiting_actions(chat_id)

    return {
        "conflicts": [
            {
                "id": conflict.id,
                "scope": conflict.scope,
                "property": conflict.property,
                "rationale": conflict.rationale,
                "options": [opt.node.value for opt in conflict.options],
            }
            for conflict in conflicts
        ],
        "actions": actions,
    }


@router.get("/{chat_id}/facts")
async def get_knowledge_graph_facts(
        chat_id: int,
        user: FromDishka[AuthenticatedUser],
        chat_repo: FromDishka[ChatRepository],
        gkg_repo: FromDishka[GKGRepository],
):
    if not await chat_repo.check_user_has_chat_async(user.id, chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")

    facts = await gkg_repo.get_facts(chat_id)
    return {"facts": facts}
