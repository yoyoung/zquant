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
 * @name 代理的配置
 * @see 在生产环境 代理是无法生效的，所以这里没有生产环境的配置
 * -------------------------------
 * The agent cannot take effect in the production environment
 * so there is no configuration of the production environment
 * For details, please see
 * https://pro.ant.design/docs/deploy
 *
 * @doc https://umijs.org/docs/guides/proxy
 * 
 * 注意：当前配置不使用代理，所有API请求直接访问baseURL（见 web/config/api.ts）
 * 此代理配置保留但不使用，如需启用代理，请修改 web/config/api.ts 中的 getApiBaseUrl() 函数
 */

// 获取代理目标地址（直接计算，不使用getter）
const getProxyTarget = (): string => {
  // 优先使用环境变量
  if (process.env.REACT_APP_API_BASE_URL) {
    return process.env.REACT_APP_API_BASE_URL;
  }
  
  // 使用配置的主机和端口
  const host = process.env.REACT_APP_API_HOST || 'localhost';
  const port = process.env.REACT_APP_API_PORT || '8000';
  return `http://${host}:${port}`;
};

const proxyTarget = getProxyTarget();

// 打印代理配置（仅在开发环境）
if (process.env.NODE_ENV === 'development') {
  console.log('[Proxy Config] ========== 代理配置 ==========');
  console.log('[Proxy Config] 代理目标地址:', proxyTarget);
  console.log('[Proxy Config] 环境变量检查:');
  console.log('[Proxy Config]   REACT_APP_API_BASE_URL:', process.env.REACT_APP_API_BASE_URL || '未设置');
  console.log('[Proxy Config]   REACT_APP_API_HOST:', process.env.REACT_APP_API_HOST || '未设置 (默认: localhost)');
  console.log('[Proxy Config]   REACT_APP_API_PORT:', process.env.REACT_APP_API_PORT || '未设置 (默认: 8000)');
  console.log('[Proxy Config] ==============================');
}

export default {
  /**
   * @name 开发环境代理配置
   * @description 将 /api/v1 请求代理到 zquant 后端服务（默认 http://localhost:8000）
   */
  dev: {
    '/api/v1': {
      target: proxyTarget,  // 使用计算出的代理目标地址，确保统一配置
      changeOrigin: true,
      // 不需要pathRewrite，因为路径完全匹配
      // @ts-ignore
      onProxyReq: (proxyReq: any, req: any, res: any) => {
        console.log('[Proxy] 代理请求:', req.method, req.url, '->', proxyTarget + req.url);
      },
    },
  },
  /**
   * @name 详细的代理配置
   * @doc https://github.com/chimurai/http-proxy-middleware
   */
  test: {
    // localhost:8000/api/** -> https://preview.pro.ant.design/api/**
    '/api/': {
      target: 'https://proapi.azurewebsites.net',
      changeOrigin: true,
      pathRewrite: { '^': '' },
    },
  },
  pre: {
    '/api/': {
      target: 'your pre url',
      changeOrigin: true,
      pathRewrite: { '^': '' },
    },
  },
};
