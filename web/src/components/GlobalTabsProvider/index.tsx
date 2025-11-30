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

import { history, useLocation, useIntl } from '@umijs/max';
import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import GlobalTabs from '../GlobalTabs';
import { useGlobalTabs, type TabItem } from '@/hooks/useGlobalTabs';
import { getMenuI18nKeyByPath } from '@/utils/routeMatcher';
import routes from '../../../config/routes';

interface GlobalTabsContextType {
  tabs: TabItem[];
  activeKey: string;
  addTab: (tab: TabItem) => void;
  removeTab: (key: string) => void;
  changeTab: (key: string) => void;
  menuSearchValue: string;
  setMenuSearchValue: (value: string) => void;
}

const GlobalTabsContext = createContext<GlobalTabsContextType | undefined>(undefined);

export const useGlobalTabsContext = () => {
  const context = useContext(GlobalTabsContext);
  if (!context) {
    throw new Error('useGlobalTabsContext must be used within GlobalTabsProvider');
  }
  return context;
};

/**
 * 根据路径获取菜单标题（从路由配置和国际化文件中查找）
 */
const getMenuTitleByPath = (path: string, formatMessage: (descriptor: { id: string; defaultMessage?: string }) => string): string => {
  // 特殊路径映射（用于确保某些页面的标题正确显示）
  const specialPathMap: Record<string, string> = {
    '/legal/disclaimer': '免责申明',
    '/legal/user-agreement': '用户协议',
    '/account/center': '个人中心',
    '/account/settings': '个人设置',
  };
  
  // 如果路径在特殊映射中，直接返回
  if (specialPathMap[path]) {
    return specialPathMap[path];
  }
  
  // 获取国际化 key（包含隐藏的路由，用于标签页标题）
  const i18nKey = getMenuI18nKeyByPath(path, routes as any[], '', undefined, true);
  
  if (i18nKey) {
    // 使用国际化 API 获取菜单名称
    const menuTitle = formatMessage({ id: i18nKey });
    // 如果获取到了有效的菜单名称（不是 key 本身），则返回
    if (menuTitle && menuTitle !== i18nKey) {
      return menuTitle;
    }
  }
  
  // 如果未找到国际化 key 或获取失败，使用路径的最后一部分作为回退
  const pathParts = path.split('/').filter(Boolean);
  const lastPart = pathParts[pathParts.length - 1];
  
  // 处理动态路由参数（如 :id）
  if (lastPart && !lastPart.includes(':')) {
    return lastPart;
  }
  
  // 如果路径为空或是根路径，返回默认值
  return path || '页面';
};

interface GlobalTabsProviderProps {
  children: React.ReactNode;
}

export const GlobalTabsProvider: React.FC<GlobalTabsProviderProps> = ({ children }) => {
  const location = useLocation();
  const { tabs, activeKey, addTab, removeTab, changeTab } = useGlobalTabs();
  const [menuSearchValue, setMenuSearchValue] = useState('');
  const intl = useIntl();

  // 监听路由变化，自动添加页卡
  useEffect(() => {
    const pathname = location.pathname;
    
    // 排除登录页面和不需要页卡的页面
    if (pathname === '/user/login' || pathname.startsWith('/user/register')) {
      return;
    }

    // 生成页卡key（使用路径）
    const tabKey = pathname;
    const tabTitle = getMenuTitleByPath(pathname, intl.formatMessage);

    // 添加或激活页卡
    addTab({
      key: tabKey,
      title: tabTitle,
      path: pathname,
      closable: true,
    });
  }, [location.pathname, addTab, intl]);

  const handleTabChange = (key: string) => {
    changeTab(key);
  };

  const handleTabRemove = (key: string) => {
    removeTab(key);
  };

  const contextValue = useMemo(
    () => ({
      tabs,
      activeKey,
      addTab,
      removeTab,
      changeTab,
      menuSearchValue,
      setMenuSearchValue,
    }),
    [tabs, activeKey, addTab, removeTab, changeTab, menuSearchValue]
  );

  return (
    <GlobalTabsContext.Provider value={contextValue}>
      <GlobalTabs
        tabs={tabs}
        activeKey={activeKey}
        onChange={handleTabChange}
        onRemove={handleTabRemove}
      >
        {children}
      </GlobalTabs>
    </GlobalTabsContext.Provider>
  );
};

