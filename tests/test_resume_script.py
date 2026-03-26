from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestResumeScript(unittest.TestCase):
    def test_pi_resume_prefers_session_file(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        script = repo / "scripts" / "codoxear-resume"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            app_dir = root / "app"
            sock_dir = app_dir / "socks"
            sock_dir.mkdir(parents=True, exist_ok=True)
            (sock_dir / "demo.json").write_text(
                json.dumps(
                    {
                        "session_id": "pi-session-id",
                        "owner": "terminal",
                        "cli": "pi",
                        "cwd": "/work/project",
                        "start_ts": 1.0,
                        "session_file": "/tmp/pi-session.jsonl",
                        "log_path": "/tmp/pi-log.jsonl",
                    }
                ),
                encoding="utf-8",
            )
            bin_dir = root / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            fake_pi = bin_dir / "pi"
            fake_pi.write_text(
                "#!/usr/bin/env bash\n"
                "printf 'PI:%s\\n' \"$*\"\n",
                encoding="utf-8",
            )
            fake_pi.chmod(fake_pi.stat().st_mode | stat.S_IXUSR)

            proc = subprocess.run(
                [str(script), "--last"],
                env={"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}", "CODEX_WEB_APP_DIR": str(app_dir)},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("PI:--session /tmp/pi-session.jsonl", proc.stdout)


if __name__ == "__main__":
    unittest.main()
