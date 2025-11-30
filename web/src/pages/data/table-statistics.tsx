import React, { useState } from 'react';
import { Card, Button, Tag, message } from 'antd';
import { ProForm, ProFormText, ProFormDatePicker, ProFormDateRangePicker } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import dayjs from 'dayjs';

import { getTableStatistics } from '@/services/zquant/data';
import { renderDateTime } from '@/components/DataTable';

const TableStatistics: React.FC = () => {
  const [dataSource, setDataSource] = useState<ZQuant.TableStatisticsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);

  const columns: ProColumns<ZQuant.TableStatisticsItem>[] = [
    {
      title: '统计日期',
      dataIndex: 'stat_date',
      width: 120,
      sorter: true,
      render: (text) => text || '-',
    },
    {
      title: '表名',
      dataIndex: 'table_name',
      width: 200,
      sorter: true,
      render: (text) => text || '-',
    },
    {
      title: '是否分表',
      dataIndex: 'is_split_table',
      width: 100,
      render: (text) => text ? <Tag color="blue">是</Tag> : <Tag>否</Tag>,
    },
    {
      title: '分表个数',
      dataIndex: 'split_count',
      width: 100,
      sorter: true,
      render: (text) => {
        if (text == null || text === undefined) return '-';
        const num = Number(text);
        if (isNaN(num)) return text;
        // 如果是整数，不显示小数点
        return num % 1 === 0 ? num.toLocaleString() : num.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
      },
    },
    {
      title: '总记录数',
      dataIndex: 'total_records',
      width: 120,
      sorter: true,
      render: (text) => {
        if (text == null || text === undefined) return '-';
        const num = Number(text);
        if (isNaN(num)) return text;
        // 如果是整数，不显示小数点
        return num % 1 === 0 ? num.toLocaleString() : num.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
      },
    },
    {
      title: '日记录数',
      dataIndex: 'daily_records',
      width: 120,
      sorter: true,
      render: (text) => {
        if (text == null || text === undefined) return '-';
        const num = Number(text);
        if (isNaN(num)) return text;
        // 如果是整数，不显示小数点
        return num % 1 === 0 ? num.toLocaleString() : num.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
      },
    },
    {
      title: '日新增记录数',
      dataIndex: 'daily_insert_count',
      width: 130,
      sorter: true,
      render: (text) => {
        if (text == null || text === undefined) return '-';
        const num = Number(text);
        if (isNaN(num)) return text;
        // 如果是整数，不显示小数点
        const formatted = num % 1 === 0 ? num.toLocaleString() : num.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
        return <span style={{ color: num > 0 ? '#52c41a' : undefined }}>{formatted}</span>;
      },
    },
    {
      title: '日更新记录数',
      dataIndex: 'daily_update_count',
      width: 130,
      sorter: true,
      render: (text) => {
        if (text == null || text === undefined) return '-';
        const num = Number(text);
        if (isNaN(num)) return text;
        // 如果是整数，不显示小数点
        const formatted = num % 1 === 0 ? num.toLocaleString() : num.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
        return <span style={{ color: num > 0 ? '#1890ff' : undefined }}>{formatted}</span>;
      },
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
      sorter: true,
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
      sorter: true,
      render: (text) => renderDateTime(text),
    },
  ];

  const handleQuery = async (values: any) => {
    setLoading(true);
    try {
      const params: ZQuant.TableStatisticsRequest = {
        stat_date: values.stat_date ? dayjs(values.stat_date).format('YYYY-MM-DD') : undefined,
        table_name: values.table_name,
        start_date: values.dateRange ? dayjs(values.dateRange[0]).format('YYYY-MM-DD') : undefined,
        end_date: values.dateRange ? dayjs(values.dateRange[1]).format('YYYY-MM-DD') : undefined,
        skip: 0,
        limit: 1000,
      };
      
      const response = await getTableStatistics(params);
      setDataSource(response.items);
      setTotal(response.total);
      message.success(`查询成功，共${response.total}条记录`);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '查询失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <ProForm
        layout="inline"
        onFinish={handleQuery}
        initialValues={{
          dateRange: [dayjs().subtract(7, 'day'), dayjs()],
        }}
        submitter={{
          render: (props, doms) => {
            return [
              <Button type="primary" key="submit" onClick={() => props.form?.submit?.()}>
                查询
              </Button>,
            ];
          },
        }}
      >
        <ProFormText
          name="table_name"
          label="表名"
          placeholder="请输入表名"
          width="sm"
        />
        <ProFormDatePicker
          name="stat_date"
          label="统计日期"
          placeholder="请选择统计日期"
        />
        <ProFormDateRangePicker
          name="dateRange"
          label="日期范围"
        />
      </ProForm>

      <ProTable<ZQuant.TableStatisticsItem>
        columns={columns}
        dataSource={dataSource}
        loading={loading}
        search={false}
        scroll={{ x: 2000 }}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
          total: total,
        }}
        style={{ marginTop: 16 }}
      />
    </Card>
  );
};

export default TableStatistics;

