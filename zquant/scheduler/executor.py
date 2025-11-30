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
任务执行器
"""

from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from zquant.data.etl.scheduler import DataScheduler
from zquant.models.scheduler import TaskExecution, TaskType
from zquant.scheduler.base import TaskExecutor


class DataSyncExecutor(TaskExecutor):
    """数据同步任务执行器"""

    def __init__(self):
        self.data_scheduler = DataScheduler()

    def get_task_type(self) -> TaskType:
        return TaskType.COMMON_TASK

    def execute(self, db: Session, config: dict[str, Any], execution: TaskExecution | None = None) -> dict[str, Any]:
        """执行数据同步任务"""
        # 优先使用 task_action，向后兼容 task_type
        task_action = config.get("task_action")

        # 向后兼容：如果没有 task_action，尝试从 task_type 推断
        if not task_action:
            task_type = config.get("task_type")
            if isinstance(task_type, TaskType):
                task_action = self._infer_task_action_from_type(task_type)
            elif isinstance(task_type, str):
                task_action = self._infer_task_action_from_string(task_type)

        if not task_action:
            raise ValueError("数据同步任务配置中必须包含 'task_action' 字段，或提供 'task_type' 字段（向后兼容）")

        # 获取任务名（用于构建 extra_info）
        task_name = None
        if execution and execution.task_id:
            from zquant.models.scheduler import ScheduledTask

            task = db.query(ScheduledTask).filter(ScheduledTask.id == execution.task_id).first()
            if task:
                task_name = task.name
        # 如果无法从 execution 获取，尝试从 config 获取
        if not task_name:
            task_name = config.get("job_name") or config.get("task_name")

        # 构建 extra_info Dict
        extra_info = None
        if task_name:
            extra_info = {"created_by": task_name, "updated_by": task_name}

        try:
            if task_action == "sync_stock_list":
                return self._sync_stock_list(db, extra_info)
            if task_action == "sync_trading_calendar":
                return self._sync_trading_calendar(db, config, extra_info)
            if task_action == "sync_daily_data":
                return self._sync_daily_data(db, config, extra_info)
            if task_action == "sync_all_daily_data":
                return self._sync_all_daily_data(db, config, extra_info)
            raise ValueError(
                f"不支持的任务动作: {task_action}。支持的 action: sync_stock_list, sync_trading_calendar, sync_daily_data, sync_all_daily_data"
            )
        except Exception as e:
            logger.error(f"执行数据同步任务失败: {e}")
            raise

    def _infer_task_action_from_type(self, task_type: TaskType) -> str | None:
        """从 TaskType 推断 task_action（向后兼容）"""
        # 注意：旧的 DATA_SYNC_* 类型可能已经不存在于枚举中，但可能存在于数据库中
        # 这里只处理可能存在的类型
        try:
            type_to_action = {
                TaskType.DATA_SYNC_STOCK_LIST: "sync_stock_list",
                TaskType.DATA_SYNC_TRADING_CALENDAR: "sync_trading_calendar",
                TaskType.DATA_SYNC_DAILY_DATA: "sync_daily_data",
                TaskType.DATA_SYNC_ALL_DAILY_DATA: "sync_all_daily_data",
            }
            return type_to_action.get(task_type)
        except AttributeError:
            # 如果 TaskType 中没有这些值，返回 None
            return None

    def _infer_task_action_from_string(self, task_type_str: str) -> str | None:
        """从字符串形式的 task_type 推断 task_action（向后兼容）"""
        string_to_action = {
            "data_sync_stock_list": "sync_stock_list",
            "data_sync_trading_calendar": "sync_trading_calendar",
            "data_sync_daily_data": "sync_daily_data",
            "data_sync_all_daily_data": "sync_all_daily_data",
        }
        return string_to_action.get(task_type_str)

    def _sync_stock_list(self, db: Session, extra_info: dict | None = None) -> dict[str, Any]:
        """同步股票列表"""
        count = self.data_scheduler.sync_stock_list(db, extra_info)
        return {"success": True, "count": count, "message": f"成功同步 {count} 条股票列表"}

    def _sync_trading_calendar(
        self, db: Session, config: dict[str, Any], extra_info: dict | None = None
    ) -> dict[str, Any]:
        """同步交易日历"""
        start_date = config.get("start_date")
        end_date = config.get("end_date")
        count = self.data_scheduler.sync_trading_calendar(db, start_date, end_date, extra_info=extra_info)
        return {"success": True, "count": count, "message": f"成功同步 {count} 条交易日历"}

    def _sync_daily_data(self, db: Session, config: dict[str, Any], extra_info: dict | None = None) -> dict[str, Any]:
        """同步单只股票的日线数据（按 ts_code 分表存储）"""
        ts_code = config.get("ts_code") or config.get("symbol")  # 兼容旧配置
        if not ts_code:
            raise ValueError("同步日线数据需要指定 ts_code 参数")

        start_date = config.get("start_date")
        end_date = config.get("end_date")
        count = self.data_scheduler.sync_daily_data(db, ts_code, start_date, end_date, extra_info)
        return {
            "success": True,
            "count": count,
            "ts_code": ts_code,
            "message": f"成功同步 {ts_code} 的 {count} 条日线数据",
        }

    def _sync_all_daily_data(
        self, db: Session, config: dict[str, Any], extra_info: dict | None = None
    ) -> dict[str, Any]:
        """同步所有股票的日线数据"""
        from datetime import date
        from zquant.models.data import TustockTradecal
        from sqlalchemy import desc

        start_date = config.get("start_date")
        end_date = config.get("end_date")
        codelist = config.get("codelist")  # 可以是字符串（逗号分隔）或列表

        # 处理 codelist：如果是字符串，转换为列表
        if isinstance(codelist, str):
            codelist = [code.strip() for code in codelist.split(",") if code.strip()]
        elif codelist is None:
            codelist = None

        # 判断是否所有参数都未传入
        all_params_empty = not codelist and not start_date and not end_date

        # 如果所有参数都未传入，获取最后一个交易日
        if all_params_empty:
            try:
                latest = (
                    db.query(TustockTradecal.cal_date)
                    .filter(TustockTradecal.is_open == 1, TustockTradecal.cal_date <= date.today())
                    .order_by(desc(TustockTradecal.cal_date))
                    .first()
                )

                if latest and latest[0]:
                    latest_date = latest[0]
                    start_date = end_date = latest_date.strftime("%Y%m%d")
                    logger.info(f"所有参数均无传入，使用最后一个交易日: {start_date}")
            except Exception as e:
                logger.warning(f"获取最后一个交易日失败: {e}，使用默认值")

        # 处理部分参数未传入的情况
        if not start_date:
            # 无start-date传参，默认开始时间为20250101
            start_date = "20250101"
            logger.info(f"未提供start-date，使用默认值: {start_date}")

        if not end_date:
            # 无end-date传参，默认结束时间为同步当日
            from datetime import date as date_class

            end_date = date_class.today().strftime("%Y%m%d")
            logger.info(f"未提供end-date，使用默认值: {end_date}")

        # 无codelist传参，默认同步所有code的数据（codelist=None）
        if codelist:
            logger.info(f"指定股票列表，共 {len(codelist)} 只股票")

        result = self.data_scheduler.sync_all_daily_data(db, start_date, end_date, extra_info, codelist)
        return {
            "success": True,
            "total": result.get("total", 0),
            "success_count": result.get("success", 0),
            "failed_count": len(result.get("failed", [])),
            "failed_symbols": result.get("failed", []),
            "message": f"同步完成: 成功 {result.get('success', 0)}/{result.get('total', 0)}",
        }


# 任务执行器注册表（延迟导入以避免循环依赖）
EXECUTOR_REGISTRY: dict[TaskType, TaskExecutor] = {}


def _init_executor_registry():
    """初始化执行器注册表（延迟导入）"""
    if not EXECUTOR_REGISTRY:
        from zquant.scheduler.executors.common_executor import CommonTaskExecutor
        from zquant.scheduler.executors.workflow_executor import WorkflowExecutor

        EXECUTOR_REGISTRY.update(
            {
                TaskType.MANUAL_TASK: CommonTaskExecutor(),  # 手动任务使用通用任务执行器
                TaskType.COMMON_TASK: CommonTaskExecutor(),
                TaskType.WORKFLOW: WorkflowExecutor(),
            }
        )


# 初始化注册表
_init_executor_registry()


def get_executor(task_type: TaskType) -> TaskExecutor:
    """获取任务执行器"""
    _init_executor_registry()  # 确保注册表已初始化
    executor = EXECUTOR_REGISTRY.get(task_type)
    if not executor:
        raise ValueError(f"未找到任务类型 {task_type} 的执行器")
    return executor
