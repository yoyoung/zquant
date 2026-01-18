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
//     - Issues: https://github.com/yoyoung/zquant/issues
//     - Documentation: https://github.com/yoyoung/zquant/blob/main/README.md
//     - Repository: https://github.com/yoyoung/zquant

import { ProTable } from '@ant-design/pro-components';
import { Button, Modal, message, Popconfirm, Tag } from 'antd';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProForm, ProFormText, ProFormSwitch } from '@ant-design/pro-components';
import ProFormSelectWithAll from '@/components/ProFormSelectWithAll';
import React, { useRef, useState, useEffect } from 'react';
import { getUsers, createUser, updateUser, deleteUser, resetUserPassword } from '@/services/zquant/users';
import { getRoles } from '@/services/zquant/roles';
import dayjs from 'dayjs';

const Users: React.FC = () => {
  const actionRef = useRef<ActionType>(null);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [resetPasswordModalVisible, setResetPasswordModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<ZQuant.UserResponse | null>(null);
  const [resettingUser, setResettingUser] = useState<ZQuant.UserResponse | null>(null);
  const [roles, setRoles] = useState<ZQuant.RoleResponse[]>([]);

  // 加载角色列表
  useEffect(() => {
    const loadRoles = async () => {
      try {
        const response = await getRoles({ limit: 1000 });
        setRoles(response.items);
      } catch (error) {
        console.error('加载角色列表失败:', error);
      }
    };
    loadRoles();
  }, []);

  const handleCreate = async (values: any) => {
    try {
      await createUser({
        username: values.username,
        email: values.email,
        password: values.password,
        password_confirm: values.password_confirm,
        role_id: values.role_id,
      });
      message.success('用户创建成功');
      setCreateModalVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '创建失败');
    }
  };

  const handleEdit = async (values: any) => {
    if (!editingUser) return;
    try {
      await updateUser(editingUser.id, {
        email: values.email,
        is_active: values.is_active,
        role_id: values.role_id,
      });
      message.success('用户更新成功');
      setEditModalVisible(false);
      setEditingUser(null);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '更新失败');
    }
  };

  const handleDelete = async (userId: number) => {
    try {
      await deleteUser(userId);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '删除失败');
    }
  };

  const handleResetPassword = async (values: any) => {
    if (!resettingUser) return;
    try {
      await resetUserPassword(resettingUser.id, {
        password: values.password,
        password_confirm: values.password_confirm,
      });
      message.success('密码重置成功');
      setResetPasswordModalVisible(false);
      setResettingUser(null);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '密码重置失败');
    }
  };

  const columns: ProColumns<ZQuant.UserResponse>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
      search: false,
      sorter: true,
    },
    {
      title: '用户名',
      dataIndex: 'username',
      width: 150,
      sorter: true,
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      width: 200,
      sorter: true,
    },
    {
      title: '角色',
      dataIndex: 'role_id',
      width: 150,
      valueType: 'select',
      sorter: false,
      valueEnum: roles.reduce((acc, role) => {
        acc[role.id] = { text: role.name };
        return acc;
      }, {} as Record<number, { text: string }>),
      render: (_, record) => {
        const role = roles.find((r) => r.id === record.role_id);
        return role?.name || record.role_id;
      },
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 100,
      valueType: 'select',
      sorter: true,
      valueEnum: {
        true: { text: '启用', status: 'Success' },
        false: { text: '禁用', status: 'Error' },
      },
      render: (isActive) => (
        <Tag color={isActive ? 'success' : 'default'}>
          {isActive ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_time',
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
            setEditingUser(record);
            setEditModalVisible(true);
          }}
        >
          编辑
        </Button>,
        <Button
          key="reset-password"
          type="link"
          onClick={() => {
            setResettingUser(record);
            setResetPasswordModalVisible(true);
          }}
        >
          重置密码
        </Button>,
        <Popconfirm
          key="delete"
          title="确定要删除这个用户吗？"
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
      <ProTable<ZQuant.UserResponse>
        headerTitle="用户管理"
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
          
          const response = await getUsers({
            skip: ((params.current || 1) - 1) * (params.pageSize || 20),
            limit: params.pageSize || 20,
            is_active: params.is_active !== undefined ? params.is_active === true : undefined,
            role_id: params.role_id,
            username: params.username,
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
            创建用户
          </Button>,
        ]}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
        }}
      />

      {/* 创建用户Modal */}
      <Modal
        title="创建用户"
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
            name="username"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
            fieldProps={{
              placeholder: '请输入用户名',
            }}
          />
          <ProFormText
            name="email"
            label="邮箱"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
            fieldProps={{
              placeholder: '请输入邮箱',
            }}
          />
          <ProFormText.Password
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 8, message: '密码至少8位' },
              {
                pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{}|;:,.<>?])/,
                message: '密码必须包含大小写字母、数字和特殊字符',
              },
            ]}
            fieldProps={{
              placeholder: '请输入密码（至少8位，包含大小写字母、数字和特殊字符）',
            }}
          />
          <ProFormText.Password
            name="password_confirm"
            label="确认密码"
            dependencies={['password']}
            rules={[
              { required: true, message: '请再次输入密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
            fieldProps={{
              placeholder: '请再次输入密码',
            }}
          />
          <ProFormSelectWithAll
            name="role_id"
            label="角色"
            options={roles.map((role) => ({
              label: role.name,
              value: role.id,
            }))}
            allValue=""
            rules={[{ required: true, message: '请选择角色' }]}
            fieldProps={{
              placeholder: '请选择角色',
            }}
          />
        </ProForm>
      </Modal>

      {/* 编辑用户Modal */}
      <Modal
        title="编辑用户"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          setEditingUser(null);
        }}
        footer={null}
        width={600}
      >
        {editingUser && (
          <ProForm
            initialValues={{
              email: editingUser.email,
              is_active: editingUser.is_active,
              role_id: editingUser.role_id,
            }}
            onFinish={handleEdit}
            submitter={{
              render: (props, doms) => {
                return [
                  <Button key="cancel" onClick={() => {
                    setEditModalVisible(false);
                    setEditingUser(null);
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
              name="email"
              label="邮箱"
              rules={[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '请输入有效的邮箱地址' },
              ]}
              fieldProps={{
                placeholder: '请输入邮箱',
              }}
            />
            <ProFormSwitch
              name="is_active"
              label="启用状态"
            />
            <ProFormSelect
              name="role_id"
              label="角色"
              rules={[{ required: true, message: '请选择角色' }]}
              options={roles.map((role) => ({
                label: role.name,
                value: role.id,
              }))}
              fieldProps={{
                placeholder: '请选择角色',
              }}
            />
          </ProForm>
        )}
      </Modal>

      {/* 重置密码Modal */}
      <Modal
        title="重置密码"
        open={resetPasswordModalVisible}
        onCancel={() => {
          setResetPasswordModalVisible(false);
          setResettingUser(null);
        }}
        footer={null}
        width={600}
      >
        {resettingUser && (
          <ProForm
            onFinish={handleResetPassword}
            submitter={{
              render: (props, doms) => {
                return [
                  <Button key="cancel" onClick={() => {
                    setResetPasswordModalVisible(false);
                    setResettingUser(null);
                  }}>
                    取消
                  </Button>,
                  <Button key="submit" type="primary" onClick={() => props.form?.submit?.()}>
                    重置密码
                  </Button>,
                ];
              },
            }}
          >
            <ProFormText.Password
              name="password"
              label="新密码"
              rules={[
                { required: true, message: '请输入新密码' },
                { min: 8, message: '密码至少8位' },
                {
                  pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{}|;:,.<>?])/,
                  message: '密码必须包含大小写字母、数字和特殊字符',
                },
              ]}
              fieldProps={{
                placeholder: '请输入新密码（至少8位，包含大小写字母、数字和特殊字符）',
              }}
            />
            <ProFormText.Password
              name="password_confirm"
              label="确认新密码"
              dependencies={['password']}
              rules={[
                { required: true, message: '请再次输入新密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error('两次输入的密码不一致'));
                  },
                }),
              ]}
              fieldProps={{
                placeholder: '请再次输入新密码',
              }}
            />
          </ProForm>
        )}
      </Modal>
    </div>
  );
};

export default Users;

