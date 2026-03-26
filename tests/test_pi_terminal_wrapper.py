from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestPiTerminalWrapper(unittest.TestCase):
    def test_wrapper_sets_pi_cli_env(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        script = repo / "scripts" / "codoxear-pi"
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            bin_dir = td_path / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            fake_python = bin_dir / "python3"
            fake_python.write_text(
                "#!/usr/bin/env bash\n"
                "printf 'CLI:%s\\n' \"${CODEX_WEB_CLI:-}\"\n"
                "printf 'ARGS:%s\\n' \"$*\"\n",
                encoding="utf-8",
            )
            fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)

            env = dict(os.environ)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

            proc = subprocess.run(
                [str(script), "--model", "sonnet"],
                cwd=str(td_path),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("CLI:pi", proc.stdout)
        self.assertIn("ARGS:-m codoxear.broker --model sonnet", proc.stdout)


if __name__ == "__main__":
    unittest.main()
