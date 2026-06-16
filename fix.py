#!/usr/bin/env python3
from pathlib import Path
import argparse, sys
EXT = {".py",".js",".html",".yaml",".yml",".sh",".txt",".md",".json",".service",".rules",".ps1",".bat"}
def is_utf16(data):
    return (len(data) >= 2 and data[:2] in (b"\xff\xfe", b"\xfe\xff")) or (b"\x00" in data[:min(400, len(data))])
def fix_file(path, dry_run=False):
    data = path.read_bytes()
    if not data or not is_utf16(data): return False
    if data[:2] == b"\xff\xfe": text = data[2:].decode("utf-16-le", errors="replace")
    elif data[:2] == b"\xfe\xff": text = data[2:].decode("utf-16-be", errors="replace")
    else:
        try: text = data.decode("utf-16-le")
        except UnicodeDecodeError: text = data.decode("utf-16-be", errors="replace")
    if not dry_run: path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
    print("fixed:", path); return True
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", default=["."])
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    n = 0
    for raw in args.paths:
        p = Path(raw).resolve()
        files = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file() and (f.suffix.lower() in EXT or f.name == "xinitrc") and "__pycache__" not in f.parts]
        for f in files:
            if fix_file(f, args.dry_run): n += 1
    print(f"Done. Fixed {n} file(s).")
    return 0
if __name__ == "__main__": sys.exit(main())