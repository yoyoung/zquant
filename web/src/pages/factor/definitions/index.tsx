// Copyright 2025 ZQuant Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the Apache License is distributed on an "AS IS" BASIS,
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
import { Button, Tag, Popconfirm, message, Modal, Form, Input, Switch, Select } from 'antd';
import SelectWithAll from '@/components/SelectWithAll';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import React, { useRef, useState } from 'react';
import {
  getFactorDefinitions,
  createFactorDefinition,
  updateFactorDefinition,
  deleteFactorDefinition,
} from '@/services/zquant/factor';
import dayjs from 'dayjs';

const FactorDefinitions: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [form] = Form.useForm();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<ZQuant.FactorDefinitionResponse | null>(null);

  const columns: ProColumns<ZQuant.FactorDefinitionResponse>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
      sorter: true,
    },
    {
      title: '因子名称',
      dataIndex: 'factor_name',
      width: 150,
      sorter: true,
    },
    {
      title: '中文简称',
      dataIndex: 'cn_name',
      width: 120,
    },
    {
      title: '英文简称',
      dataIndex: 'en_name',
      width: 120,
    },
    {
      title: '列名',
      dataIndex: 'column_name',
      width: 150,
    },
    {
      title: '因子类型',
      dataIndex: 'factor_type',
      width: 120,
      render: (_, record) => {
        const factorType = record.factor_type || '单因子';
        return (
          <Tag color={factorType === '组合因子' ? 'blue' : 'default'}>
            {factorType}
          </Tag>
        );
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      width: 100,
      render: (_, record) => (
        <Tag color={record.enabled ? 'green' : 'red'}>{record.enabled ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_time',
      width: 180,
      sorter: true,
      render: (_, record) => dayjs(record.created_time).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      render: (_, record) => [
        <Button
          key="edit"
          type="link"
          size="small"
          onClick={() => {
            setEditingRecord(record);
            form.setFieldsValue(record);
            setModalVisible(true);
          }}
        >
          编辑
        </Button>,
        <Popconfirm
          key="delete"
          title="确定要删除这个因子定义吗？"
          onConfirm={async () => {
            try {
              await deleteFactorDefinition(record.id);
              message.success('删除成功');
              actionRef.current?.reload();
            } catch (error: any) {
              message.error(error?.response?.data?.detail || '删除失败');
            }
          }}
        >
          <Button type="link" size="small" danger>
            删除
          </Button>
        </Popconfirm>,
      ],
    },
  ];

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingRecord) {
        await updateFactorDefinition(editingRecord.id, values);
        message.success('更新成功');
      } else {
        await createFactorDefinition(values);
        message.success('创建成功');
      }
      setModalVisible(false);
      setEditingRecord(null);
      form.resetFields();
      actionRef.current?.reload();
    } catch (error: any) {
      if (error?.errorFields) {
        // 表单验证失败，返回 false 阻止 Modal 关闭
        return false;
      }
      message.error(error?.response?.data?.detail || '操作失败');
      // 其他错误也返回 false，让用户看到错误信息
      return false;
    }
  };

  return (
    <div>
      <ProTable<ZQuant.FactorDefinitionResponse>
        headerTitle="因子定义列表"
        actionRef={actionRef}
        rowKey="id"
        search={false}
        toolBarRender={() => [
          <Button
            key="create"
            type="primary"
            onClick={() => {
              setEditingRecord(null);
              form.resetFields();
              setModalVisible(true);
            }}
          >
            新建因子定义
          </Button>,
        ]}
        request={async (params, sort) => {
          const response = await getFactorDefinitions({
            skip: ((params.current || 1) - 1) * (params.pageSize || 20),
            limit: params.pageSize || 20,
            order_by: Object.keys(sort || {})[0] || 'id',
            order: Object.values(sort || {})[0] === 'ascend' ? 'asc' : 'desc',
          });
          return {
            data: response.items,
            success: true,
            total: response.total,
          };
        }}
        columns={columns}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
        }}
      />

      <Modal
        title={editingRecord ? '编辑因子定义' : '新建因子定义'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          setEditingRecord(null);
          form.resetFields();
        }}
        width={600}
        maskClosable={true}
        keyboard={true}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="factor_name"
            label="因子名称"
            rules={[{ required: true, message: '请输入因子名称' }]}
          >
            <Input disabled={!!editingRecord} placeholder="因子名称（唯一标识）" />
          </Form.Item>
          <Form.Item name="cn_name" label="中文简称" rules={[{ required: true, message: '请输入中文简称' }]}>
            <Input placeholder="中文简称" />
          </Form.Item>
          <Form.Item name="en_name" label="英文简称">
            <Input placeholder="英文简称" />
          </Form.Item>
          <Form.Item name="column_name" label="列名" rules={[{ required: true, message: '请输入列名' }]}>
            <Input placeholder="因子表数据列名" />
          </Form.Item>
          <Form.Item
            name="factor_type"
            label="因子类型"
            initialValue="单因子"
            rules={[{ required: true, message: '请选择因子类型' }]}
          >
            <SelectWithAll
              placeholder="请选择因子类型"
              options={[
                { label: '单因子', value: '单因子' },
                { label: '组合因子', value: '组合因子' },
              ]}
              allValue=""
            />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={4} placeholder="因子详细描述" />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default FactorDefinitions;

