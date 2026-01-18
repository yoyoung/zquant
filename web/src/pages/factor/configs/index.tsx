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
import { Button, Tag, Popconfirm, message, Modal, Form, Select, Switch, Space, Alert } from 'antd';
import SelectWithAll from '@/components/SelectWithAll';
import { PlusOutlined, MinusCircleOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import React, { useRef, useState, useEffect } from 'react';
import {
  getFactorDefinitions,
  getFactorModels,
  getFactorConfigs,
  getFactorConfigById,
  createFactorConfig,
  updateFactorConfigById,
  deleteFactorConfigById,
} from '@/services/zquant/factor';
import dayjs from 'dayjs';

// 因子配置行类型（用于表格显示）
type FactorConfigRow = {
  factor_id: number;
  factor_name: string;
  cn_name: string;
  mapping_count: number;
  enabled: boolean;
  created_by?: string | null;
  created_time: string;
  updated_by?: string | null;
  updated_time: string;
};

const FactorConfigs: React.FC = () => {
  const actionRef = useRef<ActionType>(null);
  const [form] = Form.useForm();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingFactorId, setEditingFactorId] = useState<number | null>(null);
  const [factorDefinitions, setFactorDefinitions] = useState<ZQuant.FactorDefinitionResponse[]>([]);
  const [factorModels, setFactorModels] = useState<ZQuant.FactorModelResponse[]>([]);
  const [selectedFactorId, setSelectedFactorId] = useState<number | undefined>();

  // 加载因子定义列表
  useEffect(() => {
    getFactorDefinitions({ limit: 1000 }).then((res) => {
      setFactorDefinitions(res.items);
    });
  }, []);

  // 当选择因子时，加载该因子的模型列表
  useEffect(() => {
    if (selectedFactorId) {
      getFactorModels({ factor_id: selectedFactorId, limit: 1000 }).then((res) => {
        setFactorModels(res.items);
      });
    } else {
      setFactorModels([]);
    }
  }, [selectedFactorId]);

  // 获取默认模型
  const getDefaultModel = (factorId: number) => {
    return factorModels.find((m) => m.factor_id === factorId && m.is_default);
  };

  // 获取因子名称
  const getFactorName = (factorId: number) => {
    const factor = factorDefinitions.find((f) => f.id === factorId);
    return factor ? factor.factor_name : '';
  };

  // 获取因子中文名
  const getFactorCnName = (factorId: number) => {
    const factor = factorDefinitions.find((f) => f.id === factorId);
    return factor ? factor.cn_name : '';
  };

  const columns: ProColumns<FactorConfigRow>[] = [
    {
      title: '因子ID',
      dataIndex: 'factor_id',
      width: 100,
      sorter: true,
    },
    {
      title: '因子名称',
      dataIndex: 'factor_name',
      width: 150,
      sorter: true,
    },
    {
      title: '中文名',
      dataIndex: 'cn_name',
      width: 120,
    },
    {
      title: '映射数量',
      dataIndex: 'mapping_count',
      width: 100,
      render: (_, record) => {
        const count = record.mapping_count || 0;
        return <Tag color={count > 0 ? 'blue' : 'default'}>{count}</Tag>;
      },
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
      title: '创建人',
      dataIndex: 'created_by',
      width: 100,
      render: (_, record) => record.created_by || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_time',
      width: 180,
      sorter: true,
      render: (_, record) => dayjs(record.created_time).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '修改人',
      dataIndex: 'updated_by',
      width: 100,
      render: (_, record) => record.updated_by || '-',
    },
    {
      title: '更新时间',
      dataIndex: 'updated_time',
      width: 180,
      sorter: true,
      render: (_, record) => dayjs(record.updated_time).format('YYYY-MM-DD HH:mm:ss'),
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
          onClick={async () => {
            try {
              setEditingFactorId(record.factor_id);
              setSelectedFactorId(record.factor_id);
              
              // 加载配置
              const config = await getFactorConfigById(record.factor_id);
              
              // 设置表单值
              form.setFieldsValue({
                factor_id: record.factor_id,
                enabled: config.enabled,
                mappings: config.config.mappings && config.config.mappings.length > 0 
                  ? config.config.mappings.map((m: ZQuant.FactorConfigMappingItem) => ({
                      model_id: m.model_id,
                      codes: m.codes || [],
                    }))
                  : [{ model_id: undefined, codes: [] }],
              });
              
              setModalVisible(true);
            } catch (error: any) {
              if (error?.response?.status === 404) {
                // 配置不存在，使用默认值
                form.setFieldsValue({
                  factor_id: record.factor_id,
                  enabled: true,
                  mappings: [{ model_id: undefined, codes: [] }],
                });
                setModalVisible(true);
              } else {
                message.error(error?.response?.data?.detail || '加载配置失败');
              }
            }
          }}
        >
          编辑
        </Button>,
        <Popconfirm
          key="delete"
          title="确定要删除这个因子配置吗？"
          onConfirm={async () => {
            try {
              await deleteFactorConfigById(record.factor_id);
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
      const factorId = values.factor_id;
      
      // 处理映射数据
      const mappings = values.mappings.map((m: any) => ({
        model_id: m.model_id,
        codes: m.codes && Array.isArray(m.codes) && m.codes.length > 0
          ? m.codes.map((c: string) => c.trim()).filter((c: string) => c)
          : null,
      }));

      if (editingFactorId) {
        // 更新
        await updateFactorConfigById(factorId, {
          enabled: values.enabled,
          mappings: mappings,
        });
        message.success('更新成功');
      } else {
        // 创建
        await createFactorConfig({
          factor_id: factorId,
          enabled: values.enabled,
          mappings: mappings,
        });
        message.success('创建成功');
      }

      setModalVisible(false);
      setEditingFactorId(null);
      form.resetFields();
      setSelectedFactorId(undefined);
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

  const handleCancel = () => {
    setModalVisible(false);
    setEditingFactorId(null);
    form.resetFields();
    setSelectedFactorId(undefined);
  };

  // 获取默认模型提示信息
  const getDefaultModelHint = () => {
    if (!selectedFactorId) return null;
    const defaultModel = getDefaultModel(selectedFactorId);
    if (defaultModel) {
      return (
        <Alert
          message={`提示：未在映射中指定的股票代码将使用默认模型 "${defaultModel.model_name} (${defaultModel.model_code})"`}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      );
    }
    return (
      <Alert
        message="提示：该因子暂无默认模型，请确保在因子模型中设置一个默认模型"
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
      />
    );
  };

  return (
    <div>
      <ProTable<FactorConfigRow>
        headerTitle="因子配置列表"
        actionRef={actionRef}
        rowKey="factor_id"
        search={false}
        toolBarRender={() => [
          <Button
            key="create"
            type="primary"
            onClick={() => {
              setEditingFactorId(null);
              setSelectedFactorId(undefined);
              form.resetFields();
              form.setFieldsValue({
                enabled: true,
                mappings: [{ model_id: undefined, codes: [] }],
              });
              setModalVisible(true);
            }}
          >
            新建因子配置
          </Button>,
        ]}
        request={async (params, sort) => {
          try {
            // 确保因子定义已加载
            let definitions = factorDefinitions;
            if (definitions.length === 0) {
              const defsResponse = await getFactorDefinitions({ limit: 1000 });
              definitions = defsResponse.items;
              setFactorDefinitions(definitions);
            }

            // 处理排序参数
            let order_by: string | undefined;
            let order: 'asc' | 'desc' | undefined;
            
            if (sort && typeof sort === 'object') {
              const sortKeys = Object.keys(sort);
              if (sortKeys.length > 0) {
                const field = sortKeys[0];
                const direction = sort[field];
                order_by = field === 'factor_id' ? 'factor_id' : field;
                if (direction === 'ascend') {
                  order = 'asc';
                } else if (direction === 'descend') {
                  order = 'desc';
                }
              }
            }

            const response = await getFactorConfigs({
              skip: ((params.current || 1) - 1) * (params.pageSize || 20),
              limit: params.pageSize || 20,
              order_by,
              order,
            });

            // 转换数据格式
            const rows: FactorConfigRow[] = response.items.map((config: ZQuant.FactorConfigResponse) => {
              const factorId = config.factor_id;
              const factor = definitions.find((f) => f.id === factorId);
              return {
                factor_id: factorId,
                factor_name: factor?.factor_name || '',
                cn_name: factor?.cn_name || '',
                mapping_count: config.config.mappings ? config.config.mappings.length : 0,
                enabled: config.enabled,
                created_by: config.created_by,
                created_time: config.created_time,
                updated_by: config.updated_by,
                updated_time: config.updated_time,
              };
            });

            return {
              data: rows,
              success: true,
              total: response.total,
            };
          } catch (error) {
            console.error('获取因子配置列表失败:', error);
            return {
              data: [],
              success: false,
              total: 0,
            };
          }
        }}
        columns={columns}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
        }}
      />

      <Modal
        title={editingFactorId ? '编辑因子配置' : '新建因子配置'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={handleCancel}
        width={800}
        okText="保存"
        cancelText="取消"
        maskClosable={true}
        keyboard={true}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="factor_id" label="因子" rules={[{ required: true, message: '请选择因子' }]}>
            <SelectWithAll
              placeholder="选择因子"
              disabled={!!editingFactorId}
              onChange={(value) => {
                setSelectedFactorId(value);
                // 重置映射列表
                form.setFieldsValue({
                  mappings: [{ model_id: undefined, codes: [] }],
                });
              }}
              options={factorDefinitions.map((f) => ({ 
                label: `${f.cn_name} (${f.factor_name})`, 
                value: f.id 
              }))}
              allValue=""
            />
          </Form.Item>

          {getDefaultModelHint()}

          <Form.Item name="enabled" label="启用" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>

          <Form.Item
            label="模型-股票代码映射"
            tooltip="配置多个模型和股票代码的映射对。如果某个股票代码不在任何映射的codes列表中，将使用该因子的默认模型。"
            required
          >
            <Form.List
              name="mappings"
              rules={[
                {
                  validator: async (_, mappings) => {
                    if (!mappings || mappings.length === 0) {
                      return Promise.reject(new Error('至少需要一个映射配置'));
                    }
                  },
                },
              ]}
            >
              {(fields, { add, remove }) => (
                <>
                  {fields.map((field, index) => (
                    <Space key={field.key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                      <Form.Item
                        {...field}
                        name={[field.name, 'model_id']}
                        label={index === 0 ? '模型' : ''}
                        rules={[{ required: true, message: '请选择模型' }]}
                        style={{ flex: 1 }}
                      >
                        <SelectWithAll
                          placeholder="选择模型"
                          disabled={!selectedFactorId}
                          options={factorModels.map((m) => ({ 
                            label: `${m.model_name} (${m.model_code})${m.is_default ? ' [默认]' : ''}`, 
                            value: m.id 
                          }))}
                          allValue=""
                        />
                      </Form.Item>
                      <Form.Item
                        {...field}
                        name={[field.name, 'codes']}
                        label={index === 0 ? '股票代码' : ''}
                        tooltip="留空表示默认配置，用于所有未在其它映射中指定的股票"
                        style={{ flex: 2 }}
                      >
                        <Select
                          mode="tags"
                          placeholder="输入股票代码，按回车添加（留空表示默认配置）"
                          tokenSeparators={[',']}
                          options={[]}
                          style={{ width: '100%' }}
                        />
                      </Form.Item>
                      {fields.length > 1 && (
                        <Form.Item label={index === 0 ? '操作' : ''}>
                          <Button
                            type="link"
                            danger
                            icon={<MinusCircleOutlined />}
                            onClick={() => remove(field.name)}
                          >
                            删除
                          </Button>
                        </Form.Item>
                      )}
                    </Space>
                  ))}
                  <Form.Item>
                    <Button
                      type="dashed"
                      onClick={() => add({ model_id: undefined, codes: [] })}
                      block
                      icon={<PlusOutlined />}
                    >
                      添加映射
                    </Button>
                  </Form.Item>
                </>
              )}
            </Form.List>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default FactorConfigs;
