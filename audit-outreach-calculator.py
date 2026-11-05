#!/usr/bin/env python3
"""Static audit of outreach-calculator.html.

CORRECTED 2026-11-04. The previous version of this script produced a false FAIL.

Why it failed
-------------
1. It collected output ids with  re.findall(r'id="(out[A-Za-z]+)"', src)  which
   requires camelCase immediately after "out". The page ships hyphenated ids
   (id="out-deliverable", id="out-posreplies", id="out-meetings", ...) so that
   pattern matched 0 times -> it printed "output spans: 0".
2. It collected JS element references with double quotes only
   (getElementById\("([^"]+)"\) and \b(?:el|num|pct|set)\("([^"]+)"), while the
   page calls el('out-deliverable') with SINGLE quotes, so that also matched 0
   times -> it printed "ids referenced: 0".
3. It then required len(outputs) == 9 while the page deliberately ships 7 output
   rows, so even a correct count of 7 would have failed the exit test.

Two zero counts from two wrong patterns plus a stale expected constant is the
entire false FAIL. The page was correct; the audit was wrong.

What this version does
----------------------
Counts output ids by scanning every id attribute and keeping the values that
contain the substring "out-", quote style agnostic. Prints each id it finds,
then prints PASS or FAIL with the reason for every failed check.

Usage:
    python3 pipeline3/packs/outreach-agency/tools/audit-outreach-calculator.py \
        pipeline3/packs/outreach-agency/tools/outreach-calculator.html

Default target is outreach-calculator.html next to this script.
Exit codes: 0 = PASS, 1 = FAIL, 2 = target file missing.
"""

import os
import re
import sys

DEFAULT_TARGET = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "outreach-calculator.html",
)

ID_ATTR_RE = re.compile(r"""\bid\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
SPAN_ID_RE = re.compile(
    r"""<span\b[^>]*\bid\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE
)
LABEL_FOR_RE = re.compile(
    r"""<label\b[^>]*\bfor\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE
)
ROW_LABEL_RE = re.compile(
    r"""<span\b[^>]*class\s*=\s*(?:"row-label"|'row-label')""", re.IGNORECASE
)
SCRIPT_RE = re.compile(r"<script\b[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)
EXTERNAL_RE = re.compile(
    r"""(?:src|href)\s*=\s*(?:"(?:https?:)?//[^"]*"|'(?:https?:)?//[^']*')""",
    re.IGNORECASE,
)


def _val(match):
    return match.group(1) if match.group(1) is not None else match.group(2)


def audit(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        html = fh.read()

    failures = []

    # 1. Output ids: any id attribute whose value contains "out-".
    all_ids = [_val(m) for m in ID_ATTR_RE.finditer(html)]
    out_ids = [i for i in all_ids if "out-" in i]

    print("Output ids found (id attribute containing 'out-'):")
    if out_ids:
        for i in out_ids:
            print("  - %s" % i)
    else:
        print("  (none)")
    print("Output id count: %d" % len(out_ids))
    if not out_ids:
        failures.append("no id attribute contains the substring 'out-'")

    # 2. Output spans: <span id="...out-...">.
    span_ids = [_val(m) for m in SPAN_ID_RE.finditer(html)]
    span_out_ids = [i for i in span_ids if "out-" in i]
    print("Output spans (<span id=...out-...>): %d" % len(span_out_ids))
    if not span_out_ids:
        failures.append("no <span> carries an id containing 'out-'")

    # 3. Input labels.
    label_targets = set(_val(m) for m in LABEL_FOR_RE.finditer(html))
    print("Input labels (<label for=...>): %d" % len(label_targets))

    # 4. Output row labels must match the output id count.
    row_labels = len(ROW_LABEL_RE.findall(html))
    print("Output row labels (span.row-label): %d" % row_labels)
    if row_labels != len(out_ids):
        failures.append(
            "output id count (%d) does not match output row label count (%d)"
            % (len(out_ids), row_labels)
        )

    # 5. aria-live present.
    has_aria_live = "aria-live" in html
    print("aria-live present: %s" % ("yes" if has_aria_live else "no"))
    if not has_aria_live:
        failures.append("aria-live attribute missing")

    # 6. Exactly one addEventListener('input') wiring.
    input_listeners = len(
        re.findall(r"""addEventListener\(\s*['"]input['"]""", html)
    )
    print("addEventListener('input') count: %d" % input_listeners)
    if input_listeners != 1:
        failures.append(
            "expected exactly 1 addEventListener('input'), found %d" % input_listeners
        )

    # 7. Balanced JS braces across inline <script> blocks.
    js = "\n".join(SCRIPT_RE.findall(html))
    opens = js.count("{")
    closes = js.count("}")
    print("JS braces: %d open / %d close" % (opens, closes))
    if opens != closes:
        failures.append("unbalanced JS braces: %d open vs %d close" % (opens, closes))

    # 8. Zero external references.
    externals = EXTERNAL_RE.findall(html)
    print("External references: %d" % len(externals))
    if externals:
        failures.append("external references present: %s" % ", ".join(externals))

    print("")
    if failures:
        print("RESULT: FAIL")
        for reason in failures:
            print("  reason: %s" % reason)
        return 1

    print("RESULT: PASS")
    print(
        "  reason: %d output ids, %d output spans, %d row labels, aria-live present, "
        "1 input listener, balanced JS braces, 0 external references"
        % (len(out_ids), len(span_out_ids), row_labels)
    )
    return 0


def main(argv):
    target = argv[1] if len(argv) > 1 else DEFAULT_TARGET
    if not os.path.isfile(target):
        print("RESULT: FAIL")
        print("  reason: target file not found: %s" % target)
        return 2
    print("Auditing: %s" % target)
    print("")
    return audit(target)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
