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

import React, { useState, useEffect, useRef } from 'react';
import { Card, Button, Tag, message, Modal, Space } from 'antd';
import { ProForm, ProFormText, ProFormDatePicker } from '@ant-design/pro-components';
import ProFormSelectWithAll from '@/components/ProFormSelectWithAll';
import type { ProFormInstance } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { useLocation } from '@umijs/max';
import dayjs from 'dayjs';
import { formatDuration } from '@/utils/format';

import { getDataOperationLogs } from '@/services/zquant/data';
import { usePageCache } from '@/hooks/usePageCache';
import { renderDateTime } from '@/components/DataTable';

const SyncLogs: React.FC = () => {
  const location = useLocation();
  const formRef = useRef<ProFormInstance>();
  const pageCache = usePageCache();

  const [dataSource, setDataSource] = useState<ZQuant.DataOperationLogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [errorDetailVisible, setErrorDetailVisible] = useState(false);
  const [selectedError, setSelectedError] = useState<string>('');

  // 从缓存恢复状态
  useEffect(() => {
    const cachedFormValues = pageCache.getFormValues();
    if (cachedFormValues && formRef.current) {
      formRef.current.setFieldsValue(cachedFormValues);
    }

    const cachedDataSource = pageCache.getDataSource()?.dataSource;
    const cachedTotal = pageCache.get()?.total;
    if (cachedDataSource && cachedDataSource.length > 0) {
      setDataSource(cachedDataSource);
      if (cachedTotal !== undefined) {
        setTotal(cachedTotal);
      }
    }

    const cachedErrorDetailVisible = pageCache.getModalState('errorDetailModal');
    if (cachedErrorDetailVisible !== undefined) {
      setErrorDetailVisible(cachedErrorDetailVisible);
    }

    const cachedSelectedError = pageCache.get()?.selectedError;
    if (cachedSelectedError) {
      setSelectedError(cachedSelectedError);
    }
  }, [pageCache, location.pathname]);

  const handleQuery = async (values: any) => {
    setLoading(true);
    try {
      // 保存表单值到缓存
      pageCache.saveFormValues(values);

      const request: ZQuant.DataOperationLogRequest = {
        table_name: values.table_name,
        operation_type: values.operation_type,
        operation_result: values.operation_result,
        start_date: values.start_date ? dayjs(values.start_date).format('YYYY-MM-DD') : undefined,
        end_date: values.end_date ? dayjs(values.end_date).format('YYYY-MM-DD') : undefined,
        skip: 0,
        limit: 1000,
      };

      const response = await getDataOperationLogs(request);
      setDataSource(response.items);
      setTotal(response.total);

      // 保存数据到缓存
      pageCache.saveDataSource(response.items);
      pageCache.update({ total: response.total });

      message.success(`查询成功，共${response.total}条记录`);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '查询失败');
    } finally {
      setLoading(false);
    }
  };

  const handleViewError = (errorMessage: string) => {
    setSelectedError(errorMessage || '无错误信息');
    setErrorDetailVisible(true);
    // 保存到缓存
    pageCache.saveModalState('errorDetailModal', true);
    pageCache.update({ selectedError: errorMessage || '无错误信息' });
  };

  const getOperationTypeTag = (type?: string) => {
    const typeMap: Record<string, { color: string; text: string }> = {
      insert: { color: 'success', text: '插入' },
      update: { color: 'processing', text: '更新' },
      delete: { color: 'error', text: '删除' },
      sync: { color: 'default', text: '同步' },
    };
    const config = typeMap[type || ''] || { color: 'default', text: type || '-' };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const getResultTag = (result?: string) => {
    const resultMap: Record<string, { color: string; text: string }> = {
      success: { color: 'success', text: '成功' },
      failed: { color: 'error', text: '失败' },
      partial_success: { color: 'warning', text: '部分成功' },
    };
    const config = resultMap[result || ''] || { color: 'default', text: result || '-' };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const columns: ProColumns<ZQuant.DataOperationLogItem>[] = [
    {
      title: '序号',
      dataIndex: 'index',
      valueType: 'index',
      width: 60,
      fixed: 'left',
    },
    {
      title: '日志ID',
      dataIndex: 'id',
      width: 100,
      sorter: true,
      fixed: 'left',
    },
    {
      title: '数据源',
      dataIndex: 'data_source',
      width: 100,
      sorter: true,
      render: (text: any) => text || '-',
    },
    {
      title: 'API接口',
      dataIndex: 'api_interface',
      width: 150,
      sorter: true,
      render: (text: any) => text || '-',
    },
    {
      title: '接口数据量',
      dataIndex: 'api_data_count',
      width: 120,
      sorter: true,
      align: 'right',
      render: (text: any) => text !== null && text !== undefined ? (Number(text)).toLocaleString() : '-',
    },
    {
      title: '数据表名',
      dataIndex: 'table_name',
      width: 220,
      sorter: true,
      ellipsis: true,
      render: (text: any) => text || '-',
    },
    {
      title: '操作类型',
      dataIndex: 'operation_type',
      width: 100,
      sorter: true,
      render: (_: any, record: ZQuant.DataOperationLogItem) => getOperationTypeTag(record.operation_type),
    },
    {
      title: '插入记录数',
      dataIndex: 'insert_count',
      width: 120,
      sorter: true,
      align: 'right',
      render: (text: any) => text !== null && text !== undefined ? (Number(text)).toLocaleString() : '-',
    },
    {
      title: '更新记录数',
      dataIndex: 'update_count',
      width: 120,
      sorter: true,
      align: 'right',
      render: (text: any) => text !== null && text !== undefined ? (Number(text)).toLocaleString() : '-',
    },
    {
      title: '删除记录数',
      dataIndex: 'delete_count',
      width: 120,
      sorter: true,
      align: 'right',
      render: (text: any) => text !== null && text !== undefined ? (Number(text)).toLocaleString() : '-',
    },
    {
      title: '操作结果',
      dataIndex: 'operation_result',
      width: 100,
      sorter: true,
      render: (_: any, record: ZQuant.DataOperationLogItem) => getResultTag(record.operation_result),
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      width: 180,
      sorter: true,
      render: (text: any) => renderDateTime(text),
    },
    {
      title: '结束时间',
      dataIndex: 'end_time',
      width: 180,
      sorter: true,
      render: (text: any) => renderDateTime(text),
    },
    {
      title: '执行耗时',
      dataIndex: 'duration_seconds',
      width: 120,
      sorter: true,
      align: 'right',
      render: (text: any) => formatDuration(text),
    },
    {
      title: '创建人',
      dataIndex: 'created_by',
      width: 120,
      sorter: true,
      render: (text: any) => text || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_time',
      width: 180,
      sorter: true,
      render: (text: any) => renderDateTime(text),
    },
    {
      title: '修改人',
      dataIndex: 'updated_by',
      width: 120,
      sorter: true,
      render: (text: any) => text || '-',
    },
    {
      title: '修改时间',
      dataIndex: 'updated_time',
      width: 180,
      sorter: true,
      render: (text: any) => renderDateTime(text),
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      width: 150,
      ellipsis: true,
      fixed: 'right',
      render: (text: any) => {
        if (!text) return '-';
        return (
          <Button
            type="link"
            size="small"
            onClick={() => handleViewError(text)}
            style={{ padding: 0 }}
          >
            查看详情
          </Button>
        );
      },
    },
  ];

  return (
    <Card bordered={false}>
      <ProForm
        formRef={formRef}
        layout="inline"
        onFinish={handleQuery}
        onValuesChange={() => {
          if (formRef.current) {
            const formValues = formRef.current.getFieldsValue();
            pageCache.saveFormValues(formValues);
          }
        }}
        initialValues={{
          start_date: dayjs().subtract(1, 'month'),
          end_date: dayjs(),
        }}
        submitter={{
          render: (props) => {
            return (
              <Space>
                <Button type="primary" key="submit" onClick={() => props.form?.submit?.()}>
                  查询
                </Button>
                <Button key="reset" onClick={() => {
                  props.form?.resetFields();
                  formRef.current?.submit();
                }}>
                  重置
                </Button>
              </Space>
            );
          },
        }}
      >
        <ProFormText
          name="table_name"
          label="数据表名"
          placeholder="代码或表名"
          width="sm"
        />
        <ProFormSelectWithAll
          name="operation_type"
          label="操作类型"
          options={[
            { label: '插入', value: 'insert' },
            { label: '更新', value: 'update' },
            { label: '删除', value: 'delete' },
            { label: '同步', value: 'sync' },
          ]}
          allValue=""
          width="xs"
        />
        <ProFormSelectWithAll
          name="operation_result"
          label="操作结果"
          options={[
            { label: '成功', value: 'success' },
            { label: '失败', value: 'failed' },
            { label: '部分成功', value: 'partial_success' },
          ]}
          allValue=""
          width="xs"
        />
        <ProFormDatePicker
          name="start_date"
          label="开始日期"
        />
        <ProFormDatePicker
          name="end_date"
          label="结束日期"
        />
      </ProForm>

      <ProTable<ZQuant.DataOperationLogItem>
        columns={columns}
        dataSource={dataSource}
        loading={loading}
        search={false}
        scroll={{ x: 2500, y: 'calc(100vh - 350px)' }}
        pagination={{
          pageSize: 50,
          showSizeChanger: true,
          total: total,
          showTotal: (t) => `共 ${t} 条记录`,
        }}
        size="small"
        style={{ marginTop: 16 }}
        rowKey="id"
      />

      <Modal
        title="错误信息详情"
        open={errorDetailVisible}
        onCancel={() => {
          setErrorDetailVisible(false);
          pageCache.saveModalState('errorDetailModal', false);
        }}
        footer={[
          <Button key="close" onClick={() => setErrorDetailVisible(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: '500px', overflow: 'auto', backgroundColor: '#f5f5f5', padding: 16, borderRadius: 4 }}>
          {selectedError}
        </pre>
      </Modal>
    </Card>
  );
};

export default SyncLogs;
