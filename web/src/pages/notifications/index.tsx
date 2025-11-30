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
import {
  Badge,
  Button,
  Card,
  Dropdown,
  Empty,
  List,
  message,
  Popconfirm,
  Space,
  Tag,
  Typography,
} from 'antd';
import {
  BellOutlined,
  CheckCircleOutlined,
  DeleteOutlined,
  MoreOutlined,
  ReadOutlined,
} from '@ant-design/icons';
import React, { useState } from 'react';
import { useRequest } from '@umijs/max';
import { notifications } from '@/services/zquant';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const { Text } = Typography;

// 通知类型标签映射
const typeTagMap: Record<ZQuant.NotificationType, { color: string; text: string }> = {
  system: { color: 'blue', text: '系统' },
  strategy: { color: 'green', text: '策略' },
  backtest: { color: 'orange', text: '回测' },
  data: { color: 'cyan', text: '数据' },
  warning: { color: 'red', text: '警告' },
};

const NotificationsPage: React.FC = () => {
  const [filter, setFilter] = useState<{
    is_read?: boolean;
    type?: ZQuant.NotificationType;
  }>({});
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
  });

  // 获取通知统计
  const { data: stats, refresh: refreshStats } = useRequest(
    () => notifications.getNotificationStats(),
    {
      refreshDeps: [filter, pagination],
    }
  );

  // 获取通知列表
  const { data, loading, refresh } = useRequest(
    () =>
      notifications.getNotifications({
        skip: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
        is_read: filter.is_read,
        type: filter.type,
        order_by: 'created_at',
        order: 'desc',
      }),
    {
      refreshDeps: [filter, pagination],
      onError: (error) => {
        message.error('获取通知列表失败');
        console.error(error);
      },
    }
  );

  const notificationList = data?.items || [];
  const total = data?.total || 0;

  // 格式化时间
  const formatTime = (time: string) => {
    return dayjs(time).fromNow();
  };

  // 标记为已读
  const handleMarkAsRead = async (notificationId: number) => {
    try {
      await notifications.markNotificationAsRead(notificationId);
      message.success('已标记为已读');
      refresh();
      refreshStats();
    } catch (error) {
      message.error('标记已读失败');
      console.error(error);
    }
  };

  // 全部标记为已读
  const handleMarkAllAsRead = async () => {
    try {
      const result = await notifications.markAllNotificationsAsRead();
      message.success(result.message || '全部标记为已读成功');
      refresh();
      refreshStats();
    } catch (error) {
      message.error('全部标记为已读失败');
      console.error(error);
    }
  };

  // 删除通知
  const handleDelete = async (notificationId: number) => {
    try {
      await notifications.deleteNotification(notificationId);
      message.success('删除成功');
      refresh();
      refreshStats();
    } catch (error) {
      message.error('删除失败');
      console.error(error);
    }
  };

  // 筛选菜单
  const filterMenuItems = [
    {
      key: 'all',
      label: '全部',
      onClick: () => setFilter({}),
    },
    {
      key: 'unread',
      label: (
        <Space>
          未读
          {stats?.unread_count ? (
            <Badge count={stats.unread_count} size="small" />
          ) : null}
        </Space>
      ),
      onClick: () => setFilter({ is_read: false }),
    },
    {
      key: 'read',
      label: '已读',
      onClick: () => setFilter({ is_read: true }),
    },
  ];

  // 类型筛选菜单
  const typeMenuItems = [
    {
      key: 'all',
      label: '全部类型',
      onClick: () => setFilter((prev) => ({ ...prev, type: undefined })),
    },
    ...Object.entries(typeTagMap).map(([key, value]) => ({
      key,
      label: value.text,
      onClick: () => setFilter((prev) => ({ ...prev, type: key as ZQuant.NotificationType })),
    })),
  ];

  return (
    <PageContainer
      title="通知中心"
      extra={
        <Space>
          <Dropdown
            menu={{ items: filterMenuItems }}
            placement="bottomRight"
          >
            <Button>
              {filter.is_read === false
                ? '未读'
                : filter.is_read === true
                ? '已读'
                : '全部'}
            </Button>
          </Dropdown>
          <Dropdown
            menu={{ items: typeMenuItems }}
            placement="bottomRight"
          >
            <Button>
              {filter.type ? typeTagMap[filter.type].text : '全部类型'}
            </Button>
          </Dropdown>
          <Button
            icon={<ReadOutlined />}
            onClick={handleMarkAllAsRead}
            disabled={!stats?.unread_count || stats.unread_count === 0}
          >
            全部标记为已读
          </Button>
        </Space>
      }
    >
      <Card>
        {notificationList.length === 0 ? (
          <Empty
            description="暂无通知"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ padding: '60px 0' }}
          />
        ) : (
          <List
            loading={loading}
            dataSource={notificationList}
            pagination={{
              current: pagination.current,
              pageSize: pagination.pageSize,
              total: total,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条`,
              onChange: (page, pageSize) => {
                setPagination({ current: page, pageSize });
              },
            }}
            renderItem={(item) => (
              <List.Item
                style={{
                  backgroundColor: item.is_read ? 'transparent' : '#f0f7ff',
                  padding: '16px',
                  marginBottom: '8px',
                  borderRadius: '4px',
                }}
                actions={[
                  <Space>
                  {!item.is_read && (
                    <Button
                      type="text"
                      size="small"
                      icon={<CheckCircleOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMarkAsRead(item.id);
                      }}
                    >
                      标记已读
                    </Button>
                  )}
                  <Popconfirm
                    title="确定要删除这条通知吗？"
                    onConfirm={(e) => {
                      e?.stopPropagation();
                      handleDelete(item.id);
                    }}
                    onCancel={(e) => e?.stopPropagation()}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={(e) => e.stopPropagation()}
                    >
                      删除
                    </Button>
                  </Popconfirm>
                </Space>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Tag color={typeTagMap[item.type].color}>
                        {typeTagMap[item.type].text}
                      </Tag>
                      <Text strong={!item.is_read}>{item.title}</Text>
                      {!item.is_read && (
                        <Badge status="processing" text="未读" />
                      )}
                    </Space>
                  }
                  description={
                    <div>
                      <div style={{ marginBottom: '8px' }}>{item.content}</div>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {formatTime(item.created_at)}
                      </Text>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </PageContainer>
  );
};

export default NotificationsPage;

