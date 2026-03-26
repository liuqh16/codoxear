from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from codoxear.cli_support import cli_bin
from codoxear.cli_support import cli_home
from codoxear.cli_support import cli_logs_dir
from codoxear.cli_support import claude_assistant_text
from codoxear.cli_support import infer_cli_from_log_path
from codoxear.cli_support import is_gemini_chat_log_path
from codoxear.cli_support import is_pi_session_log_path
from codoxear.cli_support import normalize_cli_name
from codoxear.cli_support import parse_cli_name
from codoxear.cli_support import read_gemini_log_cwd
from codoxear.cli_support import read_gemini_rollout_objs
from codoxear.cli_support import read_gemini_session_id
from codoxear.cli_support import read_pi_log_cwd
from codoxear.cli_support import read_pi_session_id
from codoxear.cli_support import session_id_from_log_path


class TestCliSupport(unittest.TestCase):
    def test_normalize_and_parse_gemini(self) -> None:
        self.assertEqual(normalize_cli_name("gemini"), "gemini")
        self.assertEqual(normalize_cli_name("google-gemini"), "gemini")
        self.assertEqual(normalize_cli_name("pi-coding-agent"), "pi")
        self.assertEqual(parse_cli_name("gemini"), "gemini")
        self.assertEqual(parse_cli_name("pi"), "pi")
        with self.assertRaises(ValueError):
            parse_cli_name("unknown-cli")

    def test_gemini_home_bin_and_logs_dir(self) -> None:
        with TemporaryDirectory() as td:
            home = Path(td) / ".g"
            with patch.dict(os.environ, {"GEMINI_HOME": str(home), "GEMINI_BIN": "/usr/local/bin/gemini"}, clear=False):
                self.assertEqual(cli_home("gemini"), home)
                self.assertEqual(cli_logs_dir("gemini"), home / "tmp")
                self.assertEqual(cli_bin("gemini"), "/usr/local/bin/gemini")

    def test_pi_home_bin_and_logs_dir(self) -> None:
        with TemporaryDirectory() as td:
            home = Path(td) / ".pi-home"
            with patch.dict(os.environ, {"PI_HOME": str(home), "PI_BIN": "/usr/local/bin/pi"}, clear=False):
                self.assertEqual(cli_home("pi"), home)
                self.assertEqual(cli_logs_dir("pi"), home / "agent" / "sessions")
                self.assertEqual(cli_bin("pi"), "/usr/local/bin/pi")

    def test_gemini_log_helpers(self) -> None:
        with TemporaryDirectory() as td:
            gem_home = Path(td) / ".gemini"
            chats = gem_home / "tmp" / "project-x" / "chats"
            chats.mkdir(parents=True, exist_ok=True)
            (chats.parent / ".project_root").write_text("/work/project-x\n", encoding="utf-8")
            sid = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
            log = chats / "session-2026-03-02T00-00-abcd1234.json"
            payload = {
                "sessionId": sid,
                "messages": [
                    {
                        "type": "user",
                        "timestamp": "2026-03-02T00:00:00.000Z",
                        "content": [{"text": "hello"}],
                    },
                    {
                        "type": "gemini",
                        "timestamp": "2026-03-02T00:00:02.000Z",
                        "content": "done",
                        "thoughts": [{"subject": "draft"}],
                        "tokens": {"tool": 0},
                    },
                ],
            }
            log.write_text(json.dumps(payload), encoding="utf-8")

            with patch.dict(os.environ, {"GEMINI_HOME": str(gem_home)}, clear=False):
                self.assertTrue(is_gemini_chat_log_path(log, gemini_tmp_dir=cli_logs_dir("gemini")))
                self.assertEqual(read_gemini_session_id(log), sid)
                self.assertEqual(read_gemini_log_cwd(log), "/work/project-x")
                self.assertEqual(infer_cli_from_log_path(log), "gemini")
                self.assertEqual(session_id_from_log_path(log, cli="gemini"), sid)
                objs = read_gemini_rollout_objs(log)
                self.assertEqual(len(objs), 2)
                self.assertEqual(objs[0].get("type"), "user")
                self.assertEqual(objs[1].get("type"), "assistant")
                self.assertTrue(bool(objs[1].get("_gemini_turn_end")))


    def test_pi_log_helpers(self) -> None:
        with TemporaryDirectory() as td:
            pi_home = Path(td) / ".pi"
            log = pi_home / "agent" / "sessions" / "--work-project-x--" / "2026-03-02_demo.jsonl"
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(
                '{"type":"session","version":3,"id":"pi-session-1","timestamp":"2026-03-02T00:00:00.000Z","cwd":"/work/project-x"}\n'
                '{"type":"message","id":"u1","timestamp":"2026-03-02T00:00:01.000Z","message":{"role":"user","content":"hello"}}\n',
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"PI_HOME": str(pi_home)}, clear=False):
                self.assertTrue(is_pi_session_log_path(log, pi_sessions_dir=cli_logs_dir("pi")))
                self.assertEqual(read_pi_session_id(log), "pi-session-1")
                self.assertEqual(read_pi_log_cwd(log), "/work/project-x")
                self.assertEqual(infer_cli_from_log_path(log), "pi")
                self.assertEqual(session_id_from_log_path(log, cli="pi"), "pi-session-1")

    def test_gemini_thinking_only_row_does_not_mark_turn_end(self) -> None:
        with TemporaryDirectory() as td:
            gem_home = Path(td) / ".gemini"
            chats = gem_home / "tmp" / "project-x" / "chats"
            chats.mkdir(parents=True, exist_ok=True)
            sid = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
            log = chats / "session-2026-03-02T00-00-abcd1234.json"
            payload = {
                "sessionId": sid,
                "messages": [
                    {
                        "type": "user",
                        "timestamp": "2026-03-02T00:00:00.000Z",
                        "content": [{"text": "hello"}],
                    },
                    {
                        "type": "gemini",
                        "timestamp": "2026-03-02T00:00:02.000Z",
                        "content": "",
                        "thoughts": [{"subject": "draft"}],
                        "tokens": {"thoughts": 12},
                    },
                ],
            }
            log.write_text(json.dumps(payload), encoding="utf-8")

            with patch.dict(os.environ, {"GEMINI_HOME": str(gem_home)}, clear=False):
                objs = read_gemini_rollout_objs(log)
                self.assertEqual(len(objs), 2)
                self.assertEqual(objs[1].get("type"), "assistant")
                self.assertFalse(bool(objs[1].get("_gemini_turn_end")))

    def test_claude_assistant_text_filters_dot_placeholder_and_blank(self) -> None:
        dot_obj = {
            "type": "assistant",
            "message": {
                "stop_reason": None,
                "usage": {"output_tokens": 1},
                "content": [{"type": "text", "text": "."}],
            },
        }
        self.assertIsNone(claude_assistant_text(dot_obj))

        blank_obj = {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "\n\n"}],
            },
        }
        self.assertIsNone(claude_assistant_text(blank_obj))

        ok_obj = {
            "type": "assistant",
            "message": {
                "stop_reason": "end_turn",
                "usage": {"output_tokens": 2},
                "content": [{"type": "text", "text": "OK"}],
            },
        }
        self.assertEqual(claude_assistant_text(ok_obj), "OK")


if __name__ == "__main__":
    unittest.main()
