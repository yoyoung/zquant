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

import { PageContainer, ProForm, ProFormText } from '@ant-design/pro-components';
import { useModel, Helmet } from '@umijs/max';
import { Card, message, Tabs } from 'antd';
import React, { useState } from 'react';
import { updateUser, resetUserPassword, getCurrentUser } from '@/services/zquant/users';
import { flushSync } from 'react-dom';
import { ADMIN_ROLE_ID } from '@/constants/roles';
import Settings from '../../../../config/defaultSettings';

const AccountSettings: React.FC = () => {
  const { initialState, setInitialState } = useModel('@@initialState');
  const { currentUser } = initialState || {};
  const [loading, setLoading] = useState(false);

  if (!currentUser) {
    return null;
  }

  const userId = parseInt(currentUser.userid || '0', 10);

  const handleBasicInfoSubmit = async (values: any) => {
    setLoading(true);
    try {
      await updateUser(userId, {
        email: values.email || undefined,
      });
      message.success('基本信息更新成功');
      
      // 刷新用户信息
      const userInfo = await getCurrentUser();
      const isAdmin = userInfo.role_id === ADMIN_ROLE_ID;
      flushSync(() => {
        setInitialState((s) => ({
          ...s,
          currentUser: {
            ...s?.currentUser,
            email: userInfo.email,
            name: userInfo.username,
          },
        }));
      });
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '更新失败');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordSubmit = async (values: any) => {
    if (values.password !== values.password_confirm) {
      message.error('两次输入的密码不一致');
      return;
    }

    setLoading(true);
    try {
      await resetUserPassword(userId, {
        password: values.password,
        password_confirm: values.password_confirm,
      });
      message.success('密码修改成功，请重新登录');
      
      // 延迟跳转，让用户看到成功消息
      setTimeout(() => {
        // 清除token并跳转登录
        localStorage.removeItem('access_token');
        window.location.href = '/user/login';
      }, 1500);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '密码修改失败');
    } finally {
      setLoading(false);
    }
  };

  const tabItems = [
    {
      key: 'basic',
      label: '基本信息',
      children: (
        <Card>
          <ProForm
            layout="vertical"
            initialValues={{
              username: currentUser.name,
              email: currentUser.email,
            }}
            onFinish={handleBasicInfoSubmit}
            submitter={{
              searchConfig: {
                submitText: '保存',
              },
            }}
            loading={loading}
          >
            <ProFormText
              name="username"
              label="用户名"
              disabled
              tooltip="用户名不可修改"
            />
            <ProFormText
              name="email"
              label="邮箱"
              rules={[
                {
                  type: 'email',
                  message: '请输入有效的邮箱地址',
                },
              ]}
              placeholder="请输入邮箱地址"
            />
          </ProForm>
        </Card>
      ),
    },
    {
      key: 'security',
      label: '安全设置',
      children: (
        <Card>
          <ProForm
            layout="vertical"
            onFinish={handlePasswordSubmit}
            submitter={{
              searchConfig: {
                submitText: '修改密码',
              },
            }}
            loading={loading}
          >
            <ProFormText.Password
              name="password"
              label="新密码"
              rules={[
                {
                  required: true,
                  message: '请输入新密码',
                },
                {
                  min: 8,
                  message: '密码长度至少8位',
                },
                {
                  pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{}|;:,.<>?])/,
                  message: '密码必须包含大小写字母、数字和特殊字符',
                },
              ]}
              placeholder="请输入新密码（至少8位，包含大小写字母、数字和特殊字符）"
            />
            <ProFormText.Password
              name="password_confirm"
              label="确认密码"
              dependencies={['password']}
              rules={[
                {
                  required: true,
                  message: '请确认新密码',
                },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error('两次输入的密码不一致'));
                  },
                }),
              ]}
              placeholder="请再次输入新密码"
            />
          </ProForm>
        </Card>
      ),
    },
  ];

  return (
    <>
      <Helmet>
        <title>个人设置{Settings.title && ` - ${Settings.title}`}</title>
      </Helmet>
      <PageContainer title="个人设置">
        <Tabs items={tabItems} />
      </PageContainer>
    </>
  );
};

export default AccountSettings;

