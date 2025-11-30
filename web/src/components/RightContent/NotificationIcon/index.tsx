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

import { BellOutlined } from '@ant-design/icons';
import { Badge, Dropdown, Empty, List } from 'antd';
import { createStyles } from 'antd-style';
import React, { useState } from 'react';
import { history, useIntl, useRequest } from '@umijs/max';
import { notifications } from '@/services/zquant';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

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
  notificationList: {
    width: '320px',
    maxHeight: '400px',
    overflowY: 'auto',
  },
  notificationItem: {
    padding: '12px 16px',
    borderBottom: `1px solid ${token.colorBorderSecondary}`,
    cursor: 'pointer',
    '&:hover': {
      backgroundColor: token.colorBgTextHover,
    },
  },
  notificationTitle: {
    fontSize: '14px',
    fontWeight: 500,
    marginBottom: '4px',
  },
  notificationTime: {
    fontSize: '12px',
    color: token.colorTextSecondary,
  },
}));

const NotificationIcon: React.FC = () => {
  const { styles } = useStyles();
  const intl = useIntl();
  const [open, setOpen] = useState(false);

  // 获取未读统计
  const { data: stats, refresh: refreshStats } = useRequest(
    () => notifications.getNotificationStats(),
    {
      refreshDeps: [open],
      onError: () => {
        // 静默失败，不影响用户体验
      },
    }
  );

  // 获取通知列表（最多10条）
  const { data: notificationsData, refresh: refreshNotifications } = useRequest(
    () => notifications.getNotifications({ skip: 0, limit: 10, order_by: 'created_at', order: 'desc' }),
    {
      refreshDeps: [open],
      onError: () => {
        // 静默失败，不影响用户体验
      },
    }
  );

  const notificationList = notificationsData?.items || [];
  const unreadCount = stats?.unread_count || 0;

  // 格式化时间
  const formatTime = (time: string) => {
    return dayjs(time).fromNow();
  };

  // 处理通知点击
  const handleNotificationClick = async (notification: ZQuant.NotificationResponse) => {
    if (!notification.is_read) {
      try {
        await notifications.markNotificationAsRead(notification.id);
        refreshNotifications();
        refreshStats();
      } catch (error) {
        console.error('标记已读失败:', error);
      }
    }
    setOpen(false);
    history.push(`/data/notifications`);
  };

  return (
    <Dropdown
      open={open}
      onOpenChange={setOpen}
      trigger={['click']}
      placement="bottomRight"
      dropdownRender={() => (
        <div className={styles.notificationList}>
          <div style={{ padding: '8px 16px', borderBottom: '1px solid #f0f0f0' }}>
            <strong>通知中心</strong>
          </div>
          {notificationList.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={intl.formatMessage({
                id: 'component.globalHeader.notification.empty',
                defaultMessage: '你已查看所有通知',
              })}
              style={{ padding: '40px 20px' }}
            />
          ) : (
            <List
              dataSource={notificationList}
              renderItem={(item) => (
                <List.Item
                  className={styles.notificationItem}
                  style={{
                    padding: '12px 16px',
                    backgroundColor: item.is_read ? 'transparent' : '#f0f7ff',
                  }}
                  onClick={() => handleNotificationClick(item)}
                >
                  <div style={{ width: '100%' }}>
                    <div
                      className={styles.notificationTitle}
                      style={{ fontWeight: item.is_read ? 400 : 600 }}
                    >
                      {item.title}
                    </div>
                    <div style={{ fontSize: '13px', color: '#666', marginBottom: '4px' }}>
                      {item.content}
                    </div>
                    <div className={styles.notificationTime}>{formatTime(item.created_at)}</div>
                  </div>
                </List.Item>
              )}
            />
          )}
          {notificationList.length > 0 && (
            <div
              style={{
                padding: '8px 16px',
                textAlign: 'center',
                borderTop: '1px solid #f0f0f0',
                cursor: 'pointer',
              }}
              onClick={() => {
                setOpen(false);
                history.push('/data/notifications');
              }}
            >
              {intl.formatMessage({
                id: 'component.noticeIcon.view-more',
                defaultMessage: '查看更多',
              })}
            </div>
          )}
        </div>
      )}
    >
      <div className={styles.iconWrapper}>
        <Badge count={unreadCount} size="small" offset={[-2, 2]}>
          <BellOutlined style={{ fontSize: '18px', color: '#fff' }} />
        </Badge>
      </div>
    </Dropdown>
  );
};

export default NotificationIcon;

