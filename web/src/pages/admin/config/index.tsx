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

import React, { useRef, useState } from 'react';
import { ProTable, ProForm, ProFormText, ProFormTextArea } from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { Button, Modal, message, Popconfirm, Input, Tag, Space } from 'antd';
import { EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons';
import { getAllConfigs, setConfig, updateConfig, deleteConfig, getConfig } from '@/services/zquant/config';
import { renderDateTime } from '@/components/DataTable';

const Config: React.FC = () => {
  const actionRef = useRef<ActionType>(null);
  const editFormRef = useRef<any>(null);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<ZQuant.ConfigItem | null>(null);
  const [showSensitiveValues, setShowSensitiveValues] = useState(false);
  // 存储每个敏感配置项的显示状态（列表）
  const [visibleConfigKeys, setVisibleConfigKeys] = useState<Record<string, boolean>>({});
  // 存储每个敏感配置项的显示状态（弹框）
  const [visibleModalConfigKeys, setVisibleModalConfigKeys] = useState<Record<string, boolean>>({});
  // 查看弹框状态
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [viewingConfig, setViewingConfig] = useState<ZQuant.ConfigItem | null>(null);

  // 敏感配置键列表（这些配置的值会被隐藏）
  const sensitiveKeys = ['tushare_token', 'password', 'secret', 'key', 'token'];

  const isSensitiveKey = (key: string): boolean => {
    return sensitiveKeys.some(sensitive => key.toLowerCase().includes(sensitive.toLowerCase()));
  };

  // 将配置值转换为字符串（正确处理对象和数组）
  const convertConfigValueToString = (value: any): string => {
    if (value === null || value === undefined) {
      return '';
    }
    
    // 如果是字符串 "[object Object]"，说明原始值可能是对象但被错误转换了
    // 这种情况下，我们需要尝试从其他地方获取原始值，或者返回提示
    if (typeof value === 'string' && value === '[object Object]') {
      return '[无法显示：对象类型]';
    }
    
    // 检查是否为数组
    if (Array.isArray(value)) {
      try {
        return JSON.stringify(value, null, 2);
      } catch (e) {
        return String(value);
      }
    }
    
    // 检查是否为对象（排除null，因为typeof null === 'object'）
    if (typeof value === 'object' && value !== null) {
      // 如果是对象，序列化为JSON字符串
      try {
        return JSON.stringify(value, null, 2);
      } catch (e) {
        // 如果序列化失败，尝试使用对象的toString方法
        const toString = value.toString();
        if (toString !== '[object Object]') {
          return toString;
        }
        // 如果toString也是[object Object]，尝试获取对象的键值对
        try {
          const keys = Object.keys(value);
          if (keys.length > 0) {
            return JSON.stringify(value, null, 2);
          }
        } catch (e2) {
          // 忽略错误
        }
        return '[无法显示：对象类型]';
      }
    }
    
    return String(value);
  };

  // 掩码显示敏感值（前后各4个字符）
  const maskSensitiveValue = (value: any): string => {
    // 先转换为字符串
    const strValue = convertConfigValueToString(value);
    if (!strValue) return '***';
    if (strValue.length <= 8) {
      return '****';
    }
    const prefix = strValue.substring(0, 4);
    const suffix = strValue.substring(strValue.length - 4);
    return `${prefix}****${suffix}`;
  };

  // 切换列表中的配置项显示状态
  const toggleConfigVisibility = (configKey: string) => {
    setVisibleConfigKeys((prev) => ({
      ...prev,
      [configKey]: !prev[configKey],
    }));
  };

  // 切换弹框中的配置项显示状态
  const toggleModalConfigVisibility = (configKey: string) => {
    setVisibleModalConfigKeys((prev) => ({
      ...prev,
      [configKey]: !prev[configKey],
    }));
  };

  const handleCreate = async (values: any) => {
    try {
      await setConfig({
        config_key: values.config_key,
        config_value: values.config_value,
        comment: values.comment,
      });
      message.success('配置创建成功');
      setCreateModalVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '创建失败');
    }
  };

  const handleEdit = async (values: any) => {
    if (!editingConfig) return;
    try {
      // 如果是敏感配置项且当前显示的是掩码值，使用原始值
      const configKey = editingConfig.config_key || '';
      const isSensitive = isSensitiveKey(configKey);
      const isVisible = visibleModalConfigKeys[configKey];
      const originalValueStr = convertConfigValueToString(editingConfig.config_value);
      const maskedValue = maskSensitiveValue(originalValueStr);
      const configValue = isSensitive && !isVisible && values.config_value === maskedValue
        ? editingConfig.config_value  // 保持原始类型
        : values.config_value;

      await updateConfig(editingConfig.config_key, {
        config_value: configValue,
        comment: values.comment,
      });
      message.success('配置更新成功');
      setEditModalVisible(false);
      setEditingConfig(null);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '更新失败');
    }
  };

  const handleDelete = async (configKey: string) => {
    try {
      await deleteConfig(configKey);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '删除失败');
    }
  };

  const handleViewValue = async (configKey: string) => {
    try {
      const response = await getConfig(configKey);
      setViewingConfig({
        ...response,
        config_key: configKey,
      });
      setViewModalVisible(true);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '获取配置值失败');
    }
  };

  const columns: ProColumns<ZQuant.ConfigItem>[] = [
    {
      title: '配置键',
      dataIndex: 'config_key',
      width: 200,
      sorter: (a, b) => (a.config_key || '').localeCompare(b.config_key || ''),
      render: (text) => {
        const isSensitive = isSensitiveKey(text);
        return (
          <span>
            {text}
            {isSensitive && <Tag color="red" style={{ marginLeft: 8 }}>敏感</Tag>}
          </span>
        );
      },
    },
    {
      title: '配置值',
      dataIndex: 'config_value',
      width: 300,
      ellipsis: true,
      render: (text, record) => {
        const configKey = record.config_key || '';
        const isSensitive = isSensitiveKey(configKey);
        
        // 直接使用record.config_value获取原始值，避免ProTable自动转换导致的问题
        // 如果text已经是"[object Object]"字符串，说明原始值可能是对象，需要从record中获取
        const rawValue = (typeof text === 'string' && text === '[object Object]') 
          ? record.config_value 
          : (record.config_value !== undefined ? record.config_value : text);
        
        // 处理空值或特殊值
        if (rawValue === '***' || rawValue === null || rawValue === undefined) {
          return <span style={{ color: '#999' }}>***</span>;
        }

        // 转换为字符串，正确处理对象和数组类型
        const textValue = convertConfigValueToString(rawValue);

        // 处理空字符串
        if (!textValue) {
          return <span style={{ color: '#999' }}>***</span>;
        }

        // 非敏感配置项，直接显示完整值
        if (!isSensitive) {
          return <span style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{textValue}</span>;
        }

        // 敏感配置项：根据显示状态决定显示掩码值还是完整值
        // 默认显示掩码值，点击眼睛图标后显示完整值
        const isVisible = visibleConfigKeys[configKey] === true;
        const displayValue = isVisible ? textValue : maskSensitiveValue(textValue);
        const Icon = isVisible ? EyeOutlined : EyeInvisibleOutlined;

        return (
          <Space>
            <span style={{ 
              color: isVisible ? 'inherit' : '#999',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all'
            }}>{displayValue}</span>
            <Icon
              style={{
                cursor: 'pointer',
                color: '#1890ff',
                fontSize: '16px',
              }}
              onClick={(e) => {
                e.stopPropagation();
                toggleConfigVisibility(configKey);
              }}
            />
          </Space>
        );
      },
    },
    {
      title: '说明',
      dataIndex: 'comment',
      width: 200,
      ellipsis: true,
      render: (text) => text || '-',
    },
    {
      title: '创建人',
      dataIndex: 'created_by',
      width: 100,
      render: (text) => text || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_time',
      width: 180,
      sorter: (a, b) => {
        const timeA = a.created_time ? new Date(a.created_time).getTime() : 0;
        const timeB = b.created_time ? new Date(b.created_time).getTime() : 0;
        return timeA - timeB;
      },
      render: (text) => renderDateTime(text),
    },
    {
      title: '修改人',
      dataIndex: 'updated_by',
      width: 100,
      render: (text) => text || '-',
    },
    {
      title: '修改时间',
      dataIndex: 'updated_time',
      width: 180,
      sorter: (a, b) => {
        const timeA = a.updated_time ? new Date(a.updated_time).getTime() : 0;
        const timeB = b.updated_time ? new Date(b.updated_time).getTime() : 0;
        return timeA - timeB;
      },
      render: (text) => renderDateTime(text),
    },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, record) => [
        <Button
          key="view"
          type="link"
          onClick={() => handleViewValue(record.config_key)}
        >
          查看
        </Button>,
        <Button
          key="edit"
          type="link"
          onClick={async () => {
            try {
              const response = await getConfig(record.config_key);
              setEditingConfig({
                ...record,
                config_value: response.config_value,
              });
              setEditModalVisible(true);
            } catch (error: any) {
              message.error(error?.response?.data?.detail || '获取配置失败');
            }
          }}
        >
          编辑
        </Button>,
        <Popconfirm
          key="delete"
          title="确定要删除这个配置吗？"
          onConfirm={() => handleDelete(record.config_key)}
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
      <ProTable<ZQuant.ConfigItem>
        headerTitle="配置管理"
        actionRef={actionRef}
        columns={columns}
        request={async (params) => {
          const response = await getAllConfigs(showSensitiveValues);
          return {
            data: response.items,
            success: true,
            total: response.total,
          };
        }}
        rowKey="config_key"
        search={false}
        toolBarRender={() => [
          <Button
            key="toggle"
            onClick={() => {
              setShowSensitiveValues(!showSensitiveValues);
              actionRef.current?.reload();
            }}
          >
            {showSensitiveValues ? '隐藏敏感值' : '显示敏感值'}
          </Button>,
          <Button
            key="create"
            type="primary"
            onClick={() => {
              setCreateModalVisible(true);
            }}
          >
            创建配置
          </Button>,
        ]}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
        }}
      />

      {/* 创建配置Modal */}
      <Modal
        title="创建配置"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
        width={600}
      >
        <ProForm
          onFinish={handleCreate}
          initialValues={{}}
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
            name="config_key"
            label="配置键"
            placeholder="请输入配置键，如：tushare_token"
            rules={[{ required: true, message: '请输入配置键' }]}
            width="xl"
          />
          <ProFormTextArea
            name="config_value"
            label="配置值"
            placeholder="请输入配置值（会自动加密存储）"
            rules={[{ required: true, message: '请输入配置值' }]}
            fieldProps={{
              rows: 4,
            }}
            width="xl"
          />
          <ProFormTextArea
            name="comment"
            label="配置说明"
            placeholder="请输入配置说明（可选）"
            fieldProps={{
              rows: 2,
            }}
            width="xl"
          />
        </ProForm>
      </Modal>

      {/* 查看配置Modal */}
      <Modal
        title={`配置值：${viewingConfig?.config_key || ''}`}
        open={viewModalVisible}
        onCancel={() => {
          setViewModalVisible(false);
          setViewingConfig(null);
        }}
        footer={[
          <Button key="close" onClick={() => {
            setViewModalVisible(false);
            setViewingConfig(null);
          }}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {viewingConfig && (() => {
          const configKey = viewingConfig.config_key || '';
          const isSensitive = isSensitiveKey(configKey);
          const isVisible = visibleModalConfigKeys[configKey];
          const configValueStr = convertConfigValueToString(viewingConfig.config_value);
          const displayValue = isSensitive && !isVisible 
            ? maskSensitiveValue(configValueStr) 
            : configValueStr;
          const Icon = isVisible ? EyeOutlined : EyeInvisibleOutlined;

          return (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                <strong style={{ marginRight: 8 }}>配置值：</strong>
                {isSensitive && (
                  <Icon
                    style={{
                      cursor: 'pointer',
                      color: '#1890ff',
                      fontSize: '16px',
                    }}
                    onClick={() => {
                      toggleModalConfigVisibility(configKey);
                    }}
                  />
                )}
              </div>
              <Input.TextArea
                value={displayValue}
                readOnly
                autoSize={{ minRows: 3, maxRows: 10 }}
                style={{ 
                  fontFamily: 'monospace',
                  color: isSensitive && !isVisible ? '#999' : 'inherit',
                }}
              />
              {viewingConfig.comment && (
                <p style={{ marginTop: 12 }}>
                  <strong>说明：</strong>{viewingConfig.comment}
                </p>
              )}
            </div>
          );
        })()}
      </Modal>

      {/* 编辑配置Modal */}
      <Modal
        title="编辑配置"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          setEditingConfig(null);
        }}
        footer={null}
        width={600}
      >
        <ProForm
          formRef={editFormRef}
          onFinish={handleEdit}
          initialValues={{
            config_key: editingConfig?.config_key,
            config_value: editingConfig && isSensitiveKey(editingConfig.config_key || '') && !visibleModalConfigKeys[editingConfig.config_key || '']
              ? maskSensitiveValue(convertConfigValueToString(editingConfig.config_value))
              : convertConfigValueToString(editingConfig?.config_value),
            comment: editingConfig?.comment,
          }}
          submitter={{
            render: (props, doms) => {
              return [
                <Button
                  key="cancel"
                  onClick={() => {
                    setEditModalVisible(false);
                    setEditingConfig(null);
                  }}
                >
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
            name="config_key"
            label="配置键"
            disabled
            width="xl"
          />
          {editingConfig && (() => {
            const configKey = editingConfig.config_key || '';
            const isSensitive = isSensitiveKey(configKey);
            const isVisible = visibleModalConfigKeys[configKey];
            const Icon = isVisible ? EyeOutlined : EyeInvisibleOutlined;
            const currentValueStr = convertConfigValueToString(editingConfig.config_value);
            const displayValue = isSensitive && !isVisible 
              ? maskSensitiveValue(currentValueStr) 
              : currentValueStr;

            return (
              <ProForm.Item
                name="config_value"
                label={
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <span>配置值</span>
                    {isSensitive && (
                      <Icon
                        style={{
                          cursor: 'pointer',
                          color: '#1890ff',
                          fontSize: '16px',
                          marginLeft: 8,
                        }}
                        onClick={() => {
                          toggleModalConfigVisibility(configKey);
                          // 更新表单值
                          if (editFormRef.current) {
                            const form = editFormRef.current;
                            const realValueStr = convertConfigValueToString(editingConfig.config_value);
                            form.setFieldsValue({ 
                              config_value: isVisible ? maskSensitiveValue(realValueStr) : realValueStr 
                            });
                          }
                        }}
                      />
                    )}
                  </div>
                }
                rules={[{ required: true, message: '请输入配置值' }]}
              >
                <Input.TextArea
                  placeholder="请输入配置值（会自动加密存储）"
                  rows={4}
                  style={{
                    fontFamily: 'monospace',
                    color: isSensitive && !isVisible ? '#999' : 'inherit',
                  }}
                  readOnly={isSensitive && !isVisible}
                />
              </ProForm.Item>
            );
          })()}
          <ProFormTextArea
            name="comment"
            label="配置说明"
            placeholder="请输入配置说明（可选）"
            fieldProps={{
              rows: 2,
            }}
            width="xl"
          />
        </ProForm>
      </Modal>
    </div>
  );
};

export default Config;

