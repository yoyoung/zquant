"""
强制停止所有运行在8000端口的服务（非交互式）
"""

import subprocess
import sys
import os

# 修复 Windows 控制台中文输出乱码问题
if sys.platform == "win32":
    try:
        # 设置控制台代码页为 UTF-8
        os.system("chcp 65001 >nul 2>&1")
        # 设置环境变量
        os.environ["PYTHONIOENCODING"] = "utf-8"
    except:
        pass


def get_processes_on_port(port):
    """获取监听指定端口的进程"""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            encoding="gbk" if sys.platform == "win32" else "utf-8",
            check=False,
        )

        processes = []
        for line in result.stdout.split("\n"):
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    processes.append(pid)

        return list(set(processes))
    except Exception as e:
        print(f"获取进程列表失败: {e}")
        return []


def kill_process(pid):
    """终止进程"""
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", pid], check=True, capture_output=True)
            return True
        subprocess.run(["kill", "-9", pid], check=True, capture_output=True)
        return True
    except:
        return False


def main():
    port = 8000
    print(f"查找监听端口 {port} 的进程...")

    processes = get_processes_on_port(port)

    if not processes:
        print(f"没有找到监听端口 {port} 的进程")
        return 0

    print(f"找到 {len(processes)} 个进程: {', '.join(processes)}")
    print("正在停止...")

    success_count = 0
    for pid in processes:
        if kill_process(pid):
            print(f"  [OK] 已停止进程 {pid}")
            success_count += 1
        else:
            print(f"  [FAIL] 无法停止进程 {pid}")

    # 等待一下再检查
    import time

    time.sleep(1)

    remaining = get_processes_on_port(port)
    if remaining:
        print(f"\n警告: 仍有进程在监听端口 {port}: {', '.join(remaining)}")
        return 1
    print(f"\n[成功] 端口 {port} 已释放")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
