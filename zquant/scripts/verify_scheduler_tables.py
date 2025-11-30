"""
验证定时任务表是否存在
"""

from pathlib import Path
import sys

# 添加项目根目录到路径
# 脚本位于 zquant/scripts/verify_scheduler_tables.py
# 需要将项目根目录（包含 zquant 目录的目录）添加到路径，而不是 zquant 目录本身
script_dir = Path(__file__).resolve().parent  # zquant/scripts
zquant_dir = script_dir.parent  # zquant 目录
project_root = zquant_dir.parent  # 项目根目录（包含 zquant 目录的目录）
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from zquant.database import engine


def verify_tables():
    """验证表是否存在"""
    with engine.connect() as conn:
        # 检查zq_task_scheduled_tasks表
        result = conn.execute(text("SHOW TABLES LIKE 'zq_task_scheduled_tasks'"))
        if result.fetchone():
            print("[OK] zq_task_scheduled_tasks table exists")
        else:
            print("[ERROR] zq_task_scheduled_tasks table does not exist")

        # 检查zq_task_task_executions表
        result2 = conn.execute(text("SHOW TABLES LIKE 'zq_task_task_executions'"))
        if result2.fetchone():
            print("[OK] zq_task_task_executions table exists")
        else:
            print("[ERROR] zq_task_task_executions table does not exist")


if __name__ == "__main__":
    verify_tables()
