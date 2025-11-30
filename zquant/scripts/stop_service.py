"""
停止所有运行在8000端口的服务
"""

import subprocess
import sys


def get_processes_on_port(port):
    """获取监听指定端口的进程"""
    try:
        # Windows命令：查找监听指定端口的进程
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

        return list(set(processes))  # 去重
    except Exception as e:
        print(f"获取进程列表失败: {e}")
        return []


def kill_process(pid):
    """终止进程"""
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", pid], check=True)
            return True
        subprocess.run(["kill", "-9", pid], check=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except Exception as e:
        print(f"终止进程 {pid} 失败: {e}")
        return False


def main():
    port = 8000
    print(f"查找监听端口 {port} 的进程...")

    processes = get_processes_on_port(port)

    if not processes:
        print(f"没有找到监听端口 {port} 的进程")
        return 0

    print(f"找到 {len(processes)} 个进程:")
    for pid in processes:
        print(f"  PID: {pid}")

    # 非交互模式：直接停止
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("\n[强制模式] 直接停止所有进程...")
    else:
        print("\n是否要停止这些进程? (y/n): ", end="")
        try:
            choice = input().strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\n已取消（使用 --force 参数可跳过确认）")
            return 1

        if choice != "y":
            print("已取消")
            return 1

    print("\n正在停止进程...")
    success_count = 0
    for pid in processes:
        if kill_process(pid):
            print(f"  [OK] 已停止进程 {pid}")
            success_count += 1
        else:
            print(f"  [FAIL] 无法停止进程 {pid}")

    print(f"\n已停止 {success_count}/{len(processes)} 个进程")

    # 再次检查
    remaining = get_processes_on_port(port)
    if remaining:
        print(f"\n警告: 仍有 {len(remaining)} 个进程在监听端口 {port}")
        print("  进程PID:", ", ".join(remaining))
        print("  请手动停止这些进程或重启计算机")
        return 1
    print(f"\n[成功] 端口 {port} 已释放")
    print("现在可以重新启动服务:")
    print("  uvicorn zquant.main:app --reload --host 0.0.0.0 --port 8000")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n已中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
