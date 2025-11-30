// Copyright 2025 ZQuant Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
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

import { useCallback } from 'react';
import { message } from 'antd';

/**
 * 统一错误处理Hook
 * 
 * 提供统一的错误处理和消息提示
 */
export function useErrorHandler() {
  const handleError = useCallback((error: any, defaultMessage?: string) => {
    let errorMessage = defaultMessage || '操作失败';
    
    if (error?.response) {
      // HTTP错误响应
      const { status, data } = error.response;
      
      if (data?.detail) {
        errorMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      } else if (data?.message) {
        errorMessage = data.message;
      } else {
        // 根据状态码设置默认消息
        switch (status) {
          case 400:
            errorMessage = '请求参数错误';
            break;
          case 401:
            errorMessage = '未授权，请重新登录';
            break;
          case 403:
            errorMessage = '没有权限执行此操作';
            break;
          case 404:
            errorMessage = '资源不存在';
            break;
          case 500:
            errorMessage = '服务器内部错误';
            break;
          case 503:
            errorMessage = '服务暂时不可用';
            break;
          default:
            errorMessage = `请求失败 (${status})`;
        }
      }
    } else if (error?.message) {
      errorMessage = error.message;
    } else if (typeof error === 'string') {
      errorMessage = error;
    }
    
    message.error(errorMessage);
    return errorMessage;
  }, []);

  const handleSuccess = useCallback((msg?: string) => {
    message.success(msg || '操作成功');
  }, []);

  const handleWarning = useCallback((msg: string) => {
    message.warning(msg);
  }, []);

  const handleInfo = useCallback((msg: string) => {
    message.info(msg);
  }, []);

  return {
    handleError,
    handleSuccess,
    handleWarning,
    handleInfo,
  };
}

