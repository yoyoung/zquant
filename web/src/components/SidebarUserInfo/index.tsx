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

import {
  LogoutOutlined,
  SettingOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { history, useModel } from '@umijs/max';
import type { MenuProps } from 'antd';
import { Avatar, Badge, Dropdown, Space, Typography } from 'antd';
import { createStyles } from 'antd-style';
import React from 'react';
import { flushSync } from 'react-dom';
import { outLogin } from '@/services/ant-design-pro/api';

const { Text } = Typography;

const useStyles = createStyles(({ token }) => {
  return {
    container: {
      padding: '16px',
      borderBottom: `1px solid ${token.colorBorderSecondary}`,
      backgroundColor: token.colorBgContainer,
    },
    userInfo: {
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      cursor: 'pointer',
      padding: '8px',
      borderRadius: token.borderRadius,
      transition: 'background-color 0.3s',
      '&:hover': {
        backgroundColor: token.colorBgTextHover,
      },
    },
    avatar: {
      flexShrink: 0,
    },
    userDetails: {
      flex: 1,
      minWidth: 0,
    },
    username: {
      fontSize: '14px',
      fontWeight: 500,
      color: token.colorText,
      display: 'block',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
    },
    status: {
      fontSize: '12px',
      color: token.colorTextSecondary,
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
    },
    statusDot: {
      width: '8px',
      height: '8px',
      borderRadius: '50%',
      backgroundColor: '#52c41a',
    },
  };
});

interface SidebarUserInfoProps {
  collapsed?: boolean;
}

const SidebarUserInfo: React.FC<SidebarUserInfoProps> = ({ collapsed = false }) => {
  const { styles } = useStyles();
  const { initialState, setInitialState } = useModel('@@initialState');

  /**
   * 退出登录，并且将当前的 url 保存
   */
  const loginOut = async () => {
    await outLogin();
    const { search, pathname } = window.location;
    const urlParams = new URL(window.location.href).searchParams;
    const searchParams = new URLSearchParams({
      redirect: pathname + search,
    });
    /** 此方法会跳转到 redirect 参数所在的位置 */
    const urlParamsRedirect = urlParams.get('redirect');
    // Note: There may be security issues, please note
    if (window.location.pathname !== '/user/login' && !urlParamsRedirect) {
      history.replace({
        pathname: '/user/login',
        search: searchParams.toString(),
      });
    }
  };

  const onMenuClick: MenuProps['onClick'] = (event) => {
    const { key } = event;
    if (key === 'logout') {
      flushSync(() => {
        setInitialState((s) => ({ ...s, currentUser: undefined }));
      });
      loginOut();
      return;
    }
    history.push(`/account/${key}`);
  };

  if (!initialState?.currentUser) {
    return null;
  }

  const { currentUser } = initialState;

  const menuItems: MenuProps['items'] = [
    {
      key: 'center',
      icon: <UserOutlined />,
      label: '个人中心',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '个人设置',
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
    },
  ];

  // 折叠时只显示头像图标
  if (collapsed) {
    return (
      <div className={styles.container} style={{ padding: '16px', display: 'flex', justifyContent: 'center' }}>
        <Dropdown
          menu={{
            selectedKeys: [],
            onClick: onMenuClick,
            items: menuItems,
          }}
          placement="bottomLeft"
          trigger={['click']}
        >
          <div style={{ cursor: 'pointer' }}>
            <Badge
              dot
              color="#52c41a"
            >
              <Avatar
                size={40}
                src={currentUser.avatar}
                icon={<UserOutlined />}
              />
            </Badge>
          </div>
        </Dropdown>
      </div>
    );
  }

  // 展开时显示完整信息
  return (
    <div className={styles.container}>
      <Dropdown
        menu={{
          selectedKeys: [],
          onClick: onMenuClick,
          items: menuItems,
        }}
        placement="bottomLeft"
        trigger={['click']}
      >
        <div className={styles.userInfo}>
          <Badge
            dot
            color="#52c41a"
            className={styles.avatar}
          >
            <Avatar
              size={40}
              src={currentUser.avatar}
              icon={<UserOutlined />}
            />
          </Badge>
          <div className={styles.userDetails}>
            <Text className={styles.username} title={currentUser.name}>
              {currentUser.name || '用户'}
            </Text>
            <div className={styles.status}>
              <span className={styles.statusDot} />
              <span>在线</span>
            </div>
          </div>
        </div>
      </Dropdown>
    </div>
  );
};

export default SidebarUserInfo;

