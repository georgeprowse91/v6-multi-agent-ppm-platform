from __future__ import annotations

import json
import os
import subprocess
import sys


def _build_scanner_cmd(source_report: str) -> str:
    return (
        'python -c "import pathlib,shutil; '
        f"shutil.copyfile(r'{source_report}', r'{{json_report}}'); "
        "pathlib.Path(r'{html_report}').write_text('<html></html>')\""
    )


def test_run_dast_executes_and_parses_report(tmp_path):
    report_dir = tmp_path / "security"
    report_dir.mkdir(parents=True, exist_ok=True)

    safe_report = {
        "site": [
            {
                "alerts": [
                    {
                        "name": "X-Frame-Options Header Not Set",
                        "riskcode": "1",
                        "riskdesc": "Low (Medium)",
                        "instances": [{"uri": "http://127.0.0.1:18080/api"}],
                    }
                ]
            }
        ]
    }
    source_report = tmp_path / "safe-report.json"
    source_report.write_text(json.dumps(safe_report), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "ops/tools/run_dast.py",
            "--report-dir",
            str(report_dir),
            "--scanner-cmd",
            _build_scanner_cmd(str(source_report)),
            "--timeout",
            "20",
        ],
        cwd=os.getcwd(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert (report_dir / "dast-report.json").exists()
    assert "DAST scan completed successfully" in result.stdout


def test_run_dast_fails_on_high_findings(tmp_path):
    report_dir = tmp_path / "security"
    report_dir.mkdir(parents=True, exist_ok=True)

    risky_report = {
        "site": [
            {
                "alerts": [
                    {
                        "name": "SQL Injection",
                        "riskcode": "3",
                        "riskdesc": "High (High)",
                        "instances": [{"uri": "http://127.0.0.1:18080/api"}],
                    }
                ]
            }
        ]
    }
    source_report = tmp_path / "risky-report.json"
    source_report.write_text(json.dumps(risky_report), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "ops/tools/run_dast.py",
            "--report-dir",
            str(report_dir),
            "--scanner-cmd",
            _build_scanner_cmd(str(source_report)),
            "--timeout",
            "20",
        ],
        cwd=os.getcwd(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "High/Critical DAST findings detected" in result.stdout
