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
回测服务
"""

from datetime import date, datetime
import importlib.util
import json
from typing import Any

from loguru import logger
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from zquant.backtest.engine import BacktestEngine
from zquant.backtest.performance import PerformanceAnalyzer
from zquant.models.backtest import BacktestResult, BacktestStatus, BacktestTask, Strategy, Strategy
from zquant.services.strategy import StrategyService
from zquant.utils.query_optimizer import paginate_query, optimize_query_with_relationships


class BacktestService:
    """回测服务类"""

    @staticmethod
    def create_task(
        db: Session,
        user_id: int,
        strategy_name: str,
        config: dict[str, Any],
        strategy_id: int | None = None,
        strategy_code: str | None = None,
    ) -> BacktestTask:
        """
        创建回测任务

        Args:
            db: 数据库会话
            user_id: 用户ID
            strategy_name: 策略名称
            config: 回测配置
            strategy_id: 策略ID（从策略库选择，可选）
            strategy_code: 策略代码（当strategy_id为空时必填）
        """
        # 如果提供了strategy_id，从策略库加载策略代码
        if strategy_id:
            strategy = StrategyService.get_strategy(db, strategy_id, user_id)
            if not strategy:
                # 如果是模板策略，允许所有用户使用
                strategy = db.query(Strategy).filter(Strategy.id == strategy_id, Strategy.is_template == True).first()

            if not strategy:
                raise ValueError(f"策略 {strategy_id} 不存在")

            strategy_code = strategy.code
            if not strategy_name:
                strategy_name = strategy.name

        # 验证策略代码
        if not strategy_code:
            raise ValueError("必须提供strategy_id或strategy_code")

        task = BacktestTask(
            user_id=user_id,
            strategy_id=strategy_id,
            strategy_code=strategy_code,
            strategy_name=strategy_name,
            config_json=json.dumps(config, default=str),
            status=BacktestStatus.PENDING,
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        logger.info(f"创建回测任务: {task.id}")
        return task

    @staticmethod
    def run_backtest(db: Session, task_id: int) -> BacktestResult:
        """运行回测"""
        # 获取任务
        task = db.query(BacktestTask).filter(BacktestTask.id == task_id).first()
        if not task:
            raise ValueError(f"回测任务 {task_id} 不存在")

        # 更新状态和开始时间
        task.status = BacktestStatus.RUNNING
        task.started_at = datetime.now()
        db.commit()

        try:
            # 解析配置
            config = json.loads(task.config_json)

            # 动态加载策略类
            StrategyClass = BacktestService._load_strategy_class(task.strategy_code)

            # 创建引擎（引擎会创建策略实例）
            engine = BacktestEngine(db, StrategyClass, config)
            results = engine.run()

            # 计算绩效指标
            analyzer = PerformanceAnalyzer(engine)
            metrics = analyzer.calculate_metrics()

            # 保存结果
            result = BacktestResult(
                task_id=task_id,
                total_return=metrics.get("total_return"),
                annual_return=metrics.get("annual_return"),
                max_drawdown=metrics.get("max_drawdown"),
                sharpe_ratio=metrics.get("sharpe_ratio"),
                win_rate=metrics.get("win_rate"),
                profit_loss_ratio=metrics.get("profit_loss_ratio"),
                alpha=metrics.get("alpha"),
                beta=metrics.get("beta"),
                metrics_json=json.dumps(metrics, default=str),
                trades_json=json.dumps(results.get("orders", []), default=str),
                portfolio_json=json.dumps(results.get("portfolio", {}), default=str),
            )

            db.add(result)

            # 更新任务状态和完成时间
            task.status = BacktestStatus.COMPLETED
            task.completed_at = datetime.now()

            db.commit()
            db.refresh(result)

            logger.info(f"回测任务 {task_id} 完成")
            return result

        except Exception as e:
            logger.error(f"回测任务 {task_id} 失败: {e}")
            task.status = BacktestStatus.FAILED
            task.error_message = str(e)
            db.commit()
            raise

    @staticmethod
    def _load_strategy_class(strategy_code: str):
        """动态加载策略类"""
        # 创建临时模块
        spec = importlib.util.spec_from_loader("strategy_module", loader=None)
        module = importlib.util.module_from_spec(spec)

        # 执行策略代码
        exec(strategy_code, module.__dict__)

        # 查找策略类（假设策略类名为Strategy）
        if not hasattr(module, "Strategy"):
            raise ValueError("策略代码中必须定义Strategy类")

        return module.Strategy

    @staticmethod
    def get_task(db: Session, task_id: int, user_id: int) -> BacktestTask | None:
        """获取回测任务（资源隔离）"""
        task = db.query(BacktestTask).filter(BacktestTask.id == task_id, BacktestTask.user_id == user_id).first()
        return task

    @staticmethod
    def get_user_tasks(
        db: Session, user_id: int, skip: int = 0, limit: int = 100, order_by: str | None = None, order: str = "desc"
    ) -> list[BacktestTask]:
        """获取用户的所有回测任务（支持排序）"""
        query = db.query(BacktestTask).filter(BacktestTask.user_id == user_id)

        # 排序逻辑
        if order_by:
            sortable_fields = {
                "id": BacktestTask.id,
                "name": BacktestTask.name,
                "status": BacktestTask.status,
                "created_at": BacktestTask.created_at,
                "updated_at": BacktestTask.updated_at,
            }

            if order_by in sortable_fields:
                sort_field = sortable_fields[order_by]
                if order and order.lower() == "asc":
                    query = query.order_by(asc(sort_field))
                else:
                    query = query.order_by(desc(sort_field))
            else:
                query = query.order_by(desc(BacktestTask.created_at))
        else:
            query = query.order_by(desc(BacktestTask.created_at))

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_result(db: Session, task_id: int, user_id: int) -> BacktestResult | None:
        """获取回测结果（资源隔离）"""
        task = BacktestService.get_task(db, task_id, user_id)
        if not task:
            return None

        result = db.query(BacktestResult).filter(BacktestResult.task_id == task_id).first()
        return result

    @staticmethod
    def list_results(
        db: Session, user_id: int, skip: int = 0, limit: int = 100, order_by: str | None = None, order: str = "desc"
    ) -> list[BacktestResult]:
        """获取用户的所有回测结果列表（支持排序）"""
        # 先获取用户的所有任务ID
        task_ids = db.query(BacktestTask.id).filter(BacktestTask.user_id == user_id).subquery()

        query = db.query(BacktestResult).filter(BacktestResult.task_id.in_(task_ids))

        # 排序逻辑
        if order_by:
            sortable_fields = {
                "id": BacktestResult.id,
                "task_id": BacktestResult.task_id,
                "total_return": BacktestResult.total_return,
                "annual_return": BacktestResult.annual_return,
                "sharpe_ratio": BacktestResult.sharpe_ratio,
                "created_at": BacktestResult.created_at,
            }

            if order_by in sortable_fields:
                sort_field = sortable_fields[order_by]
                if order and order.lower() == "asc":
                    query = query.order_by(asc(sort_field))
                else:
                    query = query.order_by(desc(sort_field))
            else:
                query = query.order_by(desc(BacktestResult.created_at))
        else:
            query = query.order_by(desc(BacktestResult.created_at))

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def delete_result(db: Session, result_id: int, user_id: int) -> bool:
        """删除回测结果（级联删除任务）"""
        result = db.query(BacktestResult).filter(BacktestResult.id == result_id).first()

        if not result:
            return False

        # 验证任务属于当前用户
        task = BacktestService.get_task(db, result.task_id, user_id)
        if not task:
            return False

        # 删除任务（会级联删除结果）
        db.delete(task)
        db.commit()

        logger.info(f"删除回测结果: {result_id} (任务: {result.task_id})")
        return True
