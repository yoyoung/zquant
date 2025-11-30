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

import { MailOutlined } from '@ant-design/icons';
import { Badge, Dropdown, Empty, List } from 'antd';
import { createStyles } from 'antd-style';
import React, { useState } from 'react';
import { useIntl } from '@umijs/max';

const useStyles = createStyles(({ token }) => ({
  iconWrapper: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '40px',
    height: '40px',
    cursor: 'pointer',
    borderRadius: '4px',
    transition: 'all 0.3s',
    color: 'rgba(255, 255, 255, 0.85)',
    '&:hover': {
      backgroundColor: 'rgba(255, 255, 255, 0.1)',
      color: '#fff',
    },
  },
  messageList: {
    width: '320px',
    maxHeight: '400px',
    overflowY: 'auto',
  },
  messageItem: {
    padding: '12px 16px',
    borderBottom: `1px solid ${token.colorBorderSecondary}`,
    cursor: 'pointer',
    '&:hover': {
      backgroundColor: token.colorBgTextHover,
    },
  },
  messageTitle: {
    fontSize: '14px',
    fontWeight: 500,
    marginBottom: '4px',
  },
  messageTime: {
    fontSize: '12px',
    color: token.colorTextSecondary,
  },
}));

interface MessageItem {
  id: string;
  title: string;
  content: string;
  time: string;
  read: boolean;
}

// 模拟消息数据
const mockMessages: MessageItem[] = [
  {
    id: '1',
    title: '系统消息',
    content: '您的策略回测已完成',
    time: '5分钟前',
    read: false,
  },
  {
    id: '2',
    title: '提醒消息',
    content: '您的投资组合有新的交易信号',
    time: '30分钟前',
    read: false,
  },
];

const MessageIcon: React.FC = () => {
  const { styles } = useStyles();
  const intl = useIntl();
  const [messages] = useState<MessageItem[]>(mockMessages);

  const unreadCount = messages.filter((m) => !m.read).length;

  const messageMenu = {
    items: [
      {
        key: 'header',
        label: (
          <div style={{ padding: '8px 16px', borderBottom: '1px solid #f0f0f0' }}>
            <strong>消息中心</strong>
          </div>
        ),
      },
    ],
    overlay: (
      <div className={styles.messageList}>
        {messages.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={intl.formatMessage({
              id: 'component.globalHeader.message.empty',
              defaultMessage: '您已读完所有消息',
            })}
            style={{ padding: '40px 20px' }}
          />
        ) : (
          <List
            dataSource={messages}
            renderItem={(item) => (
              <List.Item
                className={styles.messageItem}
                style={{ padding: '12px 16px' }}
              >
                <div style={{ width: '100%' }}>
                  <div className={styles.messageTitle}>{item.title}</div>
                  <div style={{ fontSize: '13px', color: '#666', marginBottom: '4px' }}>
                    {item.content}
                  </div>
                  <div className={styles.messageTime}>{item.time}</div>
                </div>
              </List.Item>
            )}
          />
        )}
        {messages.length > 0 && (
          <div
            style={{
              padding: '8px 16px',
              textAlign: 'center',
              borderTop: '1px solid #f0f0f0',
              cursor: 'pointer',
            }}
            onClick={() => {
              // 跳转到消息页面
              console.log('查看全部消息');
            }}
          >
            {intl.formatMessage({
              id: 'component.noticeIcon.view-more',
              defaultMessage: '查看更多',
            })}
          </div>
        )}
      </div>
    ),
  };

  return (
    <Dropdown menu={messageMenu} trigger={['click']} placement="bottomRight">
      <div className={styles.iconWrapper}>
        <Badge count={unreadCount || 98} size="small" offset={[-2, 2]}>
          <MailOutlined style={{ fontSize: '18px' }} />
        </Badge>
      </div>
    </Dropdown>
  );
};

export default MessageIcon;

