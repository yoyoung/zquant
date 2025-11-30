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
定时任务系统初始化脚本

整合了以下功能：
1. 创建数据库表（zq_task_scheduled_tasks 和 zq_task_task_executions）
2. 创建示例任务（5个基础示例任务）
3. 创建编排任务示例（3个编排任务示例）
4. 创建ZQuant任务（8个ZQuant数据同步任务）

使用方法：
    python scripts/init_scheduler.py                    # 默认：建表+创建ZQuant任务
    python scripts/init_scheduler.py --all             # 执行所有步骤（表+示例+编排+ZQuant）
    python scripts/init_scheduler.py --tables-only     # 只创建表
    python scripts/init_scheduler.py --examples-only   # 只创建示例任务
    python scripts/init_scheduler.py --workflow-only   # 只创建编排任务
    python scripts/init_scheduler.py --zquant-only      # 只创建ZQuant任务
    python scripts/init_scheduler.py --force            # 强制重新创建（删除已存在的任务）
"""

import argparse
from pathlib import Path
import sys

# 添加项目根目录到路径
# 脚本位于 zquant/scripts/init_scheduler.py
# 需要将项目根目录（包含 zquant 目录的目录）添加到路径，而不是 zquant 目录本身
script_dir = Path(__file__).resolve().parent  # zquant/scripts
zquant_dir = script_dir.parent  # zquant 目录
project_root = zquant_dir.parent  # 项目根目录（包含 zquant 目录的目录）
sys.path.insert(0, str(project_root))

from loguru import logger
from sqlalchemy import text
from sqlalchemy.orm import Session

from zquant.database import SessionLocal, engine
from zquant.models.scheduler import ScheduledTask, TaskType
from zquant.services.scheduler import SchedulerService


def create_tables():
    """创建定时任务相关表"""
    logger.info("开始创建数据库表...")
    try:
        with engine.connect() as conn:
            # 创建scheduled_tasks表
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS zq_task_scheduled_tasks (
                    id INTEGER AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    job_id VARCHAR(100) NOT NULL UNIQUE,
                    task_type VARCHAR(50) NOT NULL,
                    cron_expression VARCHAR(100),
                    interval_seconds INTEGER,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    paused BOOLEAN NOT NULL DEFAULT FALSE,
                    description TEXT,
                    config_json TEXT,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    retry_interval INTEGER NOT NULL DEFAULT 60,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_name (name),
                    INDEX idx_job_id (job_id),
                    INDEX idx_task_type (task_type),
                    INDEX idx_enabled (enabled),
                    INDEX idx_paused (paused)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            )

            # 创建task_executions表
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS zq_task_task_executions (
                    id INTEGER AUTO_INCREMENT PRIMARY KEY,
                    task_id INTEGER NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    duration_seconds INTEGER,
                    result_json TEXT,
                    error_message TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_task_id (task_id),
                    INDEX idx_status (status),
                    INDEX idx_start_time (start_time)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            )

            conn.commit()
            logger.info("✓ 数据库表创建成功！")
            return True
    except Exception as e:
        logger.error(f"✗ 创建数据库表失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def _create_single_task(db: Session, task_config: dict, skip_tasks: set, existing_names: set) -> tuple[bool, bool]:
    """
    创建单个任务的辅助函数

    Args:
        db: 数据库会话
        task_config: 任务配置字典，包含以下字段:
            - name: 任务名称
            - cron_expression: Cron表达式（可选）
            - description: 任务描述
            - config: 任务配置
            - max_retries: 最大重试次数（默认3）
            - retry_interval: 重试间隔（默认300）
            - enabled: 是否启用（默认True）
        skip_tasks: 需要跳过的任务名称集合
        existing_names: 已存在的任务名称集合

    Returns:
        (是否创建成功, 是否跳过)
    """
    name = task_config["name"]

    # 检查是否需要跳过
    if name in skip_tasks:
        logger.info(f"⊘ 跳过任务: {name}（在SKIP_TASKS配置中）")
        return False, True

    # 检查是否已存在
    if name in existing_names:
        logger.info(f"○ 任务已存在: {name}")
        return False, False

    # 创建任务
    try:
        # 根据任务名称判断任务类型：包含"STEP"的为通用任务，否则为手动任务
        is_manual_task = "STEP" not in name
        task_type = TaskType.MANUAL_TASK if is_manual_task else TaskType.COMMON_TASK
        
        # 手动任务不设置调度参数
        cron_expression = None if is_manual_task else task_config.get("cron_expression")
        interval_seconds = None if is_manual_task else task_config.get("interval_seconds")
        
        # 手动任务默认不启用
        enabled = task_config.get("enabled", False) if is_manual_task else task_config.get("enabled", True)
        
        task = SchedulerService.create_task(
            db=db,
            name=name,
            task_type=task_type,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            description=task_config.get("description", ""),
            config=task_config.get("config", {}),
            max_retries=task_config.get("max_retries", 3),
            retry_interval=task_config.get("retry_interval", 300),
            enabled=enabled,
        )
        task_type_label = "手动任务" if is_manual_task else "通用任务"
        logger.info(f"✓ 创建任务: {name} (ID: {task.id}, 类型: {task_type_label})")
        return True, False
    except Exception as e:
        if "Duplicate entry" in str(e) or "1062" in str(e):
            logger.info(f"○ 任务已存在: {name}（数据库中存在）")
            return False, False
        raise


def create_zquant_tasks(force: bool = False):
    """创建ZQuant任务"""
    logger.info("开始创建ZQuant任务...")
    db: Session = SessionLocal()

    try:
        # ========== 配置：需要跳过的任务列表 ==========
        # 在此列表中添加任务名称，这些任务将不会被初始化
        SKIP_TASKS = {
            "示例任务-快速测试",
            "示例任务-每分钟",
            "示例任务-每日18点",
            "示例任务-已禁用",
            "示例任务-实时进度演示",
            "示例任务-命令执行",
            "同步所有股票日线数据-数据库任务",
        }
        # ============================================

        # 如果强制模式，先删除已存在的示例任务
        if force:
            existing_tasks = db.query(ScheduledTask).filter(ScheduledTask.name.like("示例任务-%")).all()
            for task in existing_tasks:
                db.delete(task)
            db.commit()
            logger.info(f"已删除 {len(existing_tasks)} 个已存在的示例任务")

        # 定义所有任务配置
        task_configs = [
            {
                "name": "STEP1-同步交易日历（当日）-命令执行",
                "cron_expression": "0 2 * * *",  # 每天凌晨2点执行
                "description": "使用命令执行方式同步交易日历数据，每天自动更新交易日历",
                "config": {"command": "python zquant/scheduler/job/sync_trading_calendar.py", "timeout_seconds": 600},
                "max_retries": 3,
                "retry_interval": 300,
                "enabled": True,
            },
            {
                "name": "STEP2-同步股票列表（当日）-命令执行",
                "cron_expression": "0 1 * * *",  # 每天凌晨1点执行
                "description": "使用命令执行方式同步股票列表数据，每天自动更新股票基础信息",
                "config": {"command": "python zquant/scheduler/job/sync_stock_list.py", "timeout_seconds": 300},
                "max_retries": 3,
                "retry_interval": 300,
                "enabled": True,
            },
            {
                "name": "STEP3-同步日线数据（当日）-命令执行",
                "cron_expression": "0 18 * * *",  # 每天收盘后18:00执行
                "description": "使用命令执行方式同步所有股票的日线数据，每天收盘后自动更新日线数据",
                "config": {"command": "python zquant/scheduler/job/sync_daily_data.py", "timeout_seconds": 3600},
                "max_retries": 3,
                "retry_interval": 600,
                "enabled": True,
            },
            {
                "name": "STEP4-同步所有股票日线数据（当日）-数据库任务",
                "cron_expression": "0 18 * * *",  # 每天收盘后18:00执行
                "description": "使用数据库任务方式同步所有股票的日线数据，每天收盘后自动更新（按 ts_code 分表存储）",
                "config": {
                    "task_action": "sync_all_daily_data",
                    "start_date": None,  # None 表示使用默认（最近一年）
                    "end_date": None,  # None 表示使用默认（当天）
                },
                "max_retries": 3,
                "retry_interval": 600,
                "enabled": True,
            },
            {
                "name": "STEP4-同步每日指标数据（当日）-命令执行",
                "cron_expression": "0 18 * * *",  # 每天收盘后18:00执行
                "description": "使用命令执行方式同步所有股票的每日指标数据，每天收盘后自动更新",
                "config": {"command": "python zquant/scheduler/job/sync_daily_basic_data.py", "timeout_seconds": 3600},
                "max_retries": 3,
                "retry_interval": 600,
                "enabled": True,
            },
            {
                "name": "同步日线数据-命令执行（时间段）",
                "description": "使用命令执行方式同步历史日线数据，从20250101开始，用于历史数据补全",
                "config": {
                    "command": "python zquant/scheduler/job/sync_daily_data.py --start-date 20250101",
                    "timeout_seconds": 7200,
                },
                "max_retries": 3,
                "retry_interval": 1800,
                "enabled": False,  # 手动任务默认禁用
            },
            {
                "name": "同步每日指标数据-命令执行（时间段）",
                "description": "使用命令执行方式同步历史每日指标数据，从20250101开始，用于历史数据补全",
                "config": {
                    "command": "python zquant/scheduler/job/sync_daily_basic_data.py --start-date 20250101",
                    "timeout_seconds": 7200,
                },
                "max_retries": 3,
                "retry_interval": 1800,
                "enabled": False,  # 手动任务默认禁用
            },
            {
                "name": "STEP5-同步财务数据-利润表-命令执行",
                "cron_expression": "0 2 1 * *",  # 每月1号凌晨2点执行
                "description": "使用命令执行方式同步所有股票的财务数据（利润表），每月自动更新",
                "config": {
                    "command": "python zquant/scheduler/job/sync_financial_data.py --statement-type income",
                    "timeout_seconds": 7200,
                },
                "max_retries": 3,
                "retry_interval": 1800,
                "enabled": True,
            },
            {
                "name": "STEP6-数据表统计-命令执行",
                "cron_expression": "0 3 * * *",  # 每天凌晨3点执行（在数据同步之后）
                "description": "使用命令执行方式统计每日数据表中的数据入库情况，每天自动统计当天的数据",
                "config": {"command": "python zquant/scheduler/job/sync_table_statistics.py", "timeout_seconds": 1800},
                "max_retries": 3,
                "retry_interval": 600,
                "enabled": True,
            },
            {
                "name": "STEP7-同步因子数据（当日）-命令执行",
                "cron_expression": "0 18 * * *",  # 每天收盘后18:00执行
                "description": "使用命令执行方式同步所有股票的因子数据，每天收盘后自动更新（按 ts_code 分表存储）",
                "config": {"command": "python zquant/scheduler/job/sync_factor_data.py", "timeout_seconds": 3600},
                "max_retries": 3,
                "retry_interval": 600,
                "enabled": True,
            },
            {
                "name": "STEP8-同步专业版因子数据（当日）-命令执行",
                "cron_expression": "0 18 * * *",  # 每天收盘后18:00执行
                "description": "使用命令执行方式同步所有股票的专业版因子数据，每天收盘后自动更新（按 ts_code 分表存储）",
                "config": {"command": "python zquant/scheduler/job/sync_stkfactorpro_data.py", "timeout_seconds": 3600},
                "max_retries": 3,
                "retry_interval": 600,
                "enabled": True,
            },
            {
                "name": "同步因子数据-命令执行（时间段）",
                "description": "使用命令执行方式同步历史因子数据，从20250101开始，用于历史数据补全",
                "config": {
                    "command": "python zquant/scheduler/job/sync_factor_data.py --start-date 20250101",
                    "timeout_seconds": 7200,
                },
                "max_retries": 3,
                "retry_interval": 1800,
                "enabled": False,  # 手动任务默认禁用
            },
            {
                "name": "同步专业版因子数据-命令执行（时间段）",
                "description": "使用命令执行方式同步历史专业版因子数据，从20250101开始，用于历史数据补全",
                "config": {
                    "command": "python zquant/scheduler/job/sync_stkfactorpro_data.py --start-date 20250101",
                    "timeout_seconds": 7200,
                },
                "max_retries": 3,
                "retry_interval": 1800,
                "enabled": False,  # 手动任务默认禁用
            },
        ]

        # 检查已存在的任务
        task_names = [config["name"] for config in task_configs]
        existing_tasks = db.query(ScheduledTask).filter(ScheduledTask.name.in_(task_names)).all()
        existing_names = {task.name for task in existing_tasks}

        # 批量创建任务
        created_count = 0
        skipped_count = 0

        for task_config in task_configs:
            created, skipped = _create_single_task(
                db=db, task_config=task_config, skip_tasks=SKIP_TASKS, existing_names=existing_names
            )
            if created:
                created_count += 1
            if skipped:
                skipped_count += 1

        logger.info(f"✓ ZQuant任务创建完成！共创建 {created_count} 个新任务，跳过 {skipped_count} 个任务")
        return True

    except Exception as e:
        logger.error(f"✗ 创建ZQuant任务失败: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


def create_example_tasks(force: bool = False):
    """创建示例任务"""
    logger.info("开始创建示例任务...")
    db: Session = SessionLocal()

    try:
        # ========== 配置：需要跳过的任务列表 ==========
        # 在此列表中添加任务名称，这些任务将不会被初始化
        SKIP_TASKS = [
            "示例任务-快速测试",
            "示例任务-每分钟",
            "示例任务-每日18点",
            "示例任务-已禁用",
            "示例任务-实时进度演示",
            "示例任务-命令执行",
            "同步所有股票日线数据-数据库任务",
        ]
        # ============================================

        # 如果强制模式，先删除已存在的示例任务
        if force:
            existing_tasks = db.query(ScheduledTask).filter(ScheduledTask.name.like("示例任务-%")).all()
            for task in existing_tasks:
                db.delete(task)
            db.commit()
            logger.info(f"已删除 {len(existing_tasks)} 个已存在的示例任务")

        # 检查是否已存在（查询所有可能存在的任务名称）
        existing_tasks = (
            db.query(ScheduledTask)
            .filter(
                ScheduledTask.name.in_(
                    [
                        "示例任务-快速测试",
                        "示例任务-每分钟",
                        "示例任务-每日18点",
                        "示例任务-已禁用",
                        "示例任务-实时进度演示",
                        "示例任务-命令执行",
                        "同步所有股票日线数据-数据库任务",
                    ]
                )
            )
            .all()
        )
        existing_names = {task.name for task in existing_tasks}

        created_count = 0
        skipped_count = 0

        # 示例任务1：每30秒执行一次（快速测试）
        if "示例任务-快速测试" not in existing_names:
            task1 = SchedulerService.create_task(
                db=db,
                name="示例任务-快速测试",
                task_type=TaskType.COMMON_TASK,
                interval_seconds=30,
                description="这是一个示例任务，每30秒执行一次，用于快速测试定时任务功能",
                config={
                    "task_action": "example_task",
                    "duration_seconds": 3,
                    "success_rate": 1.0,
                    "message": "快速测试任务执行完成",
                    "steps": 5,
                },
                max_retries=3,
                retry_interval=60,
                enabled=True,
            )
            logger.info(f"✓ 创建任务: {task1.name} (ID: {task1.id})")
            created_count += 1
        else:
            logger.info("○ 任务已存在: 示例任务-快速测试")

        # 示例任务2：每分钟执行一次
        if "示例任务-每分钟" not in existing_names:
            task2 = SchedulerService.create_task(
                db=db,
                name="示例任务-每分钟",
                task_type=TaskType.COMMON_TASK,
                interval_seconds=60,
                description="示例任务，每分钟执行一次",
                config={
                    "task_action": "example_task",
                    "duration_seconds": 5,
                    "success_rate": 0.9,
                    "message": "每分钟任务执行完成",
                    "steps": 10,
                },
                max_retries=2,
                retry_interval=30,
                enabled=True,
            )
            logger.info(f"✓ 创建任务: {task2.name} (ID: {task2.id})")
            created_count += 1
        else:
            logger.info("○ 任务已存在: 示例任务-每分钟")

        # 示例任务3：使用Cron表达式（每天18:00执行）
        if "示例任务-每日18点" not in existing_names:
            task3 = SchedulerService.create_task(
                db=db,
                name="示例任务-每日18点",
                task_type=TaskType.COMMON_TASK,
                cron_expression="0 18 * * *",
                description="示例任务，每天18:00执行",
                config={
                    "task_action": "example_task",
                    "duration_seconds": 10,
                    "success_rate": 1.0,
                    "message": "每日任务执行完成",
                    "steps": 20,
                },
                max_retries=3,
                retry_interval=300,
                enabled=True,
            )
            logger.info(f"✓ 创建任务: {task3.name} (ID: {task3.id})")
            created_count += 1
        else:
            logger.info("○ 任务已存在: 示例任务-每日18点")

        # 示例任务4：禁用状态的任务
        if "示例任务-已禁用" not in existing_names:
            task4 = SchedulerService.create_task(
                db=db,
                name="示例任务-已禁用",
                task_type=TaskType.COMMON_TASK,
                interval_seconds=60,
                description="这是一个已禁用的示例任务，可以在Web界面中启用",
                config={
                    "task_action": "example_task",
                    "duration_seconds": 2,
                    "success_rate": 1.0,
                    "message": "已禁用任务执行完成",
                    "steps": 3,
                },
                max_retries=3,
                retry_interval=60,
                enabled=False,
            )
            logger.info(f"✓ 创建任务: {task4.name} (ID: {task4.id}, 已禁用)")
            created_count += 1
        else:
            logger.info("○ 任务已存在: 示例任务-已禁用")

        # 示例任务5：实时进度演示任务
        if "示例任务-实时进度演示" not in existing_names:
            task5 = SchedulerService.create_task(
                db=db,
                name="示例任务-实时进度演示",
                task_type=TaskType.COMMON_TASK,
                interval_seconds=300,
                description="这是一个用于演示实时进度查看功能的示例任务，执行时间较长，可以在执行历史中实时查看进度",
                config={
                    "task_action": "example_task",
                    "duration_seconds": 30,
                    "success_rate": 1.0,
                    "message": "实时进度演示任务执行完成",
                    "steps": 30,
                },
                max_retries=3,
                retry_interval=60,
                enabled=True,
            )
            logger.info(f"✓ 创建任务: {task5.name} (ID: {task5.id})")
            created_count += 1
        else:
            logger.info("○ 任务已存在: 示例任务-实时进度演示")

        # 示例任务6：命令执行示例任务
        if "示例任务-命令执行" not in existing_names:
            task6 = SchedulerService.create_task(
                db=db,
                name="示例任务-命令执行",
                task_type=TaskType.COMMON_TASK,
                interval_seconds=300,  # 每5分钟执行一次
                description="这是一个使用命令执行功能的示例任务，演示如何通过配置执行外部脚本",
                config={
                    "command": "python zquant/scheduler/job/example_scheduled_job.py --steps 5 --delay 1",
                    "timeout_seconds": 300,
                },
                max_retries=3,
                retry_interval=60,
                enabled=True,
            )
            logger.info(f"✓ 创建任务: {task6.name} (ID: {task6.id})")
            created_count += 1
        else:
            logger.info("○ 任务已存在: 示例任务-命令执行")

        # 示例任务7：同步交易日历-命令执行
        task7_name = "STEP1-同步交易日历（当日）-命令执行"
        if task7_name in SKIP_TASKS:
            logger.info(f"⊘ 跳过任务: {task7_name}（在SKIP_TASKS配置中）")
            skipped_count += 1
        elif task7_name not in existing_names:
            try:
                task7 = SchedulerService.create_task(
                    db=db,
                    name=task7_name,
                    task_type=TaskType.COMMON_TASK,
                    cron_expression="0 2 * * *",  # 每天凌晨2点执行
                    description="使用命令执行方式同步交易日历数据，每天自动更新交易日历",
                    config={"command": "python zquant/scheduler/job/sync_trading_calendar.py", "timeout_seconds": 600},
                    max_retries=3,
                    retry_interval=300,
                    enabled=True,
                )
                logger.info(f"✓ 创建任务: {task7_name} (ID: {task7.id})")
                created_count += 1
            except Exception as e:
                if "Duplicate entry" in str(e) or "1062" in str(e):
                    logger.info(f"○ 任务已存在: {task7_name}（数据库中存在）")
                else:
                    raise
        else:
            logger.info(f"○ 任务已存在: {task7_name}")

        # 示例任务8：同步股票列表-命令执行
        task8_name = "STEP2-同步股票列表（当日）-命令执行"
        if task8_name in SKIP_TASKS:
            logger.info(f"⊘ 跳过任务: {task8_name}（在SKIP_TASKS配置中）")
            skipped_count += 1
        elif task8_name not in existing_names:
            try:
                task8 = SchedulerService.create_task(
                    db=db,
                    name=task8_name,
                    task_type=TaskType.COMMON_TASK,
                    cron_expression="0 1 * * *",  # 每天凌晨1点执行
                    description="使用命令执行方式同步股票列表数据，每天自动更新股票基础信息",
                    config={"command": "python zquant/scheduler/job/sync_stock_list.py", "timeout_seconds": 300},
                    max_retries=3,
                    retry_interval=300,
                    enabled=True,
                )
                logger.info(f"✓ 创建任务: {task8_name} (ID: {task8.id})")
                created_count += 1
            except Exception as e:
                if "Duplicate entry" in str(e) or "1062" in str(e):
                    logger.info(f"○ 任务已存在: {task8_name}（数据库中存在）")
                else:
                    raise
        else:
            logger.info(f"○ 任务已存在: {task8_name}")

        # 示例任务9：同步日线数据-命令执行
        task9_name = "STEP3-同步日线数据（当日）-命令执行"
        if task9_name in SKIP_TASKS:
            logger.info(f"⊘ 跳过任务: {task9_name}（在SKIP_TASKS配置中）")
            skipped_count += 1
        elif task9_name not in existing_names:
            try:
                task9 = SchedulerService.create_task(
                    db=db,
                    name=task9_name,
                    task_type=TaskType.COMMON_TASK,
                    cron_expression="0 18 * * *",  # 每天收盘后18:00执行
                    description="使用命令执行方式同步所有股票的日线数据，每天收盘后自动更新日线数据",
                    config={"command": "python zquant/scheduler/job/sync_daily_data.py", "timeout_seconds": 3600},
                    max_retries=3,
                    retry_interval=600,
                    enabled=True,
                )
                logger.info(f"✓ 创建任务: {task9_name} (ID: {task9.id})")
                created_count += 1
            except Exception as e:
                if "Duplicate entry" in str(e) or "1062" in str(e):
                    logger.info(f"○ 任务已存在: {task9_name}（数据库中存在）")
                else:
                    raise
        else:
            logger.info(f"○ 任务已存在: {task9_name}")

        # 示例任务9.1：同步所有股票日线数据-数据库任务（使用 DATA_SYNC_ALL_DAILY_DATA 类型）
        task9_1_name = "STEP4-同步所有股票日线数据（当日）-数据库任务"
        if task9_1_name in SKIP_TASKS:
            logger.info(f"⊘ 跳过任务: {task9_1_name}（在SKIP_TASKS配置中）")
            skipped_count += 1
        elif task9_1_name not in existing_names:
            try:
                task9_1 = SchedulerService.create_task(
                    db=db,
                    name=task9_1_name,
                    task_type=TaskType.COMMON_TASK,
                    cron_expression="0 18 * * *",  # 每天收盘后18:00执行
                    description="使用数据库任务方式同步所有股票的日线数据，每天收盘后自动更新（按 ts_code 分表存储）",
                    config={
                        "task_action": "sync_all_daily_data",
                        "start_date": None,  # None 表示使用默认（最近一年）
                        "end_date": None,  # None 表示使用默认（当天）
                    },
                    max_retries=3,
                    retry_interval=600,
                    enabled=True,
                )
                logger.info(f"✓ 创建任务: {task9_1_name} (ID: {task9_1.id})")
                created_count += 1
            except Exception as e:
                if "Duplicate entry" in str(e) or "1062" in str(e):
                    logger.info(f"○ 任务已存在: {task9_1_name}（数据库中存在）")
                else:
                    raise
        else:
            logger.info(f"○ 任务已存在: {task9_1_name}")

        # 示例任务9.2：同步每日指标数据-命令执行
        task9_2_name = "STEP4-同步每日指标数据（当日）-命令执行"
        if task9_2_name in SKIP_TASKS:
            logger.info(f"⊘ 跳过任务: {task9_2_name}（在SKIP_TASKS配置中）")
            skipped_count += 1
        elif task9_2_name not in existing_names:
            try:
                task9_2 = SchedulerService.create_task(
                    db=db,
                    name=task9_2_name,
                    task_type=TaskType.COMMON_TASK,
                    cron_expression="0 18 * * *",  # 每天收盘后18:00执行
                    description="使用命令执行方式同步所有股票的每日指标数据，每天收盘后自动更新",
                    config={"command": "python zquant/scheduler/job/sync_daily_basic_data.py", "timeout_seconds": 3600},
                    max_retries=3,
                    retry_interval=600,
                    enabled=True,
                )
                logger.info(f"✓ 创建任务: {task9_2_name} (ID: {task9_2.id})")
                created_count += 1
            except Exception as e:
                if "Duplicate entry" in str(e) or "1062" in str(e):
                    logger.info(f"○ 任务已存在: {task9_2_name}（数据库中存在）")
                else:
                    raise
        else:
            logger.info(f"○ 任务已存在: {task9_2_name}")

        # 示例任务9.3：同步日线数据-命令执行（时间段）
        task9_3_name = "同步日线数据-命令执行（时间段）"
        if task9_3_name in SKIP_TASKS:
            logger.info(f"⊘ 跳过任务: {task9_3_name}（在SKIP_TASKS配置中）")
            skipped_count += 1
        elif task9_3_name not in existing_names:
            try:
                task9_3 = SchedulerService.create_task(
                    db=db,
                    name=task9_3_name,
                    task_type=TaskType.COMMON_TASK,
                    cron_expression="0 2 1 1 *",  # 每年1月1日凌晨2点执行（可手动触发）
                    description="使用命令执行方式同步指定时间段（2024-01-01至2025-11-16）的历史日线数据，用于历史数据补全",
                    config={
                        "command": "python zquant/scheduler/job/sync_daily_data.py --start-date 20240101 --end-date 20251116",
                        "timeout_seconds": 7200,
                    },
                    max_retries=3,
                    retry_interval=1800,
                    enabled=False,  # 默认禁用，由用户手动启用和触发
                )
                logger.info(f"✓ 创建任务: {task9_3_name} (ID: {task9_3.id})")
                created_count += 1
            except Exception as e:
                if "Duplicate entry" in str(e) or "1062" in str(e):
                    logger.info(f"○ 任务已存在: {task9_3_name}（数据库中存在）")
                else:
                    raise
        else:
            logger.info(f"○ 任务已存在: {task9_3_name}")

        # 示例任务9.4：同步每日指标数据-命令执行（时间段）
        task9_4_name = "同步每日指标数据-命令执行（时间段）"
        if task9_4_name in SKIP_TASKS:
            logger.info(f"⊘ 跳过任务: {task9_4_name}（在SKIP_TASKS配置中）")
            skipped_count += 1
        elif task9_4_name not in existing_names:
            try:
                task9_4 = SchedulerService.create_task(
                    db=db,
                    name=task9_4_name,
                    task_type=TaskType.COMMON_TASK,
                    cron_expression="0 2 1 1 *",  # 每年1月1日凌晨2点执行（可手动触发）
                    description="使用命令执行方式同步指定时间段（2024-01-01至2025-11-16）的历史每日指标数据，用于历史数据补全",
                    config={
                        "command": "python zquant/scheduler/job/sync_daily_basic_data.py --start-date 20240101 --end-date 20251116",
                        "timeout_seconds": 7200,
                    },
                    max_retries=3,
                    retry_interval=1800,
                    enabled=False,  # 默认禁用，由用户手动启用和触发
                )
                logger.info(f"✓ 创建任务: {task9_4_name} (ID: {task9_4.id})")
                created_count += 1
            except Exception as e:
                if "Duplicate entry" in str(e) or "1062" in str(e):
                    logger.info(f"○ 任务已存在: {task9_4_name}（数据库中存在）")
                else:
                    raise
        else:
            logger.info(f"○ 任务已存在: {task9_4_name}")

        # 示例任务10：同步财务数据-命令执行（利润表）
        task10_name = "STEP5-同步财务数据-利润表-命令执行"
        if task10_name in SKIP_TASKS:
            logger.info(f"⊘ 跳过任务: {task10_name}（在SKIP_TASKS配置中）")
            skipped_count += 1
        elif task10_name not in existing_names:
            try:
                task10 = SchedulerService.create_task(
                    db=db,
                    name=task10_name,
                    task_type=TaskType.COMMON_TASK,
                    cron_expression="0 2 1 * *",  # 每月1号凌晨2点执行
                    description="使用命令执行方式同步所有股票的财务数据（利润表），每月自动更新",
                    config={
                        "command": "python zquant/scheduler/job/sync_financial_data.py --statement-type income",
                        "timeout_seconds": 7200,
                    },
                    max_retries=3,
                    retry_interval=1800,
                    enabled=True,
                )
                logger.info(f"✓ 创建任务: {task10_name} (ID: {task10.id})")
                created_count += 1
            except Exception as e:
                if "Duplicate entry" in str(e) or "1062" in str(e):
                    logger.info(f"○ 任务已存在: {task10_name}（数据库中存在）")
                else:
                    raise
        else:
            logger.info(f"○ 任务已存在: {task10_name}")

        logger.info(f"✓ 示例任务创建完成！共创建 {created_count} 个新任务，跳过 {skipped_count} 个任务")
        return True

    except Exception as e:
        logger.error(f"✗ 创建示例任务失败: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


def create_workflow_examples(force: bool = False):
    """创建编排任务示例"""
    logger.info("开始创建编排任务示例...")
    db: Session = SessionLocal()

    try:
        # 如果强制模式，先删除已存在的编排任务
        if force:
            existing_workflows = (
                db.query(ScheduledTask)
                .filter(ScheduledTask.task_type == TaskType.WORKFLOW, ScheduledTask.name.like("编排任务-%"))
                .all()
            )
            for wf in existing_workflows:
                db.delete(wf)
            db.commit()
            logger.info(f"已删除 {len(existing_workflows)} 个已存在的编排任务")

        # 查询现有的示例任务
        existing_tasks = db.query(ScheduledTask).filter(ScheduledTask.name.like("示例任务-%")).all()
        task_map = {task.name: task for task in existing_tasks}

        # 创建或获取基础任务
        task_ids = {}
        task_names = [
            ("示例任务-快速测试", "快速测试任务，用于编排任务演示"),
            ("示例任务-步骤1", "编排任务步骤1"),
            ("示例任务-步骤2", "编排任务步骤2"),
            ("示例任务-步骤3", "编排任务步骤3"),
        ]

        for name, desc in task_names:
            if name not in task_map:
                task = SchedulerService.create_task(
                    db=db,
                    name=name,
                    task_type=TaskType.COMMON_TASK,
                    interval_seconds=300,
                    description=desc,
                    config={
                        "task_action": "example_task",
                        "duration_seconds": 2 if "快速" in name else 3,
                        "success_rate": 1.0,
                        "message": f"{name}执行完成",
                        "steps": 3 if "快速" in name else 5,
                    },
                    max_retries=3,
                    retry_interval=60,
                    enabled=True,
                )
                logger.info(f"✓ 创建基础任务: {task.name} (ID: {task.id})")
                task_ids[name] = task.id
            else:
                task_ids[name] = task_map[name].id
                logger.info(f"○ 使用已有任务: {name} (ID: {task_ids[name]})")

        # 检查是否已有编排任务
        existing_workflows = (
            db.query(ScheduledTask)
            .filter(ScheduledTask.task_type == TaskType.WORKFLOW, ScheduledTask.name.like("编排任务-%"))
            .all()
        )
        workflow_map = {wf.name: wf for wf in existing_workflows}

        created_count = 0

        # 创建串行编排任务
        if "编排任务-串行执行示例" not in workflow_map:
            serial_workflow = SchedulerService.create_task(
                db=db,
                name="编排任务-串行执行示例",
                task_type=TaskType.WORKFLOW,
                interval_seconds=600,
                description="串行执行示例：按顺序执行任务1→任务2→任务3",
                config={
                    "workflow_type": "serial",
                    "tasks": [
                        {"task_id": task_ids["示例任务-步骤1"], "name": "示例任务-步骤1", "dependencies": []},
                        {
                            "task_id": task_ids["示例任务-步骤2"],
                            "name": "示例任务-步骤2",
                            "dependencies": [task_ids["示例任务-步骤1"]],
                        },
                        {
                            "task_id": task_ids["示例任务-步骤3"],
                            "name": "示例任务-步骤3",
                            "dependencies": [task_ids["示例任务-步骤2"]],
                        },
                    ],
                    "on_failure": "stop",
                },
                max_retries=3,
                retry_interval=60,
                enabled=True,
            )
            logger.info(f"✓ 创建编排任务: {serial_workflow.name} (ID: {serial_workflow.id})")
            created_count += 1
        else:
            logger.info("○ 编排任务已存在: 编排任务-串行执行示例")

        # 创建并行编排任务
        if "编排任务-并行执行示例" not in workflow_map:
            parallel_workflow = SchedulerService.create_task(
                db=db,
                name="编排任务-并行执行示例",
                task_type=TaskType.WORKFLOW,
                interval_seconds=600,
                description="并行执行示例：同时执行多个独立任务",
                config={
                    "workflow_type": "parallel",
                    "tasks": [
                        {"task_id": task_ids["示例任务-快速测试"], "name": "示例任务-快速测试", "dependencies": []},
                        {"task_id": task_ids["示例任务-步骤1"], "name": "示例任务-步骤1", "dependencies": []},
                        {"task_id": task_ids["示例任务-步骤2"], "name": "示例任务-步骤2", "dependencies": []},
                    ],
                    "on_failure": "continue",
                },
                max_retries=3,
                retry_interval=60,
                enabled=True,
            )
            logger.info(f"✓ 创建编排任务: {parallel_workflow.name} (ID: {parallel_workflow.id})")
            created_count += 1
        else:
            logger.info("○ 编排任务已存在: 编排任务-并行执行示例")

        # 创建混合编排任务
        if "编排任务-混合执行示例" not in workflow_map:
            mixed_workflow = SchedulerService.create_task(
                db=db,
                name="编排任务-混合执行示例",
                task_type=TaskType.WORKFLOW,
                interval_seconds=600,
                description="混合执行示例：先并行执行任务1和任务2，然后串行执行任务3",
                config={
                    "workflow_type": "parallel",
                    "tasks": [
                        {"task_id": task_ids["示例任务-快速测试"], "name": "示例任务-快速测试", "dependencies": []},
                        {"task_id": task_ids["示例任务-步骤1"], "name": "示例任务-步骤1", "dependencies": []},
                        {
                            "task_id": task_ids["示例任务-步骤2"],
                            "name": "示例任务-步骤2",
                            "dependencies": [task_ids["示例任务-快速测试"], task_ids["示例任务-步骤1"]],
                        },
                        {
                            "task_id": task_ids["示例任务-步骤3"],
                            "name": "示例任务-步骤3",
                            "dependencies": [task_ids["示例任务-步骤2"]],
                        },
                    ],
                    "on_failure": "stop",
                },
                max_retries=3,
                retry_interval=60,
                enabled=True,
            )
            logger.info(f"✓ 创建编排任务: {mixed_workflow.name} (ID: {mixed_workflow.id})")
            created_count += 1
        else:
            logger.info("○ 编排任务已存在: 编排任务-混合执行示例")

        logger.info(f"✓ 编排任务示例创建完成！共创建 {created_count} 个新编排任务")
        return True

    except Exception as e:
        logger.error(f"✗ 创建编排任务示例失败: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="定时任务系统初始化脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python scripts/init_scheduler.py                    # 默认：建表+创建ZQuant任务
  python scripts/init_scheduler.py --all             # 执行所有步骤（表+示例+编排+ZQuant）
  python scripts/init_scheduler.py --tables-only     # 只创建数据库表
  python scripts/init_scheduler.py --examples-only    # 只创建示例任务
  python scripts/init_scheduler.py --workflow-only    # 只创建编排任务
  python scripts/init_scheduler.py --zquant-only      # 只创建ZQuant任务
  python scripts/init_scheduler.py --force            # 强制重新创建（删除已存在的任务）
        """,
    )

    parser.add_argument("--all", action="store_true", help="执行所有步骤（创建表+示例任务+编排任务+ZQuant任务）")
    parser.add_argument("--tables-only", action="store_true", help="只创建数据库表")
    parser.add_argument("--examples-only", action="store_true", help="只创建示例任务")
    parser.add_argument("--workflow-only", action="store_true", help="只创建编排任务示例")
    parser.add_argument("--zquant-only", action="store_true", help="只创建ZQuant任务（默认行为）")
    parser.add_argument("--force", action="store_true", help="强制重新创建（删除已存在的任务）")

    args = parser.parse_args()

    # 确定要执行的步骤（默认执行建表和ZQuant任务）
    if args.all:
        steps = ["tables", "examples", "workflow", "zquant"]
    elif args.tables_only:
        steps = ["tables"]
    elif args.examples_only:
        steps = ["examples"]
    elif args.workflow_only:
        steps = ["workflow"]
    elif args.zquant_only:
        steps = ["zquant"]
    else:
        # 默认执行建表和ZQuant任务
        steps = ["tables", "zquant"]

    logger.info("=" * 60)
    logger.info("定时任务系统初始化")
    logger.info("=" * 60)
    logger.info(f"执行步骤: {', '.join(steps)}")
    if args.force:
        logger.info("强制模式: 将删除已存在的任务")
    logger.info("")

    success = True

    # 执行步骤
    if "tables" in steps:
        if not create_tables():
            success = False
        logger.info("")

    if "examples" in steps:
        if not create_example_tasks(force=args.force):
            success = False
        logger.info("")

    if "workflow" in steps:
        if not create_workflow_examples(force=args.force):
            success = False
        logger.info("")

    if "zquant" in steps:
        if not create_zquant_tasks(force=args.force):
            success = False
        logger.info("")

    # 总结
    logger.info("=" * 60)
    if success:
        logger.info("初始化完成！")
        logger.info("")
        logger.info("提示：")
        logger.info("  - 访问 http://localhost:8000/admin/scheduler 查看和管理任务")
        logger.info("  - 可以随时启用/禁用任务")
        logger.info("  - 可以手动触发任务执行")
        logger.info("  - 可以查看任务执行历史和统计信息")
        logger.info("  - 编排任务支持展开查看子任务")
    else:
        logger.error("初始化过程中出现错误，请检查上面的错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
