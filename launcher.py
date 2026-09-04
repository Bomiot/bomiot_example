import os, sys, json, hashlib, fnmatch, platform, subprocess, tempfile, shutil, time
from pathlib import Path
from time import sleep
import urllib.request
import urllib.error
import uvicorn
import socket
import webbrowser
import threading
from os.path import join, exists
from bomiot_token import encrypt_info
from os import getcwd
import tkinter as tk
from PIL import Image, ImageTk
import requests

app_name = "GreaterWMS"
version = "3.0.0"
port = 8008

# === 增量更新配置（可修改为你的实际地址）===
# 远端 releases 目录的 base URL，launcher 会自动拼接 manifest 和版本文件路径
# 结构: {UPDATE_URL}manifest-{os}-{arch}.json  和  {UPDATE_URL}GreaterWMS-{version}-{Platform}/
UPDATE_URL = "http://127.0.0.1:8000/media/update/"
# 归一化：确保 UPDATE_URL 以 "/" 结尾（为空时保持空），避免拼接时少 "/" 导致 404
if UPDATE_URL:
    UPDATE_URL = UPDATE_URL.rstrip("/") + "/"


def _detect_platform():
    """检测当前平台，返回 (os_str, arch_str, platform_display)"""
    if sys.platform == "win32":
        _os = "windows"
        _display = "Windows"
    elif sys.platform == "darwin":
        _os = "macos"
        _display = "macOS"
    else:
        _os = "linux"
        _display = "Linux"
    machine = platform.machine().lower()
    _arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
    return _os, _arch, _display


def _port_available(p: int) -> bool:
    """Check if a TCP port is available for binding (no other process is listening on it)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', p))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _find_available_port(start_port: int, max_tries: int = 100) -> int:
    """Starting from start_port, return the first port that is not in use (increment by 1 each try)."""
    for candidate in range(start_port, start_port + max_tries):
        if _port_available(candidate):
            if candidate != start_port:
                print(f"Port {start_port} is in use, switched to port {candidate}")
            return candidate
    raise RuntimeError(f"No available port in range [{start_port}, {start_port + max_tries - 1}]")


# === 增量更新 ===

def _app_dir():
    """返回 launcher 所在目录（launcher.dist/）"""
    return os.path.dirname(sys.executable)


def _read_gitignore(app_dir):
    """读取 .gitignore 规则列表"""
    patterns = []
    gi = os.path.join(app_dir, ".gitignore")
    if not os.path.exists(gi):
        return patterns
    with open(gi, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def _is_ignored(rel_path, patterns):
    """判断文件是否被 .gitignore 规则匹配"""
    basename = os.path.basename(rel_path)
    for pat in patterns:
        if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(basename, pat):
            return True
        if pat.endswith("/"):
            d = pat.rstrip("/")
            if rel_path.startswith(d + "/") or ("/" + d + "/") in rel_path:
                return True
    return False


def _sha256_file(path):
    """计算单个文件的 SHA256"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _scan_local_files(app_dir, ignore_patterns):
    """
    扫描本地所有文件，返回 {相对路径: SHA256}。
    跳过：.gitignore 匹配的 / manifest.json / manifest-*.json / update.bat / update.sh
    —— manifest-*.json 必须排除，否则远端 files 里不含它时会被加入 to_delete，
       更新后本地 manifest 被删，下次启动永久跳过更新检查（问题②）。
    注：当前 check_update 比对逻辑改为「只以 manifest.files 为准」，该函数已不被主流程调用，保留作为调试工具。
    """
    result = {}
    for root, dirs, files in os.walk(app_dir):
        for fn in files:
            if fn in ("manifest.json", "update.bat", "update.sh"):
                continue
            if fn.startswith("manifest-") and fn.endswith(".json"):
                continue  # e.g. manifest-windows-x64.json
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, app_dir).replace(os.sep, "/")
            if _is_ignored(rel, ignore_patterns):
                continue
            try:
                result[rel] = _sha256_file(full)
            except Exception:
                pass
    return result


def _download(url, dest, max_retries=3):
    """下载文件到指定路径，带重试"""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GreaterWMS-Updater"})
            with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            return
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                sleep(1 * attempt)
    raise last_err


def _fetch_manifest(url, max_retries=3):
    """
    下载并解析远端 manifest JSON，带重试与健壮的错误处理。

    处理场景：
      - 服务器返回空内容（0 字节）
      - HTTP 404/5xx 错误
      - 返回非 JSON（如 HTML 错误页、空行、纯文本）
      - JSON 缺少必要字段（app_name / version / files）
      - 网络超时 / 连接失败

    返回解析成功的 dict；失败则抛出异常（调用方统一捕获处理）。
    """
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GreaterWMS-Updater"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = getattr(resp, "status", 200)
                # 1. HTTP 状态码检查（urlopen 对 4xx/5xx 会抛 HTTPError，这里额外防御）
                if status < 200 or status >= 300:
                    raise RuntimeError(f"HTTP {status}")
                raw = resp.read()
                # 2. 空响应检查
                if not raw or not raw.strip():
                    raise RuntimeError("empty response (0 bytes)")
                # 3. JSON 解析（防御 HTML/404 页面等非 JSON 内容）
                try:
                    data = json.loads(raw.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    snippet = raw[:200].decode("utf-8", errors="replace")
                    raise RuntimeError(f"non-JSON response: {snippet!r}") from e
                # 4. 类型检查：必须是对象
                if not isinstance(data, dict):
                    raise RuntimeError(f"manifest is not an object, got {type(data).__name__}")
                # 5. 必要字段完整性检查
                missing = [k for k in ("app_name", "version", "files") if k not in data]
                if missing:
                    raise RuntimeError(f"missing required fields: {missing}")
                if not isinstance(data["files"], dict):
                    raise RuntimeError(f"'files' field is not an object, got {type(data['files']).__name__}")
                return data
        except Exception as e:
            last_err = e
            print(f"[Update] Fetch manifest attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                sleep(1 * attempt)
    raise last_err


def _can_reach_server(update_url, timeout=2.0):
    """
    快速预检：用原生 socket 判断 UPDATE_URL 对应 host:port 是否可达。
    目的是在断网/网卡禁用/服务器完全宕机时，2 秒内快速跳过更新检查，
    避免进入 3 次 × 10 秒 = 33 秒的 manifest 下载重试，阻塞 splash。
    返回 True 表示"可能可达"（仅 TCP 层通，不代表 HTTP 层一定正常），
    返回 False 表示明确不可达。
    """
    try:
        from urllib.parse import urlparse
        u = urlparse(update_url if update_url.endswith("/") else update_url + "/")
        host = u.hostname
        if not host:
            return True  # 无效 URL，交给上层再判定
        if u.scheme == "https":
            port = u.port or 443
        elif u.scheme == "http":
            port = u.port or 80
        else:
            return True  # 未知协议跳过预检
        # socket.create_connection = DNS + TCP SYN，timeout 内快速失败
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.gaierror,         # DNS 解析失败（域名不存在）
            socket.timeout,          # DNS/TCP 超时
            TimeoutError,            # 部分平台的超时别名
            ConnectionRefusedError,  # host 可达但端口没开
            OSError):                # 网卡禁用、无路由、网线拔掉等(10051/ENETUNREACH)
        return False
    except Exception:
        return True  # 预检自身异常时不拦截，交由上层 HTTP 请求兜底


def _url_head_ok(url, timeout=5.0, max_retries=2):
    """
    轻量 HTTP HEAD 探测，用于在批量下载前验证「远端版本目录是否真实存在」。
    —— 避免服务器只更新了 manifest 但忘了同步 GreaterWMS-{version}-{Platform}/ 文件夹时，
       触发 _download 对 404 文件 3×60s 重试，splash 卡死近 3 分钟。
    返回 (ok: bool, reason: str)。
    """
    last_reason = ""
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(
                url, method="HEAD", headers={"User-Agent": "GreaterWMS-Updater"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", 200)
                if 200 <= status < 300:
                    return True, f"HTTP {status}"
                last_reason = f"HTTP {status}"
        except urllib.error.HTTPError as e:
            last_reason = f"HTTP {e.code}"
            if e.code == 404:
                return False, last_reason  # 404 无需重试，立即判定"文件夹不存在"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_reason = f"{type(e).__name__}"
        except Exception as e:
            last_reason = f"{type(e).__name__}: {str(e)[:40]}"
        if attempt < max_retries:
            sleep(1)
    return False, last_reason


def _generate_update_script(app_dir, temp_dir, to_delete, manifest_name=None,
                           new_exe_path=None):
    """
    生成更新脚本（update.bat / update.sh），返回脚本路径。

    参数：
      - new_exe_path：远端版本号对应的新 exe 的绝对路径（例如
         {app_dir}/GreaterWMS-3.0.1-Windows.exe）。当版本升级导致 exe 名
        包含版本号变化时，必须传该值；否则 bat 最后仍会 start 旧版本
        号的 exe（sys.executable），导致重启后内置 version 仍是旧值
        → 再次判定更新 → 死循环（用户看到"闪退"）。
    """
    is_win = sys.platform == "win32"
    exe_name = os.path.basename(sys.executable)
    exe_path = sys.executable
    # 优先启动新 exe（版本号变化时新 exe 是另一个文件），否则回退到当前 exe
    target_exe_path = new_exe_path if new_exe_path and os.path.isabs(new_exe_path) else exe_path
    target_exe_name = os.path.basename(target_exe_path)

    if is_win:
        script_path = os.path.join(app_dir, "update.bat")
        lines = ["@echo off"]
        lines.append(f':wait')
        # 用临时文件中转，避免 tasklist|find 管道死锁（CREATE_NO_WINDOW 下 find stdin 卡 EOF）
        lines.append(f'tasklist /fi "imagename eq {exe_name}" >"%TEMP%\\_bomiot_wait.tmp" 2>nul')
        lines.append(f'find /i "{exe_name}" "%TEMP%\\_bomiot_wait.tmp" >nul 2>nul')
        lines.append(f'if not errorlevel 1 ( del "%TEMP%\\_bomiot_wait.tmp" >nul 2>nul & ping -n 2 127.0.0.1 >nul 2>nul & goto wait )')
        lines.append(f'del "%TEMP%\\_bomiot_wait.tmp" >nul 2>nul')
        lines.append(f'xcopy /Y /S /E /I "{temp_dir}" "{app_dir}" >nul 2>nul')
        # 显式双保险：服务器 manifest 覆盖本地 manifest
        if manifest_name:
            lines.append(f'copy /Y "{os.path.join(temp_dir, manifest_name)}" "{os.path.join(app_dir, manifest_name)}" >nul 2>nul')
        lines.append(f'rd /S /Q "{temp_dir}" 2>nul')
        for f in to_delete:
            lines.append(f'del /F /Q "{os.path.join(app_dir, f)}" 2>nul')
        # 先启动新 exe（target_exe_path），再用 ping 做 3s 延迟后删掉旧 exe（仅当新 exe 名 != 旧 exe 名时才需要删旧版）
        #   - 不直接重命名旧 exe（文件占用可能失败）
        #   - 不在 xcopy 之前删（旧 exe 正在运行）
        lines.append(f'start "" /MIN "{target_exe_path}"')
        if target_exe_name.lower() != exe_name.lower():
            lines.append(f'ping -n 4 127.0.0.1 >nul 2>nul')
            lines.append(f'del /F /Q "{exe_path}" 2>nul')
        lines.append(f'del "%~f0"')
        with open(script_path, "w", encoding="utf-8") as f:
            f.write("\r\n".join(lines))
    else:
        script_path = os.path.join(app_dir, "update.sh")
        lines = ["#!/bin/bash"]
        lines.append(f'while pgrep -f "{exe_path}" > /dev/null 2>&1; do sleep 1; done')
        lines.append(f'cp -rf "{temp_dir}"/* "{app_dir}"/')
        # 显式双保险：服务器 manifest 覆盖本地 manifest
        if manifest_name:
            lines.append(f'cp -f "{os.path.join(temp_dir, manifest_name)}" "{os.path.join(app_dir, manifest_name)}" 2>/dev/null')
        lines.append(f'rm -rf "{temp_dir}"')
        for f in to_delete:
            lines.append(f'rm -f "{os.path.join(app_dir, f)}"')
        lines.append(f'nohup "{target_exe_path}" > /dev/null 2>&1 &')
        if target_exe_name.lower() != exe_name.lower():
            lines.append(f'sleep 3')
            lines.append(f'rm -f "{exe_path}" 2>/dev/null')
        lines.append(f'rm -- "$0"')
        with open(script_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        os.chmod(script_path, 0o755)

    return script_path


def check_update(status_label=None):
    """
    检查并执行增量更新。
    返回 True 表示已触发更新（调用方应退出），False 表示无需更新。
    """
    app_dir = _app_dir()
    if not UPDATE_URL or not UPDATE_URL.strip():
        print("[Update] UPDATE_URL is empty, update check skipped")
        return False
    _os, _arch, _display = _detect_platform()
    manifest_name = f"manifest-{_os}-{_arch}.json"
    print(f"[Update] Detected platform: {_os} {_arch} ({_display})")
    print(f"[Update] Manifest file name: {manifest_name}")
    print(f"[Update] Manifest URL: {UPDATE_URL}{manifest_name}")

    # 读本地 manifest（和远端服务器用同一个文件名）
    local_manifest_path = os.path.join(app_dir, manifest_name)
    if not os.path.exists(local_manifest_path):
        return False  # 没有 manifest，跳过
    try:
        with open(local_manifest_path, encoding="utf-8") as f:
            local_manifest = json.load(f)
    except Exception:
        return False

    # 读 .gitignore 规则
    ignore_patterns = _read_gitignore(app_dir)

    # ========= 快速网络预检（2s，避免断网卡 33s）=========
    if status_label:
        status_label.config(text="正在检查更新...")
        status_label.update()
    if not _can_reach_server(UPDATE_URL, timeout=2.0):
        err_msg = "更新检查失败：网络不可达，跳过"
        print(f"[Update] {err_msg} (server unreachable, pre-check 2s)")
        if status_label:
            status_label.config(text=err_msg)
            status_label.update()
        return False

    # 下载远端 manifest（和本地产物用同一个文件名）
    manifest_url = f"{UPDATE_URL}{manifest_name}"
    print(f"[Update] Downloading remote manifest: {manifest_url}")
    try:
        import time as _t
        _t0 = _t.time()
        remote_manifest = _fetch_manifest(manifest_url, max_retries=3)
        _size_kb = len(json.dumps(remote_manifest, ensure_ascii=False)) / 1024
        _elapsed = _t.time() - _t0
        print(f"[Update] Remote manifest downloaded: {_size_kb:.1f}KB ({_elapsed:.1f}s)")
    except urllib.error.HTTPError as e:
        # HTTP 层面的错误（404、500 等），服务器未部署或临时故障
        err_msg = f"更新检查失败：HTTP {e.code}，跳过"
        print(f"[Update] {err_msg}")
        if status_label:
            status_label.config(text=err_msg)
            status_label.update()
        return False
    except urllib.error.URLError as e:
        # 网络层错误（DNS 失败、连接超时、无网络等）
        reason = str(e.reason)[:40]
        err_msg = f"更新检查失败：网络异常，跳过"
        print(f"[Update] {err_msg} ({reason})")
        if status_label:
            status_label.config(text=err_msg)
            status_label.update()
        return False
    except (TimeoutError, OSError) as e:
        # 直接抛出的 socket 级异常（部分 urllib 版本不包进 URLError）
        # e.g. socket.timeout / ConnectionRefusedError / ENETUNREACH(10051)
        reason = f"{type(e).__name__}: {str(e)[:40]}"
        err_msg = f"更新检查失败：网络异常，跳过"
        print(f"[Update] {err_msg} ({reason})")
        if status_label:
            status_label.config(text=err_msg)
            status_label.update()
        return False
    except Exception as e:
        # 其它：空响应、非JSON内容、缺字段、超时重试耗尽
        reason = str(e)[:60]
        err_msg = f"更新检查失败：服务器无响应，跳过"
        print(f"[Update] {err_msg} ({reason})")
        if status_label:
            status_label.config(text=err_msg)
            status_label.update()
        return False

    # 版本号快速相等跳过（服务器 manifest 为最终真源，不做 >/< 方向判断，支持版本回滚）
    # —— 仅当"远端版本号 == 编译进 exe 的硬编码版本号"时，视为无变化，直接跳过，
    #    避免 1-10s 的本地 SHA256 全量扫描（日常 95% 场景命中）。
    #    其余任何情况（远端更高 = 升级 / 远端更低 = 回滚 / 版本一致但文件怀疑损坏）
    #    一律进入 hash 比对，以远端 manifest.files 为基准对齐。
    if remote_manifest.get("app_name") != app_name:
        return False
    _remote_ver = remote_manifest.get("version", "0")
    if _remote_ver == version:
        print(f"[Update] Version matches (binary {version} == remote {_remote_ver}), skipping hash scan")
        if status_label:
            status_label.config(text="已是最新版本")
            status_label.update()
        return False

    remote_version = _remote_ver
    remote_files = remote_manifest.get("files", {})
    # 文件下载 base: {UPDATE_URL}GreaterWMS-{version}-{Platform}/
    # 注：回滚场景（远端版本 < binary 版本）下拼接出的是旧版本目录，服务器需保留对应版本文件夹
    file_base_url = f"{UPDATE_URL}{app_name}-{remote_version}-{_display}/"

    _local_ver = local_manifest.get("version", "?")
    if _remote_ver < version:
        _direction = "rollback"
    else:
        _direction = "upgrade"
    if status_label:
        status_label.config(text=f"发现新版本 {remote_version}（{_direction}），正在更新...")
        status_label.update()

    print(f"[Update] {_direction} needed: binary={version} local_manifest={_local_ver} remote={remote_version}")

    # ================================================================
    # 比对：双 manifest 交集模型（remote.files = A；local.files = B）
    #   A ∩ B 且 hash(A) != hash(B)  → 下载更新（交集）
    #   A − B （远端声明、本地没有）    → 下载新增（如新版本 exe）
    #   B − A （本地声明、远端已删除）  → 列入 to_delete（如旧版本 exe、CI 已停止产出的 pyd/dll）
    #
    # 用户数据（dbs/ logs/ *.sqlite3 auth_key.py bomiot_ready.lock 等）
    # 本来就不在 local.files（CI 生成 manifest 时走 .gitignore），所以不在 B，
    # 永远不会进入 to_delete → 无需额外 protect-list。
    #
    # 保底：如果本地 manifest 缺 files（老版本、异常格式），退化为「只看远端」
    # 单向模式（不做删除），避免误删。
    # ================================================================
    to_download = []
    to_delete = []
    local_files = local_manifest.get("files") if isinstance(local_manifest, dict) else None
    if isinstance(local_files, dict):
        # ==== 标准路径：双 manifest 双向差分 ====
        A_keys = set(remote_files.keys())
        B_keys = set(local_files.keys())
        # 1) A ∩ B：交集，逐文件比较 hash
        for rel in A_keys & B_keys:
            remote_hash = remote_files[rel]
            local_path = os.path.join(app_dir, rel.replace("/", os.sep))
            # 保护锁：本地 manifest 声明过但运行时被用户删掉了 → 按"缺失"重下
            if not os.path.isfile(local_path):
                to_download.append(rel)
                continue
            try:
                local_hash = _sha256_file(local_path)
            except Exception:
                local_hash = None
            if local_hash != remote_hash:
                to_download.append(rel)
        # 2) A − B：远端新增（本地 manifest 未声明过的新文件）
        for rel in A_keys - B_keys:
            to_download.append(rel)
        # 3) B − A：CI 在上个版本声明过但本次远端 manifest 里消失了 → 视为升级/回滚时移除
        #    同时做一层双保险：这些条目必须同时能通过 _scan_local_files 使用的
        #    .gitignore + manifest-*.json 排除规则，防止 B−A 被恶意 manifest 用来
        #    指鹿为马删除用户自定义文件。
        protected_prefix = ("dbs/", "logs/", "__pycache__/")
        for rel in B_keys - A_keys:
            # 永远不删 manifest-*.json / update.* / 已知运行时目录前缀
            basename = os.path.basename(rel)
            if basename in ("update.bat", "update.sh", "manifest.json"):
                continue
            if basename.startswith("manifest-") and basename.endswith(".json"):
                continue
            rel_norm = rel.replace("\\", "/")
            skip_prefix = False
            for p in protected_prefix:
                if rel_norm.startswith(p) or ("/" + p).rstrip("/") + "/" in "/" + rel_norm:
                    skip_prefix = True
                    break
            if skip_prefix:
                continue
            # 再用 .gitignore 过滤一遍（用户自己加的忽略规则在 B−A 这里不删）
            if _is_ignored(rel_norm, ignore_patterns):
                continue
            # 最终保险：只有当本地真的存在这个被声明过的路径时才删
            local_path = os.path.join(app_dir, rel.replace("/", os.sep))
            if os.path.isfile(local_path):
                to_delete.append(rel)
    else:
        # ==== 退化路径：本地 manifest 无 files → 单向只看远端（不删任何东西）====
        print("[Update] local manifest missing 'files', falling back to one-way compare (no delete)")
        for rel, remote_hash in remote_files.items():
            local_path = os.path.join(app_dir, rel.replace("/", os.sep))
            if not os.path.isfile(local_path):
                to_download.append(rel)
                continue
            try:
                local_hash = _sha256_file(local_path)
            except Exception:
                local_hash = None
            if local_hash != remote_hash:
                to_download.append(rel)

    print(f"[Update] diff stats: to_download={len(to_download)}  to_delete(B−A)={len(to_delete)}  "
          f"(remote.files={len(remote_files)}  local.files={len(local_files) if isinstance(local_files, dict) else 'N/A'})")

    if not to_download and not to_delete:
        return False  # 没有实际变化

    # 下载变化的文件到临时目录
    temp_dir = tempfile.mkdtemp(prefix="bomiot_update_")

    # ========= 前置探测：远端版本目录是否真实存在 =========
    # 防止服务器只更新了 manifest 但忘了同步 GreaterWMS-{version}-{Platform}/ 文件夹，
    # 否则会在首个文件 404 时触发 3×60s 下载重试卡死 splash。
    if to_download:
        _probe_url = file_base_url + to_download[0]
        _ok, _reason = _url_head_ok(_probe_url, timeout=5.0, max_retries=2)
        if not _ok:
            shutil.rmtree(temp_dir, ignore_errors=True)
            if _reason == "HTTP 404":
                err_msg = f"服务器版本目录不存在（{remote_version}），跳过更新"
            else:
                err_msg = f"更新文件探测失败（{_reason}），跳过更新"
            print(f"[Update] {err_msg} probe={_probe_url}")
            if status_label:
                status_label.config(text=err_msg)
                status_label.update()
            return False
        print(f"[Update] Remote version folder verified via HEAD: {to_download[0]} ({_reason})")

    for path in to_download:
        url = file_base_url + path
        dest = os.path.join(temp_dir, path.replace("/", os.sep))
        try:
            _download(url, dest)
        except Exception as e:
            print(f"下载失败: {path} - {e}")
            # 问题③：下载失败时清理临时目录，避免系统 temp 堆积 bomiot_update_* 垃圾
            shutil.rmtree(temp_dir, ignore_errors=True)
            if status_label:
                status_label.config(text="更新下载失败，跳过")
                status_label.update()
            return False

    if status_label:
        status_label.config(text="更新下载完成，正在应用...")
        status_label.update()

    # 将新版本的 manifest 也写入 temp_dir，随 xcopy/cp 一起覆盖到 app_dir。
    # —— 因为 CI 生成 manifest 时是「先扫目录再写 manifest」，所以远端 files 不包含 manifest 自身。
    #    如果不在此显式写出，重启后本地 manifest 仍是旧版本号，会白跑一次检查周期。
    new_manifest_path = os.path.join(temp_dir, manifest_name)
    try:
        with open(new_manifest_path, "w", encoding="utf-8") as f:
            json.dump(remote_manifest, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # 写 manifest 失败不阻止更新（否则更新失败但旧二进制还在），仅打日志
        print(f"[Update] Warning: failed to write new manifest to temp: {e}")

    # 算出新 exe 在客户端目录里的绝对路径（当 version 或 platform display 变时，
    # exe 名包含这些信息，下载下来就是另一个文件；此时 bat 必须 start 新 exe
    # 才能让内置 version 常量真正更新，否则永远死循环）
    _plat_is_win = sys.platform == "win32"
    if _plat_is_win:
        new_exe_name = f"{app_name}-{remote_version}-{_display}.exe"
    else:
        new_exe_name = f"{app_name}-{remote_version}-{_display}"
    new_exe_path = os.path.join(app_dir, new_exe_name)

    # 生成更新脚本（传 manifest_name 进去，生成显式 copy 行，保证服务器 manifest 覆盖本地）
    script_path = _generate_update_script(
        app_dir, temp_dir, to_delete,
        manifest_name=manifest_name,
        new_exe_path=new_exe_path,
    )

    # 启动脚本（静默：不弹任何 cmd / terminal 黑框）
    is_win = sys.platform == "win32"
    _started_script = False
    _script_err = ""
    try:
        if is_win:
            CREATE_NO_WINDOW          = int(getattr(subprocess, "CREATE_NO_WINDOW",          0x08000000))
            CREATE_NEW_PROCESS_GROUP  = int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP",  0x00000200))
            # 注意：不要加 DETACHED_PROCESS。它会导致子进程（cmd/xcopy）在
            # 无控制台句柄环境下 xcopy 返回 err=4 "系统找不到指定的路径"，
            # 使更新文件无法被复制。CREATE_NO_WINDOW 已足够隐藏窗口。
            flags = CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
            startupinfo = subprocess.STARTUPINFO()
            # STARTF_USESHOWWINDOW = 1，SW_HIDE = 0
            try:
                startupinfo.dwFlags = int(getattr(subprocess, "STARTF_USESHOWWINDOW", 1))
            except Exception:
                startupinfo.dwFlags = 1
            startupinfo.wShowWindow = 0
            subprocess.Popen(
                ["cmd.exe", "/c", script_path],
                cwd=app_dir,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                shell=False,
                startupinfo=startupinfo,
                creationflags=flags,
            )
        else:
            subprocess.Popen(
                ["bash", script_path],
                cwd=app_dir,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                shell=False,
                start_new_session=True,
            )
        _started_script = True
    except Exception as e:
        import traceback as _tb
        _script_err = f"{type(e).__name__}: {e}\n{_tb.format_exc()}"
        print(f"[Update] FATAL: failed to start update script.\n{_script_err}")
        # 失败时把 trace 落盘，方便用户找闪退原因
        try:
            crash_log = os.path.join(app_dir, "update_crash.log")
            with open(crash_log, "a", encoding="utf-8") as f:
                f.write(f"===== {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
                f.write(f"script_path={script_path}\n")
                f.write(_script_err)
                f.write("\n")
        except Exception:
            pass

    if not _started_script:
        # 启动脚本失败：清理残留 + 不执行退出（继续跑 Django 启动，避免闪退+用户完全进不去）
        shutil.rmtree(temp_dir, ignore_errors=True)
        try: os.remove(script_path)
        except Exception: pass
        if status_label:
            status_label.config(text="更新脚本启动失败，跳过（详见 update_crash.log）")
            status_label.update()
        return False

    # 给 bat 子进程 300ms 启动缓冲（防止本进程过快退出，bat 还没起来就被系统把父进程组里的子进程一起 terminate）
    sleep(0.3)
    return True


if __name__ == "__main__":
    # 顶层兜底：任何未被捕获的异常写入 update_crash.log，避免用户只能看到「窗口灭了」没有任何线索
    _app_dir_root = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    _crash_log = os.path.join(_app_dir_root, "update_crash.log")
    import traceback as _tb_main

    def _write_crash(exc_type, exc_val, tb):
        try:
            with open(_crash_log, "a", encoding="utf-8") as f:
                f.write(f"===== UNHANDLED EXCEPTION {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
                f.write(f"frozen={getattr(sys, 'frozen', False)} executable={sys.executable}\n")
                f.write("".join(_tb_main.format_exception(exc_type, exc_val, tb)))
                f.write("\n")
        except Exception:
            pass

    sys.excepthook = _write_crash

    # Welcome page

    splash = tk.Tk()
    window_width = 675
    window_height = 329
    x = int(splash.winfo_screenwidth() / 2 - window_width / 2)
    y = int(splash.winfo_screenheight() / 2 - window_height / 2)
    canvas = tk.Canvas(splash, width=window_width, height=window_height, bg='white', highlightthickness=0)
    canvas.pack()

    splash.title("Welcome to Bomiot")
    splash.geometry(f'675x349+{x}+{y}')
    splash.overrideredirect(True)  # Borderless display
    # Load and scale image (maintain aspect ratio)
    try:
        # Load image using PIL
        image_path = join(getcwd(), 'splash.png')
        pil_img = Image.open(image_path)

        # Get original image dimensions
        img_width, img_height = pil_img.size

        # Calculate scale ratio (maintain aspect ratio)
        scale_width = window_width / img_width
        scale_height = window_height / img_height
        scale = min(scale_width, scale_height)  # Use minimum ratio to ensure image fits entirely within window

        # Calculate scaled dimensions
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)

        # Scale image
        resized_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)  # High quality scaling
        img = ImageTk.PhotoImage(resized_img)

        # Calculate center position for image
        x_pos = (window_width - new_width) // 2
        y_pos = (window_height - new_height) // 2

        # Display image on canvas (centered)
        canvas.create_image(x_pos, y_pos, anchor=tk.NW, image=img)
    except Exception as e:
        print(f"Failed to load image: {e}")
        # Display error text
        canvas.create_text(window_width / 2, window_height / 2, text="Failed to load image", font=("Arial", 12))

    # Force window refresh to ensure splash is displayed before subsequent operations
    splash.update()

    # 增量更新状态标签
    status_label = tk.Label(splash, text="正在检查更新...", font=("Arial", 10), bg='white', fg='#888888')
    status_label.pack(side='bottom', pady=5)
    splash.update()

    # 检查更新（有更新则生成脚本并退出，无更新则继续启动）
    if check_update(status_label):
        splash.destroy()
        sys.exit(0)

    # Set Django environment variables
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bomiot.server.server.settings")
    os.environ.setdefault("RUN_MAIN", "true")
    os.environ.setdefault("IS_LAN", "true")
    os.environ.setdefault('WORKERS', '1')
    lockfile = Path(join(os.path.dirname(sys.executable), 'bomiot_ready.lock'))
    if lockfile.exists():
        lockfile.unlink()
    import django

    django.setup()

    auth_key_path = Path(join(os.path.dirname(sys.executable), 'auth_key.py'))
    if auth_key_path.exists():
        auth_key_path.unlink()
    while True:
        community_key, sponsor_key = encrypt_info()
        if '/' in community_key or '/' in sponsor_key:
            continue
        else:
            break
    with open(auth_key_path, "w", encoding="utf-8") as f:
        f.write(f'COMMUNITY_KEY = "{community_key}"\n')
        f.write(f'SPONSOR_KEY = "{sponsor_key}"\n')

    from django.core.management import call_command
    from django.apps import apps
    from django.contrib.auth import get_user_model

    # Prepare makemigrations command arguments
    cmd_args = ["makemigrations"]

    # Auto-detect all apps with models
    apps_with_models = []
    for app_config in apps.get_app_configs():
        try:
            if app_config.models_module:
                models = apps.get_app_config(app_config.label).get_models()
                if models:
                    apps_with_models.append(app_config.label)
        except Exception:
            continue

    if apps_with_models:
        cmd_args.extend(apps_with_models)

    # Execute makemigrations command
    try:
        call_command(*cmd_args)
        print("Migrations created successfully.")
    except Exception as e:
        print(f"Error creating migrations: {e}")

    # Execute migrate command
    try:
        call_command('migrate')
    except Exception as e:
        print(f"Error during migration: {e}")

    for app_config in apps.get_app_configs():
        try:
            app_config.ready()
        except Exception:
            pass

    # Execute makemigrations command again
    try:
        call_command(*cmd_args)
        print("Migrations created successfully.")
    except Exception as e:
        print(f"Error creating migrations: {e}")

    # Execute migrate command again
    try:
        call_command('migrate')
    except Exception as e:
        print(f"Error during migration: {e}")

    # Keep welcome page displayed for a while (original logic: 10 seconds)
    print('System is starting up')

    # Start Django development server
    # ---- port auto-increment: if 8008 is taken, try 8009, 8010, ... up to 100 ports ----
    port = _find_available_port(port)

    print('System started successfully')
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    ip = s.getsockname()[0]
    print('Local IP address:', ip)
    s.close()
    baseurl = "http://" + ip + ":" + str(port)
    print('Opening browser at:', baseurl)


    def run_server():
        while True:
            try:
                response = requests.get(url=baseurl, timeout=2)
                print(response.status_code)
                sleep(2)
                webbrowser.open(baseurl)
                break
            except:
                print("Server not ready yet, retrying...")
                sleep(0.5)
                continue


    run_server_thread = threading.Thread(target=run_server, daemon=True)
    run_server_thread.start()

    # Manually destroy the welcome page before starting uvicorn
    splash.destroy()

    uvicorn.run(
        "bomiot_asgi:application",
        host='0.0.0.0',
        port=port,
        workers=1,
        log_level="info",
        uds=None,
        ssl_keyfile=None,
        ssl_certfile=None,
        proxy_headers=True,
        http="httptools",
        server_header=False,
        limit_concurrency=1000,
        backlog=128,
        timeout_keep_alive=5,
        timeout_graceful_shutdown=30,
        loop="auto",
    )


