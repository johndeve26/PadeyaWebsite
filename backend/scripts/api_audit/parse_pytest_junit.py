"""Parse pytest JUnit XML into the Phase 1 baseline JSON artifact."""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def classify(case: ET.Element) -> tuple[str, str | None]:
    if case.find("failure") is not None:
        return "PRE_EXISTING_PRODUCT_FAILURE", case.find("failure").get("message")
    if case.find("error") is not None:
        return "TEST_INFRASTRUCTURE_FAILURE", case.find("error").get("message")
    if case.find("skipped") is not None:
        return "EXPECTED_SKIP", case.find("skipped").get("message")
    return "PASS", None


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        raise SystemExit("usage: parse_pytest_junit.py <junit.xml> <output.json>")
    xml_path = Path(argv[1])
    out_path = Path(argv[2])
    root = ET.parse(xml_path).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        raise SystemExit("No testsuite found in junit xml")

    results = []
    for case in suite.findall(".//testcase"):
        status, message = classify(case)
        results.append(
            {
                "classname": case.get("classname"),
                "name": case.get("name"),
                "time": case.get("time"),
                "status": status,
                "message": message,
            }
        )

    payload = {
        "collected": len(results),
        "passed": sum(1 for row in results if row["status"] == "PASS"),
        "failed": sum(1 for row in results if row["status"] == "PRE_EXISTING_PRODUCT_FAILURE"),
        "skipped": sum(1 for row in results if row["status"] == "EXPECTED_SKIP"),
        "errors": sum(1 for row in results if row["status"] == "TEST_INFRASTRUCTURE_FAILURE"),
        "xfailed": 0,
        "duration_seconds": float(suite.get("time", "0") or 0),
        "results": results,
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
