#!/usr/bin/env python3
"""Command-line entry point for the rewritten AIWorkFlow engine."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import TextIO

from aiwf_core import __version__
from aiwf_core.model import AIWorkflowError, COMMAND_SPECS, CommandRequest
from aiwf_core.storage import resolve_workspace
from aiwf_core.workflow import execute


class StructuredArgumentParser(argparse.ArgumentParser):
    """Emit parse failures using the same JSON envelope as engine errors."""

    def error(self, message: str) -> None:
        error = AIWorkflowError(
            code="invalid_arguments",
            message=message,
            exit_code=2,
        )
        write_error(error, sys.stderr)
        raise SystemExit(error.exit_code)


def build_parser() -> argparse.ArgumentParser:
    parser = StructuredArgumentParser(
        prog="aiwf",
        description="Deterministic workflow engine for AIWorkFlow skills.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=StructuredArgumentParser,
    )

    for spec in COMMAND_SPECS:
        command_parser = subparsers.add_parser(spec.name, help=spec.help)
        command_parser.add_argument(
            "--workspace",
            default=".",
            help="Workspace directory (default: current directory).",
        )

    return parser


def write_error(error: AIWorkflowError, stream: TextIO) -> None:
    json.dump(
        {
            "ok": False,
            "error": error.as_dict(),
        },
        stream,
        ensure_ascii=False,
        sort_keys=True,
    )
    stream.write("\n")


def write_result(payload: dict[str, object], stream: TextIO) -> None:
    json.dump(
        {
            "ok": True,
            "result": payload,
        },
        stream,
        ensure_ascii=False,
        sort_keys=True,
    )
    stream.write("\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        workspace = resolve_workspace(args.workspace)
        result = execute(CommandRequest(command=args.command, workspace=workspace))
    except AIWorkflowError as error:
        write_error(error, sys.stderr)
        return error.exit_code
    except Exception:
        error = AIWorkflowError(
            code="internal_error",
            message="The workflow engine failed unexpectedly.",
            exit_code=70,
        )
        write_error(error, sys.stderr)
        return error.exit_code

    write_result(result, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
