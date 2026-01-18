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
分表管理服务

提供分表的自动管理功能，包括：
1. 检测新增的股票代码
2. 为新增代码批量初始化各类分表
3. 同步因子分表的列结构
4. 更新所有分表视图
"""

from loguru import logger
from sqlalchemy import text
from sqlalchemy.orm import Session

from zquant.data.storage_base import ensure_table_exists
from zquant.data.view_manager import (
    create_or_update_daily_basic_view,
    create_or_update_daily_view,
    create_or_update_factor_view,
    create_or_update_spacex_factor_view,
    create_or_update_stkfactorpro_view,
)
from zquant.database import engine
from zquant.models.data import (
    Tustock,
    create_spacex_factor_class,
    create_tustock_daily_basic_class,
    create_tustock_daily_class,
    create_tustock_factor_class,
    create_tustock_stkfactorpro_class,
    get_daily_basic_table_name,
    get_daily_table_name,
    get_factor_table_name,
    get_spacex_factor_table_name,
    get_stkfactorpro_table_name,
)
from zquant.models.scheduler import TaskExecution


class PartitionManager:
    """分表管理器"""

    @staticmethod
    def detect_new_stock_codes(db: Session) -> list[str]:
        """
        检测基础数据表中新增的股票代码（在分表中不存在的代码）

        Args:
            db: 数据库会话

        Returns:
            新增的股票代码列表（ts_code格式，如：['000001.SZ', '000002.SZ']）
        """
        try:
            # 1. 获取基础表中所有的 ts_code（不过滤状态，确保所有代码都能被检测到）
            query = text("SELECT ts_code FROM zq_data_tustock_stockbasic ORDER BY ts_code")
            result = db.execute(query)
            all_codes = [row[0] for row in result.fetchall()]

            if not all_codes:
                logger.info("基础数据表中没有股票代码")
                return []

            logger.info(f"基础数据表中共有 {len(all_codes)} 只股票")

            # 2. 获取数据库中已存在的分表（以 daily 分表为基准）
            query_tables = text("""
                SELECT TABLE_NAME 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name LIKE 'zq_data_tustock_daily_%'
                AND table_name != 'zq_data_tustock_daily_view'
            """)
            result = db.execute(query_tables)
            existing_tables = [row[0] for row in result.fetchall()]

            # 3. 从表名中提取已存在的代码
            existing_codes = set()
            for table in existing_tables:
                # 表名格式：zq_data_tustock_daily_000001
                code_part = table.replace("zq_data_tustock_daily_", "")
                # 从所有代码中查找匹配的完整 ts_code
                for ts_code in all_codes:
                    if ts_code.startswith(code_part):
                        existing_codes.add(ts_code)
                        break

            logger.info(f"已存在分表的股票数量: {len(existing_codes)}")

            # 4. 计算新增的代码
            new_codes = [code for code in all_codes if code not in existing_codes]

            if new_codes:
                logger.info(f"检测到 {len(new_codes)} 只新增股票: {new_codes[:10]}{'...' if len(new_codes) > 10 else ''}")
            else:
                logger.info("未检测到新增股票代码")

            return new_codes

        except Exception as e:
            logger.error(f"检测新增股票代码失败: {e}")
            return []

    @staticmethod
    def _get_spacex_factor_columns(db: Session) -> dict[str, Any]:
        """
        从 zq_quant_factor_definitions 表获取所有启用的因子列定义
        如果是组合因子，则展开其所有的子因子列
        """
        try:
            from sqlalchemy import text, inspect, Double
            from zquant.factor.calculators.factory import create_calculator
            
            inspector = inspect(db.get_bind())
            if "zq_quant_factor_definitions" not in inspector.get_table_names():
                return {}
            
            # 获取所有启用的因子定义
            query = text("SELECT factor_name, column_name, factor_type FROM zq_quant_factor_definitions WHERE enabled = 1")
            result = db.execute(query)
            
            columns = {}
            for row in result.fetchall():
                factor_name, column_name, factor_type = row
                
                if factor_type == "组合因子":
                    # 对于组合因子，通过计算器获取子列清单
                    try:
                        # 尝试创建一个临时的计算器实例来获取其输出列定义
                        # 注意：model_code 映射到 factor_name，或者在 factory 中有专门映射
                        calculator = create_calculator(factor_name)
                        sub_columns = calculator.get_output_columns()
                        if sub_columns:
                            columns.update(sub_columns)
                        else:
                            # 降级处理：如果没有定义子列，使用基础列名
                            columns[column_name] = Double
                    except Exception as calc_err:
                        logger.warning(f"获取组合因子 {factor_name} 子列清单失败: {calc_err}")
                        columns[column_name] = Double
                else:
                    # 普通单因子
                    if column_name:
                        columns[column_name] = Double
            
            return columns
        except Exception as e:
            logger.warning(f"获取因子列定义失败: {e}")
            return {}

    @staticmethod
    def init_partition_tables_for_codes(db: Session, codes: list[str]) -> dict:
        """
        为指定的股票代码批量初始化所有类型的分表

        Args:
            db: 数据库会话
            codes: 股票代码列表（如：['000001.SZ', '000002.SZ']）

        Returns:
            初始化结果字典，包含：
            - total: 处理的总代码数
            - success: 成功初始化的代码数
            - failed: 失败的代码列表
            - details: 详细信息
        """
        if not codes:
            return {"total": 0, "success": 0, "failed": [], "details": []}

        logger.info(f"开始为 {len(codes)} 只股票初始化分表...")

        total = len(codes)
        success_count = 0
        failed_codes = []
        details = []

        from zquant.models.data import (
            create_tustock_daily_class,
            create_tustock_daily_basic_class,
            create_tustock_factor_class,
            create_tustock_stkfactorpro_class,
            create_spacex_factor_class,
            get_daily_table_name,
            get_daily_basic_table_name,
            get_factor_table_name,
            get_stkfactorpro_table_name,
            get_spacex_factor_table_name,
        )
        from zquant.database import ensure_table_exists

        # 获取 SpaceX 因子的额外列
        spacex_columns = PartitionManager._get_spacex_factor_columns(db)
        if spacex_columns:
            logger.info(f"初始化 SpaceX 分表将包含 {len(spacex_columns)} 个因子列: {', '.join(spacex_columns.keys())}")

        for ts_code in codes:
            code_result = {
                "ts_code": ts_code,
                "daily": False,
                "daily_basic": False,
                "factor": False,
                "stkfactorpro": False,
                "spacex_factor": False,
                "errors": [],
            }

            try:
                # 1. 创建 Daily 分表
                try:
                    daily_table = get_daily_table_name(ts_code)
                    TustockDaily = create_tustock_daily_class(ts_code)
                    if ensure_table_exists(db, TustockDaily, daily_table):
                        code_result["daily"] = True
                        logger.debug(f"✓ 创建 Daily 分表: {daily_table}")
                except Exception as e:
                    code_result["errors"].append(f"Daily: {str(e)}")
                    logger.warning(f"创建 Daily 分表失败 {ts_code}: {e}")

                # 2. 创建 Daily Basic 分表
                try:
                    daily_basic_table = get_daily_basic_table_name(ts_code)
                    TustockDailyBasic = create_tustock_daily_basic_class(ts_code)
                    if ensure_table_exists(db, TustockDailyBasic, daily_basic_table):
                        code_result["daily_basic"] = True
                        logger.debug(f"✓ 创建 Daily Basic 分表: {daily_basic_table}")
                except Exception as e:
                    code_result["errors"].append(f"DailyBasic: {str(e)}")
                    logger.warning(f"创建 Daily Basic 分表失败 {ts_code}: {e}")

                # 3. 创建 Factor 分表
                try:
                    factor_table = get_factor_table_name(ts_code)
                    TustockFactor = create_tustock_factor_class(ts_code)
                    if ensure_table_exists(db, TustockFactor, factor_table):
                        code_result["factor"] = True
                        logger.debug(f"✓ 创建 Factor 分表: {factor_table}")
                except Exception as e:
                    code_result["errors"].append(f"Factor: {str(e)}")
                    logger.warning(f"创建 Factor 分表失败 {ts_code}: {e}")

                # 4. 创建 StkFactorPro 分表
                try:
                    stkfactorpro_table = get_stkfactorpro_table_name(ts_code)
                    TustockStkFactorPro = create_tustock_stkfactorpro_class(ts_code)
                    if ensure_table_exists(db, TustockStkFactorPro, stkfactorpro_table):
                        code_result["stkfactorpro"] = True
                        logger.debug(f"✓ 创建 StkFactorPro 分表: {stkfactorpro_table}")
                except Exception as e:
                    code_result["errors"].append(f"StkFactorPro: {str(e)}")
                    logger.warning(f"创建 StkFactorPro 分表失败 {ts_code}: {e}")

                # 5. 创建 SpaceX Factor 分表（包含因子列）
                try:
                    spacex_table = get_spacex_factor_table_name(ts_code)
                    SpacexFactor = create_spacex_factor_class(ts_code, extra_columns=spacex_columns)
                    if ensure_table_exists(db, SpacexFactor, spacex_table):
                        code_result["spacex_factor"] = True
                        logger.debug(f"✓ 创建 SpaceX Factor 分表: {spacex_table}")
                except Exception as e:
                    code_result["errors"].append(f"SpacexFactor: {str(e)}")
                    logger.warning(f"创建 SpaceX Factor 分表失败 {ts_code}: {e}")

                # 判断是否成功（至少有一个分表创建成功）
                if any([code_result["daily"], code_result["daily_basic"], code_result["factor"],
                       code_result["stkfactorpro"], code_result["spacex_factor"]]):
                    success_count += 1
                    logger.info(f"✓ 成功为 {ts_code} 初始化分表")
                else:
                    failed_codes.append(ts_code)
                    logger.error(f"✗ 为 {ts_code} 初始化分表全部失败")

            except Exception as e:
                code_result["errors"].append(f"整体失败: {str(e)}")
                failed_codes.append(ts_code)
                logger.error(f"为 {ts_code} 初始化分表失败: {e}")

            details.append(code_result)

        logger.info(f"分表初始化完成: 总计 {total} 只，成功 {success_count} 只，失败 {len(failed_codes)} 只")

        return {
            "total": total,
            "success": success_count,
            "failed": failed_codes,
            "details": details,
        }

    @staticmethod
    def update_all_views(db: Session) -> dict:
        """
        更新所有分表对应的视图

        Args:
            db: 数据库会话

        Returns:
            更新结果字典，包含各视图的更新状态
        """
        logger.info("开始更新所有分表视图...")

        results = {
            "daily_view": False,
            "daily_basic_view": False,
            "factor_view": False,
            "stkfactorpro_view": False,
            "spacex_factor_view": False,
        }

        try:
            # 1. 更新 Daily 视图
            try:
                if create_or_update_daily_view(db):
                    results["daily_view"] = True
                    logger.info("✓ 更新 Daily 视图成功")
                else:
                    logger.warning("⚠ 更新 Daily 视图失败")
            except Exception as e:
                logger.error(f"更新 Daily 视图异常: {e}")

            # 2. 更新 Daily Basic 视图
            try:
                if create_or_update_daily_basic_view(db):
                    results["daily_basic_view"] = True
                    logger.info("✓ 更新 Daily Basic 视图成功")
                else:
                    logger.warning("⚠ 更新 Daily Basic 视图失败")
            except Exception as e:
                logger.error(f"更新 Daily Basic 视图异常: {e}")

            # 3. 更新 Factor 视图
            try:
                if create_or_update_factor_view(db):
                    results["factor_view"] = True
                    logger.info("✓ 更新 Factor 视图成功")
                else:
                    logger.warning("⚠ 更新 Factor 视图失败")
            except Exception as e:
                logger.error(f"更新 Factor 视图异常: {e}")

            # 4. 更新 StkFactorPro 视图
            try:
                if create_or_update_stkfactorpro_view(db):
                    results["stkfactorpro_view"] = True
                    logger.info("✓ 更新 StkFactorPro 视图成功")
                else:
                    logger.warning("⚠ 更新 StkFactorPro 视图失败")
            except Exception as e:
                logger.error(f"更新 StkFactorPro 视图异常: {e}")

            # 5. 更新 SpaceX Factor 视图
            try:
                if create_or_update_spacex_factor_view(db):
                    results["spacex_factor_view"] = True
                    logger.info("✓ 更新 SpaceX Factor 视图成功")
                else:
                    logger.warning("⚠ 更新 SpaceX Factor 视图失败")
            except Exception as e:
                logger.error(f"更新 SpaceX Factor 视图异常: {e}")

        except Exception as e:
            logger.error(f"更新视图过程异常: {e}")

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"视图更新完成: {success_count}/{len(results)} 个视图更新成功")

        return results

    @staticmethod
    def sync_spacex_factor_columns(db: Session, execution: TaskExecution | None = None) -> dict:
        """
        同步所有 SpaceX Factor 分表的列结构，确保所有分表的列一致

        这个方法会：
        1. 获取所有 zq_quant_factor_spacex_* 分表
        2. 分析所有分表的列，找出所有唯一的列
        3. 为缺少列的分表添加相应的列
        4. 更新视图

        Args:
            db: 数据库会话
            execution: 执行记录对象（可选）

        Returns:
            同步结果字典，包含：
            - tables_processed: 处理的表数量
            - columns_found: 发现的唯一列总数
            - columns_added: 添加的列总数
            - details: 详细信息
        """
        from zquant.scheduler.utils import update_execution_progress

        logger.info("开始同步 SpaceX Factor 分表列结构...")
        update_execution_progress(db, execution, message="开始分析 SpaceX Factor 分表结构...")

        try:
            # 1. 获取所有 SpaceX Factor 分表
            query = text("""
                SELECT TABLE_NAME 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name LIKE 'zq_quant_factor_spacex_%'
                AND table_name != 'zq_quant_factor_spacex_view'
                ORDER BY table_name
            """)
            result = db.execute(query)
            tables = [row[0] for row in result.fetchall()]

            if not tables:
                logger.info("未找到 SpaceX Factor 分表，跳过列同步")
                update_execution_progress(db, execution, message="未找到分表，跳过同步")
                return {"tables_processed": 0, "columns_found": 0, "columns_added": 0, "details": []}

            logger.info(f"找到 {len(tables)} 个 SpaceX Factor 分表")
            update_execution_progress(db, execution, message=f"找到 {len(tables)} 个分表，正在获取列信息...")

            # 2. 获取所有分表的列信息
            all_columns = {}  # {table_name: {column_name: column_info}}
            base_columns = {"id", "ts_code", "trade_date", "created_by", "created_time", "updated_by", "updated_time"}

            for i, table in enumerate(tables, 1):
                if i % 10 == 0 or i == len(tables):
                    update_execution_progress(
                        db,
                        execution,
                        processed_items=0,  # 第一阶段不计入最终总数
                        message=f"分析表结构: {table} ({i}/{len(tables)})",
                    )

                query_cols = text(f"""
                    SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_COMMENT
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE()
                    AND table_name = :table_name
                    ORDER BY ORDINAL_POSITION
                """)
                result = db.execute(query_cols, {"table_name": table})
                columns = {}
                for row in result.fetchall():
                    col_name = row[0]
                    if col_name not in base_columns:  # 只关注因子列
                        columns[col_name] = {
                            "type": row[1],
                            "nullable": row[2],
                            "comment": row[3] or "",
                        }
                all_columns[table] = columns

            # 3. 找出所有唯一的因子列
            unique_columns = {}
            for table, cols in all_columns.items():
                for col_name, col_info in cols.items():
                    if col_name not in unique_columns:
                        unique_columns[col_name] = col_info

            logger.info(f"发现 {len(unique_columns)} 个唯一的因子列")
            update_execution_progress(
                db, execution, message=f"分析完成: 发现 {len(unique_columns)} 个唯一因子列，开始同步..."
            )

            # 4. 为每个分表添加缺失的列
            total_columns_added = 0
            details = []

            for i, table in enumerate(tables, 1):
                if i % 10 == 0 or i == len(tables):
                    update_execution_progress(
                        db,
                        execution,
                        processed_items=i - 1,
                        total_items=len(tables),
                        current_item=table,
                        message=f"正在同步列结构: {table} ({i}/{len(tables)})",
                    )

                table_cols = all_columns[table]
                missing_cols = {k: v for k, v in unique_columns.items() if k not in table_cols}

                if not missing_cols:
                    logger.debug(f"表 {table} 的列已是最新，无需添加")
                    continue

                added_count = 0
                errors = []

                for col_name, col_info in missing_cols.items():
                    try:
                        # 构建 ALTER TABLE 语句
                        nullable = "NULL" if col_info["nullable"] == "YES" else "NOT NULL"
                        comment = col_info["comment"].replace("'", "''")  # 转义单引号
                        
                        alter_sql = f"""
                            ALTER TABLE `{table}` 
                            ADD COLUMN `{col_name}` {col_info['type']} {nullable} 
                            COMMENT '{comment}'
                        """
                        
                        db.execute(text(alter_sql))
                        db.commit()
                        added_count += 1
                        total_columns_added += 1
                        logger.debug(f"✓ 为表 {table} 添加列: {col_name}")
                        
                    except Exception as e:
                        errors.append(f"{col_name}: {str(e)}")
                        logger.warning(f"为表 {table} 添加列 {col_name} 失败: {e}")
                        db.rollback()

                if added_count > 0:
                    logger.info(f"✓ 为表 {table} 添加了 {added_count} 个列")

                details.append({
                    "table": table,
                    "columns_added": added_count,
                    "errors": errors,
                })

            update_execution_progress(db, execution, processed_items=len(tables), message="列结构同步完成")

            logger.info(f"列同步完成: 处理 {len(tables)} 个表，共添加 {total_columns_added} 个列")

            return {
                "tables_processed": len(tables),
                "columns_found": len(unique_columns),
                "columns_added": total_columns_added,
                "details": details,
            }

        except Exception as e:
            logger.error(f"同步 SpaceX Factor 列结构失败: {e}")
            db.rollback()
            return {"tables_processed": 0, "columns_found": 0, "columns_added": 0, "details": [], "error": str(e)}
