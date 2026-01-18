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

import React, { createContext, useContext, useState, useCallback, ReactNode, useEffect, useRef } from 'react';

/**
 * 页面缓存数据结构
 */
export interface PageCache {
  dataSource?: any[];           // 表格数据
  total?: number;                // 数据总数
  formValues?: any;              // 表单值
  rawData?: any[];               // 原始数据
  modalStates?: Record<string, boolean>; // 弹窗状态
  queryParams?: any;            // ProTable 查询参数
  pagination?: { current: number; pageSize: number }; // 分页信息
  selectedColumns?: string[];    // 选中的列
  [key: string]: any;            // 其他自定义状态
}

/**
 * sessionStorage 键前缀
 */
const STORAGE_KEY_PREFIX = 'page_cache_';

/**
 * 从 sessionStorage 读取缓存
 */
const loadCacheFromStorage = (path: string): PageCache | undefined => {
  try {
    const key = `${STORAGE_KEY_PREFIX}${path}`;
    const stored = sessionStorage.getItem(key);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.warn(`Failed to load cache from sessionStorage for path: ${path}`, error);
  }
  return undefined;
};

/**
 * 保存缓存到 sessionStorage
 */
const saveCacheToStorage = (path: string, cache: PageCache): void => {
  try {
    const key = `${STORAGE_KEY_PREFIX}${path}`;
    sessionStorage.setItem(key, JSON.stringify(cache));
  } catch (error) {
    // sessionStorage 可能已满或被禁用
    console.warn(`Failed to save cache to sessionStorage for path: ${path}`, error);
    // 尝试清理旧缓存
    try {
      const keys = Object.keys(sessionStorage);
      const cacheKeys = keys.filter(k => k.startsWith(STORAGE_KEY_PREFIX));
      if (cacheKeys.length > 0) {
        // 删除最旧的缓存（简单策略：删除第一个）
        sessionStorage.removeItem(cacheKeys[0]);
        // 重试保存
        sessionStorage.setItem(key, JSON.stringify(cache));
      }
    } catch (retryError) {
      console.warn('Failed to save cache even after cleanup', retryError);
    }
  }
};

/**
 * 从 sessionStorage 删除缓存
 */
const removeCacheFromStorage = (path: string): void => {
  try {
    const key = `${STORAGE_KEY_PREFIX}${path}`;
    sessionStorage.removeItem(key);
  } catch (error) {
    console.warn(`Failed to remove cache from sessionStorage for path: ${path}`, error);
  }
};

/**
 * 清除所有 sessionStorage 中的缓存
 */
const clearAllCacheFromStorage = (): void => {
  try {
    const keys = Object.keys(sessionStorage);
    keys.forEach(key => {
      if (key.startsWith(STORAGE_KEY_PREFIX)) {
        sessionStorage.removeItem(key);
      }
    });
  } catch (error) {
    console.warn('Failed to clear all cache from sessionStorage', error);
  }
};

/**
 * 页面缓存Context类型
 */
interface PageCacheContextType {
  /**
   * 保存页面缓存
   * @param path 页面路径（作为缓存key）
   * @param cache 缓存数据
   */
  saveCache: (path: string, cache: PageCache) => void;
  
  /**
   * 获取页面缓存
   * @param path 页面路径
   * @returns 缓存数据，如果不存在则返回undefined
   */
  getCache: (path: string) => PageCache | undefined;
  
  /**
   * 清除指定页面的缓存
   * @param path 页面路径
   */
  clearCache: (path: string) => void;
  
  /**
   * 清除所有页面缓存
   */
  clearAllCache: () => void;
  
  /**
   * 检查指定页面是否有缓存
   * @param path 页面路径
   * @returns 是否存在缓存
   */
  hasCache: (path: string) => boolean;
}

const PageCacheContext = createContext<PageCacheContextType | undefined>(undefined);

/**
 * 页面缓存Provider组件
 */
interface PageCacheProviderProps {
  children: ReactNode;
}

export const PageCacheProvider: React.FC<PageCacheProviderProps> = ({ children }) => {
  // 使用Map存储页面缓存，key为页面路径
  // 优化：初始化时不加载所有缓存，改为延迟加载（按需加载）
  const [cacheMap, setCacheMap] = useState<Map<string, PageCache>>(() => {
    return new Map<string, PageCache>();
  });

  /**
   * 保存页面缓存（同时保存到内存和 sessionStorage）
   */
  const saveCache = useCallback((path: string, cache: PageCache) => {
    setCacheMap((prev) => {
      const newMap = new Map(prev);
      // 合并现有缓存和新缓存
      const existingCache = newMap.get(path) || {};
      const mergedCache = { ...existingCache, ...cache };
      newMap.set(path, mergedCache);
      
      // 同步保存到 sessionStorage
      saveCacheToStorage(path, mergedCache);
      
      return newMap;
    });
  }, []);

  /**
   * 获取页面缓存（优先从内存获取，如果不存在则从 sessionStorage 加载）
   * 优化：使用 useRef 避免依赖 cacheMap，减少不必要的重新渲染
   */
  const cacheMapRef = useRef<Map<string, PageCache>>(cacheMap);
  
  // 同步 cacheMapRef 和 cacheMap
  useEffect(() => {
    cacheMapRef.current = cacheMap;
  }, [cacheMap]);
  
  const getCache = useCallback((path: string): PageCache | undefined => {
    // 先从内存获取（使用 ref 避免依赖 cacheMap）
    const memoryCache = cacheMapRef.current.get(path);
    if (memoryCache) {
      return memoryCache;
    }
    
    // 如果内存中没有，尝试从 sessionStorage 加载
    const storageCache = loadCacheFromStorage(path);
    if (storageCache) {
      // 使用批量更新，避免频繁触发重新渲染
      setCacheMap((prev) => {
        // 如果已经存在，不重复设置
        if (prev.has(path)) {
          return prev;
        }
        const newMap = new Map(prev);
        newMap.set(path, storageCache);
        cacheMapRef.current = newMap;
        return newMap;
      });
      return storageCache;
    }
    
    return undefined;
  }, []);

  /**
   * 清除指定页面的缓存（同时清除内存和 sessionStorage）
   */
  const clearCache = useCallback((path: string) => {
    setCacheMap((prev) => {
      const newMap = new Map(prev);
      newMap.delete(path);
      return newMap;
    });
    // 同时清除 sessionStorage
    removeCacheFromStorage(path);
  }, []);

  /**
   * 清除所有页面缓存（同时清除内存和 sessionStorage）
   */
  const clearAllCache = useCallback(() => {
    setCacheMap(new Map());
    clearAllCacheFromStorage();
  }, []);

  /**
   * 检查指定页面是否有缓存（检查内存和 sessionStorage）
   * 优化：使用 ref 避免依赖 cacheMap
   */
  const hasCache = useCallback((path: string): boolean => {
    if (cacheMapRef.current.has(path)) {
      return true;
    }
    // 检查 sessionStorage
    const storageCache = loadCacheFromStorage(path);
    return storageCache !== undefined;
  }, []);

  const contextValue: PageCacheContextType = {
    saveCache,
    getCache,
    clearCache,
    clearAllCache,
    hasCache,
  };

  return (
    <PageCacheContext.Provider value={contextValue}>
      {children}
    </PageCacheContext.Provider>
  );
};

/**
 * 使用页面缓存Context的Hook
 * @throws 如果不在PageCacheProvider内使用会抛出错误
 */
export const usePageCacheContext = (): PageCacheContextType => {
  const context = useContext(PageCacheContext);
  if (!context) {
    throw new Error('usePageCacheContext must be used within PageCacheProvider');
  }
  return context;
};

