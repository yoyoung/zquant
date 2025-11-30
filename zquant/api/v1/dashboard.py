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
系统大盘API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from zquant.api.deps import get_current_active_user
from zquant.database import get_db
from zquant.models.user import User
from zquant.schemas.dashboard import LatestDataResponse, LocalDataStatsResponse, SyncStatusResponse, TaskStatsResponse
from zquant.services.dashboard import DashboardService

router = APIRouter()


@router.get("/sync-status", response_model=SyncStatusResponse, summary="获取数据同步状态")
def get_sync_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取数据同步监控指标

    返回以下指标：
    - Tushare同步链路是否正常
    - 当日是否交易日
    - Tushare接口返回的最新日线行情数据的交易日期
    - 当日日线行情数据是否已准备就绪
    - 数据库中最新日线数据的交易日期
    """
    status = DashboardService.get_sync_status(db)
    return SyncStatusResponse(**status)


@router.get("/task-stats", response_model=TaskStatsResponse, summary="获取定时任务统计")
def get_task_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取当日定时任务统计

    返回以下指标：
    - 当日总任务数
    - 进行中任务数
    - 已完成任务数
    - 待运行任务数
    - 出错任务数
    """
    stats = DashboardService.get_task_stats(db)
    return TaskStatsResponse(**stats)


@router.get("/latest-data", response_model=LatestDataResponse, summary="获取本地数据最新信息")
def get_latest_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取本地数据最新信息

    返回以下数据：
    - 数据操作日志表中，按table_name分组，每个表的最新记录列表
    - 数据表统计表中，按table_name分组，每个表的最新记录列表
    """
    from zquant.schemas.dashboard import LatestOperationLogItem, LatestTableStatisticsItem

    data = DashboardService.get_latest_data_info(db)

    # 转换为Schema对象
    operation_logs = [LatestOperationLogItem(**item) for item in data["latest_operation_logs"]]
    table_statistics = [LatestTableStatisticsItem(**item) for item in data["latest_table_statistics"]]

    return LatestDataResponse(
        latest_operation_logs=operation_logs,
        latest_table_statistics=table_statistics,
    )


@router.get("/local-data-stats", response_model=LocalDataStatsResponse, summary="获取本地数据统计")
def get_local_data_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取本地数据统计指标

    返回以下指标：
    - 总表数
    - 成功操作数
    - 失败操作数
    - 总插入记录数
    - 总更新记录数
    - 分表数量
    - 总记录数
    - 日记录数
    """
    stats = DashboardService.get_local_data_stats(db)
    return LocalDataStatsResponse(**stats)

