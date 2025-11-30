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
回测相关数据库模型
"""

import enum

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.mysql import DOUBLE as Double
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from zquant.database import Base


class BacktestStatus(str, enum.Enum):
    """回测任务状态"""

    PENDING = "pending"  # 等待中
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class BacktestTask(Base):
    """回测任务表"""

    __tablename__ = "zq_backtest_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("zq_app_users.id"), nullable=False, index=True)
    strategy_id = Column(Integer, ForeignKey("zq_backtest_strategies.id"), nullable=True, index=True)  # 关联策略ID（可选）
    strategy_code = Column(Text, nullable=False)  # 策略代码（Python代码字符串）
    strategy_name = Column(String(100), nullable=True)  # 策略名称
    config_json = Column(Text, nullable=False)  # 回测配置（JSON格式）
    status = Column(SQLEnum(BacktestStatus), default=BacktestStatus.PENDING, nullable=False, index=True)
    error_message = Column(Text, nullable=True)  # 错误信息
    started_at = Column(DateTime, nullable=True)  # 开始时间
    completed_at = Column(DateTime, nullable=True)  # 完成时间
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    user = relationship("User", back_populates="backtest_tasks")
    strategy = relationship("Strategy", foreign_keys=[strategy_id])
    result = relationship("BacktestResult", back_populates="task", uselist=False, cascade="all, delete-orphan")


class Strategy(Base):
    """策略表"""

    __tablename__ = "zq_backtest_strategies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("zq_app_users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)  # 策略名称
    description = Column(Text, nullable=True)  # 策略描述
    category = Column(String(50), nullable=True, index=True)  # 策略分类：technical, fundamental, quantitative, etc.
    code = Column(Text, nullable=False)  # 策略代码（Python代码字符串）
    params_schema = Column(Text, nullable=True)  # 策略参数Schema（JSON格式）
    is_template = Column(Boolean, default=False, nullable=False, index=True)  # 是否为模板策略
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    user = relationship("User", back_populates="strategies")


class BacktestResult(Base):
    """回测结果表"""

    __tablename__ = "zq_backtest_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("zq_backtest_tasks.id"), unique=True, nullable=False, index=True)

    # 核心指标
    total_return = Column(Double, nullable=True)  # 累计收益率
    annual_return = Column(Double, nullable=True)  # 年化收益率
    max_drawdown = Column(Double, nullable=True)  # 最大回撤
    sharpe_ratio = Column(Double, nullable=True)  # 夏普比率
    win_rate = Column(Double, nullable=True)  # 胜率
    profit_loss_ratio = Column(Double, nullable=True)  # 盈亏比
    alpha = Column(Double, nullable=True)  # Alpha
    beta = Column(Double, nullable=True)  # Beta

    # JSON数据
    metrics_json = Column(Text, nullable=True)  # 详细指标（JSON格式）
    trades_json = Column(Text, nullable=True)  # 交易记录（JSON格式）
    portfolio_json = Column(Text, nullable=True)  # 每日投资组合（JSON格式）

    created_at = Column(DateTime, default=func.now(), nullable=False)

    # 关系
    task = relationship("BacktestTask", back_populates="result")
