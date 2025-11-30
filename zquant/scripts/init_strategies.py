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
策略模板初始化脚本
将示例策略导入为系统模板策略
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
# 脚本位于 zquant/scripts/init_strategies.py
# 需要将项目根目录（包含 zquant 目录的目录）添加到路径，而不是 zquant 目录本身
script_dir = Path(__file__).resolve().parent  # zquant/scripts
zquant_dir = script_dir.parent  # zquant 目录
project_root = zquant_dir.parent  # 项目根目录（包含 zquant 目录的目录）
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from zquant.database import SessionLocal
from zquant.models.backtest import Strategy
from zquant.models.user import User
from zquant.services.strategy import StrategyService


# 策略模板配置
STRATEGY_TEMPLATES = [
    {
        "name": "简单均线策略",
        "description": "当短期均线上穿长期均线时买入，下穿时卖出。适合趋势明显的市场。",
        "category": "technical",
        "file": "simple_ma.py",
    },
    {
        "name": "双均线策略（增强版）",
        "description": "双均线策略的增强版本，增加了趋势过滤和仓位管理。",
        "category": "technical",
        "file": "dual_ma.py",
    },
    {
        "name": "动量策略",
        "description": "买入过去N天收益率最高的股票，卖出收益率最低的股票。适合趋势延续的市场。",
        "category": "quantitative",
        "file": "momentum.py",
    },
    {
        "name": "PE/PB价值策略",
        "description": "基于PE/PB的价值投资策略，买入低估值股票。需要启用每日指标数据。",
        "category": "fundamental",
        "file": "pe_pb_strategy.py",
    },
    {
        "name": "换手率策略",
        "description": "基于换手率的策略，买入高换手率股票（活跃度高），卖出低换手率股票。需要启用每日指标数据。",
        "category": "fundamental",
        "file": "turnover_rate_strategy.py",
    },
    {
        "name": "均值回归策略",
        "description": "当价格偏离均值超过阈值时，预期价格会回归均值，进行反向交易。适合震荡市场。",
        "category": "quantitative",
        "file": "mean_reversion.py",
    },
    {
        "name": "布林带策略",
        "description": "当价格触及下轨时买入，触及上轨时卖出。适合波动较大的市场。",
        "category": "technical",
        "file": "bollinger_bands.py",
    },
    {
        "name": "RSI策略",
        "description": "当RSI低于超卖线时买入，高于超买线时卖出。适合判断超买超卖状态。",
        "category": "technical",
        "file": "rsi_strategy.py",
    },
    {
        "name": "网格交易策略",
        "description": "在价格区间内设置网格，价格下跌时买入，上涨时卖出，赚取波动收益。适合震荡市场。",
        "category": "quantitative",
        "file": "grid_trading.py",
    },
]


def read_strategy_code(file_path: Path) -> str:
    """读取策略代码文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def init_strategies(db: Session, admin_user_id: int):
    """初始化策略模板"""
    examples_dir = project_root / "zquant" / "strategy" / "examples"

    created_count = 0
    updated_count = 0

    for template in STRATEGY_TEMPLATES:
        file_path = examples_dir / template["file"]

        if not file_path.exists():
            print(f"警告: 策略文件不存在: {file_path}")
            continue

        # 读取策略代码
        code = read_strategy_code(file_path)

        # 检查策略是否已存在（按名称）
        existing = db.query(Strategy).filter(Strategy.name == template["name"], Strategy.is_template == True).first()

        if existing:
            # 更新现有策略
            StrategyService.update_strategy(
                db,
                existing.id,
                admin_user_id,
                code=code,
                description=template["description"],
                category=template["category"],
            )
            updated_count += 1
            print(f"更新策略模板: {template['name']}")
        else:
            # 创建新策略
            StrategyService.create_strategy(
                db,
                admin_user_id,
                template["name"],
                code,
                description=template["description"],
                category=template["category"],
                is_template=True,
            )
            created_count += 1
            print(f"创建策略模板: {template['name']}")

    print(f"\n策略模板初始化完成: 创建 {created_count} 个，更新 {updated_count} 个")


def main():
    """主函数"""
    db = SessionLocal()
    try:
        # 获取管理员用户（假设第一个用户是管理员，或使用特定用户名）
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            # 如果没有admin用户，使用第一个用户
            admin_user = db.query(User).first()

        if not admin_user:
            print("错误: 未找到用户，请先创建用户")
            return

        print(f"使用用户: {admin_user.username} (ID: {admin_user.id})")
        init_strategies(db, admin_user.id)
        db.commit()
    except Exception as e:
        print(f"错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
