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
#     - Issues: https://github.com/yoyoung/zquant/issues
#     - Documentation: https://github.com/yoyoung/zquant/blob/main/README.md
#     - Repository: https://github.com/yoyoung/zquant

"""
量化选股任务服务层
"""

import json
from datetime import date
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from zquant.models.data import StockFilterResult, StockFilterStrategy
from zquant.services.stock_filter import StockFilterService
from zquant.models.scheduler import TaskExecution
from zquant.scheduler.utils import update_execution_progress
from sqlalchemy import text


class StockFilterTaskService:
    """量化选股任务服务"""

    DEFAULT_BATCH_SIZE = 10  # 默认股票处理批次大小

    @classmethod
    def execute_strategy(
        cls, 
        db: Session, 
        strategy: StockFilterStrategy | int, 
        trade_date: date | None = None,
        extra_info: dict[str, Any] | None = None,
        execution: TaskExecution | None = None,
    ) -> dict[str, Any]:
        """
        执行单个策略并保存结果

        Args:
            db: 数据库会话
            strategy: 策略对象或策略ID
            trade_date: 交易日期，如果不提供则自动获取最新交易日期
            extra_info: 额外信息字典，可包含 created_by 和 updated_by 字段
            execution: 执行记录对象（可选）

        Returns:
            执行结果
        """
        if isinstance(strategy, int):
            strategy = db.query(StockFilterStrategy).filter(StockFilterStrategy.id == strategy).first()
            if not strategy:
                return {"success": False, "message": f"未找到策略 ID: {strategy}"}

        if not trade_date:
            trade_date = cls.get_latest_trade_date(db)

        logger.info(f"开始执行选股策略: {strategy.name}, 交易日期: {trade_date}")
        update_execution_progress(db, execution, message=f"正在执行策略: {strategy.name} ({trade_date})")

        try:
            # 1. 解析策略配置
            filter_conditions = json.loads(strategy.filter_conditions) if strategy.filter_conditions else None
            sort_config = json.loads(strategy.sort_config) if strategy.sort_config else None
            
            # 2. 执行选股 - 查询完整数据（包含反范式化字段）
            # 设置 selected_columns 为 None，触发 StockFilterService 使用模型定义的全部列
            selected_columns = None
            
            items, total = StockFilterService.get_filter_results(
                db=db,
                trade_date=trade_date,
                filter_conditions=filter_conditions,
                selected_columns=selected_columns,
                sort_config=sort_config,
                skip=0,
                limit=5000, # 选股结果通常不会超过5000条
            )
            
            # 3. 清除旧结果
            db.query(StockFilterResult).filter(
                StockFilterResult.trade_date == trade_date,
                StockFilterResult.strategy_id == strategy.id
            ).delete()
            
            # 4. 获取用户名（从 extra_info 或 execution 中获取，或使用默认值）
            username = None
            if extra_info:
                username = extra_info.get("created_by") or extra_info.get("updated_by")
            
            # 如果仍没有用户名，尝试从 execution 中获取任务名称
            if not username and execution and execution.task_id:
                from zquant.models.scheduler import ScheduledTask
                task = db.query(ScheduledTask).filter(ScheduledTask.id == execution.task_id).first()
                if task:
                    username = task.name
            
            # 如果还是没有，使用默认值
            if not username:
                username = "system"
            
            # 5. 保存新结果（使用反范式化的保存方法）
            if items:
                saved_count = StockFilterService.save_filter_results(
                    db=db,
                    trade_date=trade_date,
                    strategy_id=strategy.id,
                    strategy_name=strategy.name,
                    stock_data=items,  # 传递完整的股票数据
                    username=username,
                )
            else:
                saved_count = 0
                db.commit()
            
            logger.info(f"策略 '{strategy.name}' 在 {trade_date} 执行完成，选中 {saved_count} 只股票")
            
            return {
                "success": True, 
                "message": f"策略 '{strategy.name}' 执行完成", 
                "count": saved_count,
                "trade_date": trade_date
            }

        except Exception as e:
            db.rollback()
            logger.error(f"执行策略 '{strategy.name}' 失败: {e}")
            return {"success": False, "message": str(e)}

    @classmethod
    def _extract_static_filters(cls, filter_conditions: Any) -> dict[str, list[str]]:
        """
        从复杂的筛选条件中提取静态过滤项 (ts_code, exchange)
        """
        static_filters = {"ts_code": [], "exchange": []}
        
        if not filter_conditions:
            return static_filters

        def _process_condition(cond: dict[str, Any]):
            field = cond.get("field")
            operator = str(cond.get("operator", "")).upper()
            value = cond.get("value")
            is_not = cond.get("not", False) or cond.get("not_", False)

            if is_not: # 排除 NOT 条件，因为 NOT IN 或 NOT = 无法用于精确预过滤
                return

            if field in ["ts_code", "exchange"]:
                if operator == "=" and isinstance(value, str):
                    static_filters[field].append(value)
                elif operator == "IN" and isinstance(value, list):
                    static_filters[field].extend([v for v in value if isinstance(v, str)])

        def _walk(node: Any):
            if isinstance(node, list):
                for item in node:
                    _walk(item)
            elif isinstance(node, dict):
                if "field" in node:
                    _process_condition(node)
                elif "conditions" in node:
                    # 只有 AND 逻辑下的子条件可以用于交集过滤
                    # 如果是 OR，预过滤逻辑会变得复杂，暂时只处理 AND 下的静态提取
                    logic = node.get("logic", "AND").upper()
                    if logic == "AND":
                        _walk(node["conditions"])

        _walk(filter_conditions)
        
        # 去重
        static_filters["ts_code"] = list(set(static_filters["ts_code"]))
        static_filters["exchange"] = list(set(static_filters["exchange"]))
        
        return static_filters

    @classmethod
    def _apply_pre_filters(cls, db: Session, codes: list[str], static_filters: dict[str, list[str]]) -> list[str]:
        """
        应用提取出的静态过滤条件
        """
        if not static_filters["ts_code"] and not static_filters["exchange"]:
            return codes
            
        result_codes = set(codes)
        
        # 1. ts_code 过滤 (取交集)
        if static_filters["ts_code"]:
            result_codes = result_codes.intersection(set(static_filters["ts_code"]))
            
        # 2. exchange 过滤 (取交集)
        if static_filters["exchange"] and result_codes:
            from zquant.models.data import Tustock
            exchange_stocks = db.query(Tustock.ts_code).filter(
                Tustock.exchange.in_(static_filters["exchange"]),
                Tustock.ts_code.in_(list(result_codes)) # 在当前已缩小范围内进一步缩小
            ).all()
            result_codes = set([s.ts_code for s in exchange_stocks])
            
        return sorted(list(result_codes))

    @classmethod
    def _execute_strategy_batch_stock_priority(
        cls,
        db: Session,
        trading_dates: list[date],
        strategies: list[StockFilterStrategy],
        extra_info: dict[str, Any] | None = None,
        execution: TaskExecution | None = None,
    ) -> dict[str, Any]:
        """
        股票优先模式的批量选股实现 (已优化预过滤)
        
        Args:
            db: 数据库会话
            trading_dates: 交易日期列表
            strategies: 策略列表
            extra_info: 额外信息
            execution: 执行记录
            
        Returns:
            执行结果汇总
        """
        from zquant.models.data import Tustock
        from zquant.config import settings
        
        # 1. 获取所有待处理股票作为基准列表
        query = db.query(Tustock.ts_code).filter(Tustock.delist_date.is_(None))
        if settings.DEFAULT_EXCHANGES:
            query = query.filter(Tustock.exchange.in_(settings.DEFAULT_EXCHANGES))
        stocks = query.order_by(Tustock.ts_code).all()
        base_codes = [stock.ts_code for stock in stocks]
        logger.info(f"获取到 {len(base_codes)} 只基础待处理股票")
        
        # 2. 清理旧结果
        start_date, end_date = trading_dates[0], trading_dates[-1]
        logger.info(f"清理旧选股结果: {start_date} 至 {end_date}, 共 {len(strategies)} 个策略")
        for strategy in strategies:
            deleted = db.query(StockFilterResult).filter(
                StockFilterResult.trade_date >= start_date,
                StockFilterResult.trade_date <= end_date,
                StockFilterResult.strategy_id == strategy.id
            ).delete()
            if deleted > 0:
                logger.debug(f"已清理策略 '{strategy.name}' 的 {deleted} 条旧结果")
        db.commit()
        
        # 3. 初始化统计
        # 进度条使用原始全量规模：每只股票 x 每个策略
        original_total_items = len(base_codes) * len(strategies)
        processed_items = 0
        total_results = 0
        success_count = 0
        failed_count = 0
        
        # 获取操作用户名
        username = extra_info.get("created_by", "system") if extra_info else "system"
        
        update_execution_progress(
            db, 
            execution, 
            total_items=original_total_items, 
            processed_items=0, 
            message=f"开始批量选股 (分批处理模式): {len(base_codes)}只股票 x {len(strategies)}个策略"
        )

        # 获取批次大小配置
        batch_size = cls.DEFAULT_BATCH_SIZE
        if extra_info and "batch_size" in extra_info:
            try:
                batch_size = int(extra_info["batch_size"])
            except (ValueError, TypeError):
                pass

        # 4. 循环策略进行选股 (修改循环顺序以支持预过滤优化)
        for strategy_idx, strategy in enumerate(strategies, 1):
            # 4.1 提取静态过滤条件并执行预过滤
            filter_conditions = json.loads(strategy.filter_conditions) if strategy.filter_conditions else None
            static_filters = cls._extract_static_filters(filter_conditions)
            strategy_codes = cls._apply_pre_filters(db, base_codes, static_filters)
            
            static_count = len(strategy_codes)
            
            # 4.2 执行动态数据预过滤：进一步缩小范围，只保留在目标时段内至少有一天满足条件的股票
            if strategy_codes:
                strategy_codes = StockFilterService.get_matched_codes_in_period(
                    db=db,
                    ts_codes=strategy_codes,
                    start_date=start_date,
                    end_date=end_date,
                    filter_conditions=filter_conditions
                )
            
            final_count = len(strategy_codes)
            skip_count = len(base_codes) - final_count
            
            logger.info(f"策略 '{strategy.name}' ({strategy_idx}/{len(strategies)}) 预过滤完成: "
                        f"全量 {len(base_codes)} -> 静态过滤后 {static_count} -> 动态过滤后 {final_count} "
                        f"(累计跳过 {skip_count} 只股票), 批次大小: {batch_size}")

            # 4.3 分批处理该策略下的有效股票
            for i in range(0, len(strategy_codes), batch_size):
                batch_codes = strategy_codes[i : i + batch_size]
                try:
                    # 批量查询该组股票在时间段内的选股结果
                    matched_items = StockFilterService.get_filter_results_for_stocks_period(
                        db=db,
                        ts_codes=batch_codes,
                        start_date=start_date,
                        end_date=end_date,
                        filter_conditions=filter_conditions,
                        selected_columns=None # 获取所有反范式化列
                    )
                    
                    if matched_items:
                        # 按日期分组保存
                        from collections import defaultdict
                        by_date = defaultdict(list)
                        for item in matched_items:
                            d = item.pop("trade_date")
                            if isinstance(d, str):
                                d = date.fromisoformat(d)
                            by_date[d].append(item)
                            
                        for match_date, items in by_date.items():
                            StockFilterService.save_filter_results(
                                db=db,
                                trade_date=match_date,
                                strategy_id=strategy.id,
                                strategy_name=strategy.name,
                                stock_data=items,
                                username=username
                            )
                            total_results += len(items)
                    
                    success_count += len(batch_codes)
                except Exception as e:
                    logger.error(f"批处理模式选股异常: codes={batch_codes[:2]}..., strategy={strategy.name}, error={e}")
                    failed_count += len(batch_codes)
                
                # 更新处理计数 (针对当前批次)
                processed_items += len(batch_codes)
                
                # 定期更新进度
                update_execution_progress(
                    db,
                    execution,
                    processed_items=processed_items,
                    total_items=original_total_items,
                    current_item=f"{strategy.name} | {batch_codes[0]}...",
                    message=f"策略 '{strategy.name}': 已处理 {min(i + batch_size, len(strategy_codes))}/{len(strategy_codes)}"
                )
            
            # 一个策略处理完后，将该策略中被“跳过”的股票份额补齐到进度中，确保进度条平滑进入下一个策略
            processed_items += skip_count
            logger.info(f"策略 '{strategy.name}' 执行完成，命中结果总数={total_results}")

        return {
            "success": True,
            "message": "批量选股任务完成",
            "total_days": len(trading_dates),
            "total_strategies": len(strategies),
            "total_results": total_results,
            "success_count": success_count,
            "failed_count": failed_count,
        }

    @classmethod
    def batch_execute_strategies(
        cls,
        db: Session,
        start_date: date | None = None,
        end_date: date | None = None,
        strategy_id: int | None = None,
        extra_info: dict[str, Any] | None = None,
        execution: TaskExecution | None = None,
    ) -> dict[str, Any]:
        """
        批量执行量化选股策略（支持多日期和指定策略）

        Args:
            db: 数据库会话
            start_date: 开始日期
            end_date: 结束日期
            strategy_id: 指定策略ID（可选）
            extra_info: 额外信息
            execution: 执行记录对象（可选）

        Returns:
            执行结果汇总
        """
        # 1. 处理日期范围
        if not start_date or not end_date:
            latest_date = cls.get_latest_trade_date(db)
            start_date = start_date or latest_date
            end_date = end_date or latest_date

        from zquant.utils.date_helper import DateHelper
        trading_dates = DateHelper.get_trading_dates(db, start_date, end_date)
        if not trading_dates:
            logger.info(f"在日期范围 {start_date} 至 {end_date} 内未找到交易日")
            return {"success": True, "message": "日期范围内无交易日", "total_days": 0, "total_results": 0}

        # 2. 获取策略列表
        if strategy_id:
            strategy = db.query(StockFilterStrategy).filter(StockFilterStrategy.id == strategy_id).first()
            strategies = [strategy] if strategy else []
        else:
            strategies = db.query(StockFilterStrategy).all()

        if not strategies:
            logger.info("未找到任何选股策略")
            return {"success": True, "message": "未找到有效策略", "total_strategies": 0, "total_results": 0}

        logger.info(f"开始批量选股任务: {len(trading_dates)} 个交易日, {len(strategies)} 个策略")

        # 3. 初始化进度
        total_days = len(trading_dates)
        total_strategies = len(strategies)
        total_items = total_days * total_strategies
        processed_items = 0
        total_results = 0
        success_count = 0
        failed_count = 0
        failed_details = []

        # 针对多日任务，启用股票优先优化模式
        if total_days > 1:
            logger.info(f"检测到多日选股任务 ({total_days}天)，启用股票优先优化模式...")
            return cls._execute_strategy_batch_stock_priority(
                db, trading_dates, strategies, extra_info, execution
            )

        update_execution_progress(
            db, 
            execution, 
            total_items=total_items, 
            processed_items=0, 
            message=f"开始批量选股任务: {len(trading_dates)}天 x {len(strategies)}个策略"
        )

        # 4. 循环执行
        for current_date in trading_dates:
            for strategy in strategies:
                processed_items += 1
                try:
                    # 更新进度
                    update_execution_progress(
                        db,
                        execution,
                        processed_items=processed_items - 1,
                        current_item=f"{current_date} | {strategy.name}",
                        message=f"正在执行: {strategy.name} ({current_date})",
                    )

                    # 记录日志
                    logger.info(
                        f"量化选股进度: {current_date} | {strategy.name} - "
                        f"已处理 {processed_items}/{total_items} "
                        f"(成功={success_count}, 失败={failed_count}, 总结果={total_results})"
                    )

                    res = cls.execute_strategy(
                        db=db, 
                        strategy=strategy, 
                        trade_date=current_date,
                        extra_info=extra_info,
                        execution=execution,
                    )
                    if res["success"]:
                        success_count += 1
                        total_results += res["count"]
                    else:
                        failed_count += 1
                        failed_details.append({
                            "date": str(current_date),
                            "strategy": strategy.name,
                            "error": res["message"]
                        })

                except Exception as e:
                    if "Task terminated" in str(e):
                        raise
                    logger.error(f"执行选股异常 ({current_date} | {strategy.name}): {e}")
                    failed_count += 1
                    failed_details.append({
                        "date": str(current_date),
                        "strategy": strategy.name,
                        "error": str(e)
                    })

        # 5. 完成更新
        update_execution_progress(
            db, 
            execution, 
            processed_items=total_items, 
            message=f"批量选股任务完成: 成功={success_count}, 失败={failed_count}, 总数={total_results}"
        )

        return {
            "success": failed_count == 0,
            "message": f"任务完成: 成功={success_count}, 失败={failed_count}, 结果={total_results}",
            "total_days": total_days,
            "total_strategies": total_strategies,
            "success_count": success_count,
            "failed_count": failed_count,
            "total_results": total_results,
            "failed_details": failed_details,
        }

    @classmethod
    def batch_execute_all_strategies(
        cls,
        db: Session,
        trade_date: date | None = None,
        extra_info: dict[str, Any] | None = None,
        execution: TaskExecution | None = None,
    ) -> dict[str, Any]:
        """
        批量执行所有量化选股策略并保存结果（为了兼容旧调用，转发给新方法）
        """
        return cls.batch_execute_strategies(
            db=db,
            start_date=trade_date,
            end_date=trade_date,
            extra_info=extra_info,
            execution=execution
        )

    @classmethod
    def get_latest_trade_date(cls, db: Session) -> date:
        """获取数据库中最小的有数据的交易日期（通常建议是最近的一个交易日）"""
        try:
            # 从 zq_data_tustock_daily 视图中获取最后一条交易记录的日期
            from zquant.models.data import TUSTOCK_DAILY_VIEW_NAME
            sql = f"SELECT MAX(trade_date) FROM `{TUSTOCK_DAILY_VIEW_NAME}`"
            result = db.execute(text(sql)).scalar()
            if result:
                if isinstance(result, str):
                    return date.fromisoformat(result)
                return result
        except Exception as e:
            logger.warning(f"获取最新交易日期失败: {e}")
        
        return date.today()
