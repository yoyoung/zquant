// Copyright 2025 ZQuant Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the Apache License is distributed on an "AS IS" BASIS,
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

import routes from '../../config/routes';

/**
 * 路由配置类型
 */
interface RouteConfig {
  path?: string;
  name?: string;
  routes?: RouteConfig[];
  redirect?: string;
  hideInMenu?: boolean;
  divider?: boolean;
  component?: string;
  layout?: boolean;
  access?: string;
  icon?: string;
}

/**
 * 根据路径匹配路由配置中的路由项
 * @param pathname 当前路径
 * @param routes 路由配置数组
 * @param parentPath 父路径（用于构建完整路径）
 * @returns 匹配到的路由配置，如果未找到则返回 null
 */
export const findRouteByPath = (
  pathname: string,
  routes: RouteConfig[],
  parentPath = ''
): RouteConfig | null => {
  for (const route of routes) {
    // 跳过分隔线和隐藏的路由
    if (route.divider || route.hideInMenu) {
      continue;
    }

    // 构建完整路径
    const fullPath = route.path?.startsWith('/')
      ? route.path
      : `${parentPath}${route.path || ''}`;

    // 精确匹配
    if (fullPath === pathname && route.name && !route.redirect) {
      return route;
    }

    // 处理动态路由（如 /backtest/detail/:id）
    if (route.path && route.path.includes(':')) {
      const routePattern = route.path.replace(/:[^/]+/g, '[^/]+');
      const regex = new RegExp(`^${routePattern}$`);
      if (regex.test(pathname)) {
        return route;
      }
    }

    // 递归查找子路由
    if (route.routes) {
      const found = findRouteByPath(pathname, route.routes, fullPath);
      if (found) {
        return found;
      }
    }
  }

  return null;
};

/**
 * 根据路由的 name 构建国际化 key
 * @param route 路由配置
 * @param parentName 父路由的 name（用于构建嵌套的国际化 key）
 * @returns 国际化 key，如 'menu.welcome' 或 'menu.backtest.backtest-list'
 */
export const buildMenuI18nKey = (route: RouteConfig, parentName?: string): string => {
  if (!route.name) {
    return '';
  }

  // 如果路由名称包含点号（如 'list.table-list'），说明已经是完整的国际化 key 的一部分
  if (route.name.includes('.')) {
    return `menu.${route.name}`;
  }

  // 如果有父路由名称，构建嵌套的 key（如 menu.backtest.backtest-list）
  if (parentName) {
    return `menu.${parentName}.${route.name}`;
  }

  // 否则直接使用路由名称（如 menu.welcome）
  return `menu.${route.name}`;
};

/**
 * 递归查找路由并构建完整的国际化 key
 * @param pathname 当前路径
 * @param routes 路由配置数组
 * @param parentPath 父路径
 * @param parentName 父路由的 name
 * @param includeHidden 是否包含隐藏的路由（hideInMenu），用于标签页标题等场景
 * @returns 国际化 key，如果未找到则返回空字符串
 */
export const getMenuI18nKeyByPath = (
  pathname: string,
  routes: RouteConfig[],
  parentPath = '',
  parentName?: string,
  includeHidden = false
): string => {
  for (const route of routes) {
    // 跳过分隔线，根据 includeHidden 参数决定是否跳过隐藏的路由
    if (route.divider || (!includeHidden && route.hideInMenu)) {
      continue;
    }

    // 构建完整路径
    const fullPath = route.path?.startsWith('/')
      ? route.path
      : `${parentPath}${route.path || ''}`;

    // 精确匹配（排除 redirect 路由）
    if (fullPath === pathname && route.name && !route.redirect) {
      return buildMenuI18nKey(route, parentName);
    }

    // 处理动态路由（如 /backtest/detail/:id）
    if (route.path && route.path.includes(':')) {
      const routePattern = route.path.replace(/:[^/]+/g, '[^/]+');
      const regex = new RegExp(`^${routePattern}$`);
      if (regex.test(pathname)) {
        return buildMenuI18nKey(route, parentName);
      }
    }

    // 递归查找子路由（传递当前路由的 name 作为父名称）
    if (route.routes) {
      const childKey = getMenuI18nKeyByPath(
        pathname,
        route.routes,
        fullPath,
        route.name || parentName,
        includeHidden
      );
      if (childKey) {
        return childKey;
      }
    }
  }

  return '';
};

/**
 * 根据路径获取菜单的国际化 key（使用默认路由配置）
 * @param pathname 当前路径
 * @returns 国际化 key，如果未找到则返回空字符串
 */
export const getMenuI18nKey = (pathname: string): string => {
  return getMenuI18nKeyByPath(pathname, routes as RouteConfig[]);
};

