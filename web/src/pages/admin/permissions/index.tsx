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
import { ProForm, ProFormText, ProFormSelect, ProFormTextArea } from '@ant-design/pro-components';
import React, { useRef, useState } from 'react';
import { getPermissions, createPermission, updatePermission, deletePermission } from '@/services/zquant/permissions';
import dayjs from 'dayjs';

const Permissions: React.FC = () => {
  const actionRef = useRef<ActionType>(null);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingPermission, setEditingPermission] = useState<ZQuant.PermissionResponse | null>(null);

  // 资源类型选项（可以从后端获取或硬编码）
  const resourceOptions = [
    { label: 'user', value: 'user' },
    { label: 'role', value: 'role' },
    { label: 'permission', value: 'permission' },
    { label: 'data', value: 'data' },
    { label: 'backtest', value: 'backtest' },
  ];

  // 操作类型选项
  const actionOptions = [
    { label: 'create', value: 'create' },
    { label: 'read', value: 'read' },
    { label: 'update', value: 'update' },
    { label: 'delete', value: 'delete' },
    { label: 'sync', value: 'sync' },
    { label: 'run', value: 'run' },
  ];

  const handleCreate = async (values: any) => {
    try {
      await createPermission({
        name: values.name,
        resource: values.resource,
        action: values.action,
        description: values.description,
      });
      message.success('权限创建成功');
      setCreateModalVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '创建失败');
    }
  };

  const handleEdit = async (values: any) => {
    if (!editingPermission) return;
    try {
      await updatePermission(editingPermission.id, {
        name: values.name,
        resource: values.resource,
        action: values.action,
        description: values.description,
      });
      message.success('权限更新成功');
      setEditModalVisible(false);
      setEditingPermission(null);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '更新失败');
    }
  };

  const handleDelete = async (permissionId: number) => {
    try {
      await deletePermission(permissionId);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '删除失败');
    }
  };

  const columns: ProColumns<ZQuant.PermissionResponse>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
      search: false,
      sorter: true,
    },
    {
      title: '权限名称',
      dataIndex: 'name',
      width: 200,
      sorter: true,
    },
    {
      title: '资源类型',
      dataIndex: 'resource',
      width: 150,
      valueType: 'select',
      sorter: true,
      valueEnum: resourceOptions.reduce((acc, opt) => {
        acc[opt.value] = { text: opt.label };
        return acc;
      }, {} as Record<string, { text: string }>),
      render: (text) => <Tag>{text}</Tag>,
    },
    {
      title: '操作类型',
      dataIndex: 'action',
      width: 150,
      valueType: 'select',
      sorter: true,
      valueEnum: actionOptions.reduce((acc, opt) => {
        acc[opt.value] = { text: opt.label };
        return acc;
      }, {} as Record<string, { text: string }>),
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      width: 300,
      ellipsis: true,
      search: false,
      sorter: false,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      search: false,
      sorter: true,
      render: (text) => text ? dayjs(String(text)).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      render: (_, record) => [
        <Button
          key="edit"
          type="link"
          onClick={() => {
            setEditingPermission(record);
            setEditModalVisible(true);
          }}
        >
          编辑
        </Button>,
        <Popconfirm
          key="delete"
          title="确定要删除这个权限吗？"
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
      <ProTable<ZQuant.PermissionResponse>
        headerTitle="权限管理"
        actionRef={actionRef}
        columns={columns}
        request={async (params, sort) => {
          // 处理排序参数
          let order_by: string | undefined;
          let order: 'asc' | 'desc' | undefined;
          
          if (sort && typeof sort === 'object') {
            const sortKeys = Object.keys(sort);
            if (sortKeys.length > 0) {
              const field = sortKeys[0];
              const direction = sort[field];
              order_by = field;
              if (direction === 'ascend') {
                order = 'asc';
              } else if (direction === 'descend') {
                order = 'desc';
              }
            }
          }
          
          const response = await getPermissions({
            skip: ((params.current || 1) - 1) * (params.pageSize || 20),
            limit: params.pageSize || 20,
            resource: params.resource,
            order_by,
            order,
          });
          return {
            data: response.items,
            success: true,
            total: response.total,
          };
        }}
        rowKey="id"
        search={{
          labelWidth: 'auto',
        }}
        toolBarRender={() => [
          <Button
            key="create"
            type="primary"
            onClick={() => {
              setCreateModalVisible(true);
            }}
          >
            创建权限
          </Button>,
        ]}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
        }}
      />

      {/* 创建权限Modal */}
      <Modal
        title="创建权限"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
        }}
        footer={null}
        width={600}
      >
        <ProForm
          onFinish={handleCreate}
          submitter={{
            render: (props, doms) => {
              return [
                <Button key="cancel" onClick={() => setCreateModalVisible(false)}>
                  取消
                </Button>,
                <Button key="submit" type="primary" onClick={() => props.form?.submit?.()}>
                  创建
                </Button>,
              ];
            },
          }}
        >
          <ProFormText
            name="name"
            label="权限名称"
            rules={[{ required: true, message: '请输入权限名称' }]}
            fieldProps={{
              placeholder: '例如: user:create',
            }}
          />
          <ProFormSelect
            name="resource"
            label="资源类型"
            rules={[{ required: true, message: '请选择资源类型' }]}
            options={resourceOptions}
            fieldProps={{
              placeholder: '请选择资源类型',
            }}
          />
          <ProFormSelect
            name="action"
            label="操作类型"
            rules={[{ required: true, message: '请选择操作类型' }]}
            options={actionOptions}
            fieldProps={{
              placeholder: '请选择操作类型',
            }}
          />
          <ProFormTextArea
            name="description"
            label="描述"
            fieldProps={{
              placeholder: '请输入权限描述（可选）',
              rows: 3,
            }}
          />
        </ProForm>
      </Modal>

      {/* 编辑权限Modal */}
      <Modal
        title="编辑权限"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          setEditingPermission(null);
        }}
        footer={null}
        width={600}
      >
        {editingPermission && (
          <ProForm
            initialValues={{
              name: editingPermission.name,
              resource: editingPermission.resource,
              action: editingPermission.action,
              description: editingPermission.description,
            }}
            onFinish={handleEdit}
            submitter={{
              render: (props, doms) => {
                return [
                  <Button key="cancel" onClick={() => {
                    setEditModalVisible(false);
                    setEditingPermission(null);
                  }}>
                    取消
                  </Button>,
                  <Button key="submit" type="primary" onClick={() => props.form?.submit?.()}>
                    更新
                  </Button>,
                ];
              },
            }}
          >
            <ProFormText
              name="name"
              label="权限名称"
              rules={[{ required: true, message: '请输入权限名称' }]}
              fieldProps={{
                placeholder: '例如: user:create',
              }}
            />
            <ProFormSelect
              name="resource"
              label="资源类型"
              rules={[{ required: true, message: '请选择资源类型' }]}
              options={resourceOptions}
              fieldProps={{
                placeholder: '请选择资源类型',
              }}
            />
            <ProFormSelect
              name="action"
              label="操作类型"
              rules={[{ required: true, message: '请选择操作类型' }]}
              options={actionOptions}
              fieldProps={{
                placeholder: '请选择操作类型',
              }}
            />
            <ProFormTextArea
              name="description"
              label="描述"
              fieldProps={{
                placeholder: '请输入权限描述（可选）',
                rows: 3,
              }}
            />
          </ProForm>
        )}
      </Modal>
    </div>
  );
};

export default Permissions;

