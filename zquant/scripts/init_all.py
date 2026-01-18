# Copyright 2025 ZQuant Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the Apache License is distributed on an "AS IS" BASIS,
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
一键初始化脚本
整合所有初始化功能，确保一次执行即可完成所有初始化操作

使用方法：
    python zquant/scripts/init_all.py                    # 默认执行核心初始化（Mini 模式）
    python zquant/scripts/init_all.py --full            # 执行完整初始化（包含非核心步骤）
    python zquant/scripts/init_all.py --skip-view        # 跳过视图初始化
    python zquant/scripts/init_all.py --skip-factor     # 跳过因子初始化
    python zquant/scripts/init_all.py --skip-strategies # 跳过策略模板初始化
    python zquant/scripts/init_all.py --force           # 强制模式（传递给子脚本）
    python zquant/scripts/init_all.py --stop-on-error    # 遇到错误立即停止
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
script_dir = Path(__file__).resolve().parent  # zquant/scripts
zquant_dir = script_dir.parent  # zquant 目录
project_root = zquant_dir.parent  # 项目根目录
sys.path.insert(0, str(project_root))

from loguru import logger

# 导入各个初始化模块的函数
from zquant.scripts.init_db import init_database
from zquant.scripts.init_scheduler import create_tables as create_scheduler_tables, create_zquant_tasks
from zquant.scripts.init_view import (
    create_daily_view,
    create_daily_basic_view,
    create_factor_view,
    create_stkfactorpro_view,
    create_spacex_factor_view,
)
from zquant.scripts.init_factor import (
    create_tables as create_factor_tables,
    create_turnover_rate_factor,
    create_hyper_activity_factor,
)
from zquant.scripts.init_stock_filter import init_stock_filter_strategies
from zquant.scripts.init_strategies import init_strategies

from zquant.database import SessionLocal
from zquant.models.user import User


def init_database_step(force: bool = False) -> bool:
    """步骤1: 初始化数据库（创建数据库、表、角色权限、管理员用户）"""
    logger.info("=" * 60)
    logger.info("步骤 1/5: 数据库初始化")
    logger.info("=" * 60)
    try:
        success = init_database()
        if success:
            logger.info("✓ 数据库初始化完成")
        else:
            logger.error("✗ 数据库初始化失败")
        return success
    except Exception as e:
        logger.error(f"✗ 数据库初始化异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def init_factor_step(force: bool = False) -> bool:
    """步骤2: 初始化因子系统"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("步骤 2/6: 因子系统初始化")
    logger.info("=" * 60)
    try:
        # 创建因子相关表
        if not create_factor_tables():
            logger.error("✗ 创建因子相关表失败")
            return False
        
        # 创建换手率因子
        if not create_turnover_rate_factor(force=force):
            logger.error("✗ 创建换手率因子失败")
            return False
        
        # 创建超活跃组合因子
        if not create_hyper_activity_factor(force=force):
            logger.warning("⚠ 创建超活跃组合因子失败（不影响整体流程）")
        
        logger.info("✓ 因子系统初始化完成")
        return True
    except Exception as e:
        logger.error(f"✗ 因子系统初始化异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def init_stock_filter_step(force: bool = False) -> bool:
    """步骤3: 初始化选股系统"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("步骤 3/6: 选股系统初始化")
    logger.info("=" * 60)
    try:
        if init_stock_filter_strategies(force=force):
            logger.info("✓ 选股系统初始化完成")
            return True
        else:
            logger.error("✗ 选股系统初始化失败")
            return False
    except Exception as e:
        logger.error(f"✗ 选股系统初始化异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def init_scheduler_step(force: bool = False, mini: bool = False) -> bool:
    """步骤4: 初始化定时任务系统"""
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"步骤 4/6: 定时任务系统初始化{' (Mini 模式)' if mini else ''}")
    logger.info("=" * 60)
    try:
        # 创建定时任务表
        if not create_scheduler_tables():
            logger.error("✗ 创建定时任务表失败")
            return False
        
        # 创建ZQuant任务
        if not create_zquant_tasks(force=force, mini=mini):
            logger.error("✗ 创建ZQuant任务失败")
            return False
        
        logger.info("✓ 定时任务系统初始化完成")
        return True
    except Exception as e:
        logger.error(f"✗ 定时任务系统初始化异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def init_view_step(force: bool = False, mini: bool = False) -> bool:
    """步骤5: 初始化数据视图"""
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"步骤 5/6: 数据视图初始化{' (Mini 模式)' if mini else ''}")
    logger.info("=" * 60)
    db = SessionLocal()
    try:
        # 1. 调用视图创建函数
        # 注意：这些函数在 init_view.py 中已经被优化为优先使用 Python 直接创建
        if not create_daily_view(db, force=force):
            logger.warning("⚠ 创建日线数据视图失败（可能没有数据表）")
        
        if not create_daily_basic_view(db, force=force):
            logger.warning("⚠ 创建每日指标数据视图失败（可能没有数据表）")
        
        if not create_factor_view(db, force=force):
            logger.warning("⚠ 创建因子数据视图失败（可能没有数据表）")
        
        # Mini 模式跳过 stkfactorpro
        if not mini:
            if not create_stkfactorpro_view(db, force=force):
                logger.warning("⚠ 创建专业版因子数据视图失败（可能没有数据表）")
        
        if not create_spacex_factor_view(db, force=force):
            logger.warning("⚠ 创建自定义量化因子结果视图失败（可能没有数据表）")
        
        logger.info("✓ 数据视图初始化完成")
        return True
    except Exception as e:
        logger.error(f"✗ 数据视图初始化异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def init_strategies_step(force: bool = False) -> bool:
    """步骤6: 初始化策略模板"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("步骤 6/6: 策略模板初始化")
    logger.info("=" * 60)
    db = SessionLocal()
    try:
        # 获取管理员用户
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            logger.error("✗ 未找到管理员用户，请先执行数据库初始化")
            return False
        
        # 初始化策略模板
        init_strategies(db, admin_user.id)
        db.commit()
        
        logger.info("✓ 策略模板初始化完成")
        return True
    except Exception as e:
        logger.error(f"✗ 策略模板初始化异常: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="一键初始化脚本 - 整合所有初始化功能",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python zquant/scripts/init_all.py                    # 默认执行核心初始化（Mini 模式）
  python zquant/scripts/init_all.py --full            # 执行完整初始化
  python zquant/scripts/init_all.py --skip-view        # 跳过视图初始化
  python zquant/scripts/init_all.py --skip-factor      # 跳过因子初始化
  python zquant/scripts/init_all.py --skip-strategies  # 跳过策略模板初始化
  python zquant/scripts/init_all.py --force            # 强制模式
  python zquant/scripts/init_all.py --stop-on-error    # 遇到错误立即停止
        """,
    )
    
    parser.add_argument("--skip-db", action="store_true", help="跳过数据库初始化")
    parser.add_argument("--skip-factor", action="store_true", help="跳过因子初始化")
    parser.add_argument("--skip-stock-filter", action="store_true", help="跳过选股系统初始化")
    parser.add_argument("--skip-scheduler", action="store_true", help="跳过定时任务初始化")
    parser.add_argument("--skip-view", action="store_true", help="跳过视图初始化")
    parser.add_argument("--skip-strategies", action="store_true", help="跳过策略模板初始化")
    parser.add_argument("--full", action="store_true", help="完整模式（包括所有非核心初始化步骤）")
    parser.add_argument("--force", action="store_true", help="强制模式（传递给子脚本）")
    parser.add_argument("--stop-on-error", action="store_true", help="遇到错误立即停止")
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("ZQuant 一键初始化脚本")
    logger.info("=" * 60)
    logger.info("")
    
    # 执行步骤记录
    steps_executed = []
    steps_failed = []
    
    # 步骤1: 数据库初始化（必须执行，不能跳过）
    if not args.skip_db:
        success = init_database_step(force=args.force)
        steps_executed.append(("数据库初始化", success))
        if not success:
            steps_failed.append("数据库初始化")
            if args.stop_on_error:
                logger.error("遇到错误，停止执行")
                sys.exit(1)
    else:
        logger.warning("⚠ 跳过数据库初始化（不推荐）")
    
    # 步骤2: 因子初始化
    if not args.skip_factor:
        success = init_factor_step(force=args.force)
        steps_executed.append(("因子初始化", success))
        if not success:
            steps_failed.append("因子初始化")
            if args.stop_on_error:
                logger.error("遇到错误，停止执行")
                sys.exit(1)
    else:
        logger.info("⊘ 跳过因子初始化")

    # 步骤3: 选股系统初始化
    if not args.skip_stock_filter:
        success = init_stock_filter_step(force=args.force)
        steps_executed.append(("选股系统初始化", success))
        if not success:
            steps_failed.append("选股系统初始化")
            if args.stop_on_error:
                logger.error("遇到错误，停止执行")
                sys.exit(1)
    else:
        logger.info("⊘ 跳过选股系统初始化")
    
    # 步骤4: 定时任务初始化
    if not args.skip_scheduler:
        success = init_scheduler_step(force=args.force, mini=not args.full)
        steps_executed.append(("定时任务初始化", success))
        if not success:
            steps_failed.append("定时任务初始化")
            if args.stop_on_error:
                logger.error("遇到错误，停止执行")
                sys.exit(1)
    else:
        logger.info("⊘ 跳过定时任务初始化")
    
    # 步骤5: 视图初始化
    if not args.skip_view:
        success = init_view_step(force=args.force, mini=not args.full)
        steps_executed.append(("视图初始化", success))
        if not success:
            steps_failed.append("视图初始化")
            if args.stop_on_error:
                logger.error("遇到错误，停止执行")
                sys.exit(1)
    else:
        logger.info("⊘ 跳过视图初始化")
    
    # 步骤6: 策略模板初始化
    if not args.skip_strategies:
        success = init_strategies_step(force=args.force)
        steps_executed.append(("策略模板初始化", success))
        if not success:
            steps_failed.append("策略模板初始化")
            if args.stop_on_error:
                logger.error("遇到错误，停止执行")
                sys.exit(1)
    else:
        logger.info("⊘ 跳过策略模板初始化")
    
    # 输出执行摘要
    logger.info("")
    logger.info("=" * 60)
    logger.info("初始化执行摘要")
    logger.info("=" * 60)
    
    for step_name, success in steps_executed:
        status = "✓ 成功" if success else "✗ 失败"
        logger.info(f"{status}: {step_name}")
    
    if steps_failed:
        logger.error("")
        logger.error(f"以下步骤执行失败: {', '.join(steps_failed)}")
        logger.error("请检查上面的错误信息并修复问题后重试")
        sys.exit(1)
    else:
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ 所有初始化步骤执行完成！")
        logger.info("=" * 60)
        logger.info("")
        logger.info("提示：")
        logger.info("  - 默认管理员账号: admin / admin123（请及时修改密码）")
        logger.info("  - 访问 http://localhost:8000/docs 查看API文档")
        logger.info("  - 访问 http://localhost:8000/admin/scheduler 管理定时任务")
        logger.info("  - 访问 http://localhost:8000/factor 管理因子")
        logger.info("  - 访问 http://localhost:8000/backtest/strategies 查看策略模板")
        logger.info("")
        logger.info("数据同步提示：")
        logger.info("  - 初始化脚本仅创建了表结构和基本配置。")
        logger.info("  - 如果您需要同步 Tushare 历史数据进行测试，请运行：")
        logger.info("    python zquant/scripts/seed_data.py")
        logger.info("  - 或者使用定时任务系统进行数据同步。")


if __name__ == "__main__":
    main()
