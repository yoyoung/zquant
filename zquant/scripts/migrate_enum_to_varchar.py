# Copyright 2025 ZQuant Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: kevin
# Contact:
#     - Email: kevin@vip.qq.com
#     - Wechat: zquant2025
#     - Issues: https://github.com/zquant/zquant/issues
#     - Documentation: https://docs.zquant.com
#     - Repository: https://github.com/zquant/zquant

"""
将 ENUM 类型迁移为 VARCHAR 类型
用于更新已存在的数据库表，将 ENUM 列改为 VARCHAR
"""

from pathlib import Path
import sys

# 添加项目根目录到路径
# 脚本位于 zquant/scripts/migrate_enum_to_varchar.py
# 需要将项目根目录（包含 zquant 目录的目录）添加到路径，而不是 zquant 目录本身
script_dir = Path(__file__).resolve().parent  # zquant/scripts
zquant_dir = script_dir.parent  # zquant 目录
project_root = zquant_dir.parent  # 项目根目录（包含 zquant 目录的目录）
sys.path.insert(0, str(project_root))

from sqlalchemy import text

from zquant.database import engine


def migrate_enum_to_varchar():
    """将 ENUM 类型迁移为 VARCHAR 类型"""
    with engine.connect() as conn:
        try:
            # 检查表是否存在
            result = conn.execute(text("SHOW TABLES LIKE 'zq_task_scheduled_tasks'"))
            if not result.fetchone():
                print("[跳过] zq_task_scheduled_tasks 表不存在")
            else:
                # 检查 task_type 列的类型
                result = conn.execute(text("SHOW COLUMNS FROM zq_task_scheduled_tasks WHERE Field = 'task_type'"))
                column_info = result.fetchone()
                if column_info:
                    current_type = column_info[1]
                    if "enum" in current_type.lower():
                        print(f"当前 task_type 类型: {current_type}")
                        print("将 task_type 从 ENUM 改为 VARCHAR(50)...")
                        conn.execute(
                            text("""
                            ALTER TABLE zq_task_scheduled_tasks 
                            MODIFY COLUMN task_type VARCHAR(50) NOT NULL
                        """)
                        )
                        print("[成功] task_type 已更新为 VARCHAR(50)")
                    else:
                        print(f"[跳过] task_type 已经是 VARCHAR 类型: {current_type}")

            # 检查 zq_task_task_executions 表
            result = conn.execute(text("SHOW TABLES LIKE 'zq_task_task_executions'"))
            if not result.fetchone():
                print("[跳过] zq_task_task_executions 表不存在")
            else:
                # 检查 status 列的类型
                result = conn.execute(text("SHOW COLUMNS FROM zq_task_task_executions WHERE Field = 'status'"))
                column_info = result.fetchone()
                if column_info:
                    current_type = column_info[1]
                    if "enum" in current_type.lower():
                        print(f"当前 status 类型: {current_type}")
                        print("将 status 从 ENUM 改为 VARCHAR(20)...")
                        conn.execute(
                            text("""
                            ALTER TABLE zq_task_task_executions 
                            MODIFY COLUMN status VARCHAR(20) NOT NULL
                        """)
                        )
                        print("[成功] status 已更新为 VARCHAR(20)")
                    else:
                        print(f"[跳过] status 已经是 VARCHAR 类型: {current_type}")

            conn.commit()
            print("\n[完成] 迁移完成！")
            return True

        except Exception as e:
            print(f"[错误] 迁移失败: {e}")
            import traceback

            traceback.print_exc()
            conn.rollback()
            return False


if __name__ == "__main__":
    print("=" * 60)
    print("将 ENUM 类型迁移为 VARCHAR 类型")
    print("=" * 60)
    print("\n注意：")
    print("  - 此脚本会将 zq_task_scheduled_tasks.task_type 从 ENUM 改为 VARCHAR(50)")
    print("  - 此脚本会将 zq_task_task_executions.status 从 ENUM 改为 VARCHAR(20)")
    print("  - 现有数据会自动保留")
    print()

    try:
        if migrate_enum_to_varchar():
            print("\n[成功] 迁移完成！")
            sys.exit(0)
        else:
            print("\n[失败] 迁移失败！")
            sys.exit(1)
    except Exception as e:
        print(f"\n[失败] 执行出错: {e}")
        sys.exit(1)
