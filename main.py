from __future__ import annotations

import argparse
import json

from agent_memory_project.services.persistent_memory_service import (
    PersistentMemoryService,
)
from agent_memory_project.services.memory_orchestrator_service import (
    MemoryOrchestratorService,
)
from agent_memory_project.services.session_search_service import SessionSearchService
from agent_memory_project.services.skill_service import SkillService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a Hermes-style local memory workflow."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    memory_add_parser = subparsers.add_parser(
        "memory-add", help="Add MEMORY.md or USER.md entry."
    )
    memory_add_parser.add_argument(
        "--target", required=True, choices=["memory", "user"]
    )
    memory_add_parser.add_argument("--content", required=True)

    memory_replace_parser = subparsers.add_parser(
        "memory-replace", help="Replace a persistent entry."
    )
    memory_replace_parser.add_argument(
        "--target", required=True, choices=["memory", "user"]
    )
    memory_replace_parser.add_argument("--old-text", required=True)
    memory_replace_parser.add_argument("--content", required=True)

    memory_remove_parser = subparsers.add_parser(
        "memory-remove", help="Remove a persistent entry."
    )
    memory_remove_parser.add_argument(
        "--target", required=True, choices=["memory", "user"]
    )
    memory_remove_parser.add_argument("--old-text", required=True)

    memory_show_parser = subparsers.add_parser(
        "memory-show", help="Show one persistent store."
    )
    memory_show_parser.add_argument(
        "--target", required=True, choices=["memory", "user"]
    )

    subparsers.add_parser(
        "prompt-block", help="Render startup system-prompt memory block."
    )

    skills_list_parser = subparsers.add_parser(
        "skills-list", help="List installed skills."
    )
    skills_list_parser.set_defaults(command="skills-list")

    skills_catalog_parser = subparsers.add_parser(
        "skills-catalog",
        help="List only skill names, descriptions, and triggers.",
    )
    skills_catalog_parser.set_defaults(command="skills-catalog")

    skill_add_parser = subparsers.add_parser(
        "skill-add", help="Create a reusable skill."
    )
    skill_add_parser.add_argument("--skill-name", required=True)
    skill_add_parser.add_argument("--description", required=True)
    skill_add_parser.add_argument("--triggers", nargs="*", default=[])
    skill_add_parser.add_argument("--steps", nargs="*", default=[])
    skill_add_parser.add_argument("--examples", nargs="*", default=[])

    skill_match_parser = subparsers.add_parser(
        "skill-match", help="Match skills for a task."
    )
    skill_match_parser.add_argument("--query", required=True)
    skill_match_parser.add_argument("--limit", type=int, default=5)

    skill_view_parser = subparsers.add_parser(
        "skill-view",
        help="Load one full SKILL.md payload by slug or name.",
    )
    skill_view_parser.add_argument("--slug", required=True)

    session_append_parser = subparsers.add_parser(
        "session-add", help="Append a session event."
    )
    session_append_parser.add_argument("--session-id", required=True)
    session_append_parser.add_argument("--role", default="user")
    session_append_parser.add_argument("--content", required=True)

    sessions_list_parser = subparsers.add_parser(
        "sessions-list", help="List known sessions."
    )
    sessions_list_parser.set_defaults(command="sessions-list")

    session_events_parser = subparsers.add_parser(
        "session-events", help="List session events."
    )
    session_events_parser.add_argument("--session-id", required=True)
    session_events_parser.add_argument("--limit", type=int, default=50)

    session_search_parser = subparsers.add_parser(
        "session-search", help="Search within a session."
    )
    session_search_parser.add_argument("--session-id", required=True)
    session_search_parser.add_argument("--query", required=True)
    session_search_parser.add_argument("--limit", type=int, default=5)

    session_extract_parser = subparsers.add_parser(
        "session-extract",
        help="Extract persistent-memory or skill candidates from a session.",
    )
    session_extract_parser.add_argument("--session-id", required=True)
    session_extract_parser.add_argument("--query")
    session_extract_parser.add_argument("--limit", type=int, default=10)

    materialize_parser = subparsers.add_parser(
        "materialize-suggestion",
        help="Write an extracted suggestion into persistent memory or skills.",
    )
    materialize_parser.add_argument("--kind", required=True)
    materialize_parser.add_argument("--title", required=True)
    materialize_parser.add_argument("--content", required=True)

    return parser.parse_args()


def dump(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    args = parse_args()
    persistent_service = PersistentMemoryService()
    orchestrator_service = MemoryOrchestratorService()
    skill_service = SkillService()
    session_service = SessionSearchService()

    if args.command == "memory-add":
        dump(persistent_service.add_entry(args.target, args.content))
        return

    if args.command == "memory-replace":
        dump(persistent_service.replace_entry(args.target, args.old_text, args.content))
        return

    if args.command == "memory-remove":
        dump(persistent_service.remove_entry(args.target, args.old_text))
        return

    if args.command == "memory-show":
        dump(persistent_service.get_store_state(args.target))
        return

    if args.command == "prompt-block":
        dump({"prompt_block": persistent_service.render_system_prompt_block()})
        return

    if args.command == "skills-list":
        dump([item.to_dict() for item in skill_service.list_skills()])
        return

    if args.command == "skills-catalog":
        dump(skill_service.list_skill_catalog())
        return

    if args.command == "skill-add":
        dump(
            skill_service.save_skill(
                skill_name=args.skill_name,
                description=args.description,
                triggers=args.triggers,
                steps=args.steps,
                examples=args.examples,
            ).to_dict()
        )
        return

    if args.command == "skill-match":
        dump(
            [
                item.to_dict()
                for item in skill_service.match_skills(args.query, args.limit)
            ]
        )
        return

    if args.command == "skill-view":
        dump(skill_service.view_skill(args.slug).to_dict())
        return

    if args.command == "session-add":
        dump(
            session_service.append_event(
                args.session_id, args.role, args.content
            ).to_dict()
        )
        return

    if args.command == "sessions-list":
        dump(session_service.list_sessions())
        return

    if args.command == "session-events":
        dump(
            [
                item.to_dict()
                for item in session_service.list_events(args.session_id, args.limit)
            ]
        )
        return

    if args.command == "session-search":
        items, summary = session_service.search_events(
            args.session_id, args.query, args.limit
        )
        dump(
            {
                "session_id": args.session_id,
                "query": args.query,
                "summary": summary,
                "items": [item.to_dict() for item in items],
            }
        )
        return

    if args.command == "session-extract":
        if args.query:
            items, _ = session_service.search_events(
                args.session_id, args.query, args.limit
            )
        else:
            items = session_service.list_events(args.session_id, args.limit)
        dump(
            {
                "session_id": args.session_id,
                "summary": orchestrator_service.summarize_events(items),
                "suggestions": [
                    item.to_dict()
                    for item in orchestrator_service.extract_suggestions(items)
                ],
            }
        )
        return

    if args.command == "materialize-suggestion":
        kind = args.kind.strip().lower()
        if kind == "persistent_user":
            dump(
                {
                    "destination": "persistent:user",
                    "payload": persistent_service.add_entry("user", args.content),
                }
            )
            return
        if kind == "persistent_memory":
            dump(
                {
                    "destination": "persistent:memory",
                    "payload": persistent_service.add_entry("memory", args.content),
                }
            )
            return
        if kind == "skill":
            dump(
                {
                    "destination": "skills",
                    "payload": skill_service.save_skill(
                        skill_name=args.title,
                        description=args.content,
                    ).to_dict(),
                }
            )
            return
        raise SystemExit(f"Unsupported suggestion kind: {args.kind}")

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
