# -*- coding: utf-8 -*-
"""
@Date: 2026/1/7 14:16
@Author: Damian
@Email: zengyuwei1995@163.com
@File: photo2painting.py
@Description: 
"""
import os
import sys
import time
import argparse
import tempfile
import subprocess
from pathlib import Path

from reverie.settings import PATH
from reverie.utils import utils_data, utils_log, utils_database

log_filename = os.path.splitext(os.path.basename(__file__))[0]
logger = utils_log.logger_config_local(f'{PATH}/log/{log_filename}.log')

# Photoshop 可执行路径（如需可用 --photoshop 覆盖）
PS_PATH = r"D:\03_software\adobe\photoshop\Adobe Photoshop 2023\Photoshop.exe"

# 主模板：在这里用特殊标记 __ACTIONS__ / {input} / {output}，后面用 str.replace 注入内容，避免与 JS 大量花括号发生冲突。
JSX_WRAPPER = r'''
// Auto-generated JSX wrapper: actions will be executed sequentially
try {
    // input/output tokens will be replaced by Python
    var INPUT_PATH = "{input}";
    var OUTPUT_PATH = "{output}";

    // start actions
__ACTIONS__

} catch (e) {
    if (e && e.toString) {
        alert("Error in script: " + e.toString());
    }
}
'''


def to_photoshop_path(p: Path) -> str:
    # ExtendScript 在 Windows 下接受正斜杠路径更稳健
    return p.as_posix()


def default_open_action():
    return r'''
    // Action: open input file
    var fileRef = new File(INPUT_PATH);
    if (!fileRef.exists) throw("Input file not found: " + INPUT_PATH);
    var doc = app.open(fileRef);
    '''


def default_resize_half_action():
    return r'''
    // Action: resize width/height to 50% (pixels)
    var wpx = doc.width.as("px");
    var hpx = doc.height.as("px");
    var newW = UnitValue(wpx/2, "px");
    var newH = UnitValue(hpx/2, "px");
    doc.resizeImage(newW, newH, doc.resolution, ResampleMethod.BICUBICSHARPER);
    '''


def default_save_close_action():
    return r'''
    // Action: save to OUTPUT_PATH (jpg/png fallback to psd), then close
    var ext = OUTPUT_PATH.toLowerCase().split(".").pop();
    if (ext == "jpg" || ext == "jpeg") {
        var jpgOpts = new JPEGSaveOptions();
        jpgOpts.quality = 10; // 0-12
        doc.saveAs(new File(OUTPUT_PATH), jpgOpts, true, Extension.LOWERCASE);
    } else if (ext == "png") {
        var pngOpts = new PNGSaveOptions();
        doc.saveAs(new File(OUTPUT_PATH), pngOpts, true, Extension.LOWERCASE);
    } else {
        var psdOpts = new PhotoshopSaveOptions();
        doc.saveAs(new File(OUTPUT_PATH), psdOpts, true, Extension.LOWERCASE);
    }
    doc.close(SaveOptions.DONOTSAVECHANGES);
    '''


def read_jsx_text_file(path: Path) -> str:
    """
    读取文本 jsx 文件，替换 __INPUT__ / __OUTPUT__ 为 wrapper 的 {input}/{output} token，
    并以注释包裹返回。
    """
    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"JSX file not found: {path}")
    text = path.read_text(encoding="utf-8")
    # 把外部文件占位符转换为 wrapper 占位符（仅对文本 jsx 有用）
    text = text.replace("__INPUT__", "{input}").replace("__OUTPUT__", "{output}")
    return f'\n// ----- begin included file: {path} -----\n' + text + f'\n// ----- end included file: {path} -----\n'


def build_middle_action_from_path(resize_path: str) -> str:
    """
    根据给定路径返回中间动作字符串：
    - 如果是文本 jsx：读取并返回内容（并已把 __INPUT__/__OUTPUT__ 转为 {input}/{output}）
    - 如果是 JSXBIN（二进制，文件头为 @JSXBIN）：返回一段调用 $.evalFile 的代码片段，
      直接在 ExtendScript 中载入并执行该二进制文件。
    """
    if not resize_path:
        return default_resize_half_action()

    p = Path(resize_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"resize jsx file not found: {p}")

    # 检测是否为 JSXBIN：读取头部若以 @JSXBIN 开头，则视为二进制编译格式
    try:
        head = p.read_bytes()[:8]
    except Exception as e:
        raise RuntimeError(f"Failed to read file header: {p} -> {e}")

    if head.startswith(b'@JSXBIN'):
        # 生成一段会在 ExtendScript 中执行该 jsxbin 的代码
        # 注意这里把路径写成 Photoshop-friendly 的正斜杠形式
        inc_path = to_photoshop_path(p)
        inc_action = f'''
    // Action: include/execute JSXBIN file
    var includedFile = new File("{inc_path}");
    if (!includedFile.exists) throw("Included jsxbin not found: " + "{inc_path}");
    // evalFile 可以直接执行编译后的 jsxbin 文件
    $.evalFile(includedFile);
    '''
        return inc_action
    else:
        # 不是 jsxbin，认为是文本 jsx，按文本读取并做替换
        return read_jsx_text_file(p)


def build_actions_with_optional_resize_jsx(resize_jsx_path: str):
    """
    构建动作列表：
    - open
    - 如果提供 resize_jsx_path 则插入该文件内容（已做占位符替换或 jsxbin eval），否则使用内置的 50% 缩放动作
    - save_close
    """
    open_action = default_open_action()
    save_action = default_save_close_action()

    middle_action = build_middle_action_from_path(resize_jsx_path) if resize_jsx_path else default_resize_half_action()

    return [open_action, middle_action, save_action]


def build_and_run_jsx(temp_jsx, input_path: Path, output_path: Path, photoshop_exe: Path):
    logger.info("Temporary JSX:", temp_jsx)
    logger.info("Using Photoshop:", photoshop_exe)
    logger.info("Input :", input_path)
    logger.info("Output:", output_path)

    # 4) 调用 Photoshop 执行 jsx（如果找不到指定 exe，会尝试 'Photoshop.exe'）
    try:
        exe_cmd = [str(photoshop_exe), "-r", temp_jsx] if photoshop_exe.exists() else ["Photoshop.exe", "-r", temp_jsx]
        proc = subprocess.Popen(exe_cmd, shell=False)

        print("Photoshop started (pid {}).".format(proc.pid))
        print("脚本已派发给 Photoshop 执行。")
    except Exception as e:
        print("Failed to start Photoshop:", e, file=sys.stderr)
        # 不强制删除 temp_jsx，便于调试
        sys.exit(1)


def poll_move(temp_jsx):
    start_time = time.time()
    wait_timeout_seconds = 600  # 等待最大秒数（可根据需要调整或放到参数）
    poll_interval = 1.0  # 轮询间隔（秒）
    try:
        while True:
            if os.path.exists(output_path):
                utils_data.move(source_path, finish_path)
                break

            elapsed = time.time() - start_time
            if elapsed > wait_timeout_seconds:
                print(f"Timeout waiting for JSX to finish ({wait_timeout_seconds}s). Not moving file. Check {temp_jsx} and Photoshop.", file=sys.stderr)
                # 可选：proc.kill()，或把文件移动到错误目录；此处选择不移动以便人工检查
                break

            # 心跳输出（每 10 秒刷新一次，避免太多日志）
            if int(elapsed) % 10 == 0:
                print(f"Waiting for done file ({output_path})... elapsed: {int(elapsed)}s", end="\r")
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("Interrupted while waiting for JSX completion.", file=sys.stderr)


def get_jsx(actions, input_path):
    # 1) 合并 actions：直接把 actions 列表按顺序串成字符串
    actions_js = "\n".join(actions)

    # 2) 将 tokens 注入 wrapper（注意使用 as_posix() 提供正斜杠路径）
    jsx = JSX_WRAPPER.replace("__ACTIONS__", actions_js) \
        .replace("{input}", to_photoshop_path(input_path)) \
        .replace("{output}", to_photoshop_path(output_path))
    # 3) 写临时 jsx 文件
    with tempfile.NamedTemporaryFile("w", suffix=".jsx", delete=False, encoding="utf-8") as f:
        f.write(jsx)
        temp_jsx = f.name
    return temp_jsx


def do_work(file_path, output_path, finish_path):
    input_path = Path(file_path).expanduser().resolve()
    if not input_path.exists():
        print("Error: input file not found:", input_path, file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = Path(output_path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_path = input_path.with_name(input_path.stem + "_resized" + input_path.suffix)

    photoshop_exe = Path(args.photoshop)

    try:
        actions = build_actions_with_optional_resize_jsx(args.jsx_path)
    except FileNotFoundError as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("Error building actions:", e, file=sys.stderr)
        sys.exit(1)

    temp_jsx = get_jsx(actions, input_path)
    build_and_run_jsx(temp_jsx, input_path, output_path, photoshop_exe)
    poll_move(temp_jsx)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Use Photoshop and an actions list to process an image.")
    parser.add_argument("--input", default=fr"{PATH}\tests\input", help="输入图片路径")
    parser.add_argument("--finish", default=fr"{PATH}\tests\finish", help="输出图片路径（可选）")
    parser.add_argument("--output", default=fr"{PATH}\tests\output", help="输出图片路径（可选）")
    parser.add_argument("--photoshop", default=r"D:\03_software\adobe\photoshop\Adobe Photoshop 2023\Photoshop.exe", help="Photoshop.exe 路径")
    parser.add_argument("--jsx_path", default=fr"{PATH}\data\action\Real-Paint-FX-subject.jsx", help="可选：用本地 jsx 或 jsxbin 文件替换默认的 resize_half_action（文本 jsx 可使用 __INPUT__ / __OUTPUT__ 占位）")
    args = parser.parse_args()

    files = utils_data.find_file(args.input)
    # logger.info(files)
    for file in files:
        source_path = Path(fr"{args.input}\{file}")  # 源文件
        finish_path = Path(fr"{args.finish}\{file}")  # 目标路径
        output_path = Path(fr"{args.output}\{file}")  # 目标路径
        if source_path.suffix.lower() in ['.jpg', '.png']:
            print(file)
            do_work(source_path, output_path, finish_path)


