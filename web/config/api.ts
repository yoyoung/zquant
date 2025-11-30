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
 * API配置
 * 支持通过环境变量配置API地址
 * 
 * 注意：当前配置不使用代理，所有请求直接访问配置的baseURL
 * 
 * 环境变量配置方式：
 * 1. 设置完整的API基础URL（优先级最高）：
 *    REACT_APP_API_BASE_URL=http://192.168.1.100:8000
 * 
 * 2. 或者分别设置主机和端口：
 *    REACT_APP_API_HOST=192.168.1.100
 *    REACT_APP_API_PORT=8000
 * 
 * 默认值：localhost:8000
 */
const getApiBaseUrl = (): string => {
  // 优先使用环境变量中的完整URL
  if (process.env.REACT_APP_API_BASE_URL) {
    console.log('[API_CONFIG] 使用环境变量 REACT_APP_API_BASE_URL:', process.env.REACT_APP_API_BASE_URL);
    return process.env.REACT_APP_API_BASE_URL;
  }
  
  // 所有环境都直接使用baseURL，不使用代理
  // 使用配置的主机和端口，默认 localhost:8000
  const host = process.env.REACT_APP_API_HOST || 'localhost';
  const port = process.env.REACT_APP_API_PORT || '8000';
  const url = `http://${host}:${port}`;
  console.log(`[API_CONFIG] ${process.env.NODE_ENV === 'development' ? '开发' : '生产'}环境，直接访问URL:`, url);
  return url;
};

const getApiHost = (): string => {
  return process.env.REACT_APP_API_HOST || 'localhost';
};

const getApiPort = (): string => {
  return process.env.REACT_APP_API_PORT || '8000';
};

export const API_CONFIG = {
  baseURL: getApiBaseUrl(),
  host: getApiHost(),
  port: getApiPort(),
  // 完整的API地址（用于非代理场景）
  get fullURL(): string {
    const url = `http://${this.host}:${this.port}`;
    console.log('[API_CONFIG] fullURL:', url);
    return url;
  },
};

// 打印配置信息（仅在开发环境）
if (process.env.NODE_ENV === 'development') {
  console.log('[API_CONFIG] 配置信息:', {
    baseURL: API_CONFIG.baseURL,
    host: API_CONFIG.host,
    port: API_CONFIG.port,
    fullURL: API_CONFIG.fullURL,
    NODE_ENV: process.env.NODE_ENV,
    REACT_APP_API_BASE_URL: process.env.REACT_APP_API_BASE_URL,
    REACT_APP_API_HOST: process.env.REACT_APP_API_HOST,
    REACT_APP_API_PORT: process.env.REACT_APP_API_PORT,
  });
}
