from __future__ import annotations

import argparse
import json

from agent_memory_project.services.memory_service import MemoryService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a minimal local memory workflow.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-memories", help="List stored memories.")

    remember_parser = subparsers.add_parser("remember", help="Store a new memory.")
    remember_parser.add_argument("--content", required=True, help="Memory content.")
    remember_parser.add_argument("--source", default="cli", help="Memory source label.")
    remember_parser.add_argument(
        "--tags",
        nargs="*",
        default=[],
        help="Optional memory tags.",
    )

    recall_parser = subparsers.add_parser("recall", help="Search stored memories.")
    recall_parser.add_argument("--query", required=True, help="Search query.")
    recall_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max number of results.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = MemoryService()

    if args.command == "list-memories":
        items = [memory.to_dict() for memory in service.list_memories()]
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return

    if args.command == "remember":
        memory = service.remember(
            content=args.content,
            source=args.source,
            tags=args.tags,
        )
        print(json.dumps(memory.to_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "recall":
        items = [
            memory.to_dict()
            for memory in service.search_memories(args.query, args.limit)
        ]
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
