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

import { PageContainer } from '@ant-design/pro-components';
import { ProForm, ProFormText, ProFormTextArea } from '@ant-design/pro-components';
import { Card, Button, message, Space, Alert } from 'antd';
import { EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons';
import React, { useEffect, useState } from 'react';
import { getConfig, setConfig, testTushareToken } from '@/services/zquant/config';

const DatasourceConfig: React.FC = () => {
  const [form] = ProForm.useForm();
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [showToken, setShowToken] = useState(false);
  const [realToken, setRealToken] = useState<string>('');
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    data_count?: number;
  } | null>(null);

  // 掩码显示敏感值（前后各4个字符）
  const maskSensitiveValue = (value: string): string => {
    if (!value) return '***';
    if (value.length <= 8) {
      return '****';
    }
    const prefix = value.substring(0, 4);
    const suffix = value.substring(value.length - 4);
    return `${prefix}****${suffix}`;
  };

  // 页面加载时获取当前配置
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await getConfig('tushare_token');
        if (response.config_value) {
          const tokenValue = response.config_value;
          setRealToken(tokenValue);
          // 默认隐藏，显示掩码值
          form.setFieldsValue({
            tushare_token: maskSensitiveValue(tokenValue),
            comment: response.comment || 'Tushare 数据源 Token 配置',
          });
        } else {
          // 如果未配置，设置默认说明
          form.setFieldsValue({
            comment: 'Tushare 数据源 Token 配置',
          });
        }
      } catch (error: any) {
        // 如果配置不存在，不显示错误，只设置默认说明
        if (error?.response?.status !== 404) {
          message.error(error?.response?.data?.detail || '获取配置失败');
        } else {
          form.setFieldsValue({
            comment: 'Tushare 数据源 Token 配置',
          });
        }
      }
    };

    fetchConfig();
  }, [form]);

  // 保存配置
  const handleSave = async (values: any) => {
    setLoading(true);
    try {
      // 如果当前值是掩码值，使用保存的真实值；否则使用用户输入的值
      const tokenValue = values.tushare_token?.includes('****') && realToken 
        ? realToken 
        : values.tushare_token;
      
      await setConfig({
        config_key: 'tushare_token',
        config_value: tokenValue,
        comment: values.comment || 'Tushare 数据源 Token 配置',
      });
      
      // 更新真实值
      setRealToken(tokenValue);
      // 保存后重置为隐藏状态
      setShowToken(false);
      form.setFieldsValue({
        tushare_token: maskSensitiveValue(tokenValue),
      });
      
      message.success('配置保存成功');
      setTestResult(null); // 清除之前的测试结果
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '保存失败');
    } finally {
      setLoading(false);
    }
  };

  // 测试 Token 有效性
  const handleTest = async () => {
    let token = form.getFieldValue('tushare_token');
    
    // 如果当前值是掩码值，使用保存的真实值
    if (token?.includes('****') && realToken) {
      token = realToken;
    }
    
    if (!token || !token.trim()) {
      message.warning('请先输入 Tushare Token');
      return;
    }

    setTesting(true);
    setTestResult(null);
    
    try {
      const result = await testTushareToken({ token: token.trim() });
      setTestResult(result);
      
      if (result.success) {
        message.success(result.message);
      } else {
        message.error(result.message);
      }
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || error?.message || '测试失败';
      setTestResult({
        success: false,
        message: errorMessage,
      });
      message.error(errorMessage);
    } finally {
      setTesting(false);
    }
  };

  return (
    <PageContainer title="数据源配置" subTitle="配置和管理 Tushare 数据源 Token">
      <Card>
        <ProForm
          form={form}
          layout="vertical"
          onFinish={handleSave}
          submitter={{
            render: (props, doms) => {
              return (
                <Space>
                  <Button
                    type="primary"
                    loading={loading}
                    onClick={() => {
                      form.submit();
                    }}
                    disabled={loading || testing}
                  >
                    保存配置
                  </Button>
                  <Button
                    type="default"
                    loading={testing}
                    onClick={handleTest}
                    disabled={loading || testing}
                  >
                    Token有效性测试
                  </Button>
                </Space>
              );
            },
          }}
        >
          <ProFormText
            name="tushare_token"
            label={
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <span>Tushare Token</span>
                <span
                  style={{
                    cursor: 'pointer',
                    color: '#1890ff',
                    fontSize: '16px',
                    marginLeft: 8,
                  }}
                  onClick={() => {
                    const currentValue = form.getFieldValue('tushare_token');
                    const isMasked = currentValue && currentValue.includes('****');
                    
                    if (showToken) {
                      // 从显示切换到隐藏
                      if (realToken && currentValue === realToken) {
                        // 如果当前显示的是真实值，切换为掩码值
                        form.setFieldsValue({
                          tushare_token: maskSensitiveValue(realToken),
                        });
                      } else if (currentValue && !isMasked) {
                        // 如果当前是用户输入的新值，保存到 realToken 并切换为掩码值
                        setRealToken(currentValue);
                        form.setFieldsValue({
                          tushare_token: maskSensitiveValue(currentValue),
                        });
                      }
                    } else {
                      // 从隐藏切换到显示
                      if (realToken && isMasked) {
                        // 如果当前是掩码值且有真实值，显示真实值
                        form.setFieldsValue({
                          tushare_token: realToken,
                        });
                      } else if (isMasked && !realToken) {
                        // 如果当前是掩码值但没有真实值，提示用户无法显示
                        message.warning('无法显示已掩码的值，请重新输入');
                        return;
                      } else if (currentValue && !isMasked) {
                        // 如果当前是用户输入的新值，保存到 realToken 并显示
                        setRealToken(currentValue);
                        form.setFieldsValue({
                          tushare_token: currentValue,
                        });
                      }
                    }
                    setShowToken(!showToken);
                  }}
                >
                  {showToken ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                </span>
              </div>
            }
            placeholder="请输入 Tushare Token"
            rules={[
              {
                required: true,
                message: '请输入 Tushare Token',
              },
            ]}
            fieldProps={{
              type: showToken ? 'text' : 'password',
              autoComplete: 'off',
            }}
            extra="Tushare Token 用于访问 Tushare 数据接口，请妥善保管。Token 将加密存储。"
          />

          <ProFormTextArea
            name="comment"
            label="配置说明"
            placeholder="请输入配置说明（可选）"
            fieldProps={{
              rows: 3,
            }}
          />

          {testResult && (
            <Alert
              message={testResult.success ? '测试成功' : '测试失败'}
              description={testResult.message}
              type={testResult.success ? 'success' : 'error'}
              showIcon
              style={{ marginTop: 16 }}
            />
          )}
        </ProForm>

        <div style={{ marginTop: 24, padding: 16, backgroundColor: '#f5f5f5', borderRadius: 4 }}>
          <h4 style={{ marginTop: 0, marginBottom: 8 }}>使用说明：</h4>
          <ol style={{ marginBottom: 0, paddingLeft: 20 }}>
            <li>在 <a href="https://tushare.pro/" target="_blank" rel="noopener noreferrer">Tushare 官网</a> 注册账号并获取 Token</li>
            <li>将 Token 填入上方输入框</li>
            <li>点击"Token有效性测试"按钮验证 Token 是否有效</li>
            <li>测试通过后，点击"提交"按钮保存配置</li>
            <li>Token 将自动加密存储，确保安全性</li>
          </ol>
        </div>
      </Card>
    </PageContainer>
  );
};

export default DatasourceConfig;
