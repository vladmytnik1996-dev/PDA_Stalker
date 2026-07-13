#!/usr/bin/env python3
"""Static release checks for the GitHub package. Uses only Python stdlib."""
from __future__ import annotations

import hashlib
import html.parser
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "index.html",
    "server.py",
    "start-android.sh",
    "README.md",
    "GUIDE_ANDROID.html",
    "docs/ANDROID_SETUP.md",
    "docs/TROUBLESHOOTING.md",
    "docs/GITHUB_UPLOAD.md",
    "examples/demo-map.png",
]


class Inspector(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.refs: list[tuple[str, str]] = []
        self.external_assets: list[str] = []
        self.in_script = False
        self.script_src: str | None = None
        self.script_parts: list[str] = []
        self.inline_scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {k: v for k, v in attrs}
        if data.get("id"):
            self.ids.append(data["id"] or "")
        if tag in {"img", "script", "link", "a"}:
            attr = "src" if tag in {"img", "script"} else "href"
            value = data.get(attr)
            if value:
                self.refs.append((tag, value))
                if tag in {"img", "script", "link"} and re.match(r"^(?:https?:)?//", value):
                    self.external_assets.append(value)
        if tag == "script":
            self.in_script = True
            self.script_src = data.get("src")
            self.script_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.in_script:
            if not self.script_src:
                self.inline_scripts.append("".join(self.script_parts))
            self.in_script = False
            self.script_src = None
            self.script_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_script:
            self.script_parts.append(data)


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_required() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))


def inspect_html(path: Path, allow_external_links: bool = True) -> Inspector:
    parser = Inspector()
    parser.feed(path.read_text(encoding="utf-8"))
    duplicates = sorted({item for item in parser.ids if parser.ids.count(item) > 1})
    if duplicates:
        fail(f"duplicate HTML ids in {path.name}: {duplicates}")
    if parser.external_assets:
        fail(f"external runtime assets in {path.name}: {parser.external_assets}")
    for tag, ref in parser.refs:
        if ref.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "blob:")):
            continue
        if re.match(r"^https?://", ref):
            if allow_external_links and tag == "a":
                continue
            fail(f"unexpected external ref in {path.name}: {ref}")
        clean = ref.split("#", 1)[0].split("?", 1)[0]
        if not clean:
            continue
        target = (path.parent / clean).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            fail(f"path escapes package in {path.name}: {ref}")
        if not target.exists():
            fail(f"broken local ref in {path.name}: {ref}")
    return parser



def check_markdown_refs() -> None:
    pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    for name in ("README.md", "docs/ANDROID_SETUP.md", "docs/TROUBLESHOOTING.md", "docs/GITHUB_UPLOAD.md"):
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        for ref in pattern.findall(text):
            ref = ref.strip().split(" ", 1)[0].strip("<>\"")
            if not ref or ref.startswith(("#", "http://", "https://", "mailto:")):
                continue
            clean = ref.split("#", 1)[0].split("?", 1)[0]
            target = (path.parent / clean).resolve()
            try:
                target.relative_to(ROOT.resolve())
            except ValueError:
                fail(f"Markdown path escapes package in {name}: {ref}")
            if not target.exists():
                fail(f"broken Markdown ref in {name}: {ref}")

def check_javascript(parser: Inspector) -> None:
    node = shutil.which("node")
    scripts = [s for s in parser.inline_scripts if s.strip()]
    if not scripts:
        fail("index.html contains no inline JavaScript")
    if node:
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as tmp:
            tmp.write("\n".join(scripts))
            tmp_path = Path(tmp.name)
        try:
            subprocess.run([node, "--check", str(tmp_path)], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            fail("JavaScript syntax error: " + (exc.stderr or exc.stdout))
        finally:
            tmp_path.unlink(missing_ok=True)


def check_python() -> None:
    for filename in ("server.py", "tools/verify_release.py"):
        source = (ROOT / filename).read_text(encoding="utf-8")
        try:
            compile(source, filename, "exec")
        except SyntaxError as exc:
            fail(f"Python syntax error in {filename}: {exc}")


def check_shell() -> None:
    shell = (ROOT / "start-android.sh").read_text(encoding="utf-8")
    if "127.0.0.1" not in (ROOT / "server.py").read_text(encoding="utf-8"):
        fail("server.py is not explicitly loopback-bound")
    if "python server.py" not in shell:
        fail("start-android.sh does not launch server.py")


def write_checksums() -> None:
    files = sorted(
        p for p in ROOT.rglob("*")
        if p.is_file() and p.name != "CHECKSUMS.sha256" and ".git" not in p.parts
    )
    lines = []
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
    (ROOT / "CHECKSUMS.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    check_required()
    app = inspect_html(ROOT / "index.html")
    inspect_html(ROOT / "GUIDE_ANDROID.html")
    check_markdown_refs()
    check_javascript(app)
    check_python()
    check_shell()
    write_checksums()
    print("OK: required files, HTML refs, duplicate IDs, runtime assets, JS/Python syntax and loopback server checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
