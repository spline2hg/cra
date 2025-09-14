import os
from typing import List
from src.cra_web.dtos import Issue


def parse_lint_report(report_content: str) -> List[Issue]:
    """Parse the lint report content and extract issues."""
    issues = []

    try:
        sections = report_content.split("## ")

        # Parse each section with its specific parser
        for section in sections:
            if "Pylint Output" in section:
                try:
                    pylint_issues = parse_pylint_section(section)
                    issues.extend(pylint_issues)
                except Exception as e:
                    print(f"Error parsing Pylint section: {e}")
            elif "Flake8 Output" in section:
                try:
                    flake8_issues = parse_flake8_section(section)
                    issues.extend(flake8_issues)
                except Exception as e:
                    print(f"Error parsing Flake8 section: {e}")
            elif "Bandit Output" in section:
                try:
                    bandit_issues = parse_bandit_section(section)
                    issues.extend(bandit_issues)
                except Exception as e:
                    print(f"Error parsing Bandit section: {e}")
            elif "Vulture Output" in section:
                try:
                    vulture_issues = parse_vulture_section(section)
                    issues.extend(vulture_issues)
                except Exception as e:
                    print(f"Error parsing Vulture section: {e}")
            elif "Radon Complexity" in section:
                try:
                    radon_complexity_issues = parse_radon_complexity_section(section)
                    issues.extend(radon_complexity_issues)
                except Exception as e:
                    print(f"Error parsing Radon Complexity section: {e}")
            elif "Radon Maintainability" in section:
                try:
                    radon_maintainability_issues = parse_radon_maintainability_section(
                        section
                    )
                    issues.extend(radon_maintainability_issues)
                except Exception as e:
                    print(f"Error parsing Radon Maintainability section: {e}")
            elif (
                "ESLint Output" in section
                or "Semgrep Output" in section
                or "jscpd Output" in section
            ):
                # JavaScript sections will be parsed together by the unified parser
                pass
    except Exception as e:
        print(f"Error parsing report: {e}")

    # Parse JavaScript issues using the unified parser
    try:
        javascript_issues = parse_javascript_issues(report_content)
        issues.extend(javascript_issues)
    except Exception as e:
        print(f"Error parsing JavaScript issues: {e}")

    return issues


def parse_pylint_section(section: str) -> List[Issue]:
    """Parse Pylint output section."""
    issues = []
    lines = section.split("\n")

    in_code_block = False
    for line in lines:
        if line.strip() == "```":
            in_code_block = not in_code_block
            continue

        if in_code_block and ":" in line and line.count(":") >= 3:
            try:
                parts = line.split(":")
                if len(parts) >= 5:
                    file_path = parts[0].strip()
                    line_number = int(parts[1].strip())
                    severity_code = parts[3].strip()[0].upper()
                    if severity_code == "E":
                        severity = "error"
                    elif severity_code == "W":
                        severity = "warning"
                    else:
                        severity = "info"
                    rule = parts[3].strip()
                    description = ":".join(parts[4:]).strip()

                    issues.append(
                        Issue(
                            file=file_path,
                            line=line_number,
                            severity=severity,
                            rule=rule,
                            description=description,
                            fix="No automatic fix available",
                        )
                    )
            except (ValueError, IndexError):
                continue

    return issues


def parse_vulture_section(section: str) -> List[Issue]:
    """Parse Vulture output section."""
    issues = []
    lines = section.split("\n")

    in_code_block = False
    for line in lines:
        if line.strip() == "```":
            in_code_block = not in_code_block
            continue

        if in_code_block and line.strip() and not line.startswith("#"):
            try:
                if ":" in line and "unused" in line:
                    parts = line.split(":")
                    if len(parts) >= 3:
                        file_path = parts[0].strip()
                        file_name = os.path.basename(file_path)
                        line_number = int(parts[1].strip())
                        description = ":".join(parts[2:]).strip()

                        issues.append(
                            Issue(
                                file=file_name,
                                line=line_number,
                                severity="warning",
                                rule="vulture-dead-code",
                                description=description,
                                fix="Remove unused code or mark as intentionally unused",
                            )
                        )
            except (ValueError, IndexError):
                continue

    return issues


def parse_radon_complexity_section(section: str) -> List[Issue]:
    """Parse Radon Complexity output section."""
    issues = []
    lines = section.split("\n")

    in_code_block = False
    for line in lines:
        if line.strip() == "```":
            in_code_block = not in_code_block
            continue

        if in_code_block and line.strip() and " - " in line:
            try:
                if ":" in line:
                    file_part, line_part = line.split(":", 1)
                    file_name = os.path.basename(file_part.strip())

                    if ":" in line_part:
                        line_num_part = line_part.split(":")[0].strip()
                        line_number = int(line_num_part)

                        complexity_info = line_part[line_part.find(":") + 1 :].strip()

                        issues.append(
                            Issue(
                                file=file_name,
                                line=line_number,
                                severity="warning",
                                rule="radon-complexity",
                                description=f"High complexity: {complexity_info}",
                                fix="Refactor to reduce cyclomatic complexity",
                            )
                        )
            except (ValueError, IndexError):
                continue

    return issues


def parse_radon_maintainability_section(section: str) -> List[Issue]:
    """Parse Radon Maintainability output section."""
    issues = []
    lines = section.split("\n")

    in_code_block = False
    for line in lines:
        if line.strip() == "```":
            in_code_block = not in_code_block
            continue

        if in_code_block and line.strip() and " - " in line:
            try:
                if " - " in line:
                    file_part, grade_part = line.split(" - ", 1)
                    file_name = os.path.basename(file_part.strip())
                    grade = grade_part.strip()

                    severity_map = {
                        "A": "info",
                        "B": "info",
                        "C": "warning",
                        "D": "error",
                        "E": "error",
                        "F": "error",
                    }
                    severity = severity_map.get(grade, "warning")

                    issues.append(
                        Issue(
                            file=file_name,
                            line=0,
                            severity=severity,
                            rule="radon-maintainability",
                            description=f"Maintainability grade: {grade}",
                            fix="Improve code structure and readability",
                        )
                    )
            except (ValueError, IndexError):
                continue

    return issues


def parse_flake8_section(section: str) -> List[Issue]:
    """Parse Flake8 output section."""
    issues = []
    lines = section.split("\n")

    in_code_block = False
    for line in lines:
        if line.strip() == "```":
            in_code_block = not in_code_block
            continue

        if in_code_block and ":" in line and line.count(":") >= 2:
            try:
                parts = line.split(":")
                if len(parts) >= 4:
                    file_path = parts[0].strip()
                    file_name = os.path.basename(file_path)
                    line_number = int(parts[1].strip())
                    code = parts[3].strip()[0].upper()
                    if code == "E":
                        severity = "error"
                    elif code == "W":
                        severity = "warning"
                    else:
                        severity = "info"
                    rule = parts[3].strip()
                    description = ":".join(parts[4:]).strip()

                    issues.append(
                        Issue(
                            file=file_name,
                            line=line_number,
                            severity=severity,
                            rule=rule,
                            description=description,
                            fix="No automatic fix available",
                        )
                    )
            except (ValueError, IndexError):
                continue

    return issues


def parse_bandit_section(section: str) -> List[Issue]:
    """Parse Bandit output section."""
    issues = []
    lines = section.split("\n")

    in_code_block = False
    for line in lines:
        if line.strip() == "```":
            in_code_block = not in_code_block
            continue

        if in_code_block:
            if ">>" in line or "Issue:" in line:
                issues.append(
                    Issue(
                        file="unknown",
                        line=0,
                        severity="warning",
                        rule="bandit-issue",
                        description=line.strip(),
                        fix="Review security implications",
                    )
                )

    return issues


def parse_eslint_section(section: str) -> List[Issue]:
    """Parse ESLint output section."""
    issues = []
    lines = section.split("\n")

    in_code_block = False
    for line in lines:
        if line.strip() == "```":
            in_code_block = not in_code_block
            continue

        if in_code_block and line.strip() and ":" in line and line.count(":") >= 3:
            try:
                # ESLint format: file_path:line:column: message
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    file_path = parts[0].strip()
                    file_name = os.path.basename(file_path)
                    line_number = int(parts[1].strip())
                    # Determine severity from message
                    message = parts[3].strip()
                    if "error" in message.lower():
                        severity = "error"
                    elif "warning" in message.lower():
                        severity = "warning"
                    else:
                        severity = "info"

                    issues.append(
                        Issue(
                            file=file_name,
                            line=line_number,
                            severity=severity,
                            rule="eslint-issue",
                            description=message,
                            fix="No automatic fix available",
                        )
                    )
            except (ValueError, IndexError):
                continue

    return issues


def parse_semgrep_section(section: str) -> List[Issue]:
    """Parse Semgrep output section."""
    issues = []
    lines = section.split("\n")

    in_code_block = False
    for line in lines:
        if line.strip() == "```":
            in_code_block = not in_code_block
            continue

        if in_code_block and line.strip() and "rule:" in line:
            try:
                # Semgrep format: file_path:line:column: rule: message
                parts = line.split(":", 4)
                if len(parts) >= 5:
                    file_path = parts[0].strip()
                    file_name = os.path.basename(file_path)
                    line_number = int(parts[1].strip())
                    rule = parts[3].strip()
                    message = parts[4].strip()

                    issues.append(
                        Issue(
                            file=file_name,
                            line=line_number,
                            severity="warning",  # Semgrep typically reports warnings
                            rule=rule,
                            description=message,
                            fix="Review security implications",
                        )
                    )
            except (ValueError, IndexError):
                continue

    return issues


def parse_jscpd_section(section: str) -> List[Issue]:
    """Parse jscpd output section."""
    issues = []
    lines = section.split("\n")

    in_code_block = False
    for line in lines:
        if line.strip() == "```":
            in_code_block = not in_code_block
            continue

        if in_code_block and "found" in line.lower() and "duplicate" in line.lower():
            try:
                # jscpd format: Found X duplicate lines in file1 and file2
                issues.append(
                    Issue(
                        file="multiple",
                        line=0,
                        severity="warning",
                        rule="jscpd-duplicate",
                        description=line.strip(),
                        fix="Extract into shared function/module",
                    )
                )
            except (ValueError, IndexError):
                continue

    return issues


def parse_javascript_issues(report_content: str) -> List[Issue]:
    """Parse all JavaScript issues from the report content."""
    issues = []

    try:
        sections = report_content.split("## ")

        for section in sections:
            if "ESLint Output" in section:
                try:
                    eslint_issues = parse_eslint_section(section)
                    issues.extend(eslint_issues)
                except Exception as e:
                    print(f"Error parsing ESLint section: {e}")
            elif "Semgrep Output" in section:
                try:
                    semgrep_issues = parse_semgrep_section(section)
                    issues.extend(semgrep_issues)
                except Exception as e:
                    print(f"Error parsing Semgrep section: {e}")
            elif "jscpd Output" in section:
                try:
                    jscpd_issues = parse_jscpd_section(section)
                    issues.extend(jscpd_issues)
                except Exception as e:
                    print(f"Error parsing jscpd section: {e}")
    except Exception as e:
        print(f"Error parsing JavaScript issues: {e}")

    return issues
