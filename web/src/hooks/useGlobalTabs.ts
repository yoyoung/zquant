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

import { history } from '@umijs/max';
import { useCallback, useState } from 'react';

export interface TabItem {
  key: string;
  title: string;
  path: string;
  closable?: boolean;
}

const MAX_TABS = 10;

export const useGlobalTabs = () => {
  const [tabs, setTabs] = useState<TabItem[]>([]);
  const [activeKey, setActiveKey] = useState<string>('');

  /**
   * 添加或激活页卡
   */
  const addTab = useCallback((tab: TabItem) => {
    setTabs((prevTabs) => {
      // 检查页卡是否已存在
      const existingTabIndex = prevTabs.findIndex((t) => t.key === tab.key);
      if (existingTabIndex !== -1) {
        // 如果存在，更新标题并切换激活状态（标题可能在语言切换时变化）
        const updatedTabs = [...prevTabs];
        updatedTabs[existingTabIndex] = {
          ...updatedTabs[existingTabIndex],
          title: tab.title, // 更新标题
        };
        setActiveKey(tab.key);
        return updatedTabs;
      }

      // 如果不存在，添加新页卡
      let newTabs = [...prevTabs, tab];

      // 如果超过最大数量，移除最旧的页卡（保留当前激活的页卡）
      if (newTabs.length > MAX_TABS) {
        // 找到当前激活页卡的索引
        const activeIndex = prevTabs.findIndex((t) => t.key === activeKey);
        if (activeIndex > 0) {
          // 如果激活页卡不是第一个，移除第一个
          newTabs = prevTabs.slice(1).concat(tab);
        } else {
          // 如果激活页卡是第一个，移除第二个
          newTabs = [prevTabs[0], ...prevTabs.slice(2), tab];
        }
      }

      setActiveKey(tab.key);
      return newTabs;
    });
  }, [activeKey]);

  /**
   * 关闭页卡
   */
  const removeTab = useCallback((targetKey: string) => {
    setTabs((prevTabs) => {
      const newTabs = prevTabs.filter((tab) => tab.key !== targetKey);
      
      // 如果关闭的是当前激活的页卡
      if (targetKey === activeKey) {
        // 找到下一个激活的页卡
        const currentIndex = prevTabs.findIndex((tab) => tab.key === targetKey);
        let newActiveKey = '';
        
        if (newTabs.length > 0) {
          // 优先选择右侧的页卡，如果没有则选择左侧的
          if (currentIndex < newTabs.length) {
            newActiveKey = newTabs[currentIndex].key;
          } else {
            newActiveKey = newTabs[newTabs.length - 1].key;
          }
        }
        
        setActiveKey(newActiveKey);
        
        // 跳转到新激活的页卡路径
        if (newActiveKey) {
          const targetTab = newTabs.find((tab) => tab.key === newActiveKey);
          if (targetTab) {
            history.push(targetTab.path);
          }
        } else {
          // 如果没有页卡了，跳转到首页
          history.push('/welcome');
        }
      }
      
      return newTabs;
    });
  }, [activeKey]);

  /**
   * 切换页卡
   */
  const changeTab = useCallback((key: string) => {
    setActiveKey(key);
    const tab = tabs.find((t) => t.key === key);
    if (tab) {
      history.push(tab.path);
    }
  }, [tabs]);

  /**
   * 根据路径获取页卡标题
   */
  const getTabTitleByPath = useCallback((path: string, menuData: any[]): string => {
    const findTitle = (routes: any[], currentPath: string): string => {
      for (const route of routes) {
        if (route.path === currentPath && route.name) {
          return route.name;
        }
        if (route.routes) {
          const found = findTitle(route.routes, currentPath);
          if (found) return found;
        }
      }
      return '';
    };
    
    return findTitle(menuData, path) || path;
  }, []);

  return {
    tabs,
    activeKey,
    addTab,
    removeTab,
    changeTab,
    getTabTitleByPath,
  };
};

