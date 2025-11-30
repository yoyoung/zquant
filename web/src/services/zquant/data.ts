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
import { request } from '@umijs/max';

/**
 * 获取财务数据
 * POST /api/v1/data/fundamentals
 */
export async function getFundamentals(body: ZQuant.FundamentalsRequest) {
  return request<ZQuant.FundamentalsResponse>('/api/v1/data/fundamentals', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 获取交易日历
 * POST /api/v1/data/calendar
 */
export async function getCalendar(body: ZQuant.CalendarRequest) {
  return request<ZQuant.CalendarResponse>('/api/v1/data/calendar', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 获取股票列表
 * POST /api/v1/data/stocks
 */
export async function getStocks(body?: ZQuant.StockListRequest) {
  return request<ZQuant.StockListResponse>('/api/v1/data/stocks', {
    method: 'POST',
    data: body || {},
  });
}

/**
 * 获取日线数据
 * POST /api/v1/data/daily
 */
export async function getDailyData(body?: ZQuant.DailyDataRequest) {
  return request<ZQuant.DailyDataResponse>('/api/v1/data/daily', {
    method: 'POST',
    data: body || {},
  });
}

/**
 * 从Tushare接口获取日线数据
 * POST /api/v1/data/daily/fetch-from-api
 */
export async function fetchDailyDataFromApi(body: ZQuant.DailyDataFetchRequest) {
  return request<ZQuant.DailyDataFetchResponse>('/api/v1/data/daily/fetch-from-api', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 数据校验：对比数据库数据和接口数据
 * POST /api/v1/data/daily/validate
 */
export async function validateDailyData(body: ZQuant.DailyDataValidateRequest) {
  return request<ZQuant.DailyDataValidateResponse>('/api/v1/data/daily/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 从Tushare接口获取每日指标数据
 * POST /api/v1/data/daily-basic/fetch-from-api
 */
export async function fetchDailyBasicDataFromApi(body: ZQuant.DailyBasicFetchRequest) {
  return request<ZQuant.DailyBasicFetchResponse>('/api/v1/data/daily-basic/fetch-from-api', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 每日指标数据校验
 * POST /api/v1/data/daily-basic/validate
 */
export async function validateDailyBasicData(body: ZQuant.DailyBasicValidateRequest) {
  return request<ZQuant.DailyBasicValidateResponse>('/api/v1/data/daily-basic/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 从Tushare接口获取技术因子数据
 * POST /api/v1/data/factor/fetch-from-api
 */
export async function fetchFactorDataFromApi(body: ZQuant.FactorDataFetchRequest) {
  return request<ZQuant.FactorDataFetchResponse>('/api/v1/data/factor/fetch-from-api', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 技术因子数据校验
 * POST /api/v1/data/factor/validate
 */
export async function validateFactorData(body: ZQuant.FactorDataValidateRequest) {
  return request<ZQuant.FactorDataValidateResponse>('/api/v1/data/factor/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 从Tushare接口获取专业版因子数据
 * POST /api/v1/data/stkfactorpro/fetch-from-api
 */
export async function fetchStkFactorProDataFromApi(body: ZQuant.StkFactorProDataFetchRequest) {
  return request<ZQuant.StkFactorProDataFetchResponse>('/api/v1/data/stkfactorpro/fetch-from-api', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 专业版因子数据校验
 * POST /api/v1/data/stkfactorpro/validate
 */
export async function validateStkFactorProData(body: ZQuant.StkFactorProDataValidateRequest) {
  return request<ZQuant.StkFactorProDataValidateResponse>('/api/v1/data/stkfactorpro/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 从Tushare接口获取财务数据
 * POST /api/v1/data/fundamentals/fetch-from-api
 */
export async function fetchFundamentalsFromApi(body: ZQuant.FundamentalsFetchRequest) {
  return request<ZQuant.FundamentalsFetchResponse>('/api/v1/data/fundamentals/fetch-from-api', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 财务数据校验
 * POST /api/v1/data/fundamentals/validate
 */
export async function validateFundamentals(body: ZQuant.FundamentalsValidateRequest) {
  return request<ZQuant.FundamentalsValidateResponse>('/api/v1/data/fundamentals/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 从Tushare接口获取股票列表
 * POST /api/v1/data/stocks/fetch-from-api
 */
export async function fetchStockListFromApi(body: ZQuant.StockListFetchRequest) {
  return request<ZQuant.StockListFetchResponse>('/api/v1/data/stocks/fetch-from-api', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 股票列表数据校验
 * POST /api/v1/data/stocks/validate
 */
export async function validateStockList(body: ZQuant.StockListValidateRequest) {
  return request<ZQuant.StockListValidateResponse>('/api/v1/data/stocks/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 从Tushare接口获取交易日历
 * POST /api/v1/data/calendar/fetch-from-api
 */
export async function fetchCalendarFromApi(body: ZQuant.CalendarFetchRequest) {
  return request<ZQuant.CalendarFetchResponse>('/api/v1/data/calendar/fetch-from-api', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 交易日历数据校验
 * POST /api/v1/data/calendar/validate
 */
export async function validateCalendar(body: ZQuant.CalendarValidateRequest) {
  return request<ZQuant.CalendarValidateResponse>('/api/v1/data/calendar/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body,
  });
}

/**
 * 获取每日指标数据
 * POST /api/v1/data/daily-basic
 */
export async function getDailyBasicData(body?: ZQuant.DailyBasicRequest) {
  return request<ZQuant.DailyBasicResponse>('/api/v1/data/daily-basic', {
    method: 'POST',
    data: body || {},
  });
}

/**
 * 获取因子数据
 * POST /api/v1/data/factor
 */
export async function getFactorData(body?: ZQuant.FactorDataRequest) {
  return request<ZQuant.FactorDataResponse>('/api/v1/data/factor', {
    method: 'POST',
    data: body || {},
  });
}

/**
 * 获取专业版因子数据
 * POST /api/v1/data/stkfactorpro
 */
export async function getStkFactorProData(body?: ZQuant.StkFactorProDataRequest) {
  return request<ZQuant.StkFactorProDataResponse>('/api/v1/data/stkfactorpro', {
    method: 'POST',
    data: body || {},
  });
}

/**
 * 获取数据操作日志
 * POST /api/v1/data/operation-logs
 */
export async function getDataOperationLogs(body?: ZQuant.DataOperationLogRequest) {
  return request<ZQuant.DataOperationLogResponse>('/api/v1/data/operation-logs', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body || {},
  });
}

/**
 * 获取数据表统计
 * POST /api/v1/data/table-statistics
 */
export async function getTableStatistics(body?: ZQuant.TableStatisticsRequest) {
  return request<ZQuant.TableStatisticsResponse>('/api/v1/data/table-statistics', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body || {},
  });
}

/**
 * 执行数据表统计（手动触发）
 * POST /api/v1/data/statistics-table-data
 */
export async function statisticsTableData(body?: ZQuant.StatisticsTableDataRequest) {
  return request<ZQuant.StatisticsTableDataResponse>('/api/v1/data/statistics-table-data', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: body || {},
  });
}

/**
 * 手动触发数据同步（管理员）
 * POST /api/v1/data/sync
 */
export async function syncData() {
  return request<{
    message: string;
    stock_count: number;
    calendar_count: number;
  }>('/api/v1/data/sync', {
    method: 'POST',
  });
}

