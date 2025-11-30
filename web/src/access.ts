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

/**
 * @see https://umijs.org/docs/max/access#access
 * */
import { ADMIN_ROLE_ID, RESEARCHER_ROLE_ID, USER_ROLE_ID } from '@/constants/roles';

export default function access(
  initialState: { currentUser?: API.CurrentUser } | undefined,
) {
  const { currentUser } = initialState ?? {};
  const roleId = (currentUser as any)?.role_id;
  
  // 判断是否为管理员：根据 access 字段或 role_id 字段
  const isAdmin = currentUser && (
    currentUser.access === 'admin' || 
    roleId === ADMIN_ROLE_ID
  );
  
  // 判断是否为策略研究员
  const isResearcher = currentUser && roleId === RESEARCHER_ROLE_ID;
  
  // 判断是否为量化平台用户
  const isUser = currentUser && roleId === USER_ROLE_ID;
  
  // 数据访问权限：所有角色都可以访问
  const canAccessData = !!currentUser;
  
  // 回测访问权限：管理员和策略研究员可以访问，量化平台用户只能查看
  const canAccessBacktest = isAdmin || isResearcher || isUser;
  
  // 因子管理权限：管理员和策略研究员可以访问
  const canAccessFactor = isAdmin || isResearcher;
  
  // 我的关注权限：所有角色都可以访问
  const canAccessWatchlist = !!currentUser;
  
  // API密钥权限：管理员和策略研究员可以访问
  const canAccessApiKeys = isAdmin || isResearcher;
  
  return {
    canAdmin: !!isAdmin,
    canResearcher: !!isResearcher,
    canUser: !!isUser,
    canAccessData,
    canAccessBacktest,
    canAccessFactor,
    canAccessWatchlist,
    canAccessApiKeys,
  };
}
