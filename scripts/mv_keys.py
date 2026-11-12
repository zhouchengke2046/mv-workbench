#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MV 工作台 Key 与余额管理。

唯一真源：~/.config/mv-workbench/keys.json（目录 0700 / 文件 0600）
可用 MV_KEYS_PATH 覆盖路径（测试/多工作区）。

命令：
  init [--force] [--from-env]
  status
  set <runninghub|router> [--stdin] [--label X] [--account X] [--base-url X] [--proxy X]
  balance [--write workbench.html] [--no-backup] [--timeout 12]
  exec -- <命令...>

安全约束：
- 原始 key 只从 keys.json 读，不打印、不写入 HTML/DATA/日志；
- HTML 的 DATA.keys 只存掩码、余额、查询时间、错误；
- exec 用 keys.json 覆盖 RUNNINGHUB_API_KEY / APIMART_KEY，避免 shell 残留 key 串号。
"""

import argparse
import copy
import datetime
import getpass
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_KEYS_PATH = Path.home() / ".config" / "mv-workbench" / "keys.json"

TEMPLATE = {
    "_note": "MV 工作台唯一 Key 配置；文件权限 0600；不要提交到仓库、不要发给他人。",
    "runninghub": {
        "api_key": "",
        "label": "RunningHub",
        "account": "",
    },
    "router": {
        "api_key": "",
        "label": "Router",
        "provider": "new-api",
        "base_url": "https://router.kcacher.top",
        "balance_path": "/v1/dashboard/billing/subscription",
        "balance_mode": "newapi",
        "proxy": "",
    },
}

RH_ACCOUNT_URL = "https://www.runninghub.cn/uc/openapi/accountStatus"
WORKBENCH_MARKER = "const DATA = "


def keys_path():
    return Path(os.environ.get("MV_KEYS_PATH") or str(DEFAULT_KEYS_PATH)).expanduser()


def die(message, code=1):
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False), file=sys.stderr)
    raise SystemExit(code)


def mask(value):
    value = (value or "").strip()
    if not value:
        return ""
    tail = value[-4:] if len(value) >= 4 else value[-2:]
    return "••••" + tail


def to_float(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").replace("$", "").replace("¥", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def redact(text, key):
    if key and text:
        return str(text).replace(key, mask(key))
    return text


def _normalize(cfg):
    if not isinstance(cfg, dict):
        die("keys.json 顶层必须是 JSON 对象")
    for name in ("runninghub", "router"):
        if not isinstance(cfg.get(name), dict):
            cfg[name] = copy.deepcopy(TEMPLATE[name])
    if not cfg["router"].get("balance_mode"):
        cfg["router"]["balance_mode"] = "newapi"
    return cfg


def load_cfg():
    path = keys_path()
    if not path.exists():
        return copy.deepcopy(TEMPLATE), False
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die("keys.json 不是合法 JSON：%s" % exc)
    except OSError as exc:
        die("读取 keys.json 失败：%s" % exc)
    return _normalize(cfg), True


def save_cfg(cfg):
    path = keys_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
    except OSError as exc:
        die("创建配置目录失败：%s" % exc)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(path)
        os.chmod(path, 0o600)
    except OSError as exc:
        die("保存 keys.json 失败：%s" % exc)


def http_json(url, method="GET", headers=None, payload=None, proxy="", timeout=12):
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    opener = urllib.request.build_opener(*handlers)
    body = None
    request_headers = dict(headers or {})
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
        return json.loads(raw), None
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", "replace")
        except Exception:
            detail = ""
        return None, "HTTP %s：%s" % (exc.code, detail[:300])
    except Exception as exc:
        return None, "%s：%s" % (type(exc).__name__, exc)


def balance_runninghub(cfg, timeout):
    section = cfg.get("runninghub") or {}
    key = (section.get("api_key") or "").strip()
    result = {
        "label": section.get("label") or "RunningHub",
        "account": section.get("account") or "",
        "configured": bool(key),
        "masked": mask(key),
        "ok": False,
        "balance": None,
        "unit": "币",
        "wallet": None,
        "wallet_unit": None,
        "unlimited": False,
        "error": None,
    }
    if not key:
        result["error"] = "未配置 runninghub.api_key"
        return result

    response, error = http_json(
        RH_ACCOUNT_URL,
        method="POST",
        payload={"apikey": key, "extension": "all"},
        proxy=(section.get("proxy") or "").strip(),
        timeout=timeout,
    )
    if error:
        result["error"] = redact(error, key)
        return result
    if not isinstance(response, dict):
        result["error"] = "响应不是 JSON 对象"
        return result
    if response.get("code") not in (0, "0", None):
        result["error"] = redact(str(response.get("msg") or response), key)
        return result

    data = response.get("data")
    if not isinstance(data, dict):
        result["error"] = "响应缺少 data"
        return result
    coins = data.get("remainCoins")
    wallet = data.get("remainMoney")
    if coins is None and wallet is None:
        result["error"] = "响应缺少 remainCoins/remainMoney"
        return result

    result.update(
        {
            "ok": True,
            "balance": to_float(coins) if coins is not None else to_float(wallet),
            "unit": "币" if coins is not None else (data.get("currency") or "CNY"),
            "wallet": to_float(wallet) if wallet is not None else None,
            "wallet_unit": data.get("currency") or "CNY",
            "running_tasks": data.get("currentTaskCounts"),
            "api_type": data.get("apiType"),
        }
    )
    return result


def balance_newapi(section, key, base_url, timeout):
    proxy = (section.get("proxy") or "").strip()
    headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
    result = {
        "label": section.get("label") or "Router",
        "provider": section.get("provider") or "new-api",
        "base_url": base_url,
        "balance_mode": "newapi",
        "configured": True,
        "masked": mask(key),
        "ok": False,
        "balance": None,
        "unit": "CNY",
        "unlimited": False,
        "hard_limit": None,
        "used": None,
        "error": None,
    }

    sub, error = http_json(
        base_url + "/v1/dashboard/billing/subscription",
        headers=headers,
        proxy=proxy,
        timeout=timeout,
    )
    if error:
        result["error"] = redact(error, key)
        return result
    if not isinstance(sub, dict):
        result["error"] = "订阅接口响应不是 JSON 对象"
        return result
    if isinstance(sub.get("error"), dict):
        result["error"] = redact(str(sub["error"].get("message") or sub["error"]), key)
        return result

    usage, error = http_json(
        base_url + "/v1/dashboard/billing/usage",
        headers=headers,
        proxy=proxy,
        timeout=timeout,
    )
    if error:
        result["error"] = redact(error, key)
        return result
    if not isinstance(usage, dict):
        result["error"] = "用量接口响应不是 JSON 对象"
        return result
    if isinstance(usage.get("error"), dict):
        result["error"] = redact(str(usage["error"].get("message") or usage["error"]), key)
        return result

    hard_limit = None
    for field in ("hard_limit_usd", "soft_limit_usd", "system_hard_limit_usd"):
        if sub.get(field) is not None:
            hard_limit = to_float(sub[field])
            break
    if hard_limit is None:
        result["error"] = "订阅接口缺少 hard_limit_usd"
        return result

    total_usage = to_float(usage.get("total_usage")) or 0.0
    used = total_usage / 100.0

    unit = (section.get("currency") or "").strip().upper()
    status, _ = http_json(base_url + "/api/status", proxy=proxy, timeout=timeout)
    if isinstance(status, dict):
        data = status.get("data") if isinstance(status.get("data"), dict) else status
        quota_type = str(data.get("quota_display_type") or "").strip().upper()
        if quota_type in ("CNY", "USD", "TOKENS"):
            unit = quota_type
    if unit not in ("CNY", "USD", "TOKENS"):
        unit = "USD"

    unlimited = hard_limit >= 100000000
    remaining = None if unlimited else max(0.0, hard_limit - used)
    result.update(
        {
            "ok": True,
            "balance": remaining,
            "unit": "tokens" if unit == "TOKENS" else unit,
            "unlimited": unlimited,
            "hard_limit": hard_limit,
            "used": used,
        }
    )
    return result


def balance_router(cfg, timeout):
    section = cfg.get("router") or {}
    key = (section.get("api_key") or "").strip()
    base_url = (section.get("base_url") or "https://router.kcacher.top").rstrip("/")
    path = section.get("balance_path") or "/v1/balance"
    if not path.startswith("/"):
        path = "/" + path
    result = {
        "label": section.get("label") or "Router",
        "provider": section.get("provider") or "",
        "base_url": base_url,
        "configured": bool(key),
        "masked": mask(key),
        "ok": False,
        "balance": None,
        "unit": "USD",
        "unlimited": False,
        "error": None,
    }
    if not key:
        result["error"] = "未配置 router.api_key"
        return result

    mode = (section.get("balance_mode") or "newapi").strip().lower()
    if mode in ("newapi", "new-api"):
        return balance_newapi(section, key, base_url, timeout)

    response, error = http_json(
        base_url + path,
        headers={"Authorization": "Bearer " + key, "Accept": "application/json"},
        proxy=(section.get("proxy") or "").strip(),
        timeout=timeout,
    )
    if error:
        result["error"] = redact(error, key)
        return result
    if not isinstance(response, dict):
        result["error"] = "响应不是 JSON 对象"
        return result

    data = response.get("data") if isinstance(response.get("data"), dict) else response
    unlimited = bool(response.get("unlimited_quota") or data.get("unlimited_quota"))
    if unlimited:
        result.update({"ok": True, "unlimited": True, "balance": None, "unit": "不限"})
        return result

    value = None
    field = None
    for candidate in ("total_available", "total_balance", "balance", "remaining", "credits", "quota"):
        if candidate in data and data.get(candidate) is not None:
            value = to_float(data.get(candidate))
            field = candidate
            break
        if candidate in response and response.get(candidate) is not None:
            value = to_float(response.get(candidate))
            field = candidate
            break
    if value is None:
        keys = ",".join(sorted(str(k) for k in response.keys())[:8])
        result["error"] = "未识别余额字段（返回 keys：%s）" % (keys or "空")
        return result

    currency = data.get("currency") or response.get("currency") or "USD"
    unit = "credits" if field == "credits" else str(currency).upper()
    result.update({"ok": True, "balance": value, "unit": unit, "field": field})
    return result


def to_data_keys(payload):
    output = {}
    for name, fallback in (("runninghub", "RunningHub"), ("router", "Router")):
        item = payload.get(name) or {}
        output[name] = {
            "label": item.get("label") or fallback,
            "account": item.get("account") or "",
            "configured": bool(item.get("configured")),
            "masked": item.get("masked") or "",
            "ok": bool(item.get("ok")),
            "balance": item.get("balance"),
            "unit": item.get("unit") or ("币" if name == "runninghub" else "USD"),
            "wallet": item.get("wallet"),
            "wallet_unit": item.get("wallet_unit"),
            "unlimited": bool(item.get("unlimited")),
            "checked_at": payload.get("checked_at"),
            "error": item.get("error"),
        }
    return output


def update_workbench(path, keys_data, backup=True):
    page = Path(path).expanduser()
    if not page.exists():
        die("找不到工作台：%s" % page)
    html = page.read_text(encoding="utf-8")
    index = html.find(WORKBENCH_MARKER)
    if index < 0:
        die("workbench.html 里找不到 %s" % WORKBENCH_MARKER)
    start = index + len(WORKBENCH_MARKER)
    try:
        data, end = json.JSONDecoder().raw_decode(html[start:])
    except json.JSONDecodeError as exc:
        die("workbench.html 的 DATA 不是合法 JSON：%s" % exc)
    data["keys"] = keys_data
    new_json = json.dumps(data, ensure_ascii=False)

    backup_path = None
    if backup:
        backup_path = page.with_name(page.name + ".bak")
        backup_path.write_text(html, encoding="utf-8")
        try:
            os.chmod(backup_path, 0o600)
        except OSError:
            pass

    page.write_text(html[:start] + new_json + html[start + end :], encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "written": str(page),
                "backup": str(backup_path) if backup_path else None,
                "keys": keys_data,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_init(args):
    path = keys_path()
    if path.exists() and not args.force:
        print(
            json.dumps(
                {"ok": True, "exists": True, "path": str(path), "message": "已存在，未覆盖；要重置加 --force"},
                ensure_ascii=False,
            )
        )
        return
    cfg = copy.deepcopy(TEMPLATE)
    if args.from_env:
        for env_name, section in (("RUNNINGHUB_API_KEY", "runninghub"), ("APIMART_KEY", "router")):
            value = (os.environ.get(env_name) or "").strip()
            if value:
                cfg[section]["api_key"] = value
    save_cfg(cfg)
    print(
        json.dumps(
            {
                "ok": True,
                "path": str(path),
                "runninghub_configured": bool(cfg["runninghub"]["api_key"]),
                "router_configured": bool(cfg["router"]["api_key"]),
                "next": "用 config router 设 base_url/balance_mode；用 set <runninghub|router> 补 key；再 balance --write <workbench.html>",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_status(args):
    cfg, exists = load_cfg()
    path = keys_path()
    stat = path.stat() if path.exists() else None
    mode = oct(stat.st_mode & 0o777) if stat else None
    rh = cfg.get("runninghub") or {}
    rt = cfg.get("router") or {}
    print(
        json.dumps(
            {
                "ok": True,
                "path": str(path),
                "exists": exists,
                "mode": mode,
                "permissions_ok": bool(stat and (stat.st_mode & 0o077) == 0),
                "runninghub": {
                    "configured": bool((rh.get("api_key") or "").strip()),
                    "masked": mask(rh.get("api_key")),
                    "label": rh.get("label") or "RunningHub",
                    "account": rh.get("account") or "",
                },
                "router": {
                    "configured": bool((rt.get("api_key") or "").strip()),
                    "masked": mask(rt.get("api_key")),
                    "label": rt.get("label") or "Router",
                    "provider": rt.get("provider") or "",
                    "base_url": rt.get("base_url") or "",
                    "balance_mode": rt.get("balance_mode") or "newapi",
                },
                "env": {
                    "RUNNINGHUB_API_KEY": bool(os.environ.get("RUNNINGHUB_API_KEY")),
                    "APIMART_KEY": bool(os.environ.get("APIMART_KEY")),
                },
                "note": "exec 会清掉 shell 里的 key，只使用 keys.json；原始 key 不进入 HTML/DATA。",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_set(args):
    cfg, _ = load_cfg()
    name = args.name
    if name not in ("runninghub", "router"):
        die("只支持 runninghub 或 router", 2)
    if args.stdin:
        key = sys.stdin.readline().strip()
    else:
        key = getpass.getpass("%s API key（输入不回显）: " % name).strip()
    if not key:
        die("空 key，未修改")
    cfg[name]["api_key"] = key
    if args.label:
        cfg[name]["label"] = args.label
    if args.account and name == "runninghub":
        cfg[name]["account"] = args.account
    if args.base_url and name == "router":
        cfg[name]["base_url"] = args.base_url.rstrip("/")
    if args.balance_path and name == "router":
        cfg[name]["balance_path"] = args.balance_path
    if args.balance_mode and name == "router":
        cfg[name]["balance_mode"] = args.balance_mode
    if args.provider and name == "router":
        cfg[name]["provider"] = args.provider
    if args.proxy is not None and name == "router":
        cfg[name]["proxy"] = args.proxy
    save_cfg(cfg)
    print(
        json.dumps(
            {"ok": True, "name": name, "masked": mask(key), "path": str(keys_path())},
            ensure_ascii=False,
        )
    )


def cmd_config(args):
    cfg, _ = load_cfg()
    section = args.section
    if section not in ("runninghub", "router"):
        die("只支持 runninghub 或 router", 2)
    changed = False
    if args.label:
        cfg[section]["label"] = args.label
        changed = True
    if args.account and section == "runninghub":
        cfg[section]["account"] = args.account
        changed = True
    if section == "router":
        if args.base_url:
            cfg[section]["base_url"] = args.base_url.rstrip("/")
            changed = True
        if args.balance_path:
            cfg[section]["balance_path"] = args.balance_path
            changed = True
        if args.balance_mode:
            cfg[section]["balance_mode"] = args.balance_mode
            changed = True
        if args.provider:
            cfg[section]["provider"] = args.provider
            changed = True
        if args.proxy is not None:
            cfg[section]["proxy"] = args.proxy
            changed = True
    if changed:
        save_cfg(cfg)
    print(
        json.dumps(
            {
                "ok": True,
                "section": section,
                "changed": changed,
                "configured": bool((cfg[section].get("api_key") or "").strip()),
                "masked": mask(cfg[section].get("api_key")),
                "label": cfg[section].get("label"),
                "base_url": cfg[section].get("base_url"),
                "balance_mode": cfg[section].get("balance_mode"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_balance(args):
    cfg, _ = load_cfg()
    checked_at = now_iso()
    payload = {
        "checked_at": checked_at,
        "keys_path": str(keys_path()),
        "runninghub": balance_runninghub(cfg, args.timeout),
        "router": balance_router(cfg, args.timeout),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.write:
        keys_data = to_data_keys(payload)
        serialized = json.dumps(keys_data, ensure_ascii=False)
        for section in ("runninghub", "router"):
            raw = ((cfg.get(section) or {}).get("api_key") or "").strip()
            if raw and raw in serialized:
                die("拒绝写入：DATA 中出现原始 key")
        update_workbench(args.write, keys_data, backup=not args.no_backup)


def cmd_exec(command, need="any"):
    cfg, exists = load_cfg()
    if not exists:
        die("未找到 %s；先运行 mv_keys.py init" % keys_path())
    runninghub = ((cfg.get("runninghub") or {}).get("api_key") or "").strip()
    router = ((cfg.get("router") or {}).get("api_key") or "").strip()

    if need in ("runninghub", "both") and not runninghub:
        die("这条命令需要 runninghub key，但 keys.json 未配置")
    if need in ("router", "both") and not router:
        die("这条命令需要 router key，但 keys.json 未配置")
    if need == "any" and not runninghub and not router:
        die("keys.json 里没有配置任何 key；先运行 mv_keys.py set ...")

    env = os.environ.copy()
    # 清掉 shell 残留，确保只用 keys.json，避免串号
    for name in ("RUNNINGHUB_API_KEY", "APIMART_KEY", "ROUTER_API_KEY", "APIMART_BASE_URL"):
        env.pop(name, None)
    if runninghub:
        env["RUNNINGHUB_API_KEY"] = runninghub
    if router:
        env["APIMART_KEY"] = router
        env["ROUTER_API_KEY"] = router
        base_url = ((cfg.get("router") or {}).get("base_url") or "").strip()
        if base_url:
            env["APIMART_BASE_URL"] = base_url.rstrip("/")
        proxy = ((cfg.get("router") or {}).get("proxy") or "").strip()
        if proxy:
            env["https_proxy"] = proxy
            env["http_proxy"] = proxy
            env["HTTPS_PROXY"] = proxy
            env["HTTP_PROXY"] = proxy

    try:
        completed = subprocess.run(command, env=env)
        raise SystemExit(completed.returncode)
    except FileNotFoundError:
        die("命令不存在：%s" % command[0], 127)
    except OSError as exc:
        die("exec 失败：%s" % exc, 126)


def build_parser():
    parser = argparse.ArgumentParser(description="MV 工作台 Key 与余额管理")
    subparsers = parser.add_subparsers(dest="cmd")

    init = subparsers.add_parser("init", help="创建 keys.json 模板（不覆盖）")
    init.add_argument("--force", action="store_true", help="覆盖已有配置")
    init.add_argument("--from-env", action="store_true", help="从 RUNNINGHUB_API_KEY / APIMART_KEY 导入")

    subparsers.add_parser("status", help="查看配置状态（掩码）")

    set_parser = subparsers.add_parser("set", help="设置 key（交互输入，不回显）")
    set_parser.add_argument("name", choices=["runninghub", "router"])
    set_parser.add_argument("--stdin", action="store_true", help="从 stdin 读一行（自动化用）")
    set_parser.add_argument("--label", help="显示名")
    set_parser.add_argument("--account", help="RunningHub 账号备注")
    set_parser.add_argument("--base-url", help="Router base URL")
    set_parser.add_argument("--balance-path", help="Router 余额路径，默认 /v1/balance")
    set_parser.add_argument("--balance-mode", choices=["newapi", "openai"], help="Router 余额模式")
    set_parser.add_argument("--provider", help="Router 类型，例如 new-api")
    set_parser.add_argument("--proxy", help="Router 代理，例如 http://127.0.0.1:7897")

    config = subparsers.add_parser("config", help="只改元数据，不动 api_key")
    config.add_argument("section", choices=["runninghub", "router"])
    config.add_argument("--label")
    config.add_argument("--account")
    config.add_argument("--base-url")
    config.add_argument("--balance-path")
    config.add_argument("--balance-mode", choices=["newapi", "openai"])
    config.add_argument("--provider")
    config.add_argument("--proxy")

    balance = subparsers.add_parser("balance", help="查询余额；可写回 workbench.html")
    balance.add_argument("--write", metavar="WORKBENCH_HTML", help="把掩码+余额写进 DATA.keys")
    balance.add_argument("--no-backup", action="store_true", help="写回时不生成 .bak")
    balance.add_argument("--timeout", type=int, default=12, help="单次查询超时秒数")

    execute = subparsers.add_parser("exec", help="带 keys.json 环境变量执行命令")
    execute.add_argument(
        "--need",
        choices=["any", "runninghub", "router", "both"],
        default="any",
        help="要求哪份 key 已配置；放在 -- 之前",
    )
    execute.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return
    if args.cmd == "init":
        cmd_init(args)
    elif args.cmd == "status":
        cmd_status(args)
    elif args.cmd == "set":
        cmd_set(args)
    elif args.cmd == "config":
        cmd_config(args)
    elif args.cmd == "balance":
        cmd_balance(args)
    elif args.cmd == "exec":
        command = list(args.command or [])
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            die("用法：mv_keys.py exec [--need runninghub|router|both] -- <命令...>", 2)
        cmd_exec(command, getattr(args, "need", "any"))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
