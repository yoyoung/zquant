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

﻿/**
 * @name umi 的路由配置
 * @description 只支持 path,component,routes,redirect,wrappers,name,icon 的配置
 * @param path  path 只支持两种占位符配置，第一种是动态参数 :id 的形式，第二种是 * 通配符，通配符只能出现路由字符串的最后。
 * @param component 配置 location 和 path 匹配后用于渲染的 React 组件路径。可以是绝对路径，也可以是相对路径，如果是相对路径，会从 src/pages 开始找起。
 * @param routes 配置子路由，通常在需要为多个路径增加 layout 组件时使用。
 * @param redirect 配置路由跳转
 * @param wrappers 配置路由组件的包装组件，通过包装组件可以为当前的路由组件组合进更多的功能。 比如，可以用于路由级别的权限校验
 * @param name 配置路由的标题，默认读取国际化文件 menu.ts 中 menu.xxxx 的值，如配置 name 为 login，则读取 menu.ts 中 menu.login 的取值作为标题
 * @param icon 配置路由的图标，取值参考 https://ant.design/components/icon-cn， 注意去除风格后缀和大小写，如想要配置图标为 <StepBackwardOutlined /> 则取值应为 stepBackward 或 StepBackward，如想要配置图标为 <UserOutlined /> 则取值应为 user 或者 User
 * @doc https://umijs.org/docs/guides/routes
 */
export default [
  {
    path: '/user',
    layout: false,
    routes: [
      {
        name: 'login',
        path: '/user/login',
        component: './user/login',
      },
    ],
  },
  {
    path: '/legal',
    routes: [
      {
        name: 'user-agreement',
        path: '/legal/user-agreement',
        component: './legal/user-agreement',
        hideInMenu: true,
      },
      {
        name: 'disclaimer',
        path: '/legal/disclaimer',
        component: './legal/disclaimer',
        hideInMenu: true,
      },
    ],
  },
  {
    path: '/user',
    routes: [
      {
        name: 'apikeys',
        path: '/user/apikeys',
        icon: 'key',
        component: './user/apikeys',
        access: 'canAccessApiKeys',
      },
    ],
  },
  {
    path: '/account',
    routes: [
      {
        name: 'center',
        path: '/account/center',
        component: './account/center',
      },
      {
        name: 'settings',
        path: '/account/settings',
        component: './account/settings',
      },
    ],
  },
  {
    path: '/welcome',
    name: 'welcome',
    icon: 'smile',
    component: './Welcome',
  },
  // 系统大盘
  {
    path: '/dashboard',
    name: 'dashboard',
    icon: 'dashboard',
    component: './dashboard',
  },
  // 我的关注
  {
    path: '/watchlist',
    name: 'watchlist',
    icon: 'star',
    access: 'canAccessWatchlist',
    routes: [
      {
        path: '/watchlist',
        redirect: '/watchlist/my-watchlist',
      },
      {
        path: '/watchlist/my-watchlist',
        name: 'my-watchlist',
        component: './watchlist/my-watchlist',
      },
      {
        path: '/watchlist/my-positions',
        name: 'my-positions',
        component: './watchlist/my-positions',
      },
      {
        path: '/watchlist/quick-access',
        name: 'quick-access',
        component: './watchlist/quick-access',
      },
    ],
  },
  // 因子管理
  {
    path: '/factor',
    name: 'factor',
    icon: 'function',
    access: 'canAccessFactor',
    routes: [
      {
        path: '/factor',
        redirect: '/factor/index',
      },
      {
        path: '/factor/index',
        name: 'factor-index',
        component: './factor',
      },
    ],
  },
  // 回测
  {
    path: '/backtest',
    name: 'backtest',
    icon: 'experiment',
    access: 'canAccessBacktest',
    routes: [
      {
        path: '/backtest',
        redirect: '/backtest/list',
      },
      {
        path: '/backtest/list',
        name: 'backtest-list',
        component: './backtest',
      },
      {
        path: '/backtest/strategies',
        name: 'strategies',
        component: './backtest/strategies',
      },
      {
        path: '/backtest/strategies/create',
        name: 'strategy-create',
        component: './backtest/strategies/create',
        hideInMenu: true,
      },
      {
        path: '/backtest/strategies/:id/edit',
        name: 'strategy-edit',
        component: './backtest/strategies/[id]/edit',
        hideInMenu: true,
      },
      {
        path: '/backtest/create',
        name: 'backtest-create',
        component: './backtest/create',
      },
      {
        path: '/backtest/detail/:id',
        name: 'backtest-detail',
        component: './backtest/detail/[id]',
        hideInMenu: true,
      },
      {
        path: '/backtest/performance/:id',
        name: 'backtest-performance',
        component: './backtest/performance/[id]',
        hideInMenu: true,
      },
    ],
  },
  // 数据源
  {
    path: '/data',
    name: 'data',
    icon: 'database',
    access: 'canAccessData',
    routes: [
      {
        path: '/data',
        redirect: '/data/tushare',
      },
      {
        path: '/data/tushare',
        name: 'tushare',
        component: './data',
      },
      {
        path: '/data/divider-1',
        hideInMenu: false,
        divider: true,
        component: './divider',
      },
      {
        path: '/data/scheduler',
        name: 'scheduler',
        icon: 'clockCircle',
        component: './admin/scheduler',
      },
      {
        path: '/data/daily-summary',
        name: 'daily-summary',
        component: './data/daily-summary',
      },
      {
        path: '/data/sync-logs',
        name: 'sync-logs',
        component: './data/table-statistics',
      },
      {
        path: '/data/operation-logs',
        name: 'operation-logs',
        component: './data/operation-logs',
      },
      {
        path: '/data/notifications',
        name: 'notifications',
        icon: 'bell',
        component: './notifications',
      },
    ],
  },
  // 系统设置
  {
    path: '/admin',
    name: 'admin',
    icon: 'setting',
    access: 'canAdmin',
    routes: [
      {
        path: '/admin',
        redirect: '/admin/users',
      },
      {
        path: '/admin/users',
        name: 'users',
        icon: 'user',
        component: './admin/users',
      },
      {
        path: '/admin/roles',
        name: 'roles',
        icon: 'team',
        component: './admin/roles',
      },
      {
        path: '/admin/permissions',
        name: 'permissions',
        icon: 'safety',
        component: './admin/permissions',
      },
      {
        path: '/admin/divider-1',
        hideInMenu: false,
        divider: true,
        component: './divider',
      },
      {
        path: '/admin/datasource-config',
        name: 'datasource-config',
        icon: 'database',
        component: './admin/datasource-config',
      },
      {
        path: '/admin/divider-2',
        hideInMenu: false,
        divider: true,
        component: './divider',
      },
      {
        path: '/admin/config',
        name: 'config',
        icon: 'setting',
        component: './admin/config',
      },
      {
        path: '/admin/openapi',
        name: 'openapi',
        icon: 'api',
        component: './admin/openapi',
      },
      {
        path: '/admin/sub-page',
        name: 'sub-page',
        component: './Admin',
        hideInMenu: true,
      },
    ],
  },
  {
    name: 'list.table-list',
    icon: 'table',
    path: '/list',
    component: './table-list',
    hideInMenu: true,
  },
  {
    path: '/',
    redirect: '/welcome',
  },
  {
    path: '*',
    layout: false,
    component: './404',
  },
];
