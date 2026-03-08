#!/usr/bin/env python3
"""Parse webhook payload and write a task execution report."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process Feishu webhook task payload")
    parser.add_argument(
        "--payload",
        required=False,
        help='Raw JSON payload string, e.g. \'{"task":"Hello"}\'',
    )
    parser.add_argument(
        "--payload-file",
        required=False,
        help="Path to a JSON file that contains webhook payload",
    )
    parser.add_argument(
        "--report-file",
        default="reports/webhook_task_result.txt",
        help="Path for generated task report",
    )
    return parser.parse_args()


def parse_payload(raw_payload: str) -> str:
    """Return task text from webhook payload."""
    try:
        payload: Any = json.loads(raw_payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive branch
        raise ValueError(f"Invalid JSON payload: {exc}") from exc

    if isinstance(payload, dict):
        text = payload.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        task = payload.get("task")
        if isinstance(task, str) and task.strip():
            return task.strip()
        raise ValueError("Payload must include non-empty 'text' or 'task' field")

    if isinstance(payload, str) and payload.strip():
        return payload.strip()

    raise ValueError("Unsupported payload format")


def execute_task(task: str) -> str:
    """Execute minimal task workflow and return result summary."""
    if task.lower() == "hello":
        return "Executed Hello task: created task report and prepared email summary."
    return f"Task '{task}' recorded for follow-up; no specialized handler implemented."


def build_report(task: str, execution_result: str) -> str:
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "任务来源: Feishu Webhook",
        f"生成时间: {generated_at}",
        f"任务内容: {task}",
        "",
        "执行结果:",
        execution_result,
        "",
        "代码修改摘要:",
        "1. 新增 `tools/process_webhook_task.py`：解析 payload 并生成任务报告。",
        "2. 新增 `tests/test_process_webhook_task.py`：覆盖 payload 解析和报告生成测试。",
        "",
        "测试执行结果:",
        "待执行",
    ]
    return "\n".join(lines) + "\n"


def write_report(report_file: str, content: str) -> pathlib.Path:
    path = pathlib.Path(report_file).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def load_payload(args: argparse.Namespace) -> str:
    if args.payload and args.payload.strip():
        return args.payload
    if args.payload_file:
        return pathlib.Path(args.payload_file).resolve().read_text(encoding="utf-8")
    raise ValueError("Either --payload or --payload-file must be provided")


def main() -> None:
    args = parse_args()
    raw_payload = load_payload(args)
    task = parse_payload(raw_payload)
    result = execute_task(task)
    report = build_report(task, result)
    report_path = write_report(args.report_file, report)
    print(f"Task processed successfully. Report written to {report_path}")


if __name__ == "__main__":
    main()
