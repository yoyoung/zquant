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
//     - Issues: https://github.com/yoyoung/zquant/issues
//     - Documentation: https://github.com/yoyoung/zquant/blob/main/README.md
//     - Repository: https://github.com/yoyoung/zquant

import { useCallback, useEffect, useRef, useMemo } from 'react';
import { useLocation } from '@umijs/max';
import { usePageCacheContext, type PageCache } from '@/contexts/PageCacheContext';

/**
 * 页面缓存Hook
 * 提供便捷的页面状态缓存操作，自动基于当前路由路径管理缓存
 */
export const usePageCache = () => {
  const location = useLocation();
  const { saveCache, getCache, clearCache, hasCache } = usePageCacheContext();
  
  // 使用ref存储当前路径，避免在路径变化时重复获取
  const currentPathRef = useRef<string>(location.pathname);
  
  // 当路径变化时更新ref
  useEffect(() => {
    currentPathRef.current = location.pathname;
  }, [location.pathname]);

  /**
   * 保存当前页面的缓存
   * @param cache 要保存的缓存数据
   */
  const save = useCallback((cache: PageCache) => {
    saveCache(currentPathRef.current, cache);
  }, [saveCache]);

  /**
   * 获取当前页面的缓存
   * @returns 缓存数据，如果不存在则返回undefined
   */
  const get = useCallback((): PageCache | undefined => {
    return getCache(currentPathRef.current);
  }, [getCache]);

  /**
   * 清除当前页面的缓存
   */
  const clear = useCallback(() => {
    clearCache(currentPathRef.current);
  }, [clearCache]);

  /**
   * 检查当前页面是否有缓存
   * @returns 是否存在缓存
   */
  const has = useCallback((): boolean => {
    return hasCache(currentPathRef.current);
  }, [hasCache]);

  /**
   * 更新缓存的部分字段（合并更新）
   * @param partialCache 要更新的部分缓存数据
   */
  const update = useCallback((partialCache: Partial<PageCache>) => {
    const currentCache = get() || {};
    save({ ...currentCache, ...partialCache });
  }, [get, save]);

  /**
   * 保存表单值到缓存
   * @param formValues 表单值
   */
  const saveFormValues = useCallback((formValues: any) => {
    update({ formValues });
  }, [update]);

  /**
   * 从缓存恢复表单值
   * @returns 表单值，如果不存在则返回undefined
   */
  const getFormValues = useCallback((): any => {
    return get()?.formValues;
  }, [get]);

  /**
   * 保存数据源到缓存
   * @param dataSource 数据源
   * @param rawData 原始数据（可选）
   * @param total 总记录数（可选）
   */
  const saveDataSource = useCallback((dataSource: any[], rawData?: any[], total?: number) => {
    update({ dataSource, rawData, total });
  }, [update]);

  /**
   * 从缓存恢复数据源
   * @returns 包含dataSource、rawData和total的对象，如果不存在则返回undefined
   */
  const getDataSource = useCallback(() => {
    const cache = get();
    if (!cache) return undefined;
    return {
      dataSource: cache.dataSource,
      rawData: cache.rawData,
      total: cache.total,
    };
  }, [get]);

  /**
   * 保存弹窗状态到缓存
   * @param modalKey 弹窗的key
   * @param visible 是否可见
   */
  const saveModalState = useCallback((modalKey: string, visible: boolean) => {
    const cache = get() || {};
    const modalStates = cache.modalStates || {};
    update({ modalStates: { ...modalStates, [modalKey]: visible } });
  }, [get, update]);

  /**
   * 从缓存恢复弹窗状态
   * @param modalKey 弹窗的key
   * @returns 是否可见，如果不存在则返回undefined
   */
  const getModalState = useCallback((modalKey: string): boolean | undefined => {
    return get()?.modalStates?.[modalKey];
  }, [get]);

  /**
   * 保存 ProTable 完整状态（查询参数、分页、数据源、总数）
   * @param queryParams ProTable 查询参数
   * @param pagination 分页信息
   * @param dataSource 数据源
   * @param total 总数
   */
  const saveProTableState = useCallback((
    queryParams: any,
    pagination?: { current: number; pageSize: number },
    dataSource?: any[],
    total?: number
  ) => {
    update({
      queryParams,
      pagination,
      dataSource,
      total,
    });
  }, [update]);

  /**
   * 获取 ProTable 完整状态
   * @returns 包含 queryParams、pagination、dataSource、total 的对象
   */
  const getProTableState = useCallback(() => {
    const cache = get();
    if (!cache) return undefined;
    return {
      queryParams: cache.queryParams,
      pagination: cache.pagination,
      dataSource: cache.dataSource,
      total: cache.total,
    };
  }, [get]);

  /**
   * 保存选中的列设置
   * @param selectedColumns 选中的列数组
   */
  const saveSelectedColumns = useCallback((selectedColumns: string[]) => {
    update({ selectedColumns });
  }, [update]);

  /**
   * 从缓存恢复选中的列设置
   * @returns 选中的列数组，如果不存在则返回undefined
   */
  const getSelectedColumns = useCallback((): string[] | undefined => {
    return get()?.selectedColumns;
  }, [get]);

  return useMemo(() => ({
    // 基础方法
    save,
    get,
    clear,
    has,
    update,
    
    // 便捷方法
    saveFormValues,
    getFormValues,
    saveDataSource,
    getDataSource,
    saveModalState,
    getModalState,
    
    // ProTable 专用方法
    saveProTableState,
    getProTableState,
    saveSelectedColumns,
    getSelectedColumns,
    
    // 当前路径（只读）
    currentPath: currentPathRef.current,
  }), [
    save, get, clear, has, update, 
    saveFormValues, getFormValues, saveDataSource, 
    getDataSource, saveModalState, getModalState,
    saveProTableState, getProTableState,
    saveSelectedColumns, getSelectedColumns
  ]);
};

