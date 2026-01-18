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

import {
  ProForm,
  ProFormCheckbox,
  ProFormDatePicker,
  ProFormInstance,
  ProFormText,
  ProTable,
} from '@ant-design/pro-components';
import ProFormSelectWithAll from '@/components/ProFormSelectWithAll';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import {
  Button,
  Card,
  Checkbox,
  Col,
  Drawer,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import { SettingOutlined } from '@ant-design/icons';
import React, { useEffect, useRef, useState } from 'react';
import dayjs from 'dayjs';
import {
  createStrategy,
  deleteStrategy,
  getAvailableColumns,
  getStrategies,
  getStrategyById,
  queryFilter,
  updateStrategy,
} from '@/services/zquant/stockFilter';

const { Text } = Typography;
const { Option } = Select;

const UNIT_FACTORS: Record<string, number> = {
  total_mv: 10000, // 万元 -> 亿
  circ_mv: 10000, // 万元 -> 亿
  amount: 100000, // 千元 -> 亿
  total_share: 10000, // 万股 -> 亿股
  float_share: 10000, // 万股 -> 亿股
  free_share: 10000, // 万股 -> 亿股
};

const scaleFilterValue = (field: string, value: any, toDb: boolean = true): any => {
  const factor = UNIT_FACTORS[field];
  if (!factor || value === '' || value === null || value === undefined) return value;

  if (Array.isArray(value)) {
    return value.map(v => scaleFilterValue(field, v, toDb));
  }

  const numValue = Number(value);
  if (isNaN(numValue)) return value;

  return toDb ? numValue * factor : numValue / factor;
};

// 移除 scaleFilterConditions，因为后端现在处理单位换算
// 仅保留 UNIT_FACTORS 用于前端显示显示（Render）
const StockFilter: React.FC = () => {
  const actionRef = useRef<ActionType>(null);
  const searchFormRef = useRef<ProFormInstance>(null);
  const strategyFormRef = useRef<ProFormInstance>(null);

  const [strategies, setStrategies] = useState<ZQuant.StockFilterStrategyResponse[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState<number | undefined>(undefined);
  const [availableColumns, setAvailableColumns] = useState<ZQuant.AvailableColumnsResponse | null>(null);
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [filterConditions, setFilterConditions] = useState<ZQuant.FilterConditionGroup>({
    logic: 'AND',
    conditions: [],
  });
  const [sortConfig, setSortConfig] = useState<ZQuant.SortConfig[]>([]);
  const [queryParams, setQueryParams] = useState<any>({});
  const [strategyModalVisible, setStrategyModalVisible] = useState(false);
  const [columnDrawerVisible, setColumnDrawerVisible] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState<ZQuant.StockFilterStrategyResponse | undefined>(undefined);

  // 1. 初始化默认列
  useEffect(() => {
    const defaultCols = [
      'ts_code',
      'name',
      'industry',
      'pe',
      'pb',
      'pct_chg',
      'turnover_rate',
      'amount',
      'total_mv',
      'circ_mv',
    ];
    setSelectedColumns(defaultCols);
  }, []);

  // 2. 加载可用列并初始化查询参数（仅当未加载策略时）
  useEffect(() => {
    const loadColumns = async () => {
      try {
        const response = await getAvailableColumns();
        setAvailableColumns(response);

        setQueryParams((prev: any) => {
          // 如果用户已经加载了策略或点击了查询，不要覆盖
          if (prev.trade_date || prev._manual) return prev;

          return {
            trade_date: dayjs().format('YYYY-MM-DD'),
            _manual: false, // 标记为自动初始化加载，request 可以据此决定是否渲染全量数据
          };
        });
      } catch (error: any) {
        message.error('加载可用列失败');
      }
    };
    loadColumns();
  }, []);

  // 3. 构建表格列（使用 useMemo 稳定引用）
  const columns = React.useMemo(() => {
    if (!availableColumns) return [];

    const result: ProColumns<Record<string, any>>[] = [
      {
        title: '交易日期',
        dataIndex: 'trade_date',
        key: 'trade_date', // 添加 key
        width: 100,
        fixed: 'left',
        sorter: true,
        render: (text) => text || queryParams.trade_date, // 如果数据中没有，显示查询参数中的日期
      }
    ];

    const allColumns: ZQuant.ColumnInfo[] = [
      ...availableColumns.basic,
      ...availableColumns.daily_basic,
      ...availableColumns.daily,
      ...(availableColumns.factor || []),
      ...(availableColumns.audit || []),
    ];

    allColumns.forEach((colInfo) => {
      // 跳过交易日期，因为已经手动添加了
      if (colInfo.field === 'trade_date') return;

      const isSelected = selectedColumns.includes(colInfo.field);
      
      const column: ProColumns<Record<string, any>> = {
        title: UNIT_FACTORS[colInfo.field] ? `${colInfo.label}(亿)` : colInfo.label,
        dataIndex: colInfo.field,
        key: colInfo.field,
        sorter: colInfo.type === 'number',
        hideInTable: !isSelected, // 关键点：不再过滤 result 数组，而是用 hideInTable 控制
        render: (text: any) => {
          if (text === null || text === undefined) return '-';
          let displayValue = text;
          const factor = UNIT_FACTORS[colInfo.field];
          if (factor && typeof text === 'number') {
            displayValue = text / factor;
          }

          if (colInfo.type === 'number') {
            return typeof displayValue === 'number'
              ? displayValue.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
              : displayValue;
          }
          return displayValue;
        },
      };
      result.push(column);
    });

    return result;
  }, [availableColumns, selectedColumns, queryParams.trade_date]);

  // 加载策略列表
  useEffect(() => {
    const loadStrategies = async () => {
      try {
        const response = await getStrategies();
        setStrategies(response.items);
      } catch (error: any) {
        message.error('加载策略列表失败');
      }
    };
    loadStrategies();
  }, []);

  // 加载策略
  const handleLoadStrategy = async (strategyId: number) => {
    try {
      const strategy = await getStrategyById(strategyId);
      setSelectedStrategyId(strategyId);

      let newFilterConditions: ZQuant.FilterConditionGroup = { logic: 'AND', conditions: [] };
      if (strategy.filter_conditions) {
        if (Array.isArray(strategy.filter_conditions)) {
          newFilterConditions = {
            logic: 'AND',
            conditions: strategy.filter_conditions,
          };
        } else {
          newFilterConditions = strategy.filter_conditions;
        }
      }
      setFilterConditions(newFilterConditions);

      let newSelectedColumns = selectedColumns;
      if (strategy.selected_columns) {
        newSelectedColumns = strategy.selected_columns;
        setSelectedColumns(newSelectedColumns);
      }

      let newSortConfig = sortConfig;
      if (strategy.sort_config) {
        newSortConfig = strategy.sort_config;
        setSortConfig(newSortConfig);
      }

      // 自动触发查询
      const formValues = searchFormRef.current?.getFieldsValue();
      setQueryParams({
        trade_date: formValues?.trade_date ? dayjs(formValues.trade_date).format('YYYY-MM-DD') : dayjs().format('YYYY-MM-DD'),
        filterConditions: newFilterConditions,
        selectedColumns: newSelectedColumns,
        sortConfig: newSortConfig,
        _manual: true,
        _t: Date.now(),
      });

      message.success('策略加载成功');
    } catch (error: any) {
      message.error('加载策略失败');
    }
  };

  // 保存策略
  const handleSaveStrategy = async (values: any) => {
    try {
      const strategyData: ZQuant.StockFilterStrategyCreate = {
        name: values.name,
        description: values.description,
        filter_conditions:
          filterConditions.conditions.length > 0 ? filterConditions : undefined,
        selected_columns: selectedColumns.length > 0 ? selectedColumns : undefined,
        sort_config: sortConfig.length > 0 ? sortConfig : undefined,
      };

      if (editingStrategy) {
        await updateStrategy(editingStrategy.id, strategyData);
        message.success('更新策略成功');
      } else {
        await createStrategy(strategyData);
        message.success('保存策略成功');
      }

      setStrategyModalVisible(false);
      setEditingStrategy(undefined);
      strategyFormRef.current?.resetFields();

      // 刷新策略列表
      const response = await getStrategies();
      setStrategies(response.items);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '保存策略失败');
    }
  };

  // 删除策略
  const handleDeleteStrategy = async (strategyId: number) => {
    try {
      await deleteStrategy(strategyId);
      message.success('删除策略成功');
      const response = await getStrategies();
      setStrategies(response.items);
      if (selectedStrategyId === strategyId) {
        setSelectedStrategyId(undefined);
        setFilterConditions({ logic: 'AND', conditions: [] });
        setSortConfig([]);
      }
    } catch (error: any) {
      message.error('删除策略失败');
    }
  };

  // 添加筛选条件
  const handleAddFilter = () => {
    setFilterConditions({
      ...filterConditions,
      conditions: [
        ...filterConditions.conditions,
        { field: '', operator: '=', value: '', not: false },
      ],
    });
  };

  // 添加条件组
  const handleAddGroup = () => {
    setFilterConditions({
      ...filterConditions,
      conditions: [
        ...filterConditions.conditions,
        { logic: 'AND', conditions: [], not: false },
      ],
    });
  };

  // 删除筛选条件或条件组
  const handleRemoveCondition = (index: number) => {
    const newConditions = filterConditions.conditions.filter((_, i) => i !== index);
    setFilterConditions({
      ...filterConditions,
      conditions: newConditions,
    });
  };

  // 更新筛选条件
  const handleUpdateCondition = (index: number, updates: Partial<ZQuant.ColumnFilter>) => {
    const newConditions = [...filterConditions.conditions];
    if (newConditions[index] && 'field' in newConditions[index]) {
      newConditions[index] = { ...newConditions[index], ...updates } as ZQuant.ColumnFilter;
      setFilterConditions({
        ...filterConditions,
        conditions: newConditions,
      });
    }
  };

  // 更新条件组
  const handleUpdateGroup = (index: number, updates: Partial<ZQuant.FilterConditionGroup>) => {
    const newConditions = [...filterConditions.conditions];
    if (newConditions[index] && 'logic' in newConditions[index]) {
      newConditions[index] = { ...newConditions[index], ...updates } as ZQuant.FilterConditionGroup;
      setFilterConditions({
        ...filterConditions,
        conditions: newConditions,
      });
    }
  };

  // 更新顶层逻辑运算符
  const handleUpdateLogic = (logic: 'AND' | 'OR') => {
    setFilterConditions({
      ...filterConditions,
      logic,
    });
  };


  // 查询数据
  const handleQuery = async () => {
    const values = searchFormRef.current?.getFieldsValue();
    if (!values?.trade_date) {
      message.warning('请选择交易日期');
      return;
    }

    setQueryParams({
      trade_date: dayjs(values.trade_date).format('YYYY-MM-DD'),
      filterConditions,
      selectedColumns,
      // 保持当前的排序配置
      sortConfig,
      _manual: true,
      _t: Date.now(),
    });
  };

  return (
    <div>
      <Card>
        <ProForm
          formRef={searchFormRef}
          layout="inline"
          onFinish={handleQuery}
          submitter={{
            render: (props, doms) => {
              return (
                <Space>
                  <Button type="primary" key="submit" onClick={() => props.form?.submit?.()}>
                    查询
                  </Button>
                  <Button
                    key="save-strategy"
                    onClick={() => {
                      setEditingStrategy(undefined);
                      strategyFormRef.current?.resetFields();
                      setStrategyModalVisible(true);
                    }}
                  >
                    保存策略
                  </Button>
                  <Button key="column-settings" onClick={() => setColumnDrawerVisible(true)}>
                    列设置
                  </Button>
                </Space>
              );
            },
          }}
        >
          <ProFormDatePicker
            name="trade_date"
            label="交易日期"
            width="sm"
            initialValue={dayjs()}
            rules={[{ required: true, message: '请选择交易日期' }]}
          />
          <ProFormSelectWithAll
            name="strategy"
            label="策略模板"
            width="sm"
            options={strategies.map((s) => ({ label: s.name, value: s.id }))}
            allValue=""
            placeholder="选择策略模板"
            onChange={(value: any) => {
              if (value) {
                handleLoadStrategy(value as number);
              } else {
                setSelectedStrategyId(undefined);
                setFilterConditions({ logic: 'AND', conditions: [] });
                setSortConfig([]);
              }
            }}
          />
        </ProForm>

        {/* 筛选条件配置 */}
        <Card size="small" style={{ marginTop: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text strong>筛选条件：</Text>
              <Select
                value={filterConditions.logic}
                onChange={handleUpdateLogic}
                style={{ width: 80, marginLeft: 8 }}
              >
                <Option value="AND">AND</Option>
                <Option value="OR">OR</Option>
              </Select>
              <Button
                type="link"
                size="small"
                onClick={handleAddFilter}
                style={{ marginLeft: 8 }}
              >
                添加条件
              </Button>
              <Button
                type="link"
                size="small"
                onClick={handleAddGroup}
              >
                添加条件组
              </Button>
            </div>
            {filterConditions.conditions.map((condition, index) => {
              // 判断是条件还是条件组
              if ('logic' in condition) {
                // 条件组
                const group = condition as ZQuant.FilterConditionGroup;
                return (
                  <Card
                    key={index}
                    size="small"
                    style={{ marginLeft: 20, backgroundColor: '#f5f5f5' }}
                  >
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div>
                        <Select
                          value={group.logic}
                          onChange={(value) =>
                            handleUpdateGroup(index, { logic: value as 'AND' | 'OR' })
                          }
                          style={{ width: 80 }}
                        >
                          <Option value="AND">AND</Option>
                          <Option value="OR">OR</Option>
                        </Select>
                        <Checkbox
                          checked={group.not}
                          onChange={(e) =>
                            handleUpdateGroup(index, { not: e.target.checked })
                          }
                          style={{ marginLeft: 8 }}
                        >
                          非(NOT)
                        </Checkbox>
                        <Button
                          danger
                          size="small"
                          onClick={() => handleRemoveCondition(index)}
                          style={{ marginLeft: 8 }}
                        >
                          删除组
                        </Button>
                      </div>
                      {group.conditions.map((subCondition, subIndex) => {
                        if ('field' in subCondition) {
                          const filter = subCondition as ZQuant.ColumnFilter;
                          return (
                            <Row key={subIndex} gutter={8} align="middle">
                              <Col span={6}>
                                <Select
                                  placeholder="选择字段"
                                  value={filter.field}
                                  onChange={(value) => {
                                    const newGroup = { ...group };
                                    newGroup.conditions[subIndex] = {
                                      ...filter,
                                      field: value,
                                    };
                                    handleUpdateGroup(index, newGroup);
                                  }}
                                  style={{ width: '100%' }}
                                >
                                  {availableColumns &&
                                    [
                                      ...availableColumns.basic,
                                      ...availableColumns.daily_basic,
                                      ...availableColumns.daily,
                                      ...(availableColumns.factor || []),
                                      ...(availableColumns.audit || []),
                                    ].map((col) => (
                                      <Option key={col.field} value={col.field}>
                                        {UNIT_FACTORS[col.field] ? `${col.label}(亿)` : col.label}
                                      </Option>
                                    ))}
                                </Select>
                              </Col>
                              <Col span={4}>
                                <Select
                                  placeholder="操作符"
                                  value={filter.operator}
                                  onChange={(value) => {
                                    const newGroup = { ...group };
                                    newGroup.conditions[subIndex] = {
                                      ...filter,
                                      operator: value,
                                    };
                                    handleUpdateGroup(index, newGroup);
                                  }}
                                  style={{ width: '100%' }}
                                >
                                  <Option value="=">=</Option>
                                  <Option value="!=">!=</Option>
                                  <Option value=">">&gt;</Option>
                                  <Option value="<">&lt;</Option>
                                  <Option value=">=">&gt;=</Option>
                                  <Option value="<=">&lt;=</Option>
                                  <Option value="LIKE">包含</Option>
                                </Select>
                              </Col>
                              <Col span={6}>
                                <Input
                                  placeholder={UNIT_FACTORS[filter.field] ? "值(亿)" : "值"}
                                  value={filter.value}
                                  onChange={(e) => {
                                    const newGroup = { ...group };
                                    newGroup.conditions[subIndex] = {
                                      ...filter,
                                      value: e.target.value,
                                    };
                                    handleUpdateGroup(index, newGroup);
                                  }}
                                />
                              </Col>
                              <Col span={4}>
                                <Checkbox
                                  checked={filter.not}
                                  onChange={(e) => {
                                    const newGroup = { ...group };
                                    newGroup.conditions[subIndex] = {
                                      ...filter,
                                      not: e.target.checked,
                                    };
                                    handleUpdateGroup(index, newGroup);
                                  }}
                                >
                                  非
                                </Checkbox>
                              </Col>
                              <Col span={4}>
                                <Button
                                  danger
                                  size="small"
                                  onClick={() => {
                                    const newGroup = { ...group };
                                    newGroup.conditions = newGroup.conditions.filter(
                                      (_, i) => i !== subIndex
                                    );
                                    handleUpdateGroup(index, newGroup);
                                  }}
                                >
                                  删除
                                </Button>
                              </Col>
                            </Row>
                          );
                        }
                        return null;
                      })}
                      <Button
                        type="dashed"
                        size="small"
                        onClick={() => {
                          const newGroup = { ...group };
                          newGroup.conditions = [
                            ...newGroup.conditions,
                            { field: '', operator: '=', value: '', not: false },
                          ];
                          handleUpdateGroup(index, newGroup);
                        }}
                      >
                        添加条件
                      </Button>
                    </Space>
                  </Card>
                );
              } else {
                // 单个条件
                const filter = condition as ZQuant.ColumnFilter;
                return (
                  <Row key={index} gutter={8} align="middle">
                    <Col span={6}>
                      <Select
                        placeholder="选择字段"
                        value={filter.field}
                        onChange={(value) =>
                          handleUpdateCondition(index, { field: value })
                        }
                        style={{ width: '100%' }}
                      >
                        {availableColumns &&
                          [
                            ...availableColumns.basic,
                            ...availableColumns.daily_basic,
                            ...availableColumns.daily,
                          ].map((col) => (
                            <Option key={col.field} value={col.field}>
                              {UNIT_FACTORS[col.field] ? `${col.label}(亿)` : col.label}
                            </Option>
                          ))}
                      </Select>
                    </Col>
                    <Col span={4}>
                      <Select
                        placeholder="操作符"
                        value={filter.operator}
                        onChange={(value) =>
                          handleUpdateCondition(index, { operator: value })
                        }
                        style={{ width: '100%' }}
                      >
                        <Option value="=">=</Option>
                        <Option value="!=">!=</Option>
                        <Option value=">">&gt;</Option>
                        <Option value="<">&lt;</Option>
                        <Option value=">=">&gt;=</Option>
                        <Option value="<=">&lt;=</Option>
                        <Option value="LIKE">包含</Option>
                      </Select>
                    </Col>
                    <Col span={6}>
                      <Input
                        placeholder={UNIT_FACTORS[filter.field] ? "值(亿)" : "值"}
                        value={filter.value}
                        onChange={(e) =>
                          handleUpdateCondition(index, { value: e.target.value })
                        }
                      />
                    </Col>
                    <Col span={4}>
                      <Checkbox
                        checked={filter.not}
                        onChange={(e) =>
                          handleUpdateCondition(index, { not: e.target.checked })
                        }
                      >
                        非(NOT)
                      </Checkbox>
                    </Col>
                    <Col span={4}>
                      <Button
                        danger
                        size="small"
                        onClick={() => handleRemoveCondition(index)}
                      >
                        删除
                      </Button>
                    </Col>
                  </Row>
                );
              }
            })}
            {filterConditions.conditions.length === 0 && (
              <div>
                <Button type="dashed" onClick={handleAddFilter}>
                  添加筛选条件
                </Button>
              </div>
            )}
          </Space>
        </Card>
      </Card>

      <ProTable<Record<string, any>>
        actionRef={actionRef}
        columns={columns}
        search={false}
        options={{
          setting: false,
          fullScreen: true,
          reload: true,
        }}
        toolBarRender={() => [
          <Tooltip key="column-settings" title="列设置">
            <Button
              type="text"
              icon={<SettingOutlined />}
              onClick={() => setColumnDrawerVisible(true)}
              style={{ fontSize: 16 }}
            />
          </Tooltip>,
        ]}
        params={queryParams}
        request={async (params, sort) => {
          // 如果没有日期，或者是非手动触发的查询（即自动初始化且没加载策略），则不请求数据，避免全量数据闪烁
          if (!params.trade_date || (params._manual === false && !params.filterConditions)) {
            return { data: [], success: true, total: 0 };
          }

          try {
            // 处理排序
            const newSortConfig: ZQuant.SortConfig[] = [];
            if (sort && typeof sort === 'object' && Object.keys(sort).length > 0) {
              Object.keys(sort).forEach((field) => {
                const direction = sort[field];
                if (direction === 'ascend') {
                  newSortConfig.push({ field, order: 'asc' });
                } else if (direction === 'descend') {
                  newSortConfig.push({ field, order: 'desc' });
                }
              });
              setSortConfig(newSortConfig);
            } else if (params.sortConfig) {
              newSortConfig.push(...params.sortConfig);
            }

            const request: ZQuant.StockFilterRequest = {
              trade_date: params.trade_date,
              filter_conditions:
                params.filterConditions?.conditions?.length > 0 ? params.filterConditions : undefined,
              selected_columns: params.selectedColumns?.length > 0 ? params.selectedColumns : undefined,
              sort_config: newSortConfig.length > 0 ? newSortConfig : undefined,
              skip: ((params.current || 1) - 1) * (params.pageSize || 20),
              limit: params.pageSize || 20,
            };

            const response = await queryFilter(request);

            // 只有在明确触发查询后且有结果时显示成功信息
            if (params._manual) {
              message.success(`查询到 ${response.total} 条记录`);
            }

            return {
              data: response.items,
              success: true,
              total: response.total,
            };
          } catch (error: any) {
            message.error(error?.response?.data?.detail || '查询失败');
            return { data: [], success: false, total: 0 };
          }
        }}
        rowKey="ts_code"
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
        }}
        scroll={{ x: 1200 }}
        style={{ marginTop: 16 }}
      />

      {/* 策略管理Modal */}
      <Modal
        title={editingStrategy ? '编辑策略' : '保存策略'}
        open={strategyModalVisible}
        onCancel={() => {
          setStrategyModalVisible(false);
          setEditingStrategy(undefined);
          strategyFormRef.current?.resetFields();
        }}
        onOk={() => strategyFormRef.current?.submit()}
        width={600}
      >
        <ProForm
          formRef={strategyFormRef}
          onFinish={handleSaveStrategy}
          initialValues={editingStrategy}
        >
          <ProFormSelectWithAll
            name="name"
            label="策略名称"
            options={strategies.map((s) => ({ label: s.name, value: s.name }))}
            allValue=""
            rules={[{ required: true, message: '请输入策略名称' }]}
            placeholder="输入或选择策略名称"
          />
          <ProFormText
            name="description"
            label="策略描述"
            placeholder="输入策略描述（可选）"
          />
        </ProForm>
      </Modal>

      {/* 列设置Drawer */}
      <Drawer
        title="列设置"
        open={columnDrawerVisible}
        onClose={() => setColumnDrawerVisible(false)}
        width={400}
      >
        {availableColumns && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text strong>基础信息</Text>
              {availableColumns.basic.map((col) => (
                <div key={col.field} style={{ marginTop: 8 }}>
                  <Checkbox
                    checked={selectedColumns.includes(col.field)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedColumns([...selectedColumns, col.field]);
                      } else {
                        setSelectedColumns(selectedColumns.filter((c) => c !== col.field));
                      }
                    }}
                  >
                    {col.label}
                  </Checkbox>
                </div>
              ))}
            </div>
            <div>
              <Text strong>每日指标</Text>
              {availableColumns.daily_basic.map((col) => (
                <div key={col.field} style={{ marginTop: 8 }}>
                  <Checkbox
                    checked={selectedColumns.includes(col.field)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedColumns([...selectedColumns, col.field]);
                      } else {
                        setSelectedColumns(selectedColumns.filter((c) => c !== col.field));
                      }
                    }}
                  >
                    {col.label}
                  </Checkbox>
                </div>
              ))}
            </div>
            <div>
              <Text strong>日线数据</Text>
              {availableColumns.daily.map((col) => (
                <div key={col.field} style={{ marginTop: 8 }}>
                  <Checkbox
                    checked={selectedColumns.includes(col.field)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedColumns([...selectedColumns, col.field]);
                      } else {
                        setSelectedColumns(selectedColumns.filter((c) => c !== col.field));
                      }
                    }}
                  >
                    {col.label}
                  </Checkbox>
                </div>
              ))}
            </div>
            {availableColumns.factor && (
              <div>
                <Text strong>技术指标</Text>
                {availableColumns.factor.map((col) => (
                  <div key={col.field} style={{ marginTop: 8 }}>
                    <Checkbox
                      checked={selectedColumns.includes(col.field)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedColumns([...selectedColumns, col.field]);
                        } else {
                          setSelectedColumns(selectedColumns.filter((c) => c !== col.field));
                        }
                      }}
                    >
                      {col.label}
                    </Checkbox>
                  </div>
                ))}
              </div>
            )}
            {availableColumns.audit && (
              <div>
                <Text strong>策略与审计</Text>
                {availableColumns.audit.map((col) => (
                  <div key={col.field} style={{ marginTop: 8 }}>
                    <Checkbox
                      checked={selectedColumns.includes(col.field)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedColumns([...selectedColumns, col.field]);
                        } else {
                          setSelectedColumns(selectedColumns.filter((c) => c !== col.field));
                        }
                      }}
                    >
                      {col.label}
                    </Checkbox>
                  </div>
                ))}
              </div>
            )}
          </Space>
        )}
      </Drawer>

      {/* 策略列表 */}
      {strategies.length > 0 && (
        <Card size="small" style={{ marginTop: 16 }}>
          <Text strong>已保存的策略：</Text>
          <Space wrap style={{ marginTop: 8 }}>
            {strategies.map((strategy) => (
              <Tag
                key={strategy.id}
                color={selectedStrategyId === strategy.id ? 'blue' : 'default'}
                style={{ cursor: 'pointer' }}
                onClick={() => handleLoadStrategy(strategy.id)}
              >
                {strategy.name}
                <Popconfirm
                  title="确定要删除这个策略吗？"
                  onConfirm={() => handleDeleteStrategy(strategy.id)}
                  onCancel={(e) => e?.stopPropagation()}
                >
                  <Button
                    type="link"
                    size="small"
                    danger
                    onClick={(e) => e.stopPropagation()}
                    style={{ padding: 0, marginLeft: 4 }}
                  >
                    删除
                  </Button>
                </Popconfirm>
              </Tag>
            ))}
          </Space>
        </Card>
      )}
    </div>
  );
};

export default StockFilter;


