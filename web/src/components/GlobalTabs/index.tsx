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

import { CloseOutlined } from '@ant-design/icons';
import { Tabs } from 'antd';
import { createStyles } from 'antd-style';
import React from 'react';
import type { TabItem } from '@/hooks/useGlobalTabs';

const useStyles = createStyles(({ token }) => {
  return {
    tabsContainer: {
      backgroundColor: token.colorBgContainer,
      padding: '0 16px',
      borderBottom: `1px solid ${token.colorBorderSecondary}`,
    },
    tabContent: {
      padding: '16px',
      backgroundColor: token.colorBgLayout,
      minHeight: 'calc(100vh - 120px)',
    },
  };
});

interface GlobalTabsProps {
  tabs: TabItem[];
  activeKey: string;
  onChange: (key: string) => void;
  onRemove: (key: string) => void;
  children: React.ReactNode;
}

const GlobalTabs: React.FC<GlobalTabsProps> = ({
  tabs,
  activeKey,
  onChange,
  onRemove,
  children,
}) => {
  const { styles } = useStyles();

  // 如果没有页卡，直接显示内容
  if (tabs.length === 0) {
    return <>{children}</>;
  }

  const handleEdit = (targetKey: string, action: 'add' | 'remove') => {
    if (action === 'remove') {
      onRemove(targetKey);
    }
  };

  return (
    <div>
      <div className={styles.tabsContainer}>
        <Tabs
          type="editable-card"
          hideAdd
          activeKey={activeKey}
          onChange={onChange}
          onEdit={handleEdit}
          items={tabs.map((tab) => ({
            key: tab.key,
            label: tab.title,
            closable: tab.closable !== false,
            children: null, // 内容在下方统一渲染
          }))}
        />
      </div>
      <div className={styles.tabContent}>
        {children}
      </div>
    </div>
  );
};

export default GlobalTabs;

