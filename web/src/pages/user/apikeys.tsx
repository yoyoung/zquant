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

import { ProTable } from '@ant-design/pro-components';
import { Button, Modal, message, Popconfirm, Tag } from 'antd';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProForm, ProFormText } from '@ant-design/pro-components';
import React, { useRef, useState } from 'react';
import { getAPIKeys, createAPIKey, deleteAPIKey } from '@/services/zquant/users';
import dayjs from 'dayjs';

const APIKeys: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [newKeyData, setNewKeyData] = useState<ZQuant.APIKeyCreateResponse | null>(null);

  const handleCreate = async (values: any) => {
    try {
      const response = await createAPIKey({
        name: values.name || undefined,
      });
      setNewKeyData(response);
      message.success('API密钥创建成功，请妥善保管secret_key');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '创建失败');
    }
  };

  const handleDelete = async (keyId: number) => {
    try {
      await deleteAPIKey(keyId);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '删除失败');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success('已复制到剪贴板');
  };

  const columns: ProColumns<ZQuant.APIKeyResponse>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
      sorter: (a, b) => a.id - b.id,
    },
    {
      title: '名称',
      dataIndex: 'name',
      width: 200,
      sorter: (a, b) => {
        const nameA = a.name || '';
        const nameB = b.name || '';
        return nameA.localeCompare(nameB);
      },
      render: (text) => text || '-',
    },
    {
      title: 'Access Key',
      dataIndex: 'access_key',
      width: 250,
      ellipsis: true,
      sorter: false,
      render: (text) => (
        <span
          style={{ cursor: 'pointer' }}
          onClick={() => copyToClipboard(text)}
          title="点击复制"
        >
          {text}
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 100,
      sorter: (a, b) => {
        if (a.is_active === b.is_active) return 0;
        return a.is_active ? 1 : -1;
      },
      render: (isActive) => (
        <Tag color={isActive ? 'success' : 'default'}>
          {isActive ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '最后使用时间',
      dataIndex: 'last_used_at',
      width: 180,
      sorter: (a, b) => {
        if (!a.last_used_at && !b.last_used_at) return 0;
        if (!a.last_used_at) return 1;
        if (!b.last_used_at) return -1;
        return dayjs(a.last_used_at).valueOf() - dayjs(b.last_used_at).valueOf();
      },
      render: (text) => text ? dayjs(text).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      sorter: (a, b) => dayjs(a.created_at).valueOf() - dayjs(b.created_at).valueOf(),
      render: (text) => dayjs(text).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '过期时间',
      dataIndex: 'expires_at',
      width: 180,
      sorter: (a, b) => {
        if (!a.expires_at && !b.expires_at) return 0;
        if (!a.expires_at) return 1;
        if (!b.expires_at) return -1;
        return dayjs(a.expires_at).valueOf() - dayjs(b.expires_at).valueOf();
      },
      render: (text) => text ? dayjs(text).format('YYYY-MM-DD HH:mm:ss') : '永不过期',
    },
    {
      title: '操作',
      valueType: 'option',
      width: 100,
      render: (_, record) => [
        <Popconfirm
          key="delete"
          title="确定要删除这个API密钥吗？"
          onConfirm={() => handleDelete(record.id)}
        >
          <Button type="link" danger>
            删除
          </Button>
        </Popconfirm>,
      ],
    },
  ];

  return (
    <div>
      <ProTable<ZQuant.APIKeyResponse>
        headerTitle="API密钥管理"
        actionRef={actionRef}
        columns={columns}
        request={async () => {
          const response = await getAPIKeys();
          return {
            data: response,
            success: true,
            total: response.length,
          };
        }}
        rowKey="id"
        search={false}
        toolBarRender={() => [
          <Button
            key="create"
            type="primary"
            onClick={() => {
              setCreateModalVisible(true);
              setNewKeyData(null);
            }}
          >
            创建API密钥
          </Button>,
        ]}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
        }}
      />

      <Modal
        title="创建API密钥"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          setNewKeyData(null);
        }}
        footer={null}
        width={600}
      >
        {newKeyData ? (
          <div>
            <div style={{ marginBottom: 16, padding: 16, background: '#f5f5f5', borderRadius: 4 }}>
              <p style={{ marginBottom: 8, fontWeight: 'bold' }}>⚠️ 重要提示</p>
              <p style={{ marginBottom: 8 }}>{newKeyData.message}</p>
            </div>
            <ProForm
              submitter={false}
              initialValues={{
                access_key: newKeyData.access_key,
                secret_key: newKeyData.secret_key,
              }}
            >
              <ProFormText
                name="access_key"
                label="Access Key"
                fieldProps={{
                  readOnly: true,
                  addonAfter: (
                    <Button
                      size="small"
                      onClick={() => copyToClipboard(newKeyData.access_key)}
                    >
                      复制
                    </Button>
                  ),
                }}
              />
              <ProFormText
                name="secret_key"
                label="Secret Key"
                fieldProps={{
                  readOnly: true,
                  addonAfter: (
                    <Button
                      size="small"
                      onClick={() => copyToClipboard(newKeyData.secret_key)}
                    >
                      复制
                    </Button>
                  ),
                }}
              />
            </ProForm>
            <Button
              type="primary"
              block
              style={{ marginTop: 16 }}
              onClick={() => {
                setCreateModalVisible(false);
                setNewKeyData(null);
              }}
            >
              我已保存，关闭窗口
            </Button>
          </div>
        ) : (
          <ProForm
            onFinish={handleCreate}
            submitter={{
              render: (props, doms) => {
                return [
                  <Button
                    key="submit"
                    type="primary"
                    onClick={() => props.form?.submit?.()}
                  >
                    创建
                  </Button>,
                ];
              },
            }}
          >
            <ProFormText
              name="name"
              label="密钥名称"
              placeholder="可选，用于标识此密钥的用途"
            />
          </ProForm>
        )}
      </Modal>
    </div>
  );
};

export default APIKeys;

