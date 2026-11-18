"""deploy_check.py —— 部署前验收检查（CSDN《AI 交付的验收标准》配套仓库）

用法: python deploy_check.py <代码目录> [--port PORT]
每条检查输出 [PASS]/[FAIL] + 期望/实际；任何一条不过，退出码 1。
在 CHECKS 里追加你自己的验收条件。仅用标准库。
"""
import os
import py_compile
import re
import socket
import sys

SECRET = re.compile(
    r"(?i)(password|passwd|secret|appkey|api[_-]?key|token)\s*[:=]\s*['\"][^'\"]{6,}"
)


def check_syntax(target):
    bad = []
    for root, _, files in os.walk(target):
        for f in files:
            if f.endswith(".py"):
                p = os.path.join(root, f)
                try:
                    py_compile.compile(p, doraise=True)
                except py_compile.PyCompileError as e:
                    bad.append(f"{p}: {e.msg}")
    if bad:
        return False, f"期望全部 .py 可编译，实际 {len(bad)} 处失败：" + "；".join(bad[:3])
    return True, "全部 .py 编译通过"


def check_secrets(target):
    hits = []
    for root, _, files in os.walk(target):
        for f in files:
            if f.endswith((".py", ".js", ".ts", ".json", ".yaml", ".yml", ".ini", ".env")):
                p = os.path.join(root, f)
                try:
                    text = open(p, encoding="utf-8", errors="ignore").read()
                except OSError:
                    continue
                for m in SECRET.finditer(text):
                    hits.append(f"{p}:{text[:m.start()].count(chr(10)) + 1}")
    if hits:
        return False, f"期望 0 处硬编码凭据，实际 {len(hits)} 处：" + "；".join(hits[:3])
    return True, "未发现硬编码凭据"


def check_port(port):
    if port is None:
        return True, "未启用端口检查（--port 可开启）"
    s = socket.socket()
    s.settimeout(3)
    try:
        s.connect(("127.0.0.1", port))
        return True, f"期望端口 {port} 监听，实际在监听"
    except OSError:
        return False, f"期望端口 {port} 监听，实际未监听"
    finally:
        s.close()


def main():
    args = sys.argv[1:]
    target = args[0] if args and not args[0].startswith("--") else "."
    port = None
    if "--port" in args:
        port = int(args[args.index("--port") + 1])

    checks = [
        ("语法", lambda: check_syntax(target)),
        ("无硬编码凭据", lambda: check_secrets(target)),
        ("服务端口", lambda: check_port(port)),
    ]
    failed = 0
    for name, fn in checks:
        ok, detail = fn()
        print(f"[{'PASS' if ok else 'FAIL'}] {name}：{detail}")
        failed += 0 if ok else 1
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()