import json
import subprocess
import pathlib
from typing import List, Dict, Tuple
from cra_web.dtos import Issue


ESLINT_CFG = pathlib.Path(__file__).with_name(".eslintrc.json")


def has_javascript(path: pathlib.Path) -> bool:
    """Check if the path contains JavaScript files."""
    if path.is_file():
        return path.suffix in [".js", ".jsx"]
    elif path.is_dir():
        for file_path in path.rglob("*.js"):
            return True
        for file_path in path.rglob("*.jsx"):
            return True
    return False


def _check_tool_installed(tool_name: str) -> bool:
    """Check if a tool is installed and available in PATH."""
    try:
        subprocess.run(
            [tool_name, "--version"], capture_output=True, text=True, timeout=5
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def _ensure_tools_installed():
    """Ensure all required JavaScript tools are installed."""
    required_tools = ["eslint", "jscpd"]
    missing_tools = []

    for tool in required_tools:
        if not _check_tool_installed(tool):
            missing_tools.append(tool)

    if missing_tools:
        raise RuntimeError(
            f"Missing required tools: {', '.join(missing_tools)}. "
            f"Please install them first::"
            f"  npm install -g eslint"
            f"  npm install -g jscpd"
        )


def run_eslint(path: pathlib.Path) -> Tuple[str, List[Dict]]:
    """Run ESLint and return both raw output and parsed JSON."""
    cmd = ["eslint", "--config", str(ESLINT_CFG), "--format", "json", str(path)]
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, text=True, stderr=subprocess.DEVNULL
    )
    # ESLint returns non-zero exit code when it finds issues, but still produces output
    if result.stdout:
        try:
            json_output = json.loads(result.stdout)
            return result.stdout, json_output
        except json.JSONDecodeError:
            # If JSON parsing fails, return empty list
            return result.stdout, []
    else:
        # If no stdout, return empty list
        return "", []


def run_semgrep(path: pathlib.Path) -> Tuple[str, List[Dict]]:
    """Run Semgrep and return both raw output and parsed JSON."""
    cmd = ["semgrep", "--config=auto", "--json", str(path)]
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, text=True, stderr=subprocess.DEVNULL
    )
    if result.stdout:
        try:
            json_data = json.loads(result.stdout)
            return result.stdout, json_data.get("results", [])
        except json.JSONDecodeError:
            # If JSON parsing fails, return empty list
            return result.stdout, []
    else:
        # If no stdout, return empty list
        return "", []


def run_jscpd(path: pathlib.Path) -> Tuple[str, List[Dict]]:
    """Run jscpd and return both raw output and parsed JSON."""
    # Run jscpd with default output settings
    cmd = ["jscpd", str(path)]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )

        # Read the generated file
        output_file = pathlib.Path("-/jscpd-report.json")
        if output_file.exists():
            try:
                with open(output_file, "r") as f:
                    raw = f.read()
                # Clean up the file
                output_file.unlink()

                raw = raw.strip()
                if not raw:  # jscpd prints nothing when 0 clones
                    return raw, []
                json_data = json.loads(raw)
                return raw, json_data.get("duplicates", [])
            except (json.JSONDecodeError, Exception):
                # Clean up any files that might have been created
                if output_file.exists():
                    output_file.unlink()
                return "", []
        return "", []
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, Exception):
        # Clean up any files that might have been created
        output_file = pathlib.Path("-/jscpd-report.json")
        if output_file.exists():
            output_file.unlink()
        return "", []


def eslint_json(path: pathlib.Path) -> List[Dict]:
    """Run ESLint and return JSON output."""
    _, json_output = run_eslint(path)
    return json_output


def semgrep_json(path: pathlib.Path) -> List[Dict]:
    """Run Semgrep and return JSON output."""
    _, json_output = run_semgrep(path)
    return json_output


def jscpd_json(path: pathlib.Path) -> List[Dict]:
    """Run jscpd and return JSON output."""
    _, json_output = run_jscpd(path)
    return json_output


def js_issues(root: pathlib.Path) -> List[Issue]:
    """Run all JavaScript linters and return list of issues."""
    # Check if required tools are installed
    _ensure_tools_installed()

    issues: List[Issue] = []

    # 1. eslint + security
    try:
        eslint_results = eslint_json(root)
        for file_rec in eslint_results:
            for m in file_rec["messages"]:
                # Convert ESLint severity to our standard severity levels
                if m["severity"] == 2:
                    severity = "error"
                elif m["severity"] == 1:
                    severity = "warning"
                else:
                    severity = "info"

                issue = Issue(
                    file=file_rec["filePath"],
                    line=m["line"],
                    severity=severity,
                    rule=m.get("ruleId", "unknown"),
                    description=m["message"],
                    fix=m.get("fix", ""),
                )
                issues.append(issue)
    except Exception as e:
        print(f"Error running ESLint: {e}")

    # 2. semgrep
    try:
        semgrep_results = semgrep_json(root)
        for hit in semgrep_results:
            # Semgrep uses different severity levels, normalize them
            # Semgrep severity is in hit["extra"]["metadata"]["confidence"] or hit["extra"]["severity"]
            semgrep_severity = hit["extra"].get("severity", "INFO")
            confidence = (
                hit["extra"]["metadata"].get("confidence", "LOW")
                if "metadata" in hit["extra"]
                else "LOW"
            )

            # Use confidence for primary classification if available, otherwise use severity
            primary_severity = confidence if confidence != "LOW" else semgrep_severity

            if primary_severity.upper() in ["HIGH", "ERROR", "CRITICAL"]:
                severity = "error"
            elif primary_severity.upper() in ["MEDIUM", "WARNING", "MODERATE"]:
                severity = "warning"
            else:
                severity = "info"

            issue = Issue(
                file=hit["path"],
                line=hit["start"]["line"],
                severity=severity,
                rule=hit["check_id"],
                description=hit["extra"]["message"],
                fix=hit["extra"].get("fix", ""),
            )
            issues.append(issue)
    except Exception as e:
        print(f"Error running Semgrep: {e}")

    # 3. jscpd
    try:
        jscpd_results = jscpd_json(root)
        for dup in jscpd_results:
            issue = Issue(
                file=dup["firstFile"]["name"],
                line=dup["firstFile"]["startLine"],
                severity="warning",
                rule="duplicate-block",
                description=f"Duplicated block ({dup['lines']} lines). Also in {dup['secondFile']['name']}:{dup['secondFile']['startLine']}",
                fix="Extract into shared function/module",
            )
            issues.append(issue)
    except Exception as e:
        print(f"Error running jscpd: {e}")

    return issues


def run_js_linters(file_path: str) -> str:
    """Run all JavaScript linters and return formatted markdown report."""
    from datetime import datetime
    import pathlib

    path = pathlib.Path(file_path)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Initialize outputs
    js_eslint_output = ""
    js_semgrep_output = ""
    js_jscpd_output = ""

    try:
        # Check if required tools are installed
        _ensure_tools_installed()

        # Run ESLint
        try:
            eslint_raw, _ = run_eslint(path)
            js_eslint_output = (
                eslint_raw if eslint_raw else "No output or errors occurred."
            )
        except Exception as e:
            js_eslint_output = f"Error running ESLint: {str(e)}"

        # Run Semgrep
        try:
            semgrep_raw, _ = run_semgrep(path)
            js_semgrep_output = (
                semgrep_raw if semgrep_raw else "No output or errors occurred."
            )
        except Exception as e:
            js_semgrep_output = f"Error running Semgrep: {str(e)}"

        # Run jscpd
        try:
            jscpd_raw, _ = run_jscpd(path)
            js_jscpd_output = (
                jscpd_raw if jscpd_raw else "No output or errors occurred."
            )
        except Exception as e:
            js_jscpd_output = f"Error running jscpd: {str(e)}"

    except RuntimeError as e:
        return f"Error: {str(e)}"

    # Build the report
    report = f"""# JavaScript Linting Report

- **Path**: `{file_path}`
- **Generated on**: {timestamp}

## ESLint Output

```
{js_eslint_output or "No output or errors occurred."}
```

## Semgrep Output

```
{js_semgrep_output or "No output or errors occurred."}
```

## jscpd Output

```
{js_jscpd_output or "No output or errors occurred."}
```

---
*Report generated by CRA*
"""

    return report


def get_js_issues(file_path: str) -> List[Issue]:
    """Get structured JavaScript issues by running all linters."""
    path = pathlib.Path(file_path)
    try:
        _ensure_tools_installed()
        return js_issues(path)
    except Exception as e:
        print(f"Error getting JavaScript issues: {e}")
        return []
