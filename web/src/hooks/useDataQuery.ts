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

import { useState, useCallback, useRef } from 'react';
import { message } from 'antd';
import dayjs, { Dayjs } from 'dayjs';

/**
 * 数据查询Hook
 * 
 * 提供统一的数据查询状态管理和逻辑
 * 
 * @param queryFn 查询函数，接收查询参数，返回Promise
 * @param getItems 从响应中提取items的函数
 * @param getKey 生成记录key的函数
 * @param options 可选配置项
 * @returns 查询相关的状态和方法
 */
export function useDataQuery<TItem extends Record<string, any>>(
  queryFn: (params: any) => Promise<any>,
  getItems: (response: any) => TItem[],
  getKey: (item: TItem, index: number) => string | number,
  options?: {
    successMessage?: string | ((count: number) => string);
    errorMessage?: string;
    autoQuery?: boolean;
  }
) {
  const [dataSource, setDataSource] = useState<TItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [rawData, setRawData] = useState<TItem[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleQuery = useCallback(async (values: any) => {
    // 取消之前的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      setLoading(true);
      const [startDate, endDate] = values.dateRange || [];
      
      const params: any = {};
      if (values.ts_code) {
        params.ts_code = values.ts_code;
      }
      if (startDate) {
        params.start_date = dayjs(startDate).format('YYYY-MM-DD');
      }
      if (endDate) {
        params.end_date = dayjs(endDate).format('YYYY-MM-DD');
      }
      
      const response = await queryFn(params);
      const items = getItems(response);
      
      // 转换数据格式为表格数据
      const tableData = items.map((item, index) => ({
        key: getKey(item, index),
        ...item,
      }));
      
      setDataSource(tableData);
      setRawData(items);
      
      // 显示成功消息
      const successMsg = options?.successMessage
        ? typeof options.successMessage === 'function'
          ? options.successMessage(tableData.length)
          : options.successMessage
        : `查询成功，共${tableData.length}条记录`;
      message.success(successMsg);
    } catch (error: any) {
      // 如果是取消请求，不显示错误
      if (error?.name === 'AbortError') {
        return;
      }
      const errorMsg = options?.errorMessage || error?.response?.data?.detail || '查询失败';
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [queryFn, getItems, getKey, options]);

  return {
    dataSource,
    rawData,
    loading,
    handleQuery,
    setDataSource,
    setRawData,
  };
}

/**
 * 通用API调用Hook
 * 
 * 提供统一的API调用状态管理和错误处理
 */
export function useApiCall<TParams = any, TResponse = any>(
  apiFn: (params: TParams) => Promise<TResponse>,
  options?: {
    onSuccess?: (data: TResponse) => void;
    onError?: (error: any) => void;
    successMessage?: string;
    errorMessage?: string;
    showMessage?: boolean;
  }
) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<TResponse | null>(null);
  const [error, setError] = useState<any>(null);

  const execute = useCallback(async (params: TParams) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiFn(params);
      setData(response);
      
      if (options?.onSuccess) {
        options.onSuccess(response);
      }
      
      if (options?.showMessage !== false && options?.successMessage) {
        message.success(options.successMessage);
      }
      
      return response;
    } catch (err: any) {
      setError(err);
      
      if (options?.onError) {
        options.onError(err);
      }
      
      if (options?.showMessage !== false) {
        const errorMsg = options?.errorMessage || err?.response?.data?.detail || '操作失败';
        message.error(errorMsg);
      }
      
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiFn, options]);

  return {
    loading,
    data,
    error,
    execute,
    reset: () => {
      setData(null);
      setError(null);
    },
  };
}

/**
 * 日期范围处理Hook
 * 
 * 提供统一的日期范围处理逻辑
 */
export function useDateRange() {
  const formatDateRange = useCallback((dateRange: [Dayjs, Dayjs] | null | undefined) => {
    if (!dateRange || !dateRange[0] || !dateRange[1]) {
      return { start_date: undefined, end_date: undefined };
    }
    return {
      start_date: dayjs(dateRange[0]).format('YYYY-MM-DD'),
      end_date: dayjs(dateRange[1]).format('YYYY-MM-DD'),
    };
  }, []);

  const parseDateRange = useCallback((startDate?: string, endDate?: string): [Dayjs, Dayjs] | null => {
    if (!startDate || !endDate) {
      return null;
    }
    return [dayjs(startDate), dayjs(endDate)];
  }, []);

  return {
    formatDateRange,
    parseDateRange,
  };
}

