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

import { ProForm, ProFormDatePicker, ProFormText, ProFormTextArea, ProFormDigit, ProFormSwitch } from '@ant-design/pro-components';
import ProFormSelectWithAll from '@/components/ProFormSelectWithAll';
import { Card, message, Button, Space } from 'antd';
import { history } from '@umijs/max';
import React, { useEffect, useState, useMemo } from 'react';
import { runBacktest, getStrategyFramework, getTemplateStrategies } from '@/services/zquant/backtest';
import { getStocks } from '@/services/zquant/data';
import dayjs from 'dayjs';

const CreateBacktest: React.FC = () => {
  const [form] = ProForm.useForm();
  const [frameworkCode, setFrameworkCode] = useState<string>('');
  const [templateStrategies, setTemplateStrategies] = useState<ZQuant.StrategyResponse[]>([]);
  const [loadingFramework, setLoadingFramework] = useState(false);
  const [loadingStocks, setLoadingStocks] = useState(false);
  const [allStocks, setAllStocks] = useState<string[]>([]);

  // 加载策略框架代码
  useEffect(() => {
    const loadFramework = async () => {
      try {
        setLoadingFramework(true);
        const response = await getStrategyFramework();
        setFrameworkCode(response.code);
        // 设置默认值
        form.setFieldsValue({
          strategy_code: response.code,
        });
      } catch (error) {
        console.error('加载策略框架失败:', error);
      } finally {
        setLoadingFramework(false);
      }
    };
    loadFramework();
  }, [form]);

  // 加载策略模板列表
  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const templates = await getTemplateStrategies({ limit: 100 });
        setTemplateStrategies(templates);
      } catch (error) {
        console.error('加载策略模板失败:', error);
      }
    };
    loadTemplates();
  }, []);

  // 加载所有股票列表
  const loadAllStocks = async () => {
    try {
      setLoadingStocks(true);
      const response = await getStocks({});
      // 提取所有股票的 ts_code，过滤掉已退市的股票（delist_date 不为 null 的）
      const stockCodes = response.stocks
        .filter((stock: any) => !stock.delist_date && stock.ts_code)
        .map((stock: any) => stock.ts_code);
      setAllStocks(stockCodes);
      
      // 填充到表单
      if (stockCodes.length > 0) {
        form.setFieldsValue({
          symbols: stockCodes.join(','),
        });
        message.success(`已加载 ${stockCodes.length} 只股票`);
      } else {
        message.warning('未找到可用的股票列表');
      }
    } catch (error) {
      console.error('加载股票列表失败:', error);
      message.error('加载股票列表失败');
    } finally {
      setLoadingStocks(false);
    }
  };

  // 页面加载时自动加载所有股票
  useEffect(() => {
    loadAllStocks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 加载框架代码
  const handleLoadFramework = async () => {
    try {
      setLoadingFramework(true);
      const response = await getStrategyFramework();
      form.setFieldsValue({
        strategy_code: response.code,
      });
      message.success('策略框架代码已加载');
    } catch (error) {
      message.error('加载策略框架失败');
    } finally {
      setLoadingFramework(false);
    }
  };

  // 获取当前选择的分类
  const selectedCategory = ProForm.useWatch('strategy_category', form);

  // 根据分类过滤策略模板列表
  const filteredTemplateStrategies = useMemo(() => {
    if (!selectedCategory) {
      return templateStrategies;
    }
    return templateStrategies.filter(t => t.category === selectedCategory);
  }, [templateStrategies, selectedCategory]);

  // 处理分类变化
  const handleCategoryChange = (category: string | undefined) => {
    // 如果已选择模板，检查模板分类是否匹配
    const selectedTemplateId = form.getFieldValue('template_strategy');
    if (selectedTemplateId) {
      const selectedTemplate = templateStrategies.find(t => t.id === selectedTemplateId);
      if (selectedTemplate && selectedTemplate.category !== category) {
        // 如果模板分类不匹配，清空模板选择
        form.setFieldsValue({
          template_strategy: undefined,
        });
      }
    }
  };

  // 选择策略模板
  const handleSelectTemplate = async (strategyId: number) => {
    const template = templateStrategies.find(s => s.id === strategyId);
    if (template) {
      form.setFieldsValue({
        strategy_code: template.code,
        strategy_name: template.name,
        strategy_category: template.category,
      });
      message.success(`已加载策略模板: ${template.name}`);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const { start_date, end_date } = values;
      
      await runBacktest({
        strategy_code: values.strategy_code || '',
        strategy_name: values.strategy_name || '未命名策略',
        config: {
          start_date: start_date ? dayjs(start_date).format('YYYY-MM-DD') : dayjs().subtract(1, 'month').format('YYYY-MM-DD'),
          end_date: end_date ? dayjs(end_date).format('YYYY-MM-DD') : dayjs().format('YYYY-MM-DD'),
          initial_capital: values.initial_capital || 1000000,
          symbols: values.symbols ? values.symbols.split(',').map((s: string) => s.trim()) : [],
          frequency: values.frequency || 'daily',
          adjust_type: values.adjust_type || 'qfq',
          commission_rate: values.commission_rate || 0.0003,
          min_commission: values.min_commission || 5.0,
          tax_rate: values.tax_rate || 0.001,
          slippage_rate: values.slippage_rate || 0.001,
          benchmark: values.benchmark || undefined,
          use_daily_basic: values.use_daily_basic || false,
        },
      });
      
      message.success('回测任务创建成功');
      history.push('/backtest');
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '创建失败');
    }
  };

  return (
    <Card title="创建回测任务">
      <ProForm
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          symbols: '000001.SZ',
          initial_capital: 1000000,
          frequency: 'daily',
          adjust_type: 'qfq',
          commission_rate: 0.0003,
          min_commission: 5.0,
          tax_rate: 0.001,
          slippage_rate: 0.001,
          use_daily_basic: false,
          start_date: dayjs().subtract(1, 'month'),
          end_date: dayjs(),
        }}
      >
        <ProFormText
          name="strategy_name"
          label="策略名称"
          rules={[{ required: true, message: '请输入策略名称' }]}
          width="md"
        />
        <ProFormSelectWithAll
          name="strategy_category"
          label="策略分类"
          placeholder="请选择策略分类"
          options={[
            { label: '技术分析', value: 'technical' },
            { label: '基本面', value: 'fundamental' },
            { label: '量化策略', value: 'quantitative' },
          ]}
          allValue=""
          width="md"
          extra="选择策略所属的分类，选择后策略模板将只显示该分类的模板"
          fieldProps={{
            onChange: (value: string | undefined) => {
              handleCategoryChange(value);
            },
            allowClear: true,
          }}
        />
        <ProFormSelectWithAll
          name="template_strategy"
          label="策略模板"
          placeholder="选择策略模板（可选）"
          options={filteredTemplateStrategies.map(t => ({
            label: `${t.name}${t.description ? ` - ${t.description}` : ''}`,
            value: t.id,
          }))}
          allValue=""
          fieldProps={{
            onChange: (value: number) => {
              if (value) {
                handleSelectTemplate(value);
              }
            },
            allowClear: true,
          }}
          width="md"
          dependencies={['strategy_category']}
          extra={selectedCategory 
            ? `已筛选${filteredTemplateStrategies.length}个${selectedCategory === 'technical' ? '技术分析' : selectedCategory === 'fundamental' ? '基本面' : '量化策略'}模板` 
            : "选择模板后会自动填充策略代码、策略名称和策略分类"}
        />
        <ProFormTextArea
          name="strategy_code"
          label="策略代码"
          placeholder="请输入Python策略代码"
          rules={[{ required: true, message: '请输入策略代码' }]}
          fieldProps={{
            rows: 15,
          }}
          extra={
            <Space>
              <Button 
                type="link" 
                size="small" 
                onClick={handleLoadFramework}
                loading={loadingFramework}
              >
                加载框架代码
              </Button>
              <span style={{ color: '#999' }}>
                点击"加载框架代码"可获取策略代码模板
              </span>
            </Space>
          }
        />
        <ProFormText
          name="symbols"
          label="TS代码"
          placeholder="多个代码用逗号分隔，如：000001.SZ,600000.SH"
          rules={[{ required: true, message: '请输入TS代码' }]}
          width="md"
          extra={
            <Space>
              <Button 
                type="link" 
                size="small" 
                onClick={loadAllStocks}
                loading={loadingStocks}
              >
                全选所有股票
              </Button>
              {allStocks.length > 0 && (
                <span style={{ color: '#999' }}>
                  已加载 {allStocks.length} 只股票（默认已全选）
                </span>
              )}
            </Space>
          }
        />
        <ProFormDatePicker
          name="start_date"
          label="开始日期"
          rules={[{ required: true, message: '请选择开始日期' }]}
        />
        <ProFormDatePicker
          name="end_date"
          label="结束日期"
          rules={[{ required: true, message: '请选择结束日期' }]}
        />
        <ProFormDigit
          name="initial_capital"
          label="初始资金"
          min={0}
          width="sm"
        />
        <ProFormSelectWithAll
          name="frequency"
          label="频率"
          options={[
            { label: '日线', value: 'daily' },
          ]}
          allValue=""
          width="sm"
        />
        <ProFormSelectWithAll
          name="adjust_type"
          label="复权类型"
          options={[
            { label: '前复权', value: 'qfq' },
            { label: '后复权', value: 'hfq' },
            { label: '不复权', value: 'None' },
          ]}
          allValue=""
          width="sm"
        />
        <ProFormDigit
          name="commission_rate"
          label="佣金率"
          min={0}
          max={1}
          width="sm"
        />
        <ProFormDigit
          name="min_commission"
          label="最低佣金"
          min={0}
          width="sm"
        />
        <ProFormDigit
          name="tax_rate"
          label="印花税率"
          min={0}
          max={1}
          width="sm"
        />
        <ProFormDigit
          name="slippage_rate"
          label="滑点率"
          min={0}
          max={1}
          width="sm"
        />
        <ProFormText
          name="benchmark"
          label="基准指数"
          placeholder="如：000300.SH（沪深300）"
          width="sm"
        />
        <ProFormSwitch
          name="use_daily_basic"
          label="使用每日指标数据"
          tooltip="启用后，策略可通过 context.get_daily_basic() 访问 PE、PB、换手率等每日指标数据"
        />
      </ProForm>
    </Card>
  );
};

export default CreateBacktest;

