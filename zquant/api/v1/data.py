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
数据服务API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from zquant.api.decorators import convert_to_response_items, handle_data_api_error
from zquant.api.deps import get_current_active_user
from zquant.database import get_db
from zquant.models.user import User
from zquant.schemas.data import (
    CalendarItem,
    CalendarRequest,
    CalendarResponse,
    CalendarFetchRequest,
    CalendarFetchResponse,
    CalendarValidateRequest,
    CalendarValidateResponse,
    DailyBasicItem,
    DailyBasicRequest,
    DailyBasicResponse,
    DailyBasicFetchRequest,
    DailyBasicFetchResponse,
    DailyBasicValidateRequest,
    DailyBasicValidateResponse,
    DailyDataItem,
    DailyDataRequest,
    DailyDataResponse,
    DailyDataFetchRequest,
    DailyDataFetchResponse,
    DailyDataValidateRequest,
    DailyDataValidateResponse,
    DataOperationLogItem,
    DataOperationLogRequest,
    DataOperationLogResponse,
    FactorDataItem,
    FactorDataRequest,
    FactorDataResponse,
    FactorDataFetchRequest,
    FactorDataFetchResponse,
    FactorDataValidateRequest,
    FactorDataValidateResponse,
    FundamentalsRequest,
    FundamentalsResponse,
    FundamentalsFetchRequest,
    FundamentalsFetchResponse,
    FundamentalsValidateRequest,
    FundamentalsValidateResponse,
    StatisticsTableDataRequest,
    StatisticsTableDataResponse,
    StkFactorProDataItem,
    StkFactorProDataRequest,
    StkFactorProDataResponse,
    StkFactorProDataFetchRequest,
    StkFactorProDataFetchResponse,
    StkFactorProDataValidateRequest,
    StkFactorProDataValidateResponse,
    StockListRequest,
    StockListResponse,
    StockListFetchRequest,
    StockListFetchResponse,
    StockListValidateRequest,
    StockListValidateResponse,
    TableStatisticsItem,
    TableStatisticsRequest,
    TableStatisticsResponse,
)
from zquant.services.data import DataService

router = APIRouter()


@router.post("/fundamentals", response_model=FundamentalsResponse, summary="获取财务数据")
@handle_data_api_error
def get_fundamentals(
    request: FundamentalsRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """获取财务数据"""
    result = DataService.get_fundamentals(db, request.symbols, request.statement_type, request.report_date)
    return FundamentalsResponse(data=result.get("data", {}), field_descriptions=result.get("field_descriptions", {}))


@router.post(
    "/fundamentals/fetch-from-api", response_model=FundamentalsFetchResponse, summary="从Tushare接口获取财务数据"
)
@handle_data_api_error
def fetch_fundamentals_from_api(
    request: FundamentalsFetchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """从Tushare接口获取财务数据"""
    from loguru import logger
    from zquant.data.etl.tushare import TushareClient

    symbols = [s.strip() for s in request.symbols.split(",") if s.strip()]
    if not symbols:
        return FundamentalsFetchResponse(
            success=False,
            message="请至少提供一个股票代码",
            request_params={},
            data={},
            total_count=0,
            symbols=[],
            failed_codes=[],
        )

    start_date_str = request.start_date.strftime("%Y%m%d") if request.start_date else ""
    end_date_str = request.end_date.strftime("%Y%m%d") if request.end_date else ""
    request_params = {
        "symbols": symbols,
        "statement_type": request.statement_type,
        "start_date": start_date_str,
        "end_date": end_date_str,
    }

    try:
        client = TushareClient(db=db)
    except Exception as e:
        logger.error(f"初始化Tushare客户端失败: {e}")
        return FundamentalsFetchResponse(
            success=False,
            message=f"初始化Tushare客户端失败: {str(e)}",
            request_params=request_params,
            data={},
            total_count=0,
            symbols=symbols,
            failed_codes=symbols,
        )

    all_data = {}
    failed_codes = []
    total_count = 0

    for symbol in symbols:
        try:
            df = client.get_fundamentals(
                ts_code=symbol, start_date=start_date_str, end_date=end_date_str, statement_type=request.statement_type
            )

            if df is not None and not df.empty:
                records = df.to_dict(orient="records")
                all_data[symbol] = records
                total_count += len(records)
            else:
                logger.warning(f"{symbol} 无数据")
                failed_codes.append(symbol)
        except Exception as e:
            logger.error(f"获取 {symbol} 数据失败: {e}")
            failed_codes.append(symbol)

    success = len(failed_codes) < len(symbols)
    if len(failed_codes) == len(symbols):
        message = f"所有股票代码获取失败"
    elif len(failed_codes) > 0:
        message = f"部分股票代码获取失败: {', '.join(failed_codes)}"
    else:
        message = f"成功获取 {len(symbols)} 个股票的数据，共 {total_count} 条记录"

    return FundamentalsFetchResponse(
        success=success,
        message=message,
        request_params=request_params,
        data=all_data,
        total_count=total_count,
        symbols=symbols,
        failed_codes=failed_codes,
    )


@router.post("/fundamentals/validate", response_model=FundamentalsValidateResponse, summary="财务数据校验")
@handle_data_api_error
def validate_fundamentals(
    request: FundamentalsValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """财务数据校验：对比数据库数据和接口数据"""
    from loguru import logger
    from zquant.data.etl.tushare import TushareClient
    from zquant.schemas.data import DataDifferenceItem

    symbols = [s.strip() for s in request.symbols.split(",") if s.strip()]
    if not symbols:
        return FundamentalsValidateResponse(
            success=False,
            message="请至少提供一个股票代码",
            symbols=[],
            total_db_records=0,
            total_api_records=0,
            consistent_count=0,
            difference_count=0,
            differences=[],
            failed_codes=[],
        )

    start_date_str = request.start_date.strftime("%Y%m%d") if request.start_date else ""
    end_date_str = request.end_date.strftime("%Y%m%d") if request.end_date else ""

    try:
        client = TushareClient(db=db)
    except Exception as e:
        logger.error(f"初始化Tushare客户端失败: {e}")
        return FundamentalsValidateResponse(
            success=False,
            message=f"初始化Tushare客户端失败: {str(e)}",
            symbols=symbols,
            total_db_records=0,
            total_api_records=0,
            consistent_count=0,
            difference_count=0,
            differences=[],
            failed_codes=symbols,
        )

    # 财务数据的对比逻辑较复杂，需要按symbol + report_date + statement_type作为唯一键
    # 这里简化处理，主要对比关键字段
    numeric_tolerance = 1e-6
    all_differences = []
    all_consistents = []
    total_db_records = 0
    total_api_records = 0
    consistent_count = 0
    failed_codes = []

    for symbol in symbols:
        try:
            # 获取数据库数据
            db_result = DataService.get_fundamentals(
                db,
                [symbol],
                request.statement_type,
                None,  # 获取所有报告期
            )
            db_data = db_result.get("data", {}).get(symbol, {})

            # 获取接口数据
            try:
                df = client.get_fundamentals(
                    ts_code=symbol,
                    start_date=start_date_str,
                    end_date=end_date_str,
                    statement_type=request.statement_type,
                )

                if df is None or df.empty:
                    api_records = []
                else:
                    api_records = df.to_dict(orient="records")
            except Exception as e:
                logger.error(f"获取 {symbol} 接口数据失败: {e}")
                failed_codes.append(symbol)
                continue

            # 财务数据对比逻辑较复杂，这里简化处理
            # 实际应该按report_date对比，但为了简化，这里只做基本对比
            total_api_records += len(api_records)
            # 数据库数据可能是字典结构，需要转换
            if isinstance(db_data, dict):
                total_db_records += 1
                # 简化对比逻辑
                if len(api_records) == 0:
                    all_differences.append(
                        DataDifferenceItem(
                            ts_code=symbol,
                            trade_date="",
                            difference_type="missing_in_api",
                            field_differences={},
                            db_record=db_data,
                            api_record=None,
                        )
                    )
            else:
                total_db_records += len(db_data) if isinstance(db_data, list) else 0

        except Exception as e:
            logger.error(f"校验 {symbol} 数据失败: {e}")
            failed_codes.append(symbol)

    difference_count = len(all_differences)
    # 按照 trade_date 倒序排序（最新的日期在前）
    all_differences.sort(key=lambda x: x.trade_date or "", reverse=True)
    all_consistents.sort(key=lambda x: x.trade_date or "", reverse=True)
    
    success = len(failed_codes) < len(symbols)
    if len(failed_codes) == len(symbols):
        message = f"所有股票代码校验失败"
    elif len(failed_codes) > 0:
        message = f"部分股票代码校验失败: {', '.join(failed_codes)}"
    else:
        message = f"校验完成，共 {len(symbols)} 个股票，一致记录 {consistent_count} 条，差异记录 {difference_count} 条"

    return FundamentalsValidateResponse(
        success=success,
        message=message,
        symbols=symbols,
        total_db_records=total_db_records,
        total_api_records=total_api_records,
        consistent_count=consistent_count,
        difference_count=difference_count,
        differences=all_differences,
        consistents=all_consistents,
        failed_codes=failed_codes,
    )


@router.post("/calendar", response_model=CalendarResponse, summary="获取交易日历")
@handle_data_api_error
def get_calendar(
    request: CalendarRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """获取交易日历（返回所有字段）"""
    records = DataService.get_trading_calendar(db, request.start_date, request.end_date, request.exchange)
    items = convert_to_response_items(records, CalendarItem)
    return CalendarResponse(items=items)


@router.post("/calendar/fetch-from-api", response_model=CalendarFetchResponse, summary="从Tushare接口获取交易日历")
@handle_data_api_error
def fetch_calendar_from_api(
    request: CalendarFetchRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """从Tushare接口获取交易日历"""
    from loguru import logger
    from zquant.data.etl.tushare import TushareClient

    start_date_str = request.start_date.strftime("%Y%m%d")
    end_date_str = request.end_date.strftime("%Y%m%d")
    exchange = request.exchange or "SSE"
    request_params = {
        "start_date": start_date_str,
        "end_date": end_date_str,
        "exchange": exchange,
    }

    try:
        client = TushareClient(db=db)
    except Exception as e:
        logger.error(f"初始化Tushare客户端失败: {e}")
        return CalendarFetchResponse(
            success=False,
            message=f"初始化Tushare客户端失败: {str(e)}",
            request_params=request_params,
            data=[],
            total_count=0,
        )

    try:
        df = client.get_trade_cal(exchange=exchange, start_date=start_date_str, end_date=end_date_str)

        if df is not None and not df.empty:
            records = df.to_dict(orient="records")
            # 转换日期格式
            for record in records:
                if "cal_date" in record and record["cal_date"]:
                    cal_date_str = str(record["cal_date"])
                    if len(cal_date_str) == 8:
                        record["cal_date"] = f"{cal_date_str[:4]}-{cal_date_str[4:6]}-{cal_date_str[6:8]}"

            return CalendarFetchResponse(
                success=True,
                message=f"成功获取 {len(records)} 条记录",
                request_params=request_params,
                data=records,
                total_count=len(records),
            )
        else:
            return CalendarFetchResponse(
                success=False, message="无数据", request_params=request_params, data=[], total_count=0
            )
    except Exception as e:
        logger.error(f"获取交易日历失败: {e}")
        return CalendarFetchResponse(
            success=False, message=f"获取交易日历失败: {str(e)}", request_params=request_params, data=[], total_count=0
        )


@router.post("/calendar/validate", response_model=CalendarValidateResponse, summary="交易日历数据校验")
@handle_data_api_error
def validate_calendar(
    request: CalendarValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """交易日历数据校验：对比数据库数据和接口数据"""
    from loguru import logger
    from zquant.data.etl.tushare import TushareClient
    from zquant.schemas.data import DataDifferenceItem

    start_date_str = request.start_date.strftime("%Y%m%d")
    end_date_str = request.end_date.strftime("%Y%m%d")
    exchange = request.exchange or "SSE"

    try:
        client = TushareClient(db=db)
    except Exception as e:
        logger.error(f"初始化Tushare客户端失败: {e}")
        return CalendarValidateResponse(
            success=False,
            message=f"初始化Tushare客户端失败: {str(e)}",
            total_db_records=0,
            total_api_records=0,
            consistent_count=0,
            difference_count=0,
            differences=[],
        )

    db_records = DataService.get_trading_calendar(db, request.start_date, request.end_date, exchange)

    try:
        df = client.get_trade_cal(exchange=exchange, start_date=start_date_str, end_date=end_date_str)
        if df is None or df.empty:
            api_records = []
        else:
            api_records = df.to_dict(orient="records")
            for record in api_records:
                if "cal_date" in record and record["cal_date"]:
                    cal_date_str = str(record["cal_date"])
                    if len(cal_date_str) == 8:
                        record["cal_date"] = f"{cal_date_str[:4]}-{cal_date_str[4:6]}-{cal_date_str[6:8]}"
    except Exception as e:
        logger.error(f"获取接口数据失败: {e}")
        return CalendarValidateResponse(
            success=False,
            message=f"获取接口数据失败: {str(e)}",
            total_db_records=len(db_records),
            total_api_records=0,
            consistent_count=0,
            difference_count=0,
            differences=[],
        )

    # 构建索引（按exchange + cal_date）
    db_index = {f"{r.get('exchange', '')}_{r.get('cal_date', '')}": r for r in db_records}
    api_index = {f"{r.get('exchange', exchange)}_{r.get('cal_date', '')}": r for r in api_records}
    all_keys = set(db_index.keys()) | set(api_index.keys())
    all_differences = []
    all_consistents = []
    consistent_count = 0

    for key in all_keys:
        db_record = db_index.get(key)
        api_record = api_index.get(key)

        if db_record is None and api_record is not None:
            all_differences.append(
                DataDifferenceItem(
                    ts_code="",
                    trade_date=api_record.get("cal_date", ""),
                    difference_type="missing_in_db",
                    field_differences={},
                    db_record=None,
                    api_record=api_record,
                )
            )
        elif db_record is not None and api_record is None:
            all_differences.append(
                DataDifferenceItem(
                    ts_code="",
                    trade_date=db_record.get("cal_date", ""),
                    difference_type="missing_in_api",
                    field_differences={},
                    db_record=db_record,
                    api_record=None,
                )
            )
        elif db_record is not None and api_record is not None:
            key_fields = ["is_open", "pretrade_date"]
            field_diffs = {
                f: {"db_value": db_record.get(f), "api_value": api_record.get(f)}
                for f in key_fields
                if db_record.get(f) != api_record.get(f)
            }
            if field_diffs:
                all_differences.append(
                    DataDifferenceItem(
                        ts_code="",
                        trade_date=db_record.get("cal_date", ""),
                        difference_type="field_diff",
                        field_differences=field_diffs,
                        db_record=db_record,
                        api_record=api_record,
                    )
                )
            else:
                consistent_count += 1
                all_consistents.append(
                    DataDifferenceItem(
                        ts_code="",
                        trade_date=db_record.get("cal_date", ""),
                        difference_type="consistent",
                        field_differences={},
                        db_record=db_record,
                        api_record=api_record,
                    )
                )

    # 按照 trade_date 倒序排序（最新的日期在前）
    all_differences.sort(key=lambda x: x.trade_date or "", reverse=True)
    all_consistents.sort(key=lambda x: x.trade_date or "", reverse=True)

    return CalendarValidateResponse(
        success=True,
        message=f"校验完成，一致记录 {consistent_count} 条，差异记录 {len(all_differences)} 条",
        total_db_records=len(db_records),
        total_api_records=len(api_records),
        consistent_count=consistent_count,
        difference_count=len(all_differences),
        differences=all_differences,
        consistents=all_consistents,
    )


@router.post("/stocks", response_model=StockListResponse, summary="获取股票列表")
@handle_data_api_error
def get_stock_list(
    request: StockListRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """获取股票列表（支持按交易所、股票代码、股票名称查询）"""
    stocks = DataService.get_stock_list(db, exchange=request.exchange, symbol=request.symbol, name=request.name)
    return StockListResponse(stocks=stocks)


@router.post("/stocks/fetch-from-api", response_model=StockListFetchResponse, summary="从Tushare接口获取股票列表")
@handle_data_api_error
def fetch_stock_list_from_api(
    request: StockListFetchRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """从Tushare接口获取股票列表"""
    from loguru import logger
    from zquant.data.etl.tushare import TushareClient

    request_params = {
        "exchange": request.exchange or "",
        "list_status": request.list_status or "",
    }

    try:
        client = TushareClient(db=db)
    except Exception as e:
        logger.error(f"初始化Tushare客户端失败: {e}")
        return StockListFetchResponse(
            success=False,
            message=f"初始化Tushare客户端失败: {str(e)}",
            request_params=request_params,
            data=[],
            total_count=0,
        )

    try:
        df = client.get_stock_list(exchange=request.exchange or "", list_status=request.list_status or "")

        if df is not None and not df.empty:
            records = df.to_dict(orient="records")
            return StockListFetchResponse(
                success=True,
                message=f"成功获取 {len(records)} 条记录",
                request_params=request_params,
                data=records,
                total_count=len(records),
            )
        else:
            return StockListFetchResponse(
                success=False, message="无数据", request_params=request_params, data=[], total_count=0
            )
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        return StockListFetchResponse(
            success=False, message=f"获取股票列表失败: {str(e)}", request_params=request_params, data=[], total_count=0
        )


@router.post("/stocks/validate", response_model=StockListValidateResponse, summary="股票列表数据校验")
@handle_data_api_error
def validate_stock_list(
    request: StockListValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """股票列表数据校验：对比数据库数据和接口数据"""
    from loguru import logger
    from zquant.data.etl.tushare import TushareClient
    from zquant.schemas.data import DataDifferenceItem

    try:
        client = TushareClient(db=db)
    except Exception as e:
        logger.error(f"初始化Tushare客户端失败: {e}")
        return StockListValidateResponse(
            success=False,
            message=f"初始化Tushare客户端失败: {str(e)}",
            total_db_records=0,
            total_api_records=0,
            consistent_count=0,
            difference_count=0,
            differences=[],
        )

    db_stocks = DataService.get_stock_list(db, exchange=request.exchange, symbol=None, name=None)

    try:
        df = client.get_stock_list(exchange=request.exchange or "", list_status=request.list_status or "")
        api_stocks = df.to_dict(orient="records") if df is not None and not df.empty else []
    except Exception as e:
        logger.error(f"获取接口数据失败: {e}")
        return StockListValidateResponse(
            success=False,
            message=f"获取接口数据失败: {str(e)}",
            total_db_records=len(db_stocks),
            total_api_records=0,
            consistent_count=0,
            difference_count=0,
            differences=[],
        )

    db_index = {stock.get("ts_code"): stock for stock in db_stocks}
    api_index = {stock.get("ts_code"): stock for stock in api_stocks}
    all_keys = set(db_index.keys()) | set(api_index.keys())
    all_differences = []
    all_consistents = []
    consistent_count = 0

    for ts_code in all_keys:
        db_stock = db_index.get(ts_code)
        api_stock = api_index.get(ts_code)

        if db_stock is None and api_stock is not None:
            all_differences.append(
                DataDifferenceItem(
                    ts_code=ts_code,
                    trade_date="",
                    difference_type="missing_in_db",
                    field_differences={},
                    db_record=None,
                    api_record=api_stock,
                )
            )
        elif db_stock is not None and api_stock is None:
            all_differences.append(
                DataDifferenceItem(
                    ts_code=ts_code,
                    trade_date="",
                    difference_type="missing_in_api",
                    field_differences={},
                    db_record=db_stock,
                    api_record=None,
                )
            )
        elif db_stock is not None and api_stock is not None:
            key_fields = ["symbol", "name", "area", "industry", "market", "list_status", "list_date"]
            field_diffs = {
                f: {"db_value": db_stock.get(f), "api_value": api_stock.get(f)}
                for f in key_fields
                if db_stock.get(f) != api_stock.get(f)
            }
            if field_diffs:
                all_differences.append(
                    DataDifferenceItem(
                        ts_code=ts_code,
                        trade_date="",
                        difference_type="field_diff",
                        field_differences=field_diffs,
                        db_record=db_stock,
                        api_record=api_stock,
                    )
                )
            else:
                consistent_count += 1
                all_consistents.append(
                    DataDifferenceItem(
                        ts_code=ts_code,
                        trade_date="",
                        difference_type="consistent",
                        field_differences={},
                        db_record=db_stock,
                        api_record=api_stock,
                    )
                )

    # 按照 ts_code 排序
    all_differences.sort(key=lambda x: x.ts_code or "", reverse=False)
    all_consistents.sort(key=lambda x: x.ts_code or "", reverse=False)

    return StockListValidateResponse(
        success=True,
        message=f"校验完成，一致记录 {consistent_count} 条，差异记录 {len(all_differences)} 条",
        total_db_records=len(db_stocks),
        total_api_records=len(api_stocks),
        consistent_count=consistent_count,
        difference_count=len(all_differences),
        differences=all_differences,
        consistents=all_consistents,
    )


@router.post("/daily", response_model=DailyDataResponse, summary="获取日线数据")
@handle_data_api_error
def get_daily_data(
    request: DailyDataRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """获取日线数据（返回所有字段）"""
    records = DataService.get_daily_data(db, request.ts_code, request.start_date, request.end_date)
    items = convert_to_response_items(records, DailyDataItem)
    return DailyDataResponse(items=items)


@router.post("/daily/fetch-from-api", response_model=DailyDataFetchResponse, summary="从Tushare接口获取日线数据")
@handle_data_api_error
def fetch_daily_data_from_api(
    request: DailyDataFetchRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """
    从Tushare接口获取日线数据

    - 支持多个股票代码同时查询（用逗号分隔）
    - 返回原始JSON数据和请求参数
    """
    from loguru import logger
    from zquant.data.etl.tushare import TushareClient
    import pandas as pd

    # 解析股票代码列表
    ts_codes = [code.strip() for code in request.ts_codes.split(",") if code.strip()]
    if not ts_codes:
        return DailyDataFetchResponse(
            success=False,
            message="请至少提供一个股票代码",
            request_params={},
            data=[],
            total_count=0,
            ts_codes=[],
            failed_codes=[],
        )

    # 准备请求参数
    start_date_str = request.start_date.strftime("%Y%m%d")
    end_date_str = request.end_date.strftime("%Y%m%d")
    request_params = {
        "ts_codes": ts_codes,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "adj": request.adj or "qfq",
    }

    # 初始化Tushare客户端
    try:
        client = TushareClient(db=db)
    except Exception as e:
        logger.error(f"初始化Tushare客户端失败: {e}")
        return DailyDataFetchResponse(
            success=False,
            message=f"初始化Tushare客户端失败: {str(e)}",
            request_params=request_params,
            data=[],
            total_count=0,
            ts_codes=ts_codes,
            failed_codes=ts_codes,
        )

    # 循环获取每个股票的数据
    all_data = []
    failed_codes = []

    for ts_code in ts_codes:
        try:
            df = client.get_daily_data(
                ts_code=ts_code, start_date=start_date_str, end_date=end_date_str, adj=request.adj or "qfq"
            )

            if df is not None and not df.empty:
                # 将DataFrame转换为JSON格式
                # 使用orient='records'将每行转换为字典
                records = df.to_dict(orient="records")
                all_data.extend(records)
            else:
                logger.warning(f"{ts_code} 无数据")
                failed_codes.append(ts_code)

        except Exception as e:
            logger.error(f"获取 {ts_code} 数据失败: {e}")
            failed_codes.append(ts_code)

    # 判断是否成功
    success = len(failed_codes) < len(ts_codes)
    if len(failed_codes) == len(ts_codes):
        message = f"所有股票代码获取失败"
    elif len(failed_codes) > 0:
        message = f"部分股票代码获取失败: {', '.join(failed_codes)}"
    else:
        message = f"成功获取 {len(ts_codes)} 个股票的数据，共 {len(all_data)} 条记录"

    return DailyDataFetchResponse(
        success=success,
        message=message,
        request_params=request_params,
        data=all_data,
        total_count=len(all_data),
        ts_codes=ts_codes,
        failed_codes=failed_codes,
    )


@router.post("/daily/validate", response_model=DailyDataValidateResponse, summary="数据校验")
@handle_data_api_error
def validate_daily_data(
    request: DailyDataValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    数据校验：对比数据库数据和接口数据

    - 支持多个股票代码同时校验（用逗号分隔）
    - 返回差异统计和详情
    """
    from loguru import logger
    from zquant.data.etl.tushare import TushareClient
    from zquant.schemas.data import DataDifferenceItem
    import math
    from datetime import datetime

    # 解析股票代码列表
    ts_codes = [code.strip() for code in request.ts_codes.split(",") if code.strip()]
    if not ts_codes:
        return DailyDataValidateResponse(
            success=False,
            message="请至少提供一个股票代码",
            ts_codes=[],
            total_db_records=0,
            total_api_records=0,
            consistent_count=0,
            difference_count=0,
            differences=[],
            failed_codes=[],
        )

    # 准备日期字符串
    start_date_str = request.start_date.strftime("%Y%m%d")
    end_date_str = request.end_date.strftime("%Y%m%d")
    adj = request.adj or "qfq"

    # 初始化Tushare客户端
    try:
        client = TushareClient(db=db)
    except Exception as e:
        logger.error(f"初始化Tushare客户端失败: {e}")
        return DailyDataValidateResponse(
            success=False,
            message=f"初始化Tushare客户端失败: {str(e)}",
            ts_codes=ts_codes,
            total_db_records=0,
            total_api_records=0,
            consistent_count=0,
            difference_count=0,
            differences=[],
            failed_codes=ts_codes,
        )

    # 需要对比的字段
    compare_fields = ["open", "high", "low", "close", "pre_close", "change", "pct_chg", "vol", "amount"]
    # 数值字段的容差（相对误差）
    numeric_tolerance = 1e-6

    all_differences = []
    all_consistents = []
    total_db_records = 0
    total_api_records = 0
    consistent_count = 0
    failed_codes = []

    # 对每个股票代码进行校验
    for ts_code in ts_codes:
        try:
            # 获取数据库数据
            db_records = DataService.get_daily_data(
                db, ts_code=ts_code, start_date=request.start_date, end_date=request.end_date
            )

            # 获取接口数据
            try:
                df = client.get_daily_data(ts_code=ts_code, start_date=start_date_str, end_date=end_date_str, adj=adj)

                if df is None or df.empty:
                    api_records = []
                else:
                    # 将DataFrame转换为字典列表
                    api_records = df.to_dict(orient="records")
                    # 转换日期格式为字符串（YYYYMMDD -> YYYY-MM-DD）
                    for record in api_records:
                        if "trade_date" in record and record["trade_date"]:
                            trade_date_str = str(record["trade_date"])
                            if len(trade_date_str) == 8:
                                record["trade_date"] = (
                                    f"{trade_date_str[:4]}-{trade_date_str[4:6]}-{trade_date_str[6:8]}"
                                )
            except Exception as e:
                logger.error(f"获取 {ts_code} 接口数据失败: {e}")
                failed_codes.append(ts_code)
                continue

            # 构建数据库记录索引（ts_code + trade_date）
            db_index = {}
            for record in db_records:
                key = f"{record.get('ts_code', '')}_{record.get('trade_date', '')}"
                db_index[key] = record
                total_db_records += 1

            # 构建接口记录索引（ts_code + trade_date）
            api_index = {}
            for record in api_records:
                # 确保ts_code存在
                if "ts_code" not in record:
                    record["ts_code"] = ts_code
                key = f"{record.get('ts_code', '')}_{record.get('trade_date', '')}"
                api_index[key] = record
                total_api_records += 1

            # 找出所有唯一的键
            all_keys = set(db_index.keys()) | set(api_index.keys())

            # 对比每条记录
            for key in all_keys:
                db_record = db_index.get(key)
                api_record = api_index.get(key)

                if db_record is None and api_record is not None:
                    # 数据库缺失
                    all_differences.append(
                        DataDifferenceItem(
                            ts_code=ts_code,
                            trade_date=api_record.get("trade_date", ""),
                            difference_type="missing_in_db",
                            field_differences={},
                            db_record=None,
                            api_record=api_record,
                        )
                    )
                elif db_record is not None and api_record is None:
                    # 接口缺失
                    all_differences.append(
                        DataDifferenceItem(
                            ts_code=ts_code,
                            trade_date=db_record.get("trade_date", ""),
                            difference_type="missing_in_api",
                            field_differences={},
                            db_record=db_record,
                            api_record=None,
                        )
                    )
                elif db_record is not None and api_record is not None:
                    # 都存在，对比字段
                    field_diffs = {}
                    has_diff = False

                    for field in compare_fields:
                        db_value = db_record.get(field)
                        api_value = api_record.get(field)

                        # 处理None值
                        if db_value is None and api_value is None:
                            continue
                        if db_value is None or api_value is None:
                            field_diffs[field] = {"db_value": db_value, "api_value": api_value}
                            has_diff = True
                            continue

                        # 数值比较（考虑浮点数精度）
                        if isinstance(db_value, (int, float)) and isinstance(api_value, (int, float)):
                            # 如果都是0，认为一致
                            if db_value == 0 and api_value == 0:
                                continue
                            # 使用相对误差比较
                            if abs(db_value) > 1e-10:
                                relative_error = abs((db_value - api_value) / db_value)
                            else:
                                relative_error = abs(db_value - api_value)

                            if relative_error > numeric_tolerance:
                                field_diffs[field] = {"db_value": db_value, "api_value": api_value}
                                has_diff = True
                        else:
                            # 字符串或其他类型直接比较
                            if db_value != api_value:
                                field_diffs[field] = {"db_value": db_value, "api_value": api_value}
                                has_diff = True

                    if has_diff:
                        all_differences.append(
                            DataDifferenceItem(
                                ts_code=ts_code,
                                trade_date=db_record.get("trade_date", ""),
                                difference_type="field_diff",
                                field_differences=field_diffs,
                                db_record=db_record,
                                api_record=api_record,
                            )
                        )
                    else:
                        consistent_count += 1
                        all_consistents.append(
                            DataDifferenceItem(
                                ts_code=ts_code,
                                trade_date=db_record.get("trade_date", ""),
                                difference_type="consistent",
                                field_differences={},
                                db_record=db_record,
                                api_record=api_record,
                            )
                        )

        except Exception as e:
            logger.error(f"校验 {ts_code} 数据失败: {e}")
            failed_codes.append(ts_code)

    # 计算差异数量
    difference_count = len(all_differences)

    # 按照 trade_date 倒序排序（最新的日期在前）
    all_differences.sort(key=lambda x: x.trade_date or "", reverse=True)
    all_consistents.sort(key=lambda x: x.trade_date or "", reverse=True)

    # 判断是否成功
    success = len(failed_codes) < len(ts_codes)
    if len(failed_codes) == len(ts_codes):
        message = f"所有股票代码校验失败"
    elif len(failed_codes) > 0:
        message = f"部分股票代码校验失败: {', '.join(failed_codes)}"
    else:
        message = f"校验完成，共 {len(ts_codes)} 个股票，一致记录 {consistent_count} 条，差异记录 {difference_count} 条"

    return DailyDataValidateResponse(
        success=success,
        message=message,
        ts_codes=ts_codes,
        total_db_records=total_db_records,
        total_api_records=total_api_records,
        consistent_count=consistent_count,
        difference_count=difference_count,
        differences=all_differences,
        consistents=all_consistents,
        failed_codes=failed_codes,
    )


@router.post("/daily-basic", response_model=DailyBasicResponse, summary="获取每日指标数据")
@handle_data_api_error
def get_daily_basic_data(
    request: DailyBasicRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """获取每日指标数据（返回所有字段）"""
    records = DataService.get_daily_basic_data(db, request.ts_code, request.start_date, request.end_date)
    items = convert_to_response_items(records, DailyBasicItem)
    return DailyBasicResponse(items=items)


@router.post(
    "/daily-basic/fetch-from-api", response_model=DailyBasicFetchResponse, summary="从Tushare接口获取每日指标数据"
)
@handle_data_api_error
def fetch_daily_basic_data_from_api(
    request: DailyBasicFetchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    从Tushare接口获取每日指标数据

    - 支持多个股票代码同时查询（用逗号分隔）
    - 返回原始JSON数据和请求参数
    """
    from loguru import logger
    from zquant.data.etl.tushare import TushareClient

    # 解析股票代码列表
    ts_codes = [code.strip() for code in request.ts_codes.split(",") if code.strip()]
    if not ts_codes:
        return DailyBasicFetchResponse(
            success=False,
            message="请至少提供一个股票代码",
            request_params={},
            data=[],
            total_count=0,
            ts_codes=[],
            failed_codes=[],
        )

    # 准备请求参数
    start_date_str = request.start_date.strftime("%Y%m%d")
    end_date_str = request.end_date.strftime("%Y%m%d")
    request_params = {
        "ts_codes": ts_codes,
        "start_date": start_date_str,
        "end_date": end_date_str,
    }

    # 初始化Tushare客户端
    try:
        client = TushareClient(db=db)
    except Exception as e:
        logger.error(f"初始化Tushare客户端失败: {e}")
        return DailyBasicFetchResponse(
            success=False,
            message=f"初始化Tushare客户端失败: {str(e)}",
            request_params=request_params,
            data=[],
            total_count=0,
            ts_codes=ts_codes,
            failed_codes=ts_codes,
        )

    # 循环获取每个股票的数据
    all_data = []
    failed_codes = []

    for ts_code in ts_codes:
        try:
            df = client.get_daily_basic_data(ts_code=ts_code, start_date=start_date_str, end_date=end_date_str)

            if df is not None and not df.empty:
                records = df.to_dict(orient="records")
                all_data.extend(records)
            else:
                logger.warning(f"{ts_code} 无数据")
                failed_codes.append(ts_code)

        except Exception as e:
            logger.error(f"获取 {ts_code} 数据失败: {e}")
            failed_codes.append(ts_code)

    # 判断是否成功
    success = len(failed_codes) < len(ts_codes)
    if len(failed_codes) == len(ts_codes):
        message = f"所有股票代码获取失败"
    elif len(failed_codes) > 0:
        message = f"部分股票代码获取失败: {', '.join(failed_codes)}"
    else:
        message = f"成功获取 {len(ts_codes)} 个股票的数据，共 {len(all_data)} 条记录"

    return DailyBasicFetchResponse(
        success=success,
        message=message,
        request_params=request_params,
        data=all_data,
        total_count=len(all_data),
        ts_codes=ts_codes,
        failed_codes=failed_codes,
    )


@router.post("/daily-basic/validate", response_model=DailyBasicValidateResponse, summary="每日指标数据校验")
@handle_data_api_error
def validate_daily_basic_data(
    request: DailyBasicValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    每日指标数据校验：对比数据库数据和接口数据

    - 支持多个股票代码同时校验（用逗号分隔）
    - 返回差异统计和详情
    """
    from loguru import logger
    from zquant.data.etl.tushare import TushareClient
    from zquant.schemas.data import DataDifferenceItem

    # 解析股票代码列表
    ts_codes = [code.strip() for code in request.ts_codes.split(",") if code.strip()]
    if not ts_codes:
        return DailyBasicValidateResponse(
            success=False,
            message="请至少提供一个股票代码",
            ts_codes=[],
            total_db_records=0,
            total_api_records=0,
            consistent_count=0,
            difference_count=0,
            differences=[],
            failed_codes=[],
        )

    # 准备日期字符串
    start_date_str = request.start_date.strftime("%Y%m%d")
    end_date_str = request.end_date.strftime("%Y%m%d")

    # 初始化Tushare客户端
    try:
        client = TushareClient(db=db)
    except Exception as e:
        logger.error(f"初始化Tushare客户端失败: {e}")
        return DailyBasicValidateResponse(
            success=False,
            message=f"初始化Tushare客户端失败: {str(e)}",
            ts_codes=ts_codes,
            total_db_records=0,
            total_api_records=0,
            consistent_count=0,
            difference_count=0,
            differences=[],
            failed_codes=ts_codes,
        )

    # 需要对比的字段（每日指标的主要字段）
    compare_fields = [
        "close",
        "turnover_rate",
        "turnover_rate_f",
        "volume_ratio",
        "pe",
        "pe_ttm",
        "pb",
        "ps",
        "ps_ttm",
        "dv_ratio",
        "dv_ttm",
        "total_share",
        "float_share",
        "free_share",
        "total_mv",
        "circ_mv",
    ]
    # 数值字段的容差（相对误差）
    numeric_tolerance = 1e-6

    all_differences = []
    all_consistents = []
    total_db_records = 0
    total_api_records = 0
    consistent_count = 0
    failed_codes = []

    # 对每个股票代码进行校验
    for ts_code in ts_codes:
        try:
            # 获取数据库数据
            db_records = DataService.get_daily_basic_data(
                db, ts_code=ts_code, start_date=request.start_date, end_date=request.end_date
            )

            # 获取接口数据
            try:
                df = client.get_daily_basic_data(ts_code=ts_code, start_date=start_date_str, end_date=end_date_str)

                if df is None or df.empty:
                    api_records = []
                else:
                    api_records = df.to_dict(orient="records")
                    # 转换日期格式
                    for record in api_records:
                        if "trade_date" in record and record["trade_date"]:
                            trade_date_str = str(record["trade_date"])
                            if len(trade_date_str) == 8:
                                record["trade_date"] = (
                                    f"{trade_date_str[:4]}-{trade_date_str[4:6]}-{trade_date_str[6:8]}"
                                )
            except Exception as e:
                logger.error(f"获取 {ts_code} 接口数据失败: {e}")
                failed_codes.append(ts_code)
                continue

            # 构建数据库记录索引
            db_index = {}
            for record in db_records:
                key = f"{record.get('ts_code', '')}_{record.get('trade_date', '')}"
                db_index[key] = record
                total_db_records += 1

            # 构建接口记录索引
            api_index = {}
            for record in api_records:
                if "ts_code" not in record:
                    record["ts_code"] = ts_code
                key = f"{record.get('ts_code', '')}_{record.get('trade_date', '')}"
                api_index[key] = record
                total_api_records += 1

            # 找出所有唯一的键
            all_keys = set(db_index.keys()) | set(api_index.keys())

            # 对比每条记录
            for key in all_keys:
                db_record = db_index.get(key)
                api_record = api_index.get(key)

                if db_record is None and api_record is not None:
                    all_differences.append(
                        DataDifferenceItem(
                            ts_code=ts_code,
                            trade_date=api_record.get("trade_date", ""),
                            difference_type="missing_in_db",
                            field_differences={},
                            db_record=None,
                            api_record=api_record,
                        )
                    )
                elif db_record is not None and api_record is None:
                    all_differences.append(
                        DataDifferenceItem(
                            ts_code=ts_code,
                            trade_date=db_record.get("trade_date", ""),
                            difference_type="missing_in_api",
                            field_differences={},
                            db_record=db_record,
                            api_record=None,
                        )
                    )
                elif db_record is not None and api_record is not None:
                    # 都存在，对比字段
                    field_diffs = {}
                    has_diff = False

                    for field in compare_fields:
                        db_value = db_record.get(field)
                        api_value = api_record.get(field)

                        if db_value is None and api_value is None:
                            continue
                        if db_value is None or api_value is None:
                            field_diffs[field] = {"db_value": db_value, "api_value": api_value}
                            has_diff = True
                            continue

                        # 数值比较
                        if isinstance(db_value, (int, float)) and isinstance(api_value, (int, float)):
                            if db_value == 0 and api_value == 0:
                                continue
                            if abs(db_value) > 1e-10:
                                relative_error = abs((db_value - api_value) / db_value)
                            else:
                                relative_error = abs(db_value - api_value)

                            if relative_error > numeric_tolerance:
                                field_diffs[field] = {"db_value": db_value, "api_value": api_value}
                                has_diff = True
                        else:
                            if db_value != api_value:
                                field_diffs[field] = {"db_value": db_value, "api_value": api_value}
                                has_diff = True

                    if has_diff:
                        all_differences.append(
                            DataDifferenceItem(
                                ts_code=ts_code,
                                trade_date=db_record.get("trade_date", ""),
                                difference_type="field_diff",
                                field_differences=field_diffs,
                                db_record=db_record,
                                api_record=api_record,
                            )
                        )
                    else:
                        consistent_count += 1
                        all_consistents.append(
                            DataDifferenceItem(
                                ts_code=ts_code,
                                trade_date=db_record.get("trade_date", ""),
                                difference_type="consistent",
                                field_differences={},
                                db_record=db_record,
                                api_record=api_record,
                            )
                        )

        except Exception as e:
            logger.error(f"校验 {ts_code} 数据失败: {e}")
            failed_codes.append(ts_code)

    # 计算差异数量
    difference_count = len(all_differences)

    # 按照 trade_date 倒序排序（最新的日期在前）
    all_differences.sort(key=lambda x: x.trade_date or "", reverse=True)
    all_consistents.sort(key=lambda x: x.trade_date or "", reverse=True)

    # 判断是否成功
    success = len(failed_codes) < len(ts_codes)
    if len(failed_codes) == len(ts_codes):
        message = f"所有股票代码校验失败"
    elif len(failed_codes) > 0:
        message = f"部分股票代码校验失败: {', '.join(failed_codes)}"
    else:
        message = f"校验完成，共 {len(ts_codes)} 个股票，一致记录 {consistent_count} 条，差异记录 {difference_count} 条"

    return DailyBasicValidateResponse(
        success=success,
        message=message,
        ts_codes=ts_codes,
        total_db_records=total_db_records,
        total_api_records=total_api_records,
        consistent_count=consistent_count,
        difference_count=difference_count,
        differences=all_differences,
        consistents=all_consistents,
        failed_codes=failed_codes,
    )


@router.post("/factor", response_model=FactorDataResponse, summary="获取因子数据")
@handle_data_api_error
def get_factor_data(
    request: FactorDataRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """获取因子数据（返回所有字段）"""
    records = DataService.get_factor_data(db, request.ts_code, request.start_date, request.end_date)
    items = convert_to_response_items(records, FactorDataItem)
    return FactorDataResponse(items=items)


@router.post("/factor/fetch-from-api", response_model=FactorDataFetchResponse, summary="从Tushare接口获取技术因子数据")
@handle_data_api_error
def fetch_factor_data_from_api(
    request: FactorDataFetchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """从Tushare接口获取技术因子数据"""
    from loguru import logger
    from zquant.data.etl.tushare import TushareClient

    ts_codes = [code.strip() for code in request.ts_codes.split(",") if code.strip()]
    if not ts_codes:
        return FactorDataFetchResponse(
            success=False,
            message="请至少提供一个股票代码",
            request_params={},
            data=[],
            total_count=0,
            ts_codes=[],
            failed_codes=[],
        )

    start_date_str = request.start_date.strftime("%Y%m%d")
    end_date_str = request.end_date.strftime("%Y%m%d")
    request_params = {
        "ts_codes": ts_codes,
        "start_date": start_date_str,
        "end_date": end_date_str,
    }

    try:
        client = TushareClient(db=db)
    except Exception as e:
        logger.error(f"初始化Tushare客户端失败: {e}")
        return FactorDataFetchResponse(
            success=False,
            message=f"初始化Tushare客户端失败: {str(e)}",
            request_params=request_params,
            data=[],
            total_count=0,
            ts_codes=ts_codes,
            failed_codes=ts_codes,
        )

    all_data = []
    failed_codes = []

    for ts_code in ts_codes:
        try:
            df = client.get_stk_factor(ts_code=ts_code, start_date=start_date_str, end_date=end_date_str)

            if df is not None and not df.empty:
                records = df.to_dict(orient="records")
                all_data.extend(records)
            else:
                logger.warning(f"{ts_code} 无数据")
                failed_codes.append(ts_code)
        except Exception as e:
            logger.error(f"获取 {ts_code} 数据失败: {e}")
            failed_codes.append(ts_code)

    success = len(failed_codes) < len(ts_codes)
    if len(failed_codes) == len(ts_codes):
        message = f"所有股票代码获取失败"
    elif len(failed_codes) > 0:
        message = f"部分股票代码获取失败: {', '.join(failed_codes)}"
    else:
        message = f"成功获取 {len(ts_codes)} 个股票的数据，共 {len(all_data)} 条记录"

    return FactorDataFetchResponse(
        success=success,
        message=message,
        request_params=request_params,
        data=all_data,
        total_count=len(all_data),
        ts_codes=ts_codes,
        failed_codes=failed_codes,
    )


@router.post("/factor/validate", response_model=FactorDataValidateResponse, summary="技术因子数据校验")
@handle_data_api_error
def validate_factor_data(
    request: FactorDataValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """技术因子数据校验：对比数据库数据和接口数据"""
    from loguru import logger
    from zquant.data.etl.tushare import TushareClient
    from zquant.schemas.data import DataDifferenceItem

    ts_codes = [code.strip() for code in request.ts_codes.split(",") if code.strip()]
    if not ts_codes:
        return FactorDataValidateResponse(
            success=False,
            message="请至少提供一个股票代码",
            ts_codes=[],
            total_db_records=0,
            total_api_records=0,
            consistent_count=0,
            difference_count=0,
            differences=[],
            failed_codes=[],
        )

    start_date_str = request.start_date.strftime("%Y%m%d")
    end_date_str = request.end_date.strftime("%Y%m%d")

    try:
        client = TushareClient(db=db)
    except Exception as e:
        logger.error(f"初始化Tushare客户端失败: {e}")
        return FactorDataValidateResponse(
            success=False,
            message=f"初始化Tushare客户端失败: {str(e)}",
            ts_codes=ts_codes,
            total_db_records=0,
            total_api_records=0,
            consistent_count=0,
            difference_count=0,
            differences=[],
            failed_codes=ts_codes,
        )

    # 技术因子的主要对比字段
    compare_fields = ["close", "open", "high", "low", "pre_close", "change", "pct_change", "vol", "amount"]
    numeric_tolerance = 1e-6

    all_differences = []
    all_consistents = []
    total_db_records = 0
    total_api_records = 0
    consistent_count = 0
    failed_codes = []

    for ts_code in ts_codes:
        try:
            db_records = DataService.get_factor_data(
                db, ts_code=ts_code, start_date=request.start_date, end_date=request.end_date
            )

            try:
                df = client.get_stk_factor(ts_code=ts_code, start_date=start_date_str, end_date=end_date_str)

                if df is None or df.empty:
                    api_records = []
                else:
                    api_records = df.to_dict(orient="records")
                    for record in api_records:
                        if "trade_date" in record and record["trade_date"]:
                            trade_date_str = str(record["trade_date"])
                            if len(trade_date_str) == 8:
                                record["trade_date"] = (
                                    f"{trade_date_str[:4]}-{trade_date_str[4:6]}-{trade_date_str[6:8]}"
                                )
            except Exception as e:
                logger.error(f"获取 {ts_code} 接口数据失败: {e}")
                failed_codes.append(ts_code)
                continue

            db_index = {}
            for record in db_records:
                key = f"{record.get('ts_code', '')}_{record.get('trade_date', '')}"
                db_index[key] = record
                total_db_records += 1

            api_index = {}
            for record in api_records:
                if "ts_code" not in record:
                    record["ts_code"] = ts_code
                key = f"{record.get('ts_code', '')}_{record.get('trade_date', '')}"
                api_index[key] = record
                total_api_records += 1

            all_keys = set(db_index.keys()) | set(api_index.keys())

            for key in all_keys:
                db_record = db_index.get(key)
                api_record = api_index.get(key)

                if db_record is None and api_record is not None:
                    all_differences.append(
                        DataDifferenceItem(
                            ts_code=ts_code,
                            trade_date=api_record.get("trade_date", ""),
                            difference_type="missing_in_db",
                            field_differences={},
                            db_record=None,
                            api_record=api_record,
                        )
                    )
                elif db_record is not None and api_record is None:
                    all_differences.append(
                        DataDifferenceItem(
                            ts_code=ts_code,
                            trade_date=db_record.get("trade_date", ""),
                            difference_type="missing_in_api",
                            field_differences={},
                            db_record=db_record,
                            api_record=None,
                        )
                    )
                elif db_record is not None and api_record is not None:
                    field_diffs = {}
                    has_diff = False

                    for field in compare_fields:
                        db_value = db_record.get(field)
                        api_value = api_record.get(field)

                        if db_value is None and api_value is None:
                            continue
                        if db_value is None or api_value is None:
                            field_diffs[field] = {"db_value": db_value, "api_value": api_value}
                            has_diff = True
                            continue

                        if isinstance(db_value, (int, float)) and isinstance(api_value, (int, float)):
                            if db_value == 0 and api_value == 0:
                                continue
                            if abs(db_value) > 1e-10:
                                relative_error = abs((db_value - api_value) / db_value)
                            else:
                                relative_error = abs(db_value - api_value)

                            if relative_error > numeric_tolerance:
                                field_diffs[field] = {"db_value": db_value, "api_value": api_value}
                                has_diff = True
                        else:
                            if db_value != api_value:
                                field_diffs[field] = {"db_value": db_value, "api_value": api_value}
                                has_diff = True

                    if has_diff:
                        all_differences.append(
                            DataDifferenceItem(
                                ts_code=ts_code,
                                trade_date=db_record.get("trade_date", ""),
                                difference_type="field_diff",
                                field_differences=field_diffs,
                                db_record=db_record,
                                api_record=api_record,
                            )
                        )
                    else:
                        consistent_count += 1
                        all_consistents.append(
                            DataDifferenceItem(
                                ts_code=ts_code,
                                trade_date=db_record.get("trade_date", ""),
                                difference_type="consistent",
                                field_differences={},
                                db_record=db_record,
                                api_record=api_record,
                            )
                        )
        except Exception as e:
            logger.error(f"校验 {ts_code} 数据失败: {e}")
            failed_codes.append(ts_code)

    difference_count = len(all_differences)

    # 按照 trade_date 倒序排序（最新的日期在前）
    all_differences.sort(key=lambda x: x.trade_date or "", reverse=True)
    all_consistents.sort(key=lambda x: x.trade_date or "", reverse=True)

    success = len(failed_codes) < len(ts_codes)
    if len(failed_codes) == len(ts_codes):
        message = f"所有股票代码校验失败"
    elif len(failed_codes) > 0:
        message = f"部分股票代码校验失败: {', '.join(failed_codes)}"
    else:
        message = f"校验完成，共 {len(ts_codes)} 个股票，一致记录 {consistent_count} 条，差异记录 {difference_count} 条"

    return FactorDataValidateResponse(
        success=success,
        message=message,
        ts_codes=ts_codes,
        total_db_records=total_db_records,
        total_api_records=total_api_records,
        consistent_count=consistent_count,
        difference_count=difference_count,
        differences=all_differences,
        consistents=all_consistents,
        failed_codes=failed_codes,
    )


@router.post("/stkfactorpro", response_model=StkFactorProDataResponse, summary="获取专业版因子数据")
@handle_data_api_error
def get_stkfactorpro_data(
    request: StkFactorProDataRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取专业版因子数据（返回所有字段）"""
    records = DataService.get_stkfactorpro_data(db, request.ts_code, request.start_date, request.end_date)
    items = convert_to_response_items(records, StkFactorProDataItem)
    return StkFactorProDataResponse(items=items)


@router.post(
    "/stkfactorpro/fetch-from-api",
    response_model=StkFactorProDataFetchResponse,
    summary="从Tushare接口获取专业版因子数据",
)
@handle_data_api_error
def fetch_stkfactorpro_data_from_api(
    request: StkFactorProDataFetchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """从Tushare接口获取专业版因子数据"""
    from loguru import logger
    from zquant.data.etl.tushare import TushareClient

    ts_codes = [code.strip() for code in request.ts_codes.split(",") if code.strip()]
    if not ts_codes:
        return StkFactorProDataFetchResponse(
            success=False,
            message="请至少提供一个股票代码",
            request_params={},
            data=[],
            total_count=0,
            ts_codes=[],
            failed_codes=[],
        )

    start_date_str = request.start_date.strftime("%Y%m%d")
    end_date_str = request.end_date.strftime("%Y%m%d")
    request_params = {
        "ts_codes": ts_codes,
        "start_date": start_date_str,
        "end_date": end_date_str,
    }

    try:
        client = TushareClient(db=db)
    except Exception as e:
        logger.error(f"初始化Tushare客户端失败: {e}")
        return StkFactorProDataFetchResponse(
            success=False,
            message=f"初始化Tushare客户端失败: {str(e)}",
            request_params=request_params,
            data=[],
            total_count=0,
            ts_codes=ts_codes,
            failed_codes=ts_codes,
        )

    all_data = []
    failed_codes = []

    for ts_code in ts_codes:
        try:
            df = client.get_stk_factor_pro(ts_code=ts_code, start_date=start_date_str, end_date=end_date_str)

            if df is not None and not df.empty:
                records = df.to_dict(orient="records")
                all_data.extend(records)
            else:
                logger.warning(f"{ts_code} 无数据")
                failed_codes.append(ts_code)
        except Exception as e:
            logger.error(f"获取 {ts_code} 数据失败: {e}")
            failed_codes.append(ts_code)

    success = len(failed_codes) < len(ts_codes)
    if len(failed_codes) == len(ts_codes):
        message = f"所有股票代码获取失败"
    elif len(failed_codes) > 0:
        message = f"部分股票代码获取失败: {', '.join(failed_codes)}"
    else:
        message = f"成功获取 {len(ts_codes)} 个股票的数据，共 {len(all_data)} 条记录"

    return StkFactorProDataFetchResponse(
        success=success,
        message=message,
        request_params=request_params,
        data=all_data,
        total_count=len(all_data),
        ts_codes=ts_codes,
        failed_codes=failed_codes,
    )


@router.post("/stkfactorpro/validate", response_model=StkFactorProDataValidateResponse, summary="专业版因子数据校验")
@handle_data_api_error
def validate_stkfactorpro_data(
    request: StkFactorProDataValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """专业版因子数据校验：对比数据库数据和接口数据"""
    from loguru import logger
    from zquant.data.etl.tushare import TushareClient
    from zquant.schemas.data import DataDifferenceItem

    ts_codes = [code.strip() for code in request.ts_codes.split(",") if code.strip()]
    if not ts_codes:
        return StkFactorProDataValidateResponse(
            success=False,
            message="请至少提供一个股票代码",
            ts_codes=[],
            total_db_records=0,
            total_api_records=0,
            consistent_count=0,
            difference_count=0,
            differences=[],
            failed_codes=[],
        )

    start_date_str = request.start_date.strftime("%Y%m%d")
    end_date_str = request.end_date.strftime("%Y%m%d")

    try:
        client = TushareClient(db=db)
    except Exception as e:
        logger.error(f"初始化Tushare客户端失败: {e}")
        return StkFactorProDataValidateResponse(
            success=False,
            message=f"初始化Tushare客户端失败: {str(e)}",
            ts_codes=ts_codes,
            total_db_records=0,
            total_api_records=0,
            consistent_count=0,
            difference_count=0,
            differences=[],
            failed_codes=ts_codes,
        )

    # 专业版因子的主要对比字段（选择关键字段，因为字段很多）
    compare_fields = ["close", "open", "high", "low", "pre_close", "change", "pct_chg", "vol", "amount"]
    numeric_tolerance = 1e-6

    all_differences = []
    all_consistents = []
    total_db_records = 0
    total_api_records = 0
    consistent_count = 0
    failed_codes = []

    for ts_code in ts_codes:
        try:
            db_records = DataService.get_stkfactorpro_data(
                db, ts_code=ts_code, start_date=request.start_date, end_date=request.end_date
            )

            try:
                df = client.get_stk_factor_pro(ts_code=ts_code, start_date=start_date_str, end_date=end_date_str)

                if df is None or df.empty:
                    api_records = []
                else:
                    api_records = df.to_dict(orient="records")
                    for record in api_records:
                        if "trade_date" in record and record["trade_date"]:
                            trade_date_str = str(record["trade_date"])
                            if len(trade_date_str) == 8:
                                record["trade_date"] = (
                                    f"{trade_date_str[:4]}-{trade_date_str[4:6]}-{trade_date_str[6:8]}"
                                )
            except Exception as e:
                logger.error(f"获取 {ts_code} 接口数据失败: {e}")
                failed_codes.append(ts_code)
                continue

            db_index = {}
            for record in db_records:
                key = f"{record.get('ts_code', '')}_{record.get('trade_date', '')}"
                db_index[key] = record
                total_db_records += 1

            api_index = {}
            for record in api_records:
                if "ts_code" not in record:
                    record["ts_code"] = ts_code
                key = f"{record.get('ts_code', '')}_{record.get('trade_date', '')}"
                api_index[key] = record
                total_api_records += 1

            all_keys = set(db_index.keys()) | set(api_index.keys())

            for key in all_keys:
                db_record = db_index.get(key)
                api_record = api_index.get(key)

                if db_record is None and api_record is not None:
                    all_differences.append(
                        DataDifferenceItem(
                            ts_code=ts_code,
                            trade_date=api_record.get("trade_date", ""),
                            difference_type="missing_in_db",
                            field_differences={},
                            db_record=None,
                            api_record=api_record,
                        )
                    )
                elif db_record is not None and api_record is None:
                    all_differences.append(
                        DataDifferenceItem(
                            ts_code=ts_code,
                            trade_date=db_record.get("trade_date", ""),
                            difference_type="missing_in_api",
                            field_differences={},
                            db_record=db_record,
                            api_record=None,
                        )
                    )
                elif db_record is not None and api_record is not None:
                    field_diffs = {}
                    has_diff = False

                    for field in compare_fields:
                        db_value = db_record.get(field)
                        api_value = api_record.get(field)

                        if db_value is None and api_value is None:
                            continue
                        if db_value is None or api_value is None:
                            field_diffs[field] = {"db_value": db_value, "api_value": api_value}
                            has_diff = True
                            continue

                        if isinstance(db_value, (int, float)) and isinstance(api_value, (int, float)):
                            if db_value == 0 and api_value == 0:
                                continue
                            if abs(db_value) > 1e-10:
                                relative_error = abs((db_value - api_value) / db_value)
                            else:
                                relative_error = abs(db_value - api_value)

                            if relative_error > numeric_tolerance:
                                field_diffs[field] = {"db_value": db_value, "api_value": api_value}
                                has_diff = True
                        else:
                            if db_value != api_value:
                                field_diffs[field] = {"db_value": db_value, "api_value": api_value}
                                has_diff = True

                    if has_diff:
                        all_differences.append(
                            DataDifferenceItem(
                                ts_code=ts_code,
                                trade_date=db_record.get("trade_date", ""),
                                difference_type="field_diff",
                                field_differences=field_diffs,
                                db_record=db_record,
                                api_record=api_record,
                            )
                        )
                    else:
                        consistent_count += 1
                        all_consistents.append(
                            DataDifferenceItem(
                                ts_code=ts_code,
                                trade_date=db_record.get("trade_date", ""),
                                difference_type="consistent",
                                field_differences={},
                                db_record=db_record,
                                api_record=api_record,
                            )
                        )
        except Exception as e:
            logger.error(f"校验 {ts_code} 数据失败: {e}")
            failed_codes.append(ts_code)

    difference_count = len(all_differences)

    # 按照 trade_date 倒序排序（最新的日期在前）
    all_differences.sort(key=lambda x: x.trade_date or "", reverse=True)
    all_consistents.sort(key=lambda x: x.trade_date or "", reverse=True)

    success = len(failed_codes) < len(ts_codes)
    if len(failed_codes) == len(ts_codes):
        message = f"所有股票代码校验失败"
    elif len(failed_codes) > 0:
        message = f"部分股票代码校验失败: {', '.join(failed_codes)}"
    else:
        message = f"校验完成，共 {len(ts_codes)} 个股票，一致记录 {consistent_count} 条，差异记录 {difference_count} 条"

    return StkFactorProDataValidateResponse(
        success=success,
        message=message,
        ts_codes=ts_codes,
        total_db_records=total_db_records,
        total_api_records=total_api_records,
        consistent_count=consistent_count,
        difference_count=difference_count,
        differences=all_differences,
        consistents=all_consistents,
        failed_codes=failed_codes,
    )


@router.post("/operation-logs", response_model=DataOperationLogResponse, summary="获取数据操作日志")
@handle_data_api_error
def get_data_operation_logs(
    request: DataOperationLogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取数据操作日志列表"""
    logs, total = DataService.get_data_operation_logs(
        db=db,
        skip=request.skip or 0,
        limit=request.limit or 100,
        table_name=request.table_name,
        operation_type=request.operation_type,
        operation_result=request.operation_result,
        start_date=request.start_date,
        end_date=request.end_date,
        order_by=request.order_by,
        order=request.order or "desc",
    )

    items = convert_to_response_items(logs, DataOperationLogItem)
    return DataOperationLogResponse(items=items, total=total)


@router.post("/table-statistics", response_model=TableStatisticsResponse, summary="获取数据表统计")
@handle_data_api_error
def get_table_statistics(
    request: TableStatisticsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取数据表统计列表"""
    stats, total = DataService.get_table_statistics(
        db=db,
        skip=request.skip or 0,
        limit=request.limit or 100,
        stat_date=request.stat_date,
        table_name=request.table_name,
        start_date=request.start_date,
        end_date=request.end_date,
        order_by=request.order_by,
        order=request.order or "desc",
    )

    items = convert_to_response_items(stats, TableStatisticsItem)
    return TableStatisticsResponse(items=items, total=total)


@router.post("/statistics-table-data", response_model=StatisticsTableDataResponse, summary="执行数据表统计（手动触发）")
@handle_data_api_error
def statistics_table_data(
    request: StatisticsTableDataRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """手动触发数据表统计"""
    from datetime import date as date_type

    # 确定统计日期
    if request.stat_date:
        stat_date = request.stat_date
    else:
        # 默认统计当天
        stat_date = date_type.today()

    # 验证日期不能超过今天
    if stat_date > date_type.today():
        return StatisticsTableDataResponse(
            success=False, message=f"统计日期不能超过今天: {stat_date}", stat_date=stat_date, table_count=0
        )

    try:
        results = DataService.statistics_table_data(
            db=db, stat_date=stat_date, created_by=current_user.username if current_user else "api_user"
        )

        return StatisticsTableDataResponse(
            success=True,
            message=f"数据表统计完成，共统计 {len(results)} 个表",
            stat_date=stat_date,
            table_count=len(results),
        )
    except Exception as e:
        return StatisticsTableDataResponse(
            success=False, message=f"统计数据表失败: {e!s}", stat_date=stat_date, table_count=0
        )


@router.post("/sync", summary="手动触发数据同步（管理员）")
@handle_data_api_error
def sync_data(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """手动触发数据同步（仅管理员）"""
    # TODO: 检查管理员权限
    from zquant.data.etl.scheduler import DataScheduler

    scheduler = DataScheduler()
    # 同步股票列表和交易日历
    extra_info = {"created_by": "api_sync", "updated_by": "api_sync"}
    stock_count = scheduler.sync_stock_list(db, extra_info=extra_info)
    cal_count = scheduler.sync_trading_calendar(db, extra_info=extra_info)

    return {"message": "数据同步完成", "stock_count": stock_count, "calendar_count": cal_count}
