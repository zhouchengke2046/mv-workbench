#!/usr/bin/env python3
"""
rh_sdk.py — RunningHub 官方 SDK 的薄 CLI 封装。

补齐上游脚本未覆盖的能力：取消任务、查询工作流JSON、LoRA上传、
workflow JSON 直传、账户详情、队列状态、输出历史等。

依赖：pip install runninghub-sdk
认证：环境变量 RUNNINGHUB_API_KEY（与上游脚本一致）

命令:
  cancel <taskId>                              取消正在运行/排队的任务
  workflow-json <workflowId>                   获取工作流的 API 格式 JSON
  upload-lora <filePath>                        上传 LoRA 文件（三步链自动完成）
  run-workflow-json <jsonPath> [--node N:F=V]   本地 workflow JSON 直传运行
  account                                       账户详情（余额/RH币/运行任务/队列）
  queue                                         队列状态
  status <taskId>                              查询任务状态
  outputs <taskId>                              获取任务结果文件
  download <taskId> -o <dir>                    下载任务结果到本地目录
  copy-workflow <workflowId>                   复制工作流到自己的账号
  models                                        列出公共模型
  price <modelId>                              预览模型价格
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _get_client():
    """从环境变量初始化 SDK 客户端。"""
    key = os.environ.get("RUNNINGHUB_API_KEY", "").strip()
    if not key:
        print(json.dumps({"error": "NO_API_KEY",
                          "message": "请设置环境变量 RUNNINGHUB_API_KEY"},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    try:
        from runninghub_sdk import RunningHubClient
    except ImportError:
        print(json.dumps({"error": "SDK_NOT_INSTALLED",
                          "message": "请先 pip install runninghub-sdk"},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    return RunningHubClient(api_key=key)


def _safe_call(fn):
    """装饰器：统一捕获 SDK 调用异常，输出 JSON 错误而非裸 traceback。"""
    import functools
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        c = None
        try:
            return fn(*args, **kwargs)
        except SystemExit:
            raise
        except Exception as e:
            print(json.dumps({"error": type(e).__name__, "message": str(e)},
                             ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        finally:
            if c is not None:
                try:
                    c.close()
                except Exception:
                    pass
    return wrapper


@_safe_call
def cmd_cancel(task_id: str) -> None:
    c = _get_client()
    result = c.cancel(task_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


@_safe_call
def cmd_workflow_json(workflow_id: str, parsed: bool) -> None:
    c = _get_client()
    if parsed:
        result = c.get_workflow_json_parsed(workflow_id)
    else:
        result = c.get_workflow_json(workflow_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


@_safe_call
def cmd_upload_lora(file_path: str) -> None:
    c = _get_client()
    p = Path(file_path)
    if not p.exists():
        print(json.dumps({"error": "FILE_NOT_FOUND", "path": file_path},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    result = c.upload_lora(str(p))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


@_safe_call
def cmd_run_workflow_json(json_path: str, nodes: list[str] | None) -> None:
    """本地 workflow JSON 直传运行。"""
    c = _get_client()
    p = Path(json_path)
    if not p.exists():
        print(json.dumps({"error": "FILE_NOT_FOUND", "path": json_path},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    workflow_json = p.read_text(encoding="utf-8")

    # 解析 --node "nodeId:fieldName=value"
    node_info_list = []
    if nodes:
        for n in nodes:
            # 格式: nodeId:fieldName=value
            parts = n.split(":", 1)
            if len(parts) != 2:
                continue
            nid, rest = parts
            fv_parts = rest.split("=", 1)
            if len(fv_parts) != 2:
                continue
            fname, fval = fv_parts
            node_info_list.append({
                "nodeId": nid.strip(),
                "fieldName": fname.strip(),
                "fieldValue": fval.strip(),
            })

    # SDK 的 run 方法支持 workflow 参数
    try:
        result = c.run(workflow_id="", workflow=workflow_json,
                       node_info_list=node_info_list if node_info_list else None)
    except TypeError:
        # 如果 SDK 不支持 workflow 参数，直接用底层 API
        result = {"error": "SDK_RUN_NO_WORKFLOW_PARAM",
                  "message": "SDK 版本可能不支持 workflow 直传，请用 /task/openapi/create 接口"}
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


@_safe_call
def cmd_account() -> None:
    c = _get_client()
    result = c.get_account_status()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


@_safe_call
def cmd_queue() -> None:
    c = _get_client()
    result = c.get_queue_status()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


@_safe_call
def cmd_status(task_id: str) -> None:
    c = _get_client()
    result = c.get_status(task_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


@_safe_call
def cmd_outputs(task_id: str) -> None:
    c = _get_client()
    result = c.get_outputs(task_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


@_safe_call
def cmd_download(task_id: str, output_dir: str) -> None:
    c = _get_client()
    d = Path(output_dir)
    d.mkdir(parents=True, exist_ok=True)
    result = c.download_task_outputs(task_id, str(d))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


@_safe_call
def cmd_copy_workflow(workflow_id: str) -> None:
    c = _get_client()
    result = c.copy_workflow(workflow_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


@_safe_call
def cmd_models() -> None:
    c = _get_client()
    result = c.list_public_models()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


@_safe_call
def cmd_price(model_id: str, param: list[str] | None) -> None:
    c = _get_client()
    payload: dict = {}
    if param:
        for p in param:
            kv = p.split("=", 1)
            if len(kv) == 2:
                payload[kv[0].strip()] = kv[1].strip()
    result = c.preview_model_price(model_id, payload)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


def _parse_node_arg(arg: str) -> tuple[str, str]:
    """解析 'nodeId:value' 格式，返回 (nodeId, value)。"""
    parts = arg.split(":", 1)
    if len(parts) != 2:
        print(json.dumps({"error": "BAD_FORMAT",
                          "message": f"格式应为 nodeId:value，收到: {arg}"},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    return parts[0].strip(), parts[1]


def _upload_if_path(c, node_arg: str, upload_fn):
    """如果 value 是本地文件路径且存在，先上传再返回 fileName。"""
    nid, val = _parse_node_arg(node_arg)
    p = Path(val)
    if p.exists() and p.is_file():
        result = upload_fn(str(p))
        # SDK 返回对象或 dict，尝试提取 fileName
        if hasattr(result, "file_name"):
            val = result.file_name
        elif hasattr(result, "data") and hasattr(result.data, "fileName"):
            val = result.data.fileName
        elif isinstance(result, dict) and "data" in result:
            val = result["data"].get("fileName", val)
        else:
            val = str(result)
        print(f"[upload] {p.name} -> {val}", file=sys.stderr)
    return nid, val


@_safe_call
def cmd_run_with_modifier(workflow_id: str, text: list[str] | None,
                           seed: list[str] | None, steps: list[str] | None,
                           cfg: list[str] | None, negative: list[str] | None,
                           sampler: list[str] | None, scheduler: list[str] | None,
                           denoise: list[str] | None, checkpoint: list[str] | None,
                           image: list[str] | None, video: list[str] | None,
                           audio: list[str] | None, lora: list[str] | None,
                           lora_strength: list[str] | None, size: list[str] | None,
                           set_field: list[str] | None, wait: bool,
                           timeout: int) -> None:
    """用 NodeModifier 链式修改参数运行工作流。"""
    c = _get_client()
    m = c.create_modifier()

    # 按类型批量处理
    for arg in (text or []):
        nid, val = _parse_node_arg(arg)
        m.text(nid, val)
    for arg in (seed or []):
        nid, val = _parse_node_arg(arg)
        m.seed(nid, int(val))
    for arg in (steps or []):
        nid, val = _parse_node_arg(arg)
        m.steps(nid, int(val))
    for arg in (cfg or []):
        nid, val = _parse_node_arg(arg)
        m.cfg(nid, float(val))
    for arg in (negative or []):
        nid, val = _parse_node_arg(arg)
        m.negative_text(nid, val)
    for arg in (sampler or []):
        nid, val = _parse_node_arg(arg)
        m.sampler(nid, val)
    for arg in (scheduler or []):
        nid, val = _parse_node_arg(arg)
        m.scheduler(nid, val)
    for arg in (denoise or []):
        nid, val = _parse_node_arg(arg)
        m.denoise(nid, float(val))
    for arg in (checkpoint or []):
        nid, val = _parse_node_arg(arg)
        m.checkpoint(nid, val)
    for arg in (image or []):
        nid, val = _upload_if_path(c, arg, c.upload_file)
        m.image(nid, val)
    for arg in (video or []):
        nid, val = _upload_if_path(c, arg, c.upload_file)
        m.video(nid, val)
    for arg in (audio or []):
        nid, val = _upload_if_path(c, arg, c.upload_file)
        m.audio(nid, val)
    for arg in (lora or []):
        nid, val = _parse_node_arg(arg)
        m.lora(nid, val)
    for arg in (lora_strength or []):
        nid, val = _parse_node_arg(arg)
        m.lora_strength(nid, float(val))
    for arg in (size or []):
        # 格式: nodeId:WxH 或 nodeId:WxHxBatch
        nid, val = _parse_node_arg(arg)
        parts = val.lower().split("x")
        if len(parts) >= 2:
            w, h = int(parts[0]), int(parts[1])
            b = int(parts[2]) if len(parts) >= 3 else None
            m.size(nid, w, h, b)
    for arg in (set_field or []):
        # 格式: nodeId:fieldName:value
        parts = arg.split(":", 2)
        if len(parts) == 3:
            m.set(parts[0].strip(), parts[1].strip(), parts[2].strip())
        elif len(parts) == 2:
            # nodeId:value → 自动推断类型
            m.set(parts[0].strip(), "value", parts[1].strip())

    # 运行
    print(f"[run] workflow={workflow_id}, modifications={len(m.to_list())}",
          file=sys.stderr)
    task = c.run_with_modifier(workflow_id, m)
    print(json.dumps(task, ensure_ascii=False, indent=2, default=str))

    # 可选：等待完成
    if wait and hasattr(task, "task_id"):
        task_id = task.task_id if hasattr(task, "task_id") else task.get("data", {}).get("taskId", "")
        if task_id:
            print(f"[wait] 等待任务 {task_id} 完成（超时 {timeout}s）...",
                  file=sys.stderr)
            outputs = c.wait_for_completion(task_id, timeout=timeout)
            print(json.dumps(outputs, ensure_ascii=False, indent=2, default=str))
    c.close()


@_safe_call
def cmd_wait(task_id: str, timeout: int) -> None:
    """自动轮询等待任务完成，返回结果。"""
    c = _get_client()
    print(f"[wait] 等待任务 {task_id} 完成（超时 {timeout}s）...",
          file=sys.stderr)
    result = c.wait_for_completion(task_id, timeout=timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


# ---------- 手机号登录 ----------

@_safe_call
def cmd_login(username: str, token_cache: str) -> None:
    """手机号登录获取用户 Token（密码从环境变量 RH_PASSWORD 读，避免 ps 泄露）。"""
    password = os.environ.get("RH_PASSWORD", "").strip()
    if not password:
        print(json.dumps({"error": "NO_PASSWORD",
                          "message": "请设置环境变量 RH_PASSWORD"},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    try:
        from runninghub_sdk import RunningHubClient
    except ImportError:
        print(json.dumps({"error": "SDK_NOT_INSTALLED",
                          "message": "请先 pip install runninghub-sdk"},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    try:
        c = RunningHubClient.from_login(username, password,
                                         token_cache=token_cache or None)
        info = c.get_user_info(user_id="")
        print(json.dumps({"status": "login_ok", "user_info": info},
                         ensure_ascii=False, indent=2, default=str))
        c.close()
    except Exception as e:
        print(json.dumps({"error": "LOGIN_FAILED", "message": str(e)},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


# ---------- 输出历史 ----------

@_safe_call
def cmd_history(size: int, current: int, status: list[str] | None,
                task_type: list[str] | None, has_output: bool,
                task_name: str) -> None:
    """查询输出历史（需用户 Token，用 login 命令先登录）。"""
    c = _get_client()
    from runninghub_sdk.typedefs.output_history import OutputHistoryV2Request
    req = OutputHistoryV2Request(
        size=size, current=current, status=status,
        task_type=task_type, has_output=has_output, task_name=task_name,
    )
    result = c.query_output_history_v2(req)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


@_safe_call
def cmd_download_history(size: int, output_dir: str) -> None:
    """批量下载历史输出。"""
    c = _get_client()
    d = Path(output_dir)
    d.mkdir(parents=True, exist_ok=True)
    from runninghub_sdk.typedefs.output_history import OutputHistoryV2Request
    req = OutputHistoryV2Request(size=size, current=1, has_output=True)
    result = c.download_history_outputs(req, str(d))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


# ---------- 调用日志 ----------

@_safe_call
def cmd_call_log(task_id: str, user_id: str) -> None:
    """查调用日志详情（排查失败任务）。"""
    c = _get_client()
    result = c.get_call_log_detail(task_id, user_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


# ---------- Webhook ----------

@_safe_call
def cmd_webhook_detail(task_id: str) -> None:
    """查 webhook 事件详情。"""
    c = _get_client()
    result = c.get_webhook_detail(task_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


@_safe_call
def cmd_webhook_retry(webhook_id: str, webhook_url: str) -> None:
    """重试 webhook 事件。"""
    c = _get_client()
    c.retry_webhook(webhook_id, webhook_url)
    print(json.dumps({"status": "retry_sent", "webhook_id": webhook_id},
                     ensure_ascii=False))
    c.close()


# ---------- API Key 管理 ----------

@_safe_call
def cmd_api_keys() -> None:
    """列出所有 API Key。"""
    c = _get_client()
    result = c.list_api_keys()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


@_safe_call
def cmd_validate_key() -> None:
    """验证当前 API Key 是否有效。"""
    c = _get_client()
    ok = c.validate_api_key()
    print(json.dumps({"api_key_valid": ok}, ensure_ascii=False))
    c.close()


# ---------- 门户模板 ----------

@_safe_call
def cmd_templates(size: int, current: int, search: str, sort: str,
                  tags: list[str] | None) -> None:
    """浏览门户精选模板。"""
    c = _get_client()
    from runninghub_sdk.typedefs.portal import PortalTemplateListRequest
    req = PortalTemplateListRequest(
        size=size, current=current, search=search, sort=sort, tags=tags,
    )
    result = c.list_portal_templates(req)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    c.close()


# ---------- 标准模型 SDK 调用 ----------

@_safe_call
def cmd_run_model(endpoint: str, prompt: str, param: list[str] | None,
                  wait: bool, timeout: int) -> None:
    """用 SDK 调用标准模型 API（420 端点，与 runninghub.py 等价但更简洁）。"""
    c = _get_client()
    payload: dict = {"prompt": prompt}
    if param:
        for p in param:
            kv = p.split("=", 1)
            if len(kv) == 2:
                payload[kv[0].strip()] = kv[1].strip()
    result = c.run_model_api(endpoint, payload)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    if wait and hasattr(result, "task_id"):
        tid = result.task_id if hasattr(result, "task_id") else ""
        if tid:
            print(f"[wait] 等待 {tid}（超时 {timeout}s）...", file=sys.stderr)
            outputs = c.wait_for_completion(tid, timeout=timeout)
            print(json.dumps(outputs, ensure_ascii=False, indent=2, default=str))
    c.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RunningHub SDK CLI（补齐上游脚本未覆盖的能力）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cancel = sub.add_parser("cancel", help="取消任务")
    p_cancel.add_argument("task_id")
    p_cancel.set_defaults(fn=cmd_cancel)

    p_wfjson = sub.add_parser("workflow-json", help="获取工作流 API 格式 JSON")
    p_wfjson.add_argument("workflow_id")
    p_wfjson.add_argument("--parsed", action="store_true", help="返回解析后的对象而非字符串")
    p_wfjson.set_defaults(fn=cmd_workflow_json)

    p_lora = sub.add_parser("upload-lora", help="上传 LoRA 文件")
    p_lora.add_argument("file_path")
    p_lora.set_defaults(fn=cmd_upload_lora)

    p_rwf = sub.add_parser("run-workflow-json", help="本地 workflow JSON 直传运行")
    p_rwf.add_argument("json_path")
    p_rwf.add_argument("--node", action="append", help='节点参数: "nodeId:fieldName=value"（可重复）')
    p_rwf.set_defaults(fn=cmd_run_workflow_json)

    p_acc = sub.add_parser("account", help="账户详情")
    p_acc.set_defaults(fn=cmd_account)

    p_queue = sub.add_parser("queue", help="队列状态")
    p_queue.set_defaults(fn=cmd_queue)

    p_status = sub.add_parser("status", help="查询任务状态")
    p_status.add_argument("task_id")
    p_status.set_defaults(fn=cmd_status)

    p_out = sub.add_parser("outputs", help="获取任务结果")
    p_out.add_argument("task_id")
    p_out.set_defaults(fn=cmd_outputs)

    p_dl = sub.add_parser("download", help="下载任务结果到本地")
    p_dl.add_argument("task_id")
    p_dl.add_argument("-o", "--output", default="/tmp/rh-output", help="输出目录")
    p_dl.set_defaults(fn=cmd_download)

    p_copy = sub.add_parser("copy-workflow", help="复制工作流到自己的账号")
    p_copy.add_argument("workflow_id")
    p_copy.set_defaults(fn=cmd_copy_workflow)

    p_models = sub.add_parser("models", help="列出公共模型")
    p_models.set_defaults(fn=cmd_models)

    p_price = sub.add_parser("price", help="预览模型价格")
    p_price.add_argument("model_id", help="端点 ID")
    p_price.add_argument("--param", action="append", help='额外参数: "key=value"')
    p_price.set_defaults(fn=cmd_price)

    # === 9 个补齐命令 ===

    p_rwm = sub.add_parser("run-with-modifier", help="链式修改参数运行工作流")
    p_rwm.add_argument("workflow_id")
    p_rwm.add_argument("--text", action="append", help='文本: "nodeId:文本"')
    p_rwm.add_argument("--seed", action="append", help='种子: "nodeId:123"')
    p_rwm.add_argument("--steps", action="append", help='步数: "nodeId:20"')
    p_rwm.add_argument("--cfg", action="append", help='CFG: "nodeId:7.5"')
    p_rwm.add_argument("--negative", action="append", help='负面提示词: "nodeId:文本"')
    p_rwm.add_argument("--sampler", action="append", help='采样器: "nodeId:dpmpp_2m"')
    p_rwm.add_argument("--scheduler", action="append", help='调度器: "nodeId:karras"')
    p_rwm.add_argument("--denoise", action="append", help='去噪: "nodeId:0.8"')
    p_rwm.add_argument("--checkpoint", action="append", help='模型: "nodeId:model.safetensors"')
    p_rwm.add_argument("--image", action="append", help='图片: "nodeId:/path或fileName"')
    p_rwm.add_argument("--video", action="append", help='视频: "nodeId:/path或fileName"')
    p_rwm.add_argument("--audio", action="append", help='音频: "nodeId:/path或fileName"')
    p_rwm.add_argument("--lora", action="append", help='LoRA: "nodeId:loraName"')
    p_rwm.add_argument("--lora-strength", action="append", help='LoRA强度: "nodeId:0.8"')
    p_rwm.add_argument("--size", action="append", help='尺寸: "nodeId:512x768" 或 "nodeId:512x768x1"')
    p_rwm.add_argument("--set", action="append", help='通用字段: "nodeId:fieldName:value"')
    p_rwm.add_argument("--wait", action="store_true", help="运行后自动等待完成")
    p_rwm.add_argument("--timeout", type=int, default=300, help="等待超时秒数")
    p_rwm.set_defaults(fn=cmd_run_with_modifier)

    p_wait = sub.add_parser("wait", help="自动轮询等待任务完成")
    p_wait.add_argument("task_id")
    p_wait.add_argument("--timeout", type=int, default=300, help="超时秒数")
    p_wait.set_defaults(fn=cmd_wait)

    p_login = sub.add_parser("login", help="手机号登录获取用户 Token（密码从 RH_PASSWORD 环境变量读）")
    p_login.add_argument("username", help="手机号")
    p_login.add_argument("--token-cache", default="", help="token 缓存路径")
    p_login.set_defaults(fn=cmd_login)

    p_hist = sub.add_parser("history", help="查询输出历史")
    p_hist.add_argument("--size", type=int, default=30)
    p_hist.add_argument("--current", type=int, default=1)
    p_hist.add_argument("--status", action="append", help="状态过滤: SUCCESS/FAILED/RUNNING")
    p_hist.add_argument("--task-type", action="append", help="任务类型过滤")
    p_hist.add_argument("--has-output", action="store_true", default=True)
    p_hist.add_argument("--task-name", default="")
    p_hist.set_defaults(fn=cmd_history)

    p_dlhist = sub.add_parser("download-history", help="批量下载历史输出")
    p_dlhist.add_argument("--size", type=int, default=30)
    p_dlhist.add_argument("-o", "--output", default="/tmp/rh-history")
    p_dlhist.set_defaults(fn=cmd_download_history)

    p_calllog = sub.add_parser("call-log", help="查调用日志详情")
    p_calllog.add_argument("task_id")
    p_calllog.add_argument("user_id")
    p_calllog.set_defaults(fn=cmd_call_log)

    p_whd = sub.add_parser("webhook-detail", help="查 webhook 事件详情")
    p_whd.add_argument("task_id")
    p_whd.set_defaults(fn=cmd_webhook_detail)

    p_whr = sub.add_parser("webhook-retry", help="重试 webhook 事件")
    p_whr.add_argument("webhook_id")
    p_whr.add_argument("webhook_url")
    p_whr.set_defaults(fn=cmd_webhook_retry)

    p_keys = sub.add_parser("api-keys", help="列出所有 API Key")
    p_keys.set_defaults(fn=cmd_api_keys)

    p_val = sub.add_parser("validate-key", help="验证当前 API Key")
    p_val.set_defaults(fn=cmd_validate_key)

    p_tpl = sub.add_parser("templates", help="浏览门户精选模板")
    p_tpl.add_argument("--size", type=int, default=30)
    p_tpl.add_argument("--current", type=int, default=1)
    p_tpl.add_argument("--search", default="")
    p_tpl.add_argument("--sort", default="RECOMMEND", help="RECOMMEND/HOTTEST/NEWEST")
    p_tpl.add_argument("--tags", action="append")
    p_tpl.set_defaults(fn=cmd_templates)

    p_runmdl = sub.add_parser("run-model", help="SDK 调用标准模型 API")
    p_runmdl.add_argument("endpoint", help="端点 ID")
    p_runmdl.add_argument("--prompt", required=True)
    p_runmdl.add_argument("--param", action="append", help='额外参数: "key=value"')
    p_runmdl.add_argument("--wait", action="store_true")
    p_runmdl.add_argument("--timeout", type=int, default=300)
    p_runmdl.set_defaults(fn=cmd_run_model)

    args = parser.parse_args()
    if hasattr(args, "fn"):
        # 根据子命令调用对应函数
        import inspect
        sig = inspect.signature(args.fn)
        kwargs = {k: getattr(args, k) for k in sig.parameters if hasattr(args, k)}
        args.fn(**kwargs)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
