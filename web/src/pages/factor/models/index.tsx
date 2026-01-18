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
import { Button, Tag, Popconfirm, message, Modal, Form, Input, Switch, Select, InputNumber } from 'antd';
import SelectWithAll from '@/components/SelectWithAll';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import React, { useRef, useState, useEffect } from 'react';
import {
  getFactorModels,
  createFactorModel,
  updateFactorModel,
  deleteFactorModel,
  getFactorDefinitions,
} from '@/services/zquant/factor';
import dayjs from 'dayjs';

const FactorModels: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [form] = Form.useForm();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<ZQuant.FactorModelResponse | null>(null);
  const [factorDefinitions, setFactorDefinitions] = useState<ZQuant.FactorDefinitionResponse[]>([]);

  useEffect(() => {
    getFactorDefinitions({ limit: 1000 }).then((res) => {
      setFactorDefinitions(res.items);
    });
  }, []);

  const columns: ProColumns<ZQuant.FactorModelResponse>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 80,
      sorter: true,
    },
    {
      title: '因子',
      dataIndex: 'factor_id',
      width: 120,
      render: (_, record) => {
        const factor = factorDefinitions.find((f) => f.id === record.factor_id);
        return factor?.cn_name || record.factor_id;
      },
    },
    {
      title: '模型名称',
      dataIndex: 'model_name',
      width: 200,
    },
    {
      title: '模型代码',
      dataIndex: 'model_code',
      width: 150,
    },
    {
      title: '是否默认',
      dataIndex: 'is_default',
      width: 100,
      render: (_, record) => (
        <Tag color={record.is_default ? 'blue' : 'default'}>{record.is_default ? '默认' : '否'}</Tag>
      ),
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
            form.setFieldsValue({
              ...record,
              config_json: JSON.stringify(record.config_json || {}, null, 2),
            });
            setModalVisible(true);
          }}
        >
          编辑
        </Button>,
        <Popconfirm
          key="delete"
          title="确定要删除这个因子模型吗？"
          onConfirm={async () => {
            try {
              await deleteFactorModel(record.id);
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
      const submitData = {
        ...values,
        config_json: values.config_json ? JSON.parse(values.config_json) : undefined,
      };
      if (editingRecord) {
        await updateFactorModel(editingRecord.id, submitData);
        message.success('更新成功');
      } else {
        await createFactorModel(submitData);
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
      <ProTable<ZQuant.FactorModelResponse>
        headerTitle="因子模型列表"
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
            新建因子模型
          </Button>,
        ]}
        request={async (params, sort) => {
          const response = await getFactorModels({
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
        title={editingRecord ? '编辑因子模型' : '新建因子模型'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          setEditingRecord(null);
          form.resetFields();
        }}
        width={700}
        maskClosable={true}
        keyboard={true}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="factor_id" label="因子" rules={[{ required: true, message: '请选择因子' }]}>
            <SelectWithAll
              placeholder="选择因子"
              options={factorDefinitions.map((f) => ({ label: `${f.cn_name} (${f.factor_name})`, value: f.id }))}
              allValue=""
            />
          </Form.Item>
          <Form.Item name="model_name" label="模型名称" rules={[{ required: true, message: '请输入模型名称' }]}>
            <Input placeholder="模型名称" />
          </Form.Item>
          <Form.Item name="model_code" label="模型代码" rules={[{ required: true, message: '请输入模型代码' }]}>
            <Input placeholder="模型代码（用于识别计算器类型）" />
          </Form.Item>
          <Form.Item name="config_json" label="配置（JSON格式）">
            <Input.TextArea rows={6} placeholder='{"source": "daily_basic", "field": "turnover_rate"}' />
          </Form.Item>
          <Form.Item name="is_default" label="是否默认" valuePropName="checked" initialValue={false}>
            <Switch />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default FactorModels;

