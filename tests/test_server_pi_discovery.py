from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from codoxear.server import SessionManager


class TestServerPiDiscovery(unittest.TestCase):
    def _mgr(self) -> SessionManager:
        mgr = SessionManager.__new__(SessionManager)
        mgr._lock = threading.Lock()
        mgr._sessions = {}
        mgr._harness = {}
        mgr._aliases = {}
        mgr._files = {}
        mgr._last_discover_ts = 0.0
        return mgr

    def test_discover_existing_lists_terminal_pi_session(self) -> None:
        mgr = self._mgr()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sock_dir = root / "socks"
            sock_dir.mkdir(parents=True, exist_ok=True)
            pi_home = root / ".pi"
            log_path = pi_home / "agent" / "sessions" / "--work-project--" / "2026-03-25_demo.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(
                '{"type":"session","version":3,"id":"pi-session","timestamp":"2026-03-25T10:00:00.000Z","cwd":"/work/project"}\n'
                '{"type":"message","id":"u1","timestamp":"2026-03-25T10:00:01.000Z","message":{"role":"user","content":"hello"}}\n'
                '{"type":"message","id":"a1","timestamp":"2026-03-25T10:00:02.000Z","message":{"role":"assistant","content":[{"type":"text","text":"done"}]}}\n',
                encoding="utf-8",
            )
            sock_path = sock_dir / "broker-1.sock"
            sock_path.write_text("", encoding="utf-8")
            meta_path = sock_dir / "broker-1.json"
            meta_path.write_text(
                json.dumps(
                    {
                        "session_id": "pi-session",
                        "owner": "terminal",
                        "cli": "pi",
                        "codex_pid": 111,
                        "broker_pid": 222,
                        "cwd": "/work/project",
                        "start_ts": 1.0,
                        "log_path": str(log_path),
                        "sock_path": str(sock_path),
                        "tmux_name": None,
                    }
                ),
                encoding="utf-8",
            )
            with patch("codoxear.server.SOCK_DIR", sock_dir), patch.object(
                mgr, "_sock_call", return_value={"busy": True, "queue_len": 0, "token": None}
            ):
                mgr._discover_existing(force=True)
                sessions = mgr.list_sessions()

        self.assertEqual(len(sessions), 1)
        row = sessions[0]
        self.assertEqual(row["cli"], "pi")
        self.assertFalse(row["owned"])
        self.assertTrue(row["busy"])
        self.assertEqual(row["thread_id"], "pi-session")
        self.assertEqual(row["log_path"], str(log_path))
        self.assertEqual(row["backend"], "pty")
        self.assertEqual(row["session_file"], str(log_path))
        self.assertEqual(row["resume_hint"], f"pi --session {log_path}")

    def test_discover_existing_ignores_native_pi_sessions(self) -> None:
        mgr = self._mgr()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sock_dir = root / "socks"
            sock_dir.mkdir(parents=True, exist_ok=True)
            pi_root = root / ".pi" / "agent" / "sessions"
            session_file = pi_root / "--work-project--" / "2026-03-25_demo.jsonl"
            session_file.parent.mkdir(parents=True, exist_ok=True)
            session_file.write_text(
                '{"type":"session","version":3,"id":"native-pi","timestamp":"2026-03-25T10:00:00.000Z","cwd":"/work/project"}\n'
                '{"type":"message","id":"u1","timestamp":"2026-03-25T10:00:01.000Z","message":{"role":"user","content":"still running"}}\n',
                encoding="utf-8",
            )
            with patch("codoxear.server.SOCK_DIR", sock_dir), patch(
                "codoxear.server._cli_logs_dir", return_value=pi_root
            ), patch(
                "codoxear.server._discover_alive_pi_session_files", return_value={session_file.resolve(): 4242}
            ), patch("codoxear.server._pid_alive", side_effect=lambda pid: pid == 4242):
                mgr._discover_existing(force=True)
                sessions = mgr.list_sessions()

        self.assertEqual(sessions, [])


if __name__ == "__main__":
    unittest.main()
