import pathlib
import tempfile
import unittest

from tools import process_webhook_task


class ProcessWebhookTaskPayloadTest(unittest.TestCase):
    def test_parse_payload_reads_text_field(self) -> None:
        task = process_webhook_task.parse_payload('{"text":"Hello from text"}')
        self.assertEqual(task, "Hello from text")

    def test_parse_payload_reads_task_field(self) -> None:
        task = process_webhook_task.parse_payload('{"task":"Hello"}')
        self.assertEqual(task, "Hello")

    def test_parse_payload_rejects_missing_fields(self) -> None:
        with self.assertRaises(ValueError):
            process_webhook_task.parse_payload('{"foo":"bar"}')


class ProcessWebhookTaskReportTest(unittest.TestCase):
    def test_build_report_contains_task_and_result(self) -> None:
        report = process_webhook_task.build_report("Hello", "done")
        self.assertIn("任务内容: Hello", report)
        self.assertIn("执行结果:", report)
        self.assertIn("done", report)

    def test_write_report_creates_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_file = pathlib.Path(tmp_dir) / "reports" / "result.txt"
            content = "sample"
            written = process_webhook_task.write_report(str(output_file), content)
            self.assertTrue(written.exists())
            self.assertEqual(written.read_text(encoding="utf-8"), content)


if __name__ == "__main__":
    unittest.main()
