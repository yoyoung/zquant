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
import { Button, Modal, message, Popconfirm, Tag, Checkbox } from 'antd';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProForm, ProFormText, ProFormTextArea } from '@ant-design/pro-components';
import React, { useRef, useState, useEffect } from 'react';
import { getRoles, createRole, updateRole, deleteRole, getRolePermissions, assignPermissions } from '@/services/zquant/roles';
import { getPermissions } from '@/services/zquant/permissions';
import dayjs from 'dayjs';

const Roles: React.FC = () => {
  const actionRef = useRef<ActionType>(null);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [permissionModalVisible, setPermissionModalVisible] = useState(false);
  const [editingRole, setEditingRole] = useState<ZQuant.RoleResponse | null>(null);
  const [permissionRole, setPermissionRole] = useState<ZQuant.RoleResponse | null>(null);
  const [allPermissions, setAllPermissions] = useState<ZQuant.PermissionResponse[]>([]);
  const [rolePermissions, setRolePermissions] = useState<ZQuant.PermissionResponse[]>([]);
  const [selectedPermissions, setSelectedPermissions] = useState<number[]>([]);

  // 加载所有权限
  useEffect(() => {
    const loadPermissions = async () => {
      try {
        const response = await getPermissions({ limit: 1000 });
        setAllPermissions(response.items);
      } catch (error) {
        console.error('加载权限列表失败:', error);
      }
    };
    loadPermissions();
  }, []);

  // 加载角色的权限
  const loadRolePermissions = async (roleId: number) => {
    try {
      const permissions = await getRolePermissions(roleId);
      setRolePermissions(permissions);
      setSelectedPermissions(permissions.map((p) => p.id));
    } catch (error) {
      console.error('加载角色权限失败:', error);
    }
  };

  const handleCreate = async (values: any) => {
    try {
      await createRole({
        name: values.name,
        description: values.description,
      });
      message.success('角色创建成功');
      setCreateModalVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '创建失败');
    }
  };

  const handleEdit = async (values: any) => {
    if (!editingRole) return;
    try {
      await updateRole(editingRole.id, {
        name: values.name,
        description: values.description,
      });
      message.success('角色更新成功');
      setEditModalVisible(false);
      setEditingRole(null);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '更新失败');
    }
  };

  const handleDelete = async (roleId: number) => {
    try {
      await deleteRole(roleId);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '删除失败');
    }
  };

  const handleOpenPermissionModal = async (role: ZQuant.RoleResponse) => {
    setPermissionRole(role);
    setPermissionModalVisible(true);
    await loadRolePermissions(role.id);
  };

  const handleSavePermissions = async () => {
    if (!permissionRole) return;
    try {
      await assignPermissions(permissionRole.id, {
        permission_ids: selectedPermissions,
      });
      message.success('权限分配成功');
      setPermissionModalVisible(false);
      setPermissionRole(null);
      setSelectedPermissions([]);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '权限分配失败');
    }
  };

  // 按资源类型分组权限
  const permissionsByResource = allPermissions.reduce((acc, perm) => {
    if (!acc[perm.resource]) {
      acc[perm.resource] = [];
    }
    acc[perm.resource].push(perm);
    return acc;
  }, {} as Record<string, ZQuant.PermissionResponse[]>);

  const columns: ProColumns<ZQuant.RoleResponse>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
      search: false,
      sorter: true,
    },
    {
      title: '角色名称',
      dataIndex: 'name',
      width: 200,
      sorter: true,
    },
    {
      title: '描述',
      dataIndex: 'description',
      width: 300,
      ellipsis: true,
      search: false,
      sorter: true,
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
      width: 200,
      render: (_, record) => [
        <Button
          key="edit"
          type="link"
          onClick={() => {
            setEditingRole(record);
            setEditModalVisible(true);
          }}
        >
          编辑
        </Button>,
        <Button
          key="permissions"
          type="link"
          onClick={() => handleOpenPermissionModal(record)}
        >
          权限管理
        </Button>,
        <Popconfirm
          key="delete"
          title="确定要删除这个角色吗？"
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
      <ProTable<ZQuant.RoleResponse>
        headerTitle="角色管理"
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
          
          const response = await getRoles({
            skip: ((params.current || 1) - 1) * (params.pageSize || 20),
            limit: params.pageSize || 20,
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
            创建角色
          </Button>,
        ]}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
        }}
      />

      {/* 创建角色Modal */}
      <Modal
        title="创建角色"
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
            label="角色名称"
            rules={[{ required: true, message: '请输入角色名称' }]}
            fieldProps={{
              placeholder: '请输入角色名称',
            }}
          />
          <ProFormTextArea
            name="description"
            label="描述"
            fieldProps={{
              placeholder: '请输入角色描述（可选）',
              rows: 3,
            }}
          />
        </ProForm>
      </Modal>

      {/* 编辑角色Modal */}
      <Modal
        title="编辑角色"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          setEditingRole(null);
        }}
        footer={null}
        width={600}
      >
        {editingRole && (
          <ProForm
            initialValues={{
              name: editingRole.name,
              description: editingRole.description,
            }}
            onFinish={handleEdit}
            submitter={{
              render: (props, doms) => {
                return [
                  <Button key="cancel" onClick={() => {
                    setEditModalVisible(false);
                    setEditingRole(null);
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
              label="角色名称"
              rules={[{ required: true, message: '请输入角色名称' }]}
              fieldProps={{
                placeholder: '请输入角色名称',
              }}
            />
            <ProFormTextArea
              name="description"
              label="描述"
              fieldProps={{
                placeholder: '请输入角色描述（可选）',
                rows: 3,
              }}
            />
          </ProForm>
        )}
      </Modal>

      {/* 权限管理Modal */}
      <Modal
        title={`权限管理 - ${permissionRole?.name}`}
        open={permissionModalVisible}
        onCancel={() => {
          setPermissionModalVisible(false);
          setPermissionRole(null);
          setSelectedPermissions([]);
        }}
        onOk={handleSavePermissions}
        width={800}
        okText="保存"
        cancelText="取消"
      >
        <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
          {Object.entries(permissionsByResource).map(([resource, perms]) => (
            <div key={resource} style={{ marginBottom: 24 }}>
              <div style={{ marginBottom: 12, fontWeight: 'bold', fontSize: 16 }}>
                {resource}
              </div>
              <div>
                {perms.map((perm) => (
                  <div key={perm.id} style={{ marginBottom: 8 }}>
                    <Checkbox
                      checked={selectedPermissions.includes(perm.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedPermissions([...selectedPermissions, perm.id]);
                        } else {
                          setSelectedPermissions(selectedPermissions.filter((id) => id !== perm.id));
                        }
                      }}
                    >
                      <span style={{ marginLeft: 8 }}>
                        {perm.name} {perm.description && `(${perm.description})`}
                      </span>
                    </Checkbox>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Modal>
    </div>
  );
};

export default Roles;

