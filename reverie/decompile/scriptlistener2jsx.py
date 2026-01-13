# -*- coding: utf-8 -*-
"""
@Date: 2026/1/12 15:55
@Author: Damian
@Email: zengyuwei1995@163.com
@File: scriptlistener2jsx.py
@Description: 
"""
#!/usr/bin/env python3
# convert_listener_to_jsx.py
import re
from pathlib import Path
from reverie.settings import PATH

# 配置：修改为你的 log 路径与输出路径
LOG_PATH = Path(fr"{PATH}\data\decompile\ScriptingListenerJS.log")   # 改为真实路径
OUT_JSX = Path(fr"{PATH}\data\decompile\Real-Paint-FX-object.jsx")

# 黑名单块关键字（通常为 telemetry / state / plugin 调度）
BLACKLIST_KEYS = [
    r"hostFocusChanged",
    r"layersFiltered",
    r"pluginRun",
    r"nglProfileChanged",
    r"featureInfo",
    r"AdobeScriptAutomation Scripts",
    r"nglProfileChanged",
    r"featureInfo",
    # 如果你发现别的也要跳过，可以继续加
]

# 将被替换为占位符的 path patterns - 依据 ScriptListener 典型写法 File("C:\\...")
PATH_PATTERNS = [
    (re.compile(r'new File\("([A-Za-z]:\\\\[^"]+)"\)'), r'new File("{TMP_JSX}")'),
    # Windows绝对路径一般形式替换成 {INPUT} 或 {TMP_JSX} 更安全
    (re.compile(r'File\("([A-Za-z]:\\\\[^"]+)"\)'), r'File("{TMP_JSX}")'),
    # 如果 ScriptListener 把路径写为 C:/ 也做替换
    (re.compile(r'new File\("([A-Za-z]:/[^"]+)"\)'), r'new File("{TMP_JSX}")'),
]

# 读取原始 log
raw = LOG_PATH.read_text(encoding='utf-8', errors='ignore')

# 1) 把连续的 Listener 分段提取（ScriptListener 的分隔符通常为 // =======================================================）
blocks = re.split(r'//\s*={3,}\s*', raw)

import re
from pathlib import Path
import argparse
import shutil

# 正则：匹配 executeAction( <任何非贪婪内容 up to comma> , undefined , DialogModes.NO ) ; 可跨行
PATTERN = re.compile(
    r'executeAction\([\s\S]*?,\s*DialogModes\.NO\s*\)\s*;?',
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

clean_blocks = []
for blk in blocks:
    b = blk.strip()
    if not b:
        continue
    # 如果包含任一黑名单关键词则 skip（认为遥测/状态）
    skip = False
    for key in BLACKLIST_KEYS:
        if re.search(r'\b' + key + r'\b', b):
            skip = True
            break
    if skip:
        # 记录日志信息而非包含这些块
        clean_blocks.append("// Skipped telemetry/state block containing: {}".format(key))
        continue

    # 否则对该块进行路径占位替换与 DialogModes 强制设置
    text = b

    # 把 DialogModes.* 改为 DialogModes.NO（避免弹窗） debug
    text = process_text(text, comment_instead_of_remove=False)#True
    #text = re.sub(r'DialogModes\.\w+', 'DialogModes.NO', text)

    # 把 executeAction(..., undefined, DialogModes.NO) 的 undefined 参数维持（无变动）
    # 用 PATH_PATTERNS 替换 file path 为占位符 {TMP_JSX}
    for pat, repl in PATH_PATTERNS:
        text = pat.sub(repl, text)

    # 将三引号或奇怪的字符串整理为标准 JS 字符串（ScriptListener 某些情况会有额外引号）
    text = text.replace('"""', '"').replace("'''", "'")

    clean_blocks.append(text)

# 生成 wrapper（含 safeExec helper 和 INPUT/OUTPUT 占位）
wrapper_preamble = r'''// Auto-generated JSX from ScriptingListenerJS.log
// NOTE: This file contains extracted ActionManager blocks cleaned.
// Replace {INPUT} and {OUTPUT} with actual POSIX paths before running, or use a wrapper to inject them.

function safeExec(id, desc, mode, name) {
    try {
        executeAction(id, desc, mode);
        $.writeln((name || "executeAction") + " executed.");
    } catch (e) {
        $.writeln("Skipped " + (name || "executeAction") + " : " + e.toString());
    }
}

// caller must replace these placeholders
var INPUT_PATH = "{INPUT}";
var OUTPUT_PATH = "{OUTPUT}";

// Convert to File objects in script if needed by your blocks:
// var inFile = new File(INPUT_PATH); var doc = app.open(inFile);

try {
'''

wrapper_postamble = '''
    $.writeln("cleaned_auto.jsx finished.");
} catch (fatal) {
    alert("Fatal error in cleaned script: " + fatal.toString());
}
'''

# 合并 clean_blocks，但建议按逻辑顺序排放：open doc -> useful blocks -> save -> close
# 这里我们简单把所有 clean_blocks 串起来，你可以手动调整顺序
body = "\n\n// ---- block boundary ----\n\n".join(clean_blocks)

out_text = body#wrapper_preamble + body + wrapper_postamble

OUT_JSX.write_text(out_text, encoding='utf-8')
print("Wrote cleaned jsx to:", OUT_JSX)
print("请手动检查文件：主要确认 open/save/顺序与占位符是否正确，然后再运行。")
