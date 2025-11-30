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

import type { RequestOptions } from '@@/plugin-request/request';
import type { RequestConfig } from '@umijs/max';
import { message, notification } from 'antd';

// 错误处理方案： 错误类型
enum ErrorShowType {
  SILENT = 0,
  WARN_MESSAGE = 1,
  ERROR_MESSAGE = 2,
  NOTIFICATION = 3,
  REDIRECT = 9,
}
// 与后端约定的响应数据格式
interface ResponseStructure {
  success: boolean;
  data: any;
  errorCode?: number;
  errorMessage?: string;
  showType?: ErrorShowType;
}

/**
 * @name 错误处理
 * pro 自带的错误处理， 可以在这里做自己的改动
 * @doc https://umijs.org/docs/max/request#配置
 */
export const errorConfig: RequestConfig = {
  // 错误处理： umi@3 的错误处理方案。
  errorConfig: {
    // 错误抛出
    errorThrower: (res) => {
      const { success, data, errorCode, errorMessage, showType } =
        res as unknown as ResponseStructure;
      if (!success) {
        const error: any = new Error(errorMessage);
        error.name = 'BizError';
        error.info = { errorCode, errorMessage, showType, data };
        throw error; // 抛出自制的错误
      }
    },
    // 错误接收及处理
    errorHandler: (error: any, opts: any) => {
      if (opts?.skipErrorHandler) throw error;
      // 我们的 errorThrower 抛出的错误。
      if (error.name === 'BizError') {
        const errorInfo: ResponseStructure | undefined = error.info;
        if (errorInfo) {
          const { errorMessage, errorCode } = errorInfo;
          switch (errorInfo.showType) {
            case ErrorShowType.SILENT:
              // do nothing
              break;
            case ErrorShowType.WARN_MESSAGE:
              message.warning(errorMessage);
              break;
            case ErrorShowType.ERROR_MESSAGE:
              message.error(errorMessage);
              break;
            case ErrorShowType.NOTIFICATION:
              notification.open({
                description: errorMessage,
                message: errorCode,
              });
              break;
            case ErrorShowType.REDIRECT:
              // TODO: redirect
              break;
            default:
              message.error(errorMessage);
          }
        }
      } else if (error.response) {
        // Axios 的错误
        // FastAPI错误格式可能是：
        // 1. { detail: "错误信息" } - 简单错误
        // 2. { detail: [{ type, loc, msg, input }] } - 验证错误数组
        const status = error.response.status;
        let errorMessage = `请求失败 (${status})`;
        
        const errorData = error.response.data;
        if (errorData?.detail) {
          if (typeof errorData.detail === 'string') {
            errorMessage = errorData.detail;
          } else if (Array.isArray(errorData.detail)) {
            // Pydantic验证错误数组
            errorMessage = errorData.detail
              .map((err: any) => {
                const field = err.loc?.join('.') || '未知字段';
                return `${field}: ${err.msg || '验证失败'}`;
              })
              .join('; ');
          } else if (typeof errorData.detail === 'object') {
            // 单个验证错误对象
            const field = errorData.detail.loc?.join('.') || '未知字段';
            errorMessage = `${field}: ${errorData.detail.msg || '验证失败'}`;
          }
        }
        
        // 处理401未授权错误，清除token并跳转登录
        if (status === 401) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          // 延迟跳转，避免在非登录页面时立即跳转
          if (window.location.pathname !== '/user/login') {
            window.location.href = '/user/login';
          }
          // 延迟显示消息，确保AntdApp已经渲染
          setTimeout(() => {
            message.error('登录已过期，请重新登录');
          }, 100);
        } else {
          // 确保errorMessage是字符串
          // 延迟显示消息，避免在getInitialState阶段显示（此时AntdApp还未渲染）
          // 对于500等错误，在初始化阶段可以静默处理，避免警告
          const isInitializing = !document.querySelector('.ant-app');
          if (isInitializing) {
            // 在初始化阶段，延迟显示消息，等待AntdApp渲染完成
            setTimeout(() => {
              try {
                message.error(String(errorMessage));
              } catch (e) {
                // 如果仍然失败，使用console.error记录
                console.error('错误消息显示失败:', errorMessage);
              }
            }, 200);
          } else {
            message.error(String(errorMessage));
          }
        }
      } else if (error.request) {
        // 请求已经成功发起，但没有收到响应
        // \`error.request\` 在浏览器中是 XMLHttpRequest 的实例，
        // 而在node.js中是 http.ClientRequest 的实例
        const isInitializing = !document.querySelector('.ant-app');
        if (isInitializing) {
          setTimeout(() => {
            message.error('网络错误，请检查网络连接');
          }, 100);
        } else {
          message.error('网络错误，请检查网络连接');
        }
      } else {
        // 发送请求时出了点问题
        const isInitializing = !document.querySelector('.ant-app');
        if (isInitializing) {
          setTimeout(() => {
            message.error('请求错误，请重试');
          }, 100);
        } else {
          message.error('请求错误，请重试');
        }
      }
    },
  },

  // 请求拦截器
  requestInterceptors: [
    (config: RequestOptions) => {
      // 添加JWT token到请求头
      const token = localStorage.getItem('access_token');
      if (token && config.headers) {
        config.headers['Authorization'] = `Bearer ${token}`;
      }
      return { ...config };
    },
  ],

  // 响应拦截器
  responseInterceptors: [
    (response) => {
      // FastAPI直接返回数据，不需要处理success字段
      return response;
    },
  ],
};
