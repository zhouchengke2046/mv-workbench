#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MV 工作台 Key 与余额管理。

唯一真源：~/.config/mv-workbench/keys.json（目录 0700 / 文件 0600）
可用 MV_KEYS_PATH 覆盖路径（测试/多工作区）。

命令：
  init [--force] [--from-env]
  status
  set <runninghub|router> [--stdin] [--label X] [--account X] [--base-url X] [--proxy X]
  import --file mv-keys-import.json [--delete-source]
  watch [--dir DIR] [--timeout 300] [--data DATA_JSON]
  balance [--data DATA_JSON] [--write WORKBENCH_HTML] [--no-backup] [--timeout 12]
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
import time
import urllib.error
import urllib.request
from pathlib import Path

from console import setup

setup()

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
    "apimart": {
        "api_key": "",
        "label": "APIMart",
        "provider": "new-api",
        "base_url": "https://api.apimart.ai",
        "balance_path": "/v1/dashboard/billing/subscription",
        "balance_mode": "newapi",
        "proxy": "",
    },
}

RH_ACCOUNT_URL = "https://www.runninghub.cn/uc/openapi/accountStatus"
WORKBENCH_MARKER = "const DATA = "


def keys_path():
    return Path(os.environ.get("MV_KEYS_PATH") or str(DEFAULT_KEYS_PATH)).expanduser()


def die(message, code=1, alert=None, **alert_kw):
    if alert:
        import alerts
        alerts.emit(alert, raw=message, **alert_kw)
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
    for name in ("runninghub", "router", "apimart"):
        if not isinstance(cfg.get(name), dict):
            cfg[name] = copy.deepcopy(TEMPLATE[name])
    for name in ("router", "apimart"):
        if not cfg[name].get("balance_mode"):
            cfg[name]["balance_mode"] = "newapi"
    return cfg


def load_cfg():
    path = keys_path()
    if not path.exists():
        return copy.deepcopy(TEMPLATE), False
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die("keys.json 不是合法 JSON：%s" % exc, alert="K002")
    except OSError as exc:
        die("读取 keys.json 失败：%s" % exc, alert="K002")
    return _normalize(cfg), True


def save_cfg(cfg):
    path = keys_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
    except OSError as exc:
        die("创建配置目录失败：%s" % exc, alert="K002")
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


def balance_newapi(section, key, base_url, timeout, default_label="Router"):
    proxy = (section.get("proxy") or "").strip()
    headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
    result = {
        "label": section.get("label") or default_label,
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


def _balance_openai_like(section, timeout, name, default_base, default_label):
    key = (section.get("api_key") or "").strip()
    base_url = (section.get("base_url") or default_base).rstrip("/")
    path = section.get("balance_path") or "/v1/balance"
    if not path.startswith("/"):
        path = "/" + path
    result = {
        "label": section.get("label") or default_label,
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
        result["error"] = "未配置 %s.api_key" % name
        return result

    mode = (section.get("balance_mode") or "newapi").strip().lower()
    if mode in ("newapi", "new-api"):
        return balance_newapi(section, key, base_url, timeout, default_label=default_label)

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


def balance_router(cfg, timeout):
    return _balance_openai_like(cfg.get("router") or {}, timeout, "router", "https://router.kcacher.top", "Router")


def balance_apimart(cfg, timeout):
    return _balance_openai_like(cfg.get("apimart") or {}, timeout, "apimart", "https://api.apimart.ai", "APIMart")


def to_data_keys(payload):
    output = {}
    for name, fallback in (("runninghub", "RunningHub"), ("router", "Router"), ("apimart", "APIMart")):
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


def update_data_keys(path, keys_data):
    target = Path(path).expanduser()
    if not target.is_file():
        die("找不到 DATA：%s" % target)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die("DATA 读取失败：%s（%s）" % (target, exc), alert="W2")
    if not isinstance(data, dict):
        die("DATA 顶层必须是 JSON 对象", alert="W2")
    data["keys"] = keys_data
    serialized = json.dumps(data, ensure_ascii=False)
    for section in ("runninghub", "router", "apimart"):
        raw = (keys_data.get(section) or {}).get("_raw")
        if raw and raw in serialized:
            die("拒绝写入：DATA 中出现原始 key")
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(serialized + "\n", encoding="utf-8")
    tmp.replace(target)
    print(json.dumps({"ok": True, "written": str(target), "hint": "再运行 mvwb build 刷新页面"}, ensure_ascii=False))


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
                "next": "用 config router 设 base_url/balance_mode；用 set <runninghub|router> 补 key；再 balance --data <data.json>，最后 build 刷新页面",
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
    am = cfg.get("apimart") or {}
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
                "apimart": {
                    "configured": bool((am.get("api_key") or "").strip()),
                    "masked": mask(am.get("api_key")),
                    "label": am.get("label") or "APIMart",
                    "provider": am.get("provider") or "",
                    "base_url": am.get("base_url") or "",
                    "balance_mode": am.get("balance_mode") or "newapi",
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
        die("只支持 runninghub / router / apimart", 2)
    if args.stdin:
        key = sys.stdin.readline().strip()
    else:
        if not sys.stdin.isatty():
            die("当前没有可交互终端。请让用户在本机终端运行，或双击 setup-keys；agent 不要代输 Key", alert="K006")
        key = getpass.getpass("%s API key（输入不回显）: " % name).strip()
    if not key:
        die("空 key，未修改", alert="K003")
    cfg[name]["api_key"] = key
    if args.label:
        cfg[name]["label"] = args.label
    if args.account and name == "runninghub":
        cfg[name]["account"] = args.account
    if args.base_url and name in ("router", "apimart"):
        cfg[name]["base_url"] = args.base_url.rstrip("/")
    if args.balance_path and name in ("router", "apimart"):
        cfg[name]["balance_path"] = args.balance_path
    if args.balance_mode and name in ("router", "apimart"):
        cfg[name]["balance_mode"] = args.balance_mode
    if args.provider and name in ("router", "apimart"):
        cfg[name]["provider"] = args.provider
    if args.proxy is not None and name in ("router", "apimart"):
        cfg[name]["proxy"] = args.proxy
    save_cfg(cfg)
    print(
        json.dumps(
            {"ok": True, "name": name, "masked": mask(key), "path": str(keys_path())},
            ensure_ascii=False,
        )
    )


def _read_import_key(payload, section, flat_name):
    item = payload.get(section)
    if isinstance(item, dict):
        value = item.get("api_key") or item.get("key") or ""
    elif isinstance(item, str):
        value = item
    else:
        value = ""
    if not value:
        value = payload.get(flat_name) or ""
    return str(value).strip()


def cmd_import(args):
    """从 Key JSON 文件（如 zz-keys.json）导入，导入后可选删除源文件。"""
    src = Path(args.file).expanduser()
    if not src.is_file():
        die("找不到配置文件：%s" % src, alert="K004")
    try:
        payload = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die("配置文件读取失败：%s" % exc, alert="K003")
    if not isinstance(payload, dict):
        die("配置文件顶层必须是 JSON 对象", alert="K003")

    rh_key = _read_import_key(payload, "runninghub", "runninghub_key")
    rt_key = _read_import_key(payload, "router", "router_key")
    am_key = _read_import_key(payload, "apimart", "apimart_key")
    if not rh_key and not rt_key and not am_key:
        die("文件里没有 runninghub / router / apimart key", alert="K003")
    for label, value in (("RunningHub", rh_key), ("Router", rt_key), ("APIMart", am_key)):
        if not value:
            continue
        if value.startswith("••••") or value.startswith("****"):
            die("%s 是掩码，不是原始 Key；请重新填写完整 Key" % label, alert="K003")
        if len(value) < 8 or len(value) > 500 or any(ch in value for ch in "\r\n\t "):
            die("%s Key 格式不正确" % label, alert="K003")

    cfg, _ = load_cfg()
    imported = []
    if rh_key:
        cfg["runninghub"]["api_key"] = rh_key
        imported.append("runninghub")
    if rt_key:
        cfg["router"]["api_key"] = rt_key
        imported.append("router")
    if am_key:
        cfg["apimart"]["api_key"] = am_key
        imported.append("apimart")
    save_cfg(cfg)

    deleted = False
    delete_error = None
    if args.delete_source:
        try:
            src.unlink()
            deleted = True
        except OSError as exc:
            delete_error = str(exc)

    print(json.dumps({
        "ok": True,
        "imported": imported,
        "runninghub": mask(cfg["runninghub"].get("api_key")),
        "router": mask(cfg["router"].get("api_key")),
        "apimart": mask(cfg["apimart"].get("api_key")),
        "path": str(keys_path()),
        "source": str(src),
        "deleted_source": deleted,
        "delete_error": delete_error,
        "next": "导入后必须：mvwb keys balance --data <项目>/data.json 刷新余额/Keys 快照，再 mvwb build（否则工作台顶部显示未配置）",
    }, ensure_ascii=False, indent=2))


def _download_dirs():
    home = Path.home()
    dirs = []
    for name in ("Downloads", "Desktop", "下载"):
        path = home / name
        if path.is_dir():
            dirs.append(path)
    return dirs


def cmd_watch(args):
    """短时监听目录：出现 zz-keys.json / 导入 JSON 后自动导入并删除。"""
    dirs = [Path(d).expanduser() for d in (args.dir or _download_dirs())]
    if not dirs:
        die("找不到下载目录；用 --dir 指定", alert="K004")
    print(json.dumps({
        "ok": True,
        "watching": [str(d) for d in dirs],
        "timeout": args.timeout,
        "hint": "把老师发的 zz-keys.json 放进这个目录（或让 agent 直接 import）；不要关这个进程",
    }, ensure_ascii=False), flush=True)

    started = time.time()
    seen = set()
    while time.time() - started < args.timeout:
        for directory in dirs:
            candidates = []
            for pattern in ("mv-keys-import*.json", "zz-keys.json"):
                candidates.extend(directory.glob(pattern))
            for path in sorted(set(candidates), key=lambda p: p.stat().st_mtime, reverse=True):
                try:
                    stat1 = path.stat()
                except OSError:
                    continue
                key = (str(path), int(stat1.st_mtime), stat1.st_size)
                if key in seen or stat1.st_mtime < started - 2:
                    continue
                seen.add(key)
                time.sleep(0.5)
                try:
                    stat2 = path.stat()
                except OSError:
                    continue
                if stat2.st_size != stat1.st_size or stat2.st_size < 20:
                    continue
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if not isinstance(payload, dict):
                    continue
                if payload.get("mv_keys_import") != 1:
                    if path.name != "zz-keys.json" or not any(payload.get(k) for k in ("runninghub", "router")):
                        continue
                try:
                    cmd_import(argparse.Namespace(file=str(path), delete_source=True))
                except SystemExit:
                    print(json.dumps({"ok": False, "warning": "文件格式不对，已跳过：%s" % path}, ensure_ascii=False))
                    continue
                if args.data:
                    data = Path(args.data).expanduser()
                    if data.is_file():
                        try:
                            cmd_balance(argparse.Namespace(
                                data=str(data), write=None, no_backup=True, timeout=args.balance_timeout,
                            ))
                        except SystemExit:
                            print(json.dumps({"ok": False, "warning": "Key 已导入，但余额查询失败"}, ensure_ascii=False))
                        build = Path(__file__).resolve().parent / "build_workbench.py"
                        template = Path(__file__).resolve().parent.parent / "templates" / "workbench.html"
                        if build.is_file():
                            subprocess.call([
                                sys.executable, str(build), "--template", str(template),
                                "--data", str(data), "--out", str(data.parent / "workbench.html"),
                            ])
                return 0
        time.sleep(args.interval)
    die("等待超时：没有在 %s 找到新的 mv-keys-import*.json / zz-keys.json" % ", ".join(str(d) for d in dirs), alert="K005")


def cmd_config(args):
    cfg, _ = load_cfg()
    section = args.section
    if section not in ("runninghub", "router", "apimart"):
        die("只支持 runninghub / router / apimart", 2)
    changed = False
    if args.label:
        cfg[section]["label"] = args.label
        changed = True
    if args.account and section == "runninghub":
        cfg[section]["account"] = args.account
        changed = True
    if section in ("router", "apimart"):
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
        "apimart": balance_apimart(cfg, args.timeout),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.data:
        keys_data = to_data_keys(payload)
        serialized = json.dumps(keys_data, ensure_ascii=False)
        for section in ("runninghub", "router", "apimart"):
            raw = ((cfg.get(section) or {}).get("api_key") or "").strip()
            if raw and raw in serialized:
                die("拒绝写入：DATA 中出现原始 key")
        update_data_keys(args.data, keys_data)
    elif args.write:
        keys_data = to_data_keys(payload)
        serialized = json.dumps(keys_data, ensure_ascii=False)
        for section in ("runninghub", "router", "apimart"):
            raw = ((cfg.get(section) or {}).get("api_key") or "").strip()
            if raw and raw in serialized:
                die("拒绝写入：DATA 中出现原始 key")
        update_workbench(args.write, keys_data, backup=not args.no_backup)


def cmd_exec(command, need="any"):
    cfg, exists = load_cfg()
    if not exists:
        die("未找到 %s；先运行 mv_keys.py init" % keys_path(), alert="K002")
    runninghub = ((cfg.get("runninghub") or {}).get("api_key") or "").strip()
    router = ((cfg.get("router") or {}).get("api_key") or "").strip()
    apimart = ((cfg.get("apimart") or {}).get("api_key") or "").strip()

    if need in ("runninghub", "both") and not runninghub:
        die("这条命令需要 runninghub key，但 keys.json 未配置", alert="K001", platform="runninghub")
    if need in ("router", "both") and not router:
        die("这条命令需要 router key，但 keys.json 未配置", alert="K001", platform="router")
    if need == "apimart" and not apimart:
        die("这条命令需要 apimart key，但 keys.json 未配置", alert="K001", platform="apimart")
    if need == "any" and not runninghub and not router and not apimart:
        die("keys.json 里没有配置任何 key；先运行 mv_keys.py set ...", alert="K001")

    env = os.environ.copy()
    # 清掉 shell 残留，确保只用 keys.json，避免串号
    for name in ("RUNNINGHUB_API_KEY", "APIMART_KEY", "ROUTER_API_KEY", "APIMART_BASE_URL"):
        env.pop(name, None)
    if runninghub:
        env["RUNNINGHUB_API_KEY"] = runninghub
    if router:
        env["ROUTER_API_KEY"] = router
        env["APIMART_KEY"] = router
        base_url = ((cfg.get("router") or {}).get("base_url") or "").strip()
        if base_url:
            env["APIMART_BASE_URL"] = base_url.rstrip("/")
        proxy = ((cfg.get("router") or {}).get("proxy") or "").strip()
        if proxy:
            env["https_proxy"] = proxy
            env["http_proxy"] = proxy
            env["HTTPS_PROXY"] = proxy
            env["HTTP_PROXY"] = proxy
    if apimart:
        env["APIMART_KEY"] = apimart
        base_url = ((cfg.get("apimart") or {}).get("base_url") or "").strip()
        if base_url:
            env["APIMART_BASE_URL"] = base_url.rstrip("/")
        proxy = ((cfg.get("apimart") or {}).get("proxy") or "").strip()
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

    import_parser = subparsers.add_parser("import", help="从工作台下载的 JSON 导入 Key")
    import_parser.add_argument("--file", required=True, help="mv-keys-import.json 路径")
    import_parser.add_argument("--delete-source", action="store_true", help="导入成功后删除源文件")

    watch_parser = subparsers.add_parser("watch", help="监听下载目录，自动导入工作台下载的 Key 文件")
    watch_parser.add_argument("--dir", action="append", help="监听目录；可多次；默认 ~/Downloads、~/Desktop、~/下载")
    watch_parser.add_argument("--timeout", type=int, default=300, help="等待秒数，默认 300")
    watch_parser.add_argument("--interval", type=float, default=1.0, help="轮询间隔秒")
    watch_parser.add_argument("--data", help="导入后顺便刷新余额并重建这个 data.json 对应的工作台")
    watch_parser.add_argument("--balance-timeout", type=int, default=10, help="余额查询超时秒")

    config = subparsers.add_parser("config", help="只改元数据，不动 api_key")
    config.add_argument("section", choices=["runninghub", "router"])
    config.add_argument("--label")
    config.add_argument("--account")
    config.add_argument("--base-url")
    config.add_argument("--balance-path")
    config.add_argument("--balance-mode", choices=["newapi", "openai"])
    config.add_argument("--provider")
    config.add_argument("--proxy")

    balance = subparsers.add_parser("balance", help="查询余额；可写回 data.json")
    balance.add_argument("--data", metavar="DATA_JSON", help="把掩码+余额写进 data.json 的 keys，再 mvwb build")
    balance.add_argument("--write", metavar="WORKBENCH_HTML", help="旧版：把掩码+余额写进 HTML 的 DATA.keys")
    balance.add_argument("--no-backup", action="store_true", help="写回时不生成 .bak")
    balance.add_argument("--timeout", type=int, default=12, help="单次查询超时秒数")

    execute = subparsers.add_parser("exec", help="带 keys.json 环境变量执行命令")
    execute.add_argument(
        "--need",
        choices=["any", "runninghub", "router", "apimart", "both"],
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
    elif args.cmd == "import":
        cmd_import(args)
    elif args.cmd == "watch":
        cmd_watch(args)
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
