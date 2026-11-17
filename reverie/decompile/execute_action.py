# -*- coding: utf-8 -*-
"""
@Date: 2026/1/12 16:38
@Author: StarlightDamian
@Email: zengyuwei1995@163.com
@File: execute_action.py
@Description: 
"""
#!/usr/bin/env python3
# remove_executeaction.py
import re
from pathlib import Path
import argparse
import shutil

# 正则：匹配 executeAction( <任何非贪婪内容 up to comma> , undefined , DialogModes.NO ) ; 可跨行
PATTERN = re.compile(
    r'executeAction\(\s*[^,]+?\s*,\s*undefined\s*,\s*DialogModes\.NO\s*\)\s*;?',
    flags=re.DOTALL | re.MULTILINE
)

def process_text(text: str, comment_instead_of_remove: bool = False) -> str:
    """
    把匹配的 executeAction(...) 块替换为空或注释。
    """
    if comment_instead_of_remove:
        def repl(m):
            content = m.group(0)
            # 保留原文为注释，便于调试
            return "/* removed executeAction: " + content.replace("*/", "*\\/") + " */"
        return PATTERN.sub(repl, text)
    else:
        return PATTERN.sub('', text)

def process_file(path: Path, inplace: bool = True, comment_instead_of_remove: bool = False):
    if not path.exists():
        raise FileNotFoundError(path)
    # 备份原文件
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    print(f"Backup written to: {bak}")

    txt = path.read_text(encoding='utf-8', errors='replace')
    new_txt = process_text(txt, comment_instead_of_remove=comment_instead_of_remove)

    if inplace:
        path.write_text(new_txt, encoding='utf-8', newline='\n')
        print(f"Processed and overwritten: {path}")
    else:
        out_path = path.with_name(path.stem + "_cleaned" + path.suffix)
        out_path.write_text(new_txt, encoding='utf-8', newline='\n')
        print(f"Processed and wrote: {out_path}")

def main():
    parser = argparse.ArgumentParser(description="Remove executeAction(..., undefined, DialogModes.NO) occurrences from JSX/log files.")
    parser.add_argument("files", nargs="+", help="文件路径（可多个）")
    parser.add_argument("--comment", action="store_true", help="不直接删除，改为注释保留原文（更安全）")
    parser.add_argument("--no-backup", action="store_true", help="不生成 .bak 备份（不推荐）")
    parser.add_argument("--outdir", help="如果指定，则把结果写到该目录而不覆盖原文件")
    args = parser.parse_args()

    for f in args.files:
        p = Path(f)
        if not p.exists():
            print("Not found:", p)
            continue
        if args.outdir:
            outdir = Path(args.outdir)
            outdir.mkdir(parents=True, exist_ok=True)
            out_path = outdir / p.name
            # 写入 outdir（但仍会生成 bak 作为源文件备份）
            if not args.no_backup:
                shutil.copy2(p, p.with_suffix(p.suffix + ".bak"))
            txt = p.read_text(encoding='utf-8', errors='replace')
            new_txt = process_text(txt, comment_instead_of_remove=args.comment)
            out_path.write_text(new_txt, encoding='utf-8', newline='\n')
            print("Wrote to:", out_path)
        else:
            if not args.no_backup:
                shutil.copy2(p, p.with_suffix(p.suffix + ".bak"))
            process_file(p, inplace=True, comment_instead_of_remove=args.comment)

if __name__ == "__main__":
    main()
