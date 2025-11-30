// @ts-ignore
// Copyright 2025 ZQuant Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Author: kevin
// Contact:
//     - Email: kevin@vip.qq.com
//     - Wechat: zquant2025
//     - Issues: https://github.com/zquant/zquant/issues
//     - Documentation: https://docs.zquant.com
//     - Repository: https://github.com/zquant/zquant

/* eslint-disable */

/**
 * zquant API类型定义
 * 对应后端Pydantic模型
 */

declare namespace ZQuant {
  // ============ 认证相关 ============
  type LoginRequest = {
    username: string;
    password: string;
  };

  type Token = {
    access_token: string;
    refresh_token: string;
    token_type: string;
  };

  // ============ 用户相关 ============
  type UserResponse = {
    id: number;
    username: string;
    email: string;
    role_id: number;
    is_active: boolean;
    created_at: string;
  };

  type UserCreate = {
    username: string;
    email: string;
    password: string;
    password_confirm: string;
    role_id: number;
  };

  type UserUpdate = {
    email?: string;
    is_active?: boolean;
    role_id?: number;
  };

  type PasswordReset = {
    password: string;
    password_confirm: string;
  };

  type APIKeyCreate = {
    name?: string;
  };

  type APIKeyResponse = {
    id: number;
    access_key: string;
    name?: string;
    is_active: boolean;
    last_used_at?: string;
    created_at: string;
    expires_at?: string;
  };

  type APIKeyCreateResponse = {
    id: number;
    access_key: string;
    secret_key: string;
    name?: string;
    created_at: string;
    expires_at?: string;
    message: string;
  };

  // ============ 通知相关 ============
  type NotificationType = 'system' | 'strategy' | 'backtest' | 'data' | 'warning';

  type NotificationResponse = {
    id: number;
    user_id: number;
    type: NotificationType;
    title: string;
    content: string;
    is_read: boolean;
    extra_data?: Record<string, any>;
    created_at: string;
    updated_at: string;
  };

  type NotificationCreate = {
    user_id: number;
    type?: NotificationType;
    title: string;
    content: string;
    extra_data?: Record<string, any>;
  };

  type NotificationUpdate = {
    is_read?: boolean;
  };

  type NotificationListResponse = {
    items: NotificationResponse[];
    total: number;
    skip: number;
    limit: number;
  };

  type NotificationStatsResponse = {
    unread_count: number;
    total_count: number;
  };

  // ============ 数据相关 ============
  type FundamentalsRequest = {
    symbols: string[];
    statement_type: string; // income, balance, cashflow
    report_date?: string; // YYYY-MM-DD
  };

  type FundamentalsResponse = {
    data: Record<string, any>;
    field_descriptions: Record<string, string>; // 字段释义，字段名到释义的映射
  };

  type CalendarRequest = {
    start_date: string; // YYYY-MM-DD
    end_date: string; // YYYY-MM-DD
    exchange?: string; // 交易所，'all'或undefined表示所有交易所，SSE=上交所，SZSE=深交所
  };

  type CalendarItem = {
    id?: number; // 记录ID
    exchange?: string; // 交易所
    cal_date: string; // 日历日期（ISO格式）
    is_open?: number; // 是否交易，1=交易日，0=非交易日
    pretrade_date?: string; // 上一交易日（ISO格式）
    created_by?: string; // 创建人
    created_time?: string; // 创建时间（ISO格式）
    updated_by?: string; // 修改人
    updated_time?: string; // 修改时间（ISO格式）
  };

  type CalendarResponse = {
    items: CalendarItem[]; // 交易日历列表（包含所有字段）
  };

  type StockListRequest = {
    exchange?: string; // 交易所代码，精确查询，如：SSE=上交所，SZSE=深交所
    symbol?: string; // 股票代码，精确查询，如：000001
    name?: string; // 股票名称，模糊查询
  };

  type StockListResponse = {
    stocks: Array<{
      ts_code?: string;
      symbol?: string;
      name?: string;
      area?: string;
      industry?: string;
      fullname?: string;
      enname?: string;
      cnspell?: string;
      market?: string;
      exchange?: string;
      curr_type?: string;
      list_status?: string;
      list_date?: string;
      delist_date?: string;
      is_hs?: string;
      act_name?: string;
      act_ent_type?: string;
      created_by?: string;
      created_time?: string;
      updated_by?: string;
      updated_time?: string;
      [key: string]: any;
    }>;
  };

  type DailyDataRequest = {
    ts_code?: string; // TS代码，如：000001.SZ，undefined表示查询所有
    start_date?: string; // 开始日期，YYYY-MM-DD
    end_date?: string; // 结束日期，YYYY-MM-DD
  };

  type DailyDataItem = {
    id?: number; // 记录ID
    ts_code?: string; // TS代码
    trade_date?: string; // 交易日期（ISO格式）
    open?: number; // 开盘价
    high?: number; // 最高价
    low?: number; // 最低价
    close?: number; // 收盘价
    pre_close?: number; // 昨收价
    change?: number; // 涨跌额
    pct_chg?: number; // 涨跌幅
    vol?: number; // 成交量（手）
    amount?: number; // 成交额（千元）
    created_by?: string; // 创建人
    created_time?: string; // 创建时间（ISO格式）
    updated_by?: string; // 修改人
    updated_time?: string; // 修改时间（ISO格式）
  };

  type DailyDataResponse = {
    items: DailyDataItem[]; // 日线数据列表（包含所有字段）
  };

  // ============ 接口数据获取相关 ============
  type DailyDataFetchRequest = {
    ts_codes: string; // TS代码，支持多个，用逗号分隔，如：000001.SZ,000002.SZ
    start_date: string; // 开始日期，YYYY-MM-DD
    end_date: string; // 结束日期，YYYY-MM-DD
    adj?: string; // 复权类型：qfq=前复权, hfq=后复权, None=不复权
  };

  type DailyDataFetchResponse = {
    success: boolean; // 是否成功
    message: string; // 响应消息
    request_params: Record<string, any>; // 请求参数
    data: Record<string, any>[]; // 返回的JSON数据（DataFrame转JSON）
    total_count: number; // 总记录数
    ts_codes: string[]; // 查询的股票代码列表
    failed_codes: string[]; // 失败的股票代码列表
  };

  // ============ 数据校验相关 ============
  type DailyDataValidateRequest = {
    ts_codes: string; // TS代码，支持多个，用逗号分隔，如：000001.SZ,000002.SZ
    start_date: string; // 开始日期，YYYY-MM-DD
    end_date: string; // 结束日期，YYYY-MM-DD
    adj?: string; // 复权类型：qfq=前复权, hfq=后复权, None=不复权
  };

  type DataDifferenceItem = {
    ts_code: string; // TS代码
    trade_date: string; // 交易日期
    difference_type: string; // 差异类型：missing_in_db=数据库缺失, missing_in_api=接口缺失, field_diff=字段不一致
    field_differences: Record<string, { db_value: any; api_value: any } }; // 字段差异，格式：{字段名: {db_value: 数据库值, api_value: 接口值}}
    db_record: Record<string, any> | null; // 数据库记录（如果存在）
    api_record: Record<string, any> | null; // 接口记录（如果存在）
  };

  type DailyDataValidateResponse = {
    success: boolean; // 是否成功
    message: string; // 响应消息
    ts_codes: string[]; // 校验的股票代码列表
    total_db_records: number; // 数据库总记录数
    total_api_records: number; // 接口总记录数
    consistent_count: number; // 一致记录数
    difference_count: number; // 差异记录数
    differences: DataDifferenceItem[]; // 差异详情列表
    consistents: DataDifferenceItem[]; // 一致记录列表
    failed_codes: string[]; // 失败的股票代码列表
  };

  // ============ 每日指标接口数据获取和数据校验 ============
  type DailyBasicFetchRequest = {
    ts_codes: string; // TS代码，支持多个，用逗号分隔
    start_date: string; // 开始日期，YYYY-MM-DD
    end_date: string; // 结束日期，YYYY-MM-DD
  };

  type DailyBasicFetchResponse = {
    success: boolean;
    message: string;
    request_params: Record<string, any>;
    data: Record<string, any>[];
    total_count: number;
    ts_codes: string[];
    failed_codes: string[];
  };

  type DailyBasicValidateRequest = {
    ts_codes: string;
    start_date: string;
    end_date: string;
  };

  type DailyBasicValidateResponse = {
    success: boolean;
    message: string;
    ts_codes: string[];
    total_db_records: number;
    total_api_records: number;
    consistent_count: number;
    difference_count: number;
    differences: DataDifferenceItem[];
    consistents: DataDifferenceItem[];
    failed_codes: string[];
  };

  // ============ 技术因子接口数据获取和数据校验 ============
  type FactorDataFetchRequest = {
    ts_codes: string;
    start_date: string;
    end_date: string;
  };

  type FactorDataFetchResponse = {
    success: boolean;
    message: string;
    request_params: Record<string, any>;
    data: Record<string, any>[];
    total_count: number;
    ts_codes: string[];
    failed_codes: string[];
  };

  type FactorDataValidateRequest = {
    ts_codes: string;
    start_date: string;
    end_date: string;
  };

  type FactorDataValidateResponse = {
    success: boolean;
    message: string;
    ts_codes: string[];
    total_db_records: number;
    total_api_records: number;
    consistent_count: number;
    difference_count: number;
    differences: DataDifferenceItem[];
    consistents: DataDifferenceItem[];
    failed_codes: string[];
  };

  // ============ 专业版因子接口数据获取和数据校验 ============
  type StkFactorProDataFetchRequest = {
    ts_codes: string;
    start_date: string;
    end_date: string;
  };

  type StkFactorProDataFetchResponse = {
    success: boolean;
    message: string;
    request_params: Record<string, any>;
    data: Record<string, any>[];
    total_count: number;
    ts_codes: string[];
    failed_codes: string[];
  };

  type StkFactorProDataValidateRequest = {
    ts_codes: string;
    start_date: string;
    end_date: string;
  };

  type StkFactorProDataValidateResponse = {
    success: boolean;
    message: string;
    ts_codes: string[];
    total_db_records: number;
    total_api_records: number;
    consistent_count: number;
    difference_count: number;
    differences: DataDifferenceItem[];
    consistents: DataDifferenceItem[];
    failed_codes: string[];
  };

  // ============ 财务数据接口数据获取和数据校验 ============
  type FundamentalsFetchRequest = {
    symbols: string; // 股票代码，支持多个，用逗号分隔
    statement_type: string; // 报表类型：income, balance, cashflow
    start_date?: string; // 开始日期，YYYY-MM-DD
    end_date?: string; // 结束日期，YYYY-MM-DD
  };

  type FundamentalsFetchResponse = {
    success: boolean;
    message: string;
    request_params: Record<string, any>;
    data: Record<string, Record<string, any>[]>; // 按股票代码组织的数据
    total_count: number;
    symbols: string[];
    failed_codes: string[];
  };

  type FundamentalsValidateRequest = {
    symbols: string;
    statement_type: string;
    start_date?: string;
    end_date?: string;
  };

  type FundamentalsValidateResponse = {
    success: boolean;
    message: string;
    symbols: string[];
    total_db_records: number;
    total_api_records: number;
    consistent_count: number;
    difference_count: number;
    differences: DataDifferenceItem[];
    consistents: DataDifferenceItem[];
    failed_codes: string[];
  };

  // ============ 股票列表接口数据获取和数据校验 ============
  type StockListFetchRequest = {
    exchange?: string; // 交易所代码
    list_status?: string; // 上市状态
  };

  type StockListFetchResponse = {
    success: boolean;
    message: string;
    request_params: Record<string, any>;
    data: Record<string, any>[];
    total_count: number;
  };

  type StockListValidateRequest = {
    exchange?: string;
    list_status?: string;
  };

  type StockListValidateResponse = {
    success: boolean;
    message: string;
    total_db_records: number;
    total_api_records: number;
    consistent_count: number;
    difference_count: number;
    differences: DataDifferenceItem[];
    consistents: DataDifferenceItem[];
  };

  // ============ 交易日历接口数据获取和数据校验 ============
  type CalendarFetchRequest = {
    start_date: string;
    end_date: string;
    exchange?: string;
  };

  type CalendarFetchResponse = {
    success: boolean;
    message: string;
    request_params: Record<string, any>;
    data: Record<string, any>[];
    total_count: number;
  };

  type CalendarValidateRequest = {
    start_date: string;
    end_date: string;
    exchange?: string;
  };

  type CalendarValidateResponse = {
    success: boolean;
    message: string;
    total_db_records: number;
    total_api_records: number;
    consistent_count: number;
    difference_count: number;
    differences: DataDifferenceItem[];
    consistents: DataDifferenceItem[];
  };

  type DailyBasicRequest = {
    ts_code?: string; // TS代码，如：000001.SZ，undefined表示查询所有
    start_date?: string; // 开始日期，YYYY-MM-DD
    end_date?: string; // 结束日期，YYYY-MM-DD
  };

  type DailyBasicItem = {
    id?: number; // 记录ID
    ts_code?: string; // TS代码
    trade_date?: string; // 交易日期（ISO格式）
    close?: number; // 收盘价
    turnover_rate?: number; // 换手率
    turnover_rate_f?: number; // 换手率（自由流通股）
    volume_ratio?: number; // 量比
    pe?: number; // 市盈率(总市值/净利润)
    pe_ttm?: number; // 市盈率TTM
    pb?: number; // 市净率(总市值/净资产)
    ps?: number; // 市销率
    ps_ttm?: number; // 市销率TTM
    dv_ratio?: number; // 股息率
    dv_ttm?: number; // 股息率TTM
    total_share?: number; // 总股本（万股）
    float_share?: number; // 流通股本（万股）
    free_share?: number; // 自由流通股本（万）
    total_mv?: number; // 总市值（万元）
    circ_mv?: number; // 流通市值（万元）
    created_by?: string; // 创建人
    created_time?: string; // 创建时间（ISO格式）
    updated_by?: string; // 修改人
    updated_time?: string; // 修改时间（ISO格式）
  };

  type DailyBasicResponse = {
    items: DailyBasicItem[]; // 每日指标数据列表（包含所有字段）
  };

  // ============ 因子数据相关 ============
  type FactorDataRequest = {
    ts_code?: string; // TS代码，如：000001.SZ，undefined表示查询所有
    start_date?: string; // 开始日期，YYYY-MM-DD
    end_date?: string; // 结束日期，YYYY-MM-DD
  };

  type FactorDataItem = {
    id?: number; // 记录ID
    ts_code?: string; // TS代码
    trade_date?: string; // 交易日期（ISO格式）
    // 基础价格字段
    close?: number; // 收盘价
    open?: number; // 开盘价
    high?: number; // 最高价
    low?: number; // 最低价
    pre_close?: number; // 昨收价
    change?: number; // 涨跌额
    pct_change?: number; // 涨跌幅
    vol?: number; // 成交量（手）
    amount?: number; // 成交额（千元）
    adj_factor?: number; // 复权因子
    // 复权价格字段
    open_hfq?: number; // 开盘价后复权
    open_qfq?: number; // 开盘价前复权
    close_hfq?: number; // 收盘价后复权
    close_qfq?: number; // 收盘价前复权
    high_hfq?: number; // 最高价后复权
    high_qfq?: number; // 最高价前复权
    low_hfq?: number; // 最低价后复权
    low_qfq?: number; // 最低价前复权
    pre_close_hfq?: number; // 昨收价后复权
    pre_close_qfq?: number; // 昨收价前复权
    // 技术指标字段
    macd_dif?: number; // MACD_DIF
    macd_dea?: number; // MACD_DEA
    macd?: number; // MACD
    kdj_k?: number; // KDJ_K
    kdj_d?: number; // KDJ_D
    kdj_j?: number; // KDJ_J
    rsi_6?: number; // RSI_6
    rsi_12?: number; // RSI_12
    rsi_24?: number; // RSI_24
    boll_upper?: number; // BOLL_UPPER
    boll_mid?: number; // BOLL_MID
    boll_lower?: number; // BOLL_LOWER
    cci?: number; // CCI
    // 审计字段
    created_by?: string; // 创建人
    created_time?: string; // 创建时间（ISO格式）
    updated_by?: string; // 修改人
    updated_time?: string; // 修改时间（ISO格式）
    [key: string]: any; // 允许额外字段
  };

  type FactorDataResponse = {
    items: FactorDataItem[]; // 因子数据列表（包含所有字段）
  };

  // ============ 专业版因子数据相关 ============
  type StkFactorProDataRequest = {
    ts_code?: string; // TS代码，如：000001.SZ，undefined表示查询所有
    start_date?: string; // 开始日期，YYYY-MM-DD
    end_date?: string; // 结束日期，YYYY-MM-DD
  };

  type StkFactorProDataItem = {
    id?: number; // 记录ID
    ts_code?: string; // 股票代码
    trade_date?: string; // 交易日期（ISO格式）
    // 基础价格字段
    open?: number; // 开盘价
    open_hfq?: number; // 开盘价（后复权）
    open_qfq?: number; // 开盘价（前复权）
    high?: number; // 最高价
    high_hfq?: number; // 最高价（后复权）
    high_qfq?: number; // 最高价（前复权）
    low?: number; // 最低价
    low_hfq?: number; // 最低价（后复权）
    low_qfq?: number; // 最低价（前复权）
    close?: number; // 收盘价
    close_hfq?: number; // 收盘价（后复权）
    close_qfq?: number; // 收盘价（前复权）
    pre_close?: number; // 昨收价(前复权)
    change?: number; // 涨跌额
    pct_chg?: number; // 涨跌幅
    vol?: number; // 成交量（手）
    amount?: number; // 成交额（千元）
    // 市场指标字段
    turnover_rate?: number; // 换手率（%）
    turnover_rate_f?: number; // 换手率（自由流通股）
    volume_ratio?: number; // 量比
    pe?: number; // 市盈率
    pe_ttm?: number; // 市盈率（TTM）
    pb?: number; // 市净率
    ps?: number; // 市销率
    ps_ttm?: number; // 市销率（TTM）
    dv_ratio?: number; // 股息率（%）
    dv_ttm?: number; // 股息率（TTM）（%）
    total_share?: number; // 总股本（万股）
    float_share?: number; // 流通股本（万股）
    free_share?: number; // 自由流通股本（万）
    total_mv?: number; // 总市值（万元）
    circ_mv?: number; // 流通市值（万元）
    adj_factor?: number; // 复权因子
    // 技术指标字段（非常多，使用索引签名允许额外字段）
    // 审计字段
    created_by?: string; // 创建人
    created_time?: string; // 创建时间（ISO格式）
    updated_by?: string; // 修改人
    updated_time?: string; // 修改时间（ISO格式）
    [key: string]: any; // 允许额外字段（包含所有技术指标字段）
  };

  type StkFactorProDataResponse = {
    items: StkFactorProDataItem[]; // 专业版因子数据列表（包含所有字段）
  };

  // ============ 数据操作日志相关 ============
  type DataOperationLogItem = {
    id?: number; // 日志ID
    table_name?: string; // 数据表名
    operation_type?: string; // 操作类型：insert, update, delete, sync等
    insert_count?: number; // 插入记录数
    update_count?: number; // 更新记录数
    delete_count?: number; // 删除记录数
    operation_result?: string; // 操作结果：success, failed, partial_success
    error_message?: string; // 错误信息
    start_time?: string; // 开始时间（ISO格式）
    end_time?: string; // 结束时间（ISO格式）
    duration_seconds?: number; // 耗时(秒)
    created_by?: string; // 创建人
    created_time?: string; // 创建时间（ISO格式）
  };

  type DataOperationLogRequest = {
    table_name?: string; // 数据表名，模糊查询
    operation_type?: string; // 操作类型：insert, update, delete, sync等
    operation_result?: string; // 操作结果：success, failed, partial_success
    start_date?: string; // 开始日期（筛选created_time），YYYY-MM-DD
    end_date?: string; // 结束日期（筛选created_time），YYYY-MM-DD
    skip?: number; // 跳过记录数
    limit?: number; // 每页记录数
    order_by?: string; // 排序字段：id, table_name, operation_type, operation_result, created_time, start_time等
    order?: 'asc' | 'desc'; // 排序方向：asc 或 desc
  };

  type DataOperationLogResponse = {
    items: DataOperationLogItem[]; // 数据操作日志列表
    total: number; // 总记录数
  };

  // ============ 回测相关 ============
  type BacktestConfig = {
    start_date: string; // YYYY-MM-DD
    end_date: string; // YYYY-MM-DD
    initial_capital?: number;
    symbols: string[];
    frequency?: string; // daily（日线）
    adjust_type?: string; // qfq, hfq, None
    commission_rate?: number;
    min_commission?: number;
    tax_rate?: number;
    slippage_rate?: number;
    benchmark?: string;
    use_daily_basic?: boolean; // 是否使用每日指标数据
  };

  type BacktestRunRequest = {
    strategy_code: string;
    strategy_name: string;
    config: BacktestConfig;
  };

  type BacktestTaskResponse = {
    id: number;
    user_id: number;
    strategy_name?: string;
    status: string; // pending, running, completed, failed
    error_message?: string;
    created_at: string;
    started_at?: string;
    completed_at?: string;
    start_date?: string; // 回测数据开始日期（YYYY-MM-DD）
    end_date?: string; // 回测数据结束日期（YYYY-MM-DD）
  };

  type BacktestResultResponse = {
    id: number;
    task_id: number;
    total_return?: number;
    annual_return?: number;
    max_drawdown?: number;
    sharpe_ratio?: number;
    win_rate?: number;
    profit_loss_ratio?: number;
    alpha?: number;
    beta?: number;
    metrics_json?: string;
    trades_json?: string;
    portfolio_json?: string;
    created_at: string;
  };

  type PerformanceResponse = {
    metrics: Record<string, any>;
    trades: Array<Record<string, any>>;
    portfolio: Record<string, any>;
  };

  type StrategyResponse = {
    id: number;
    user_id: number;
    name: string;
    description?: string;
    category?: string;
    code: string;
    params_schema?: string;
    is_template: boolean;
    created_at: string;
    updated_at: string;
    can_edit?: boolean; // 是否可以编辑
    can_delete?: boolean; // 是否可以删除
  };

  // ============ 分页相关 ============
  type PageResponse<T = any> = {
    items: T[];
    total: number;
    skip: number;
    limit: number;
  };

  // ============ 角色相关 ============
  type RoleResponse = {
    id: number;
    name: string;
    description?: string;
    created_at: string;
  };

  type RoleCreate = {
    name: string;
    description?: string;
  };

  type RoleUpdate = {
    name?: string;
    description?: string;
  };

  type RoleWithPermissions = RoleResponse & {
    permissions: PermissionResponse[];
  };

  type AssignPermissionsRequest = {
    permission_ids: number[];
  };

  // ============ 权限相关 ============
  type PermissionResponse = {
    id: number;
    name: string;
    resource: string;
    action: string;
    description?: string;
    created_at: string;
  };

  type PermissionCreate = {
    name: string;
    resource: string;
    action: string;
    description?: string;
  };

  type PermissionUpdate = {
    name?: string;
    resource?: string;
    action?: string;
    description?: string;
  };

  // ============ 定时任务相关 ============
  type TaskType = 
    | 'manual_task'
    | 'common_task'
    | 'workflow';

  type TaskStatus = 'pending' | 'running' | 'success' | 'failed' | 'completed' | 'terminated';
  
  type TaskScheduleStatus = 
    | 'running'      // 运行中：任务正在按计划执行，处于活动状态
    | 'paused'       // 已暂停：任务被手动或系统暂停，暂时不执行
    | 'completed'    // 已完成：任务已成功执行完毕，无后续操作
    | 'failed'       // 失败：任务执行过程中抛出异常或未按预期完成
    | 'pending'      // 等待中：任务尚未到达执行时间点，处于等待状态
    | 'terminated'   // 异常终止：任务因错误或外部干预提前终止
    | 'disabled'     // 未启用：任务未被激活，需手动启用后才可执行
    | 'delayed'      // 延迟中：任务因延迟设置（如固定延迟）尚未触发
    | 'scheduled'    // 调度中：任务已加入调度器队列，等待执行
    | 'expired';     // 过期：任务因超时或未满足条件被取消

  type TaskCreate = {
    name: string;
    task_type: TaskType;
    cron_expression?: string;
    interval_seconds?: number;
    description?: string;
    config?: Record<string, any>;
    max_retries?: number;
    retry_interval?: number;
    enabled?: boolean;
  };

  type TaskUpdate = {
    name?: string;
    cron_expression?: string;
    interval_seconds?: number;
    description?: string;
    config?: Record<string, any>;
    max_retries?: number;
    retry_interval?: number;
  };

  type TaskResponse = {
    id: number;
    name: string;
    job_id: string;
    task_type: TaskType;
    cron_expression?: string;
    interval_seconds?: number;
    enabled: boolean;
    paused: boolean;
    description?: string;
    config: Record<string, any>;
    max_retries: number;
    retry_interval: number;
    created_at: string;
    updated_at: string;
    latest_execution_time?: string;
    latest_execution_status?: TaskStatus;
    schedule_status?: TaskScheduleStatus;
  };

  type TaskListResponse = {
    tasks: TaskResponse[];
    total: number;
  };

  type ExecutionResponse = {
    id: number;
    task_id: number;
    status: TaskStatus;
    start_time: string;
    end_time?: string;
    duration_seconds?: number;
    result: Record<string, any>;
    error_message?: string;
    retry_count: number;
    created_at: string;
  };

  type ExecutionListResponse = {
    executions: ExecutionResponse[];
    total: number;
  };

  type WorkflowTaskItem = {
    task_id: number;
    name: string;
    dependencies: number[];
  };

  type WorkflowTaskConfig = {
    workflow_type: 'serial' | 'parallel';
    tasks: WorkflowTaskItem[];
    on_failure?: 'stop' | 'continue';
  };

        type TaskStatsResponse = {
          total_executions: number;
          success_count: number;
          failed_count: number;
          running_count: number;
          success_rate: number;
          avg_duration_seconds: number;
          latest_execution_time?: string;
        };

        // ============ 数据表统计相关 ============
        type TableStatisticsItem = {
          stat_date?: string; // 统计日期（YYYY-MM-DD）
          table_name?: string; // 表名
          is_split_table?: boolean; // 是否分表
          split_count?: number; // 分表个数
          total_records?: number; // 总记录数
          daily_records?: number; // 日记录数
          daily_insert_count?: number; // 日新增记录数
          daily_update_count?: number; // 日更新记录数
          created_by?: string; // 创建人
          created_time?: string; // 创建时间（ISO格式）
          updated_by?: string; // 修改人
          updated_time?: string; // 修改时间（ISO格式）
        };

        type TableStatisticsRequest = {
          skip?: number; // 跳过记录数
          limit?: number; // 限制返回记录数
          stat_date?: string; // 统计日期，精确查询 (YYYY-MM-DD)
          table_name?: string; // 表名，模糊查询
          start_date?: string; // 开始日期，用于筛选 stat_date (YYYY-MM-DD)
          end_date?: string; // 结束日期，用于筛选 stat_date (YYYY-MM-DD)
          order_by?: string; // 排序字段
          order?: 'asc' | 'desc'; // 排序方式：asc或desc
        };

        type TableStatisticsResponse = {
          items: TableStatisticsItem[]; // 数据表统计列表
          total: number; // 总记录数
        };

        type StatisticsTableDataRequest = {
          stat_date?: string; // 统计日期（可选，默认：当天）(YYYY-MM-DD)
        };

        type StatisticsTableDataResponse = {
          success: boolean; // 是否成功
          message: string; // 响应消息
          stat_date: string; // 统计日期（YYYY-MM-DD）
          table_count: number; // 统计的表数量
        };
      }

      // ============ 配置管理相关 ============
      type ConfigItem = {
        config_key: string; // 配置键
        config_value?: string; // 配置值（已解密或隐藏）
        comment?: string; // 配置说明
        created_by?: string; // 创建人
        created_time?: string; // 创建时间（ISO格式）
        updated_by?: string; // 修改人
        updated_time?: string; // 修改时间（ISO格式）
      };

      type ConfigResponse = {
        config_key: string; // 配置键
        config_value?: string; // 配置值（已解密）
        comment?: string; // 配置说明
        created_by?: string; // 创建人
        created_time?: string; // 创建时间（ISO格式）
        updated_by?: string; // 修改人
        updated_time?: string; // 修改时间（ISO格式）
      };

      type ConfigListResponse = {
        items: ConfigItem[]; // 配置列表
        total: number; // 总记录数
      };

      type ConfigCreateRequest = {
        config_key: string; // 配置键
        config_value: string; // 配置值（明文，会自动加密）
        comment?: string; // 配置说明
      };

      type ConfigUpdateRequest = {
        config_value?: string; // 配置值（明文，会自动加密）
        comment?: string; // 配置说明
      };

      type TushareTokenTestRequest = {
        token?: string; // Token（可选，如果不提供则从数据库读取）
      };

      type TushareTokenTestResponse = {
        success: boolean; // 测试是否成功
        message: string; // 测试结果消息
        data_count?: number; // 测试接口返回的数据条数（如果成功）
      };

      // ============ 系统大盘相关 ============
      type SyncStatusResponse = {
        tushare_connection_status: boolean; // Tushare同步链路是否正常
        is_trading_day: boolean; // 当日是否交易日
        latest_trade_date_from_api: string | null; // Tushare接口返回的最新日线行情数据的交易日期（YYYY-MM-DD格式）
        today_data_ready: boolean; // 当日日线行情数据是否已准备就绪
        latest_trade_date_in_db: string | null; // 数据库中最新日线数据的交易日期（YYYY-MM-DD格式）
      };

      type TaskStatsResponse = {
        total_tasks: number; // 当日总任务数（当日所有执行记录数）
        running_tasks: number; // 进行中任务数（status=RUNNING）
        completed_tasks: number; // 已完成任务数（status=SUCCESS）
        pending_tasks: number; // 待运行任务数（status=PENDING）
        failed_tasks: number; // 出错任务数（status=FAILED）
      };

      type LatestOperationLogItem = {
        id?: number; // 日志ID
        table_name?: string; // 数据表名
        operation_type?: string; // 操作类型
        operation_result?: string; // 操作结果
        insert_count: number; // 插入记录数
        update_count: number; // 更新记录数
        delete_count: number; // 删除记录数
        start_time?: string; // 开始时间（ISO格式）
        end_time?: string; // 结束时间（ISO格式）
        duration_seconds?: number; // 耗时(秒)
        created_by?: string; // 创建人
        created_time?: string; // 创建时间（ISO格式）
      };

      type LatestTableStatisticsItem = {
        stat_date?: string; // 统计日期（ISO格式）
        table_name: string; // 表名
        is_split_table: boolean; // 是否分表
        split_count: number; // 分表个数
        total_records: number; // 总记录数
        daily_records: number; // 日记录数
        daily_insert_count: number; // 日新增记录数
        daily_update_count: number; // 日更新记录数
        created_by?: string; // 创建人
        created_time?: string; // 创建时间（ISO格式）
        updated_time?: string; // 更新时间（ISO格式）
      };

      type LatestDataResponse = {
        latest_operation_logs: LatestOperationLogItem[]; // 数据操作日志表中，按table_name分组，每个表的最新记录列表
        latest_table_statistics: LatestTableStatisticsItem[]; // 数据表统计表中，按table_name分组，每个表的最新记录列表
      };

      type LocalDataStatsResponse = {
        total_tables: number; // 总表数（有操作日志或统计的表数量，去重）
        success_operations: number; // 成功操作数（操作结果为success的记录数）
        failed_operations: number; // 失败操作数（操作结果为failed的记录数）
        total_insert_count: number; // 总插入记录数（所有操作日志的插入记录数之和）
        total_update_count: number; // 总更新记录数（所有操作日志的更新记录数之和）
        split_tables_count: number; // 分表数量（is_split_table=true的表数）
        total_records_sum: number; // 总记录数（所有表统计的总记录数之和）
        daily_records_sum: number; // 日记录数（所有表统计的日记录数之和）
      };
    }

