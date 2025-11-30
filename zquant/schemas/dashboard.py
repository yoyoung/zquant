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
系统大盘相关Pydantic模型
"""

from pydantic import BaseModel, Field


class SyncStatusResponse(BaseModel):
    """数据同步状态响应"""

    tushare_connection_status: bool = Field(..., description="Tushare同步链路是否正常")
    is_trading_day: bool = Field(..., description="当日是否交易日")
    latest_trade_date_from_api: str | None = Field(None, description="Tushare接口返回的最新日线行情数据的交易日期（YYYY-MM-DD格式）")
    today_data_ready: bool = Field(..., description="当日日线行情数据是否已准备就绪")
    latest_trade_date_in_db: str | None = Field(None, description="数据库中最新日线数据的交易日期（YYYY-MM-DD格式）")


class TaskStatsResponse(BaseModel):
    """定时任务统计响应"""

    total_tasks: int = Field(..., description="当日总任务数（当日所有执行记录数）")
    running_tasks: int = Field(..., description="进行中任务数（status=RUNNING）")
    completed_tasks: int = Field(..., description="已完成任务数（status=SUCCESS）")
    pending_tasks: int = Field(..., description="待运行任务数（status=PENDING）")
    failed_tasks: int = Field(..., description="出错任务数（status=FAILED）")


class LatestOperationLogItem(BaseModel):
    """最新操作日志项"""

    id: int | None = Field(None, description="日志ID")
    table_name: str | None = Field(None, description="数据表名")
    operation_type: str | None = Field(None, description="操作类型")
    operation_result: str | None = Field(None, description="操作结果")
    insert_count: int = Field(0, description="插入记录数")
    update_count: int = Field(0, description="更新记录数")
    delete_count: int = Field(0, description="删除记录数")
    start_time: str | None = Field(None, description="开始时间（ISO格式）")
    end_time: str | None = Field(None, description="结束时间（ISO格式）")
    duration_seconds: float | None = Field(None, description="耗时(秒)")
    created_by: str | None = Field(None, description="创建人")
    created_time: str | None = Field(None, description="创建时间（ISO格式）")


class LatestTableStatisticsItem(BaseModel):
    """最新表统计项"""

    stat_date: str | None = Field(None, description="统计日期（ISO格式）")
    table_name: str = Field(..., description="表名")
    is_split_table: bool = Field(False, description="是否分表")
    split_count: int = Field(0, description="分表个数")
    total_records: int = Field(0, description="总记录数")
    daily_records: int = Field(0, description="日记录数")
    daily_insert_count: int = Field(0, description="日新增记录数")
    daily_update_count: int = Field(0, description="日更新记录数")
    created_by: str | None = Field(None, description="创建人")
    created_time: str | None = Field(None, description="创建时间（ISO格式）")
    updated_time: str | None = Field(None, description="更新时间（ISO格式）")


class LatestDataResponse(BaseModel):
    """本地数据最新信息响应"""

    latest_operation_logs: list[LatestOperationLogItem] = Field(
        ..., description="数据操作日志表中，按table_name分组，每个表的最新记录列表"
    )
    latest_table_statistics: list[LatestTableStatisticsItem] = Field(
        ..., description="数据表统计表中，按table_name分组，每个表的最新记录列表"
    )


class LocalDataStatsResponse(BaseModel):
    """本地数据统计响应"""

    total_tables: int = Field(..., description="总表数（有操作日志或统计的表数量，去重）")
    success_operations: int = Field(..., description="成功操作数（操作结果为success的记录数）")
    failed_operations: int = Field(..., description="失败操作数（操作结果为failed的记录数）")
    total_insert_count: int = Field(..., description="总插入记录数（所有操作日志的插入记录数之和）")
    total_update_count: int = Field(..., description="总更新记录数（所有操作日志的更新记录数之和）")
    split_tables_count: int = Field(..., description="分表数量（is_split_table=true的表数）")
    total_records_sum: int = Field(..., description="总记录数（所有表统计的总记录数之和）")
    daily_records_sum: int = Field(..., description="日记录数（所有表统计的日记录数之和）")

