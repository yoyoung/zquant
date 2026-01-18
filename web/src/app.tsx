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

import type { Settings as LayoutSettings } from '@ant-design/pro-components';
import { SettingDrawer } from '@ant-design/pro-components';
import type { RequestConfig, RunTimeLayoutConfig } from '@umijs/max';
import { history, Link } from '@umijs/max';
import { App as AntdApp } from 'antd';
import React, { useMemo, useState, useCallback } from 'react';
import {
  AvatarDropdown,
  AvatarName,
  Footer,
  Question,
  SelectLang,
  MenuSearch,
  GlobalTabsProvider,
  useGlobalTabsContext,
  RightContent,
} from '@/components';
import TopNavLinks from '@/components/TopNavLinks';
import { getCurrentUser } from '@/services/zquant/users';
import defaultSettings from '../config/defaultSettings';
import { errorConfig } from './requestErrorConfig';
import { ADMIN_ROLE_ID } from '@/constants/roles';
import { SettingDrawerContext } from '@/contexts/SettingDrawerContext';
import '@ant-design/v5-patch-for-react-19';

const isDev = process.env.NODE_ENV === 'development';
const loginPath = '/user/login';

/**
 * @see https://umijs.org/docs/api/runtime-config#getinitialstate
 * */
export async function getInitialState(): Promise<{
  settings?: Partial<LayoutSettings>;
  currentUser?: API.CurrentUser;
  loading?: boolean;
  fetchUserInfo?: () => Promise<API.CurrentUser | undefined>;
}> {
  const fetchUserInfo = async () => {
    try {
      const token = localStorage.getItem('access_token');
      
      if (!token) {
        return undefined;
      }
      
      const userInfo = await getCurrentUser();
      
      // 根据role_id判断是否为管理员
      const isAdmin = userInfo.role_id === ADMIN_ROLE_ID;
      
      // 转换用户信息格式以适配ProLayout
      return {
        name: userInfo.username,
        avatar: undefined,
        userid: userInfo.id.toString(),
        email: userInfo.email,
        access: isAdmin ? 'admin' : 'user', // 根据role_id设置权限
        role_id: userInfo.role_id, // 保存role_id以便后续使用
      };
    } catch (_error: any) {
      // 获取用户信息失败时，不立即清除token和跳转
      // 可能是网络问题或token刚保存还没生效
      // 让onPageChange来处理跳转逻辑
      const { location } = history;
      
      // 只有在非登录页面且错误是401时才清除token
      if (location.pathname !== loginPath && _error?.response?.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      }
    }
    return undefined;
  };
  // 如果不是登录页面，执行
  const { location } = history;
  
  // 检查是否有token，如果有token，尝试获取用户信息
  const hasToken = localStorage.getItem('access_token');
  
  // 无需登录即可访问的页面路径
  const publicPaths = [
    loginPath,
    '/user/register',
    '/user/register-result',
    '/legal/user-agreement',
    '/legal/disclaimer',
  ];
  
  if (!publicPaths.includes(location.pathname)) {
    // 如果有token，尝试获取用户信息
    if (hasToken) {
      const currentUser = await fetchUserInfo();
      return {
        fetchUserInfo,
        currentUser: currentUser || undefined, // 即使获取失败也返回undefined，不跳转
        settings: defaultSettings as Partial<LayoutSettings>,
      };
    } else {
      // 没有token，直接跳转登录
      history.push(loginPath);
      return {
        fetchUserInfo,
        settings: defaultSettings as Partial<LayoutSettings>,
      };
    }
  }
  return {
    fetchUserInfo,
    settings: defaultSettings as Partial<LayoutSettings>,
  };
}

/**
 * 扁平化菜单路由用于搜索
 */
const flattenMenuRoutes = (routes: any[], parentPath = ''): any[] => {
  const result: any[] = [];
  for (const route of routes) {
    // 跳过分隔线
    if (route.type === 'divider' || route.divider === true) continue;
    if (route.hideInMenu) continue;
    const fullPath = route.path?.startsWith('/') ? route.path : `${parentPath}${route.path || ''}`;
    if (route.name && route.path && !route.redirect) {
      result.push({
        ...route,
        fullPath,
      });
    }
    if (route.routes) {
      result.push(...flattenMenuRoutes(route.routes, fullPath));
    }
  }
  return result;
};

/**
 * 处理菜单数据，转换分隔线
 */
const processMenuData = (menuData: any[]): any[] => {
  return menuData.map((route) => {
    // 如果是分隔线标记，转换为分隔线格式，并隐藏路径
    if (route.divider === true) {
      return { 
        type: 'divider',
        hideInMenu: false, // 分隔线需要在菜单中显示
      };
    }
    
    // 递归处理子路由
    if (route.routes) {
      return {
        ...route,
        routes: processMenuData(route.routes),
      };
    }
    
    return route;
  });
};

/**
 * 过滤菜单项
 */
const filterMenuData = (menuData: any[], searchValue: string): any[] => {
  // 先处理分隔线
  const processedData = processMenuData(menuData);
  
  if (!searchValue) return processedData;
  
  const flatRoutes = flattenMenuRoutes(processedData);
  const matchedRoutes = flatRoutes.filter((route) => {
    // 跳过分隔线
    if (route.type === 'divider') return false;
    const name = route.name || '';
    const path = route.fullPath || route.path || '';
    return (
      name.toLowerCase().includes(searchValue.toLowerCase()) ||
      path.toLowerCase().includes(searchValue.toLowerCase())
    );
  });

  // 构建匹配路径集合
  const matchedPaths = new Set<string>();
  matchedRoutes.forEach((route) => {
    const path = route.fullPath || route.path || '';
    matchedPaths.add(path);
    // 添加父路径
    const parts = path.split('/');
    for (let i = 1; i < parts.length; i++) {
      matchedPaths.add(parts.slice(0, i + 1).join('/'));
    }
  });

  // 递归过滤菜单
  const filterRoutes = (routes: any[]): any[] => {
    return routes
      .map((route) => {
        // 保留分隔线
        if (route.type === 'divider') {
          return route;
        }
        
        const path = route.fullPath || route.path || '';
        const isMatched = matchedPaths.has(path);
        
        let filteredRoute = { ...route };
        if (route.routes) {
          filteredRoute.routes = filterRoutes(route.routes);
          // 如果子路由有匹配的，保留父路由
          if (filteredRoute.routes.length > 0) {
            return filteredRoute;
          }
        }
        
        return isMatched ? filteredRoute : null;
      })
      .filter(Boolean) as any[];
  };

  return filterRoutes(processedData);
};

// 菜单搜索状态（使用模块级变量，因为 layout 函数每次都会重新执行）
let globalMenuSearchValue = '';

// ProLayout 支持的api https://procomponents.ant.design/components/layout
export const layout: RunTimeLayoutConfig = ({
  initialState,
  setInitialState,
}) => {
  // 使用 React.useState 来触发重新渲染，但实际值存储在模块级变量中
  const [, forceUpdate] = React.useReducer((x) => x + 1, 0);
  
  const setMenuSearchValue = React.useCallback((value: string) => {
    globalMenuSearchValue = value;
    forceUpdate();
  }, []);
  
  // SettingDrawer 控制函数
  const toggleSettingDrawer = useCallback(() => {
    // 通过 DOM 查询 SettingDrawer 的触发按钮并点击
    setTimeout(() => {
      const triggerButton = document.querySelector('.ant-pro-setting-drawer-handle') as HTMLElement;
      if (triggerButton) {
        // 临时显示按钮并点击
        const originalDisplay = triggerButton.style.display;
        triggerButton.style.display = 'block';
        triggerButton.style.visibility = 'visible';
        triggerButton.click();
        // 点击后立即隐藏
        setTimeout(() => {
          triggerButton.style.display = originalDisplay || 'none';
        }, 100);
      }
    }, 50);
  }, []);
  
  const settingDrawerContextValue = useMemo(() => ({
    toggle: toggleSettingDrawer,
  }), [toggleSettingDrawer]);

  return {
    headerTitleRender: (logo, title) => (
      <SettingDrawerContext.Provider value={settingDrawerContextValue}>
        <div style={{ display: 'flex', alignItems: 'center', height: '100%' }}>
          {logo}
          {title && (
            <div style={{ display: 'flex', alignItems: 'center', marginLeft: '16px' }}>
              <span style={{ fontSize: '18px', fontWeight: 500, color: '#fff' }}>{title}</span>
              <TopNavLinks />
            </div>
          )}
        </div>
      </SettingDrawerContext.Provider>
    ),
    actionsRender: () => (
      <SettingDrawerContext.Provider value={settingDrawerContextValue}>
        <RightContent />
      </SettingDrawerContext.Provider>
    ),
    // 隐藏顶部用户信息
    avatarProps: false,
    waterMarkProps: false,
    footerRender: () => <Footer />,
    // 在左侧菜单栏上方显示搜索
    menuHeaderRender: (logo, title, collapsed) => {
      const isCollapsed = typeof collapsed === 'boolean' ? collapsed : (collapsed as any)?.collapsed ?? false;
      return (
        <div>
          <MenuSearch
            placeholder="搜索菜单"
            onSearch={setMenuSearchValue}
            collapsed={isCollapsed}
          />
        </div>
      );
    },
    // 菜单数据过滤
    menuDataRender: (menuData) => {
      return filterMenuData(menuData || [], globalMenuSearchValue);
    },
    onPageChange: () => {
      const { location } = history;
      
      // 无需登录即可访问的页面路径
      const publicPaths = [
        loginPath,
        '/user/register',
        '/user/register-result',
        '/legal/user-agreement',
        '/legal/disclaimer',
      ];
      
      // 如果是公开页面，不检查用户状态
      if (publicPaths.includes(location.pathname)) {
        return;
      }
      
      // 检查是否有token
      const hasToken = localStorage.getItem('access_token');
      
      // 如果有token，即使没有currentUser也允许访问（可能是正在加载）
      // 只有在既没有token也没有currentUser时才跳转登录
      if (!initialState?.currentUser && !hasToken) {
        history.push(loginPath);
      }
    },
    bgLayoutImgList: [
      {
        src: 'https://mdn.alipayobjects.com/yuyan_qk0oxh/afts/img/D2LWSqNny4sAAAAAAAAAAAAAFl94AQBr',
        left: 85,
        bottom: 100,
        height: '303px',
      },
      {
        src: 'https://mdn.alipayobjects.com/yuyan_qk0oxh/afts/img/C2TWRpJpiC0AAAAAAAAAAAAAFl94AQBr',
        bottom: -68,
        right: -45,
        height: '303px',
      },
      {
        src: 'https://mdn.alipayobjects.com/yuyan_qk0oxh/afts/img/F6vSTbj8KpYAAAAAAAAAAAAAFl94AQBr',
        bottom: 0,
        left: 0,
        width: '331px',
      },
    ],
    links: [],
    // 自定义 403 页面
    // unAccessible: <div>unAccessible</div>,
    // 增加一个 loading 的状态
    childrenRender: (children) => {
      // if (initialState?.loading) return <PageLoading />;
      const { location } = history;
      
      // 公开页面列表（不需要布局的页面）
      const publicPaths = [
        loginPath,
        '/user/register',
        '/user/register-result',
        '/legal/user-agreement',
        '/legal/disclaimer',
      ];
      
      // 如果是公开页面，不包裹 GlobalTabsProvider 和 SettingDrawer
      if (publicPaths.includes(location.pathname)) {
        return (
          <AntdApp>
            {children}
          </AntdApp>
        );
      }
      
      // 其他页面保持原有逻辑
      return (
        <AntdApp>
          <GlobalTabsProvider>
            {children}
          </GlobalTabsProvider>
          <SettingDrawer
            disableUrlParams
            enableDarkTheme
            settings={initialState?.settings}
            onSettingChange={(settings) => {
              setInitialState((preInitialState) => ({
                ...preInitialState,
                settings,
              }));
            }}
          />
          <style>{`
            .ant-pro-setting-drawer-handle {
              display: none !important;
              visibility: hidden !important;
            }
          `}</style>
        </AntdApp>
      );
    },
    ...initialState?.settings,
  };
};

/**
 * @name request 配置，可以配置错误处理
 * 它基于 axios 和 ahooks 的 useRequest 提供了一套统一的网络请求和错误处理方案。
 * @doc https://umijs.org/docs/max/request#配置
 */
import { API_CONFIG } from '../config/api';

export const request: RequestConfig = {
  // 使用配置的API地址
  baseURL: API_CONFIG.baseURL,
  ...errorConfig,
};

// 注意：生产环境不应输出敏感配置信息
// 如需调试，请使用开发环境的调试工具
