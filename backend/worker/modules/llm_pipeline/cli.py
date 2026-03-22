from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from backend.worker.modules.llm_pipeline.orchestrator.deps_factory import create_local_runtime
from backend.worker.modules.llm_pipeline.orchestrator.orchestrator import Orchestrator
from backend.worker.modules.llm_pipeline.orchestrator.state import Attachment


def _read_attachment(path: Path) -> Attachment:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return {
        "source_id": f"file:{path.name}",
        "name": path.name,
        "text": text,
    }


async def _run_once(
    orchestrator: Orchestrator,
    runtime,
    project_id: int,
    message: str,
    attachment_paths: list[Path],
) -> None:
    attachments = [_read_attachment(path) for path in attachment_paths]
    result = await orchestrator.run(project_id=project_id, user_input=message, attachments=attachments)

    if runtime.deps.save_document_updates and result.doc_updates:
        await runtime.deps.save_document_updates(project_id, result.doc_updates)

    print("\n=== CHAT ANSWER ===")
    print(result.chat_text)

    if result.doc_updates:
        print("\n=== UPDATED SECTIONS ===")
        for update in result.doc_updates:
            print(f"- {update.section_id} [{update.status}]")

    if result.pending_conflicts:
        print("\n=== PENDING CONFLICTS ===")
        for conflict in result.pending_conflicts:
            print(f"- {conflict.scope}/{conflict.property}: {conflict.rationale}")

    pending = await runtime.store.get_pending_action_questions(project_id)
    if pending:
        print("\n=== PENDING ACTIONS ===")
        for item in pending:
            print(f"- {item}")


async def _interactive(orchestrator: Orchestrator, runtime, project_id: int) -> None:
    print("Interactive mode started. Type '/exit' to quit.")
    while True:
        message = input("\nYou> ").strip()
        if not message:
            continue
        if message in {"/exit", "exit", "quit"}:
            break
        await _run_once(orchestrator, runtime, project_id, message, [])


async def _interactive_with_attachments(
    orchestrator: Orchestrator,
    runtime,
    project_id: int,
    initial_attachment_paths: list[Path],
) -> None:
    queued_attachments = list(initial_attachment_paths)
    if queued_attachments:
        names = ", ".join(path.name for path in queued_attachments)
        print(f"Preloaded attachments for first message: {names}")

    print("Interactive mode started. Type '/exit' to quit.")
    while True:
        message = input("\nYou> ").strip()
        if not message:
            continue
        if message in {"/exit", "exit", "quit"}:
            break
        await _run_once(orchestrator, runtime, project_id, message, queued_attachments)
        # Attachments are ingested once, then dialogue continues using persisted state/GKG.
        queued_attachments = []


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run full LLM orchestrator pipeline from CLI")
    parser.add_argument("--project-id", type=int, default=1, help="Project id in local state")
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("artifacts/orchestrator_cli_state.json"),
        help="Path to local orchestrator JSON state",
    )
    parser.add_argument("--message", type=str, default=None, help="Single message to process")
    parser.add_argument(
        "--attach",
        type=Path,
        nargs="*",
        default=[],
        help="Text files to attach",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run interactive REPL mode",
    )
    parser.add_argument(
        "--load-gkg-path",
        type=Path,
        default=None,
        help="Load GKG from JSON file before processing messages",
    )
    parser.add_argument(
        "--save-gkg-path",
        type=Path,
        default=None,
        help="Save GKG to JSON file after processing",
    )
    parser.add_argument(
        "--replace-gkg",
        action="store_true",
        help="When loading GKG, replace existing nodes instead of merge by id",
    )
    return parser


async def _async_main() -> None:
    args = _build_parser().parse_args()

    runtime = await create_local_runtime(args.state_path)
    orchestrator = Orchestrator(runtime.deps)

    if args.load_gkg_path is not None:
        imported = await runtime.store.import_gkg(
            project_id=args.project_id,
            in_path=args.load_gkg_path,
            merge=not args.replace_gkg,
        )
        print(f"Loaded GKG nodes: {imported} from {args.load_gkg_path}")

    if args.interactive or args.message is None:
        await _interactive_with_attachments(
            orchestrator=orchestrator,
            runtime=runtime,
            project_id=args.project_id,
            initial_attachment_paths=args.attach,
        )
        if args.save_gkg_path is not None:
            exported = await runtime.store.export_gkg(args.project_id, args.save_gkg_path)
            print(f"Saved GKG nodes: {exported} to {args.save_gkg_path}")
        return

    await _run_once(
        orchestrator=orchestrator,
        runtime=runtime,
        project_id=args.project_id,
        message=args.message,
        attachment_paths=args.attach,
    )

    if args.save_gkg_path is not None:
        exported = await runtime.store.export_gkg(args.project_id, args.save_gkg_path)
        print(f"Saved GKG nodes: {exported} to {args.save_gkg_path}")


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()