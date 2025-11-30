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

import { QuestionCircleOutlined, UserOutlined } from '@ant-design/icons';
import { SelectLang as UmiSelectLang } from '@umijs/max';
import { Avatar } from 'antd';
import { createStyles } from 'antd-style';
import React from 'react';
import { useModel } from '@umijs/max';
import NotificationIcon from './NotificationIcon';
import SettingsIcon from './SettingsIcon';
import { AvatarDropdown } from './AvatarDropdown';

export type SiderTheme = 'light' | 'dark';

const useStyles = createStyles(({ token }) => ({
  rightContent: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
}));

export const SelectLang: React.FC = () => {
  return (
    <UmiSelectLang
      style={{
        padding: 4,
      }}
    />
  );
};

export const Question: React.FC = () => {
  const { styles } = useStyles();
  return (
    <a
      href="https://docs.zquant.com"
      target="_blank"
      rel="noreferrer"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '40px',
        height: '40px',
        cursor: 'pointer',
        borderRadius: '4px',
        transition: 'all 0.3s',
        color: 'rgba(255, 255, 255, 0.85)',
        fontSize: '18px',
        textDecoration: 'none',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
        e.currentTarget.style.color = '#fff';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = 'transparent';
        e.currentTarget.style.color = 'rgba(255, 255, 255, 0.85)';
      }}
    >
      <QuestionCircleOutlined />
    </a>
  );
};

export const RightContent: React.FC = () => {
  const { styles } = useStyles();
  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState || {};

  return (
    <div className={styles.rightContent}>
      <NotificationIcon />
      <SettingsIcon />
      <Question />
      <AvatarDropdown menu>
        <Avatar size="small" icon={<UserOutlined />} src={currentUser?.avatar} style={{ cursor: 'pointer' }} />
      </AvatarDropdown>
    </div>
  );
};
