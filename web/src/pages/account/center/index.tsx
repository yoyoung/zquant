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

import { PageContainer } from '@ant-design/pro-components';
import { useModel, Helmet } from '@umijs/max';
import { Avatar, Card, Descriptions, Space, Tag, Typography } from 'antd';
import { UserOutlined } from '@ant-design/icons';
import React from 'react';
import { history } from '@umijs/max';
import Settings from '../../../../config/defaultSettings';

const { Title } = Typography;

const AccountCenter: React.FC = () => {
  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState || {};

  if (!currentUser) {
    return null;
  }

  const handleEdit = () => {
    history.push('/account/settings');
  };

  return (
    <>
      <Helmet>
        <title>个人中心{Settings.title && ` - ${Settings.title}`}</title>
      </Helmet>
      <PageContainer
      title="个人中心"
      extra={[
        <a key="settings" onClick={handleEdit} style={{ cursor: 'pointer' }}>
          编辑资料
        </a>,
      ]}
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 用户基本信息卡片 */}
        <Card>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
              <Avatar
                size={120}
                icon={<UserOutlined />}
                src={currentUser.avatar}
                style={{ flexShrink: 0 }}
              />
              <div style={{ flex: 1 }}>
                <Title level={3} style={{ marginBottom: '8px' }}>
                  {currentUser.name}
                </Title>
                <Space>
                  <Tag color={currentUser.access === 'admin' ? 'red' : 'blue'}>
                    {currentUser.access === 'admin' ? '管理员' : '普通用户'}
                  </Tag>
                  {currentUser.email && (
                    <Tag color="default">{currentUser.email}</Tag>
                  )}
                </Space>
              </div>
            </div>

            <Descriptions
              title="基本信息"
              bordered
              column={2}
              items={[
                {
                  key: 'username',
                  label: '用户名',
                  children: currentUser.name,
                },
                {
                  key: 'email',
                  label: '邮箱',
                  children: currentUser.email || '未设置',
                },
                {
                  key: 'userid',
                  label: '用户ID',
                  children: currentUser.userid,
                },
                {
                  key: 'access',
                  label: '权限',
                  children: currentUser.access === 'admin' ? '管理员' : '普通用户',
                },
              ]}
            />
          </Space>
        </Card>

        {/* 统计数据卡片（可选） */}
        <Card title="统计信息">
          <Descriptions
            column={3}
            items={[
              {
                key: 'strategies',
                label: '策略数量',
                children: '0',
              },
              {
                key: 'watchlist',
                label: '关注列表',
                children: '0',
              },
              {
                key: 'backtests',
                label: '回测记录',
                children: '0',
              },
            ]}
          />
        </Card>
      </Space>
    </PageContainer>
    </>
  );
};

export default AccountCenter;

