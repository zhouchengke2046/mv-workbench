#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一提醒（报警）格式。

所有面向用户的失败/阻塞提醒都必须走 emit()，输出一个可直接转发的块：

    [提醒] B001 备用Key未配置 | 级别=阻塞 | 时间=2026-11-14 11:20
    平台=router 模型=muse-video-ext 错误类别=timeout 连续失败=3/10min
    已做自检：keys status ✓
    原始报错（≤300字）：URLError: operation timed out
    学生动作：把本提醒原文完整发给老师；不要重复提交任务
    需要老师：判断是否发放备用 Key 或其它处理

代码表见 references/alerts.md。学生遇到问题时，把整块原文发给老师即可，
老师按代码+平台+错误类别快速定位。原始报错统一截断 300 字并脱敏。
"""
import datetime
import sys

RAW_LIMIT = 300

CODES = {
    # ---- Key / 配置 ----
    "K001": {"title": "Key 未配置", "student": "导入老师发的 zz-keys.json（放到项目根目录或下载目录），或双击 start/setup-keys 自己输入", "teacher": "确认是否已发放 zz-keys.json / 发新的对应平台 Key"},
    "K002": {"title": "keys.json 读取失败", "student": "把本提醒发给老师；不要自己改文件", "teacher": "指导修复或重发 zz-keys.json"},
    "K003": {"title": "Key 文件格式不对", "student": "把本提醒发给老师；保留原文件不要删", "teacher": "核对 zz-keys.json 内容/格式，必要时重发"},
    "K004": {"title": "找不到 Key 文件", "student": "确认 zz-keys.json 的实际位置（项目根目录/下载目录），把路径告诉 agent", "teacher": "确认学生是否已收到文件"},
    "K005": {"title": "监听超时未收到 Key 文件", "student": "确认下载是否完成、保存在哪个目录，把路径告诉 agent；或直接说“导入 <路径>/zz-keys.json”", "teacher": "一般无需处理；学生重复导入即可"},
    "K006": {"title": "agent 环境无法交互输入 Key", "student": "双击 setup-keys（Mac: .command / Win: .cmd）自己输入，或导入 zz-keys.json", "teacher": "一般无需处理"},
    "K007": {"title": "keys.json 权限不对", "student": "把本提醒发给老师（Windows 不强制 0600，可忽略）", "teacher": "确认系统/权限差异"},
    # ---- 备用 Key ----
    "B001": {"title": "Router 连续失败，备用 Key 未配置", "student": "把本提醒原文完整发给老师，等老师处理；期间不要重复提交任务", "teacher": "判断是否发放备用 zz-keys.json（含 runninghub/apimart 字段）或其它处理"},
    # ---- 平台调用（platform 字段区分 router/runninghub/apimart）----
    "P1": {"title": "平台身份/权限失败", "student": "把本提醒发给老师", "teacher": "核对 Key/账号/应用权限；可能需要换 Key"},
    "P2": {"title": "平台余额/额度不足", "student": "把本提醒发给老师，并暂停生成", "teacher": "充值或发放新 Key"},
    "P3": {"title": "任务提交失败", "student": "把本提醒发给老师；不要反复重试", "teacher": "按错误类别定位平台/参数问题"},
    "P4": {"title": "平台任务失败", "student": "把本提醒发给老师；旧版本已保留", "teacher": "判断平台侧问题或提示词/参数问题"},
    "P5": {"title": "平台超时/网络异常", "student": "把本提醒发给老师；agent 已按策略重试/切换", "teacher": "确认平台可用性"},
    "P6": {"title": "产物下载失败", "student": "把本提醒发给老师；任务号已保留，可手动补拉", "teacher": "提供产物链接或指导补拉"},
    # ---- 工作台 / 数据 ----
    "W1": {"title": "工作台引用文件缺失", "student": "把本提醒发给老师；agent 会先修复路径或重新下载", "teacher": "确认缺失清单是否合理"},
    "W2": {"title": "DATA 不是合法 JSON", "student": "把本提醒发给老师；不要手改 data.json", "teacher": "指导修复或回退版本"},
    "W3": {"title": "工作台构建失败", "student": "把本提醒发给老师", "teacher": "按报错定位模板/数据问题"},
    "W4": {"title": "页面比数据旧", "student": "让 agent 重建工作台后强刷页面（Cmd/Ctrl+Shift+R）", "teacher": "一般无需处理"},
    # ---- 时间轴 / 时长 ----
    "T1": {"title": "音乐时长与目标偏差过大", "student": "在「接受实际 / 重做音乐 / 后期裁」里选一个", "teacher": "可给出倾向性建议"},
    "T2": {"title": "时间轴与歌词不一致", "student": "把本提醒发给老师", "teacher": "核对 lyric.json 与音频"},
    "T3": {"title": "ffmpeg/ffprobe 缺失", "student": "让 agent 安装后重试（Mac: brew / Win: winget 或 npm 镜像）", "teacher": "一般无需处理"},
    # ---- 质检 ----
    "Q1": {"title": "资产质检失败", "student": "等 agent 自动重跑一次；仍失败则按提醒处理", "teacher": "可给出改图意见"},
    "Q2": {"title": "资产质检警告", "student": "确认「用/不用」这张图", "teacher": "可给出建议"},
    "Q3": {"title": "视频段时长/规格不符", "student": "把本提醒发给老师；agent 会重跑该段", "teacher": "确认规格要求"},
}


def now_text():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def _redact(text, secrets=()):
    text = str(text or "")
    for secret in secrets:
        if secret:
            text = text.replace(str(secret), "***")
    if len(text) > RAW_LIMIT:
        text = text[:RAW_LIMIT] + "…"
    return text.replace("\n", " ")


def emit(code, *, level="阻塞", platform=None, model=None, error_class=None,
         stats=None, checks=None, raw=None, secrets=(), stream=None):
    """输出标准提醒块并返回文本。code 必须在 CODES 中。"""
    meta = CODES.get(code)
    if not meta:
        raise ValueError("未知提醒代码：%s" % code)
    stream = stream or sys.stderr
    ctx = []
    if platform:
        ctx.append("平台=%s" % platform)
    if model:
        ctx.append("模型=%s" % model)
    if error_class:
        ctx.append("错误类别=%s" % error_class)
    if stats:
        ctx.append(stats if isinstance(stats, str) else " ".join("%s=%s" % kv for kv in stats))
    lines = ["[提醒] %s %s | 级别=%s | 时间=%s" % (code, meta["title"], level, now_text())]
    if ctx:
        lines.append(" ".join(ctx))
    if checks:
        lines.append("已做自检：%s" % (checks if isinstance(checks, str) else "；".join(checks)))
    if raw:
        lines.append("原始报错（≤%d字）：%s" % (RAW_LIMIT, _redact(raw, secrets)))
    lines.append("学生动作：%s" % meta["student"])
    lines.append("需要老师：%s" % meta["teacher"])
    block = "\n".join(lines)
    print(block, file=stream, flush=True)
    return block


def fail(code, message, *, exit_code=1, stream=None, **kwargs):
    """输出提醒块后以 SystemExit 退出；message 作为原始报错/说明。"""
    emit(code, raw=message, stream=stream, **kwargs)
    raise SystemExit(exit_code)
