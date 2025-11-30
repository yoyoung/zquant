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
//     - Issues: https://github.com/zquant/zquant/issues
//     - Documentation: https://docs.zquant.com
//     - Repository: https://github.com/zquant/zquant

import { ProForm, ProFormText, ProFormTextArea, ProFormSelect } from '@ant-design/pro-components';
import { Card, message, Button, Space } from 'antd';
import { history } from '@umijs/max';
import React, { useEffect, useState, useMemo } from 'react';
import { createStrategy, getStrategyFramework, getTemplateStrategies } from '@/services/zquant/backtest';

const CreateStrategy: React.FC = () => {
  const [form] = ProForm.useForm();
  const [frameworkCode, setFrameworkCode] = useState<string>('');
  const [templateStrategies, setTemplateStrategies] = useState<ZQuant.StrategyResponse[]>([]);
  const [loadingFramework, setLoadingFramework] = useState(false);

  // 加载策略框架代码
  useEffect(() => {
    const loadFramework = async () => {
      try {
        setLoadingFramework(true);
        const response = await getStrategyFramework();
        setFrameworkCode(response.code);
        // 设置默认值
        form.setFieldsValue({
          code: response.code,
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

  // 加载框架代码
  const handleLoadFramework = async () => {
    try {
      setLoadingFramework(true);
      const response = await getStrategyFramework();
      form.setFieldsValue({
        code: response.code,
      });
      message.success('策略框架代码已加载');
    } catch (error) {
      message.error('加载策略框架失败');
    } finally {
      setLoadingFramework(false);
    }
  };

  // 获取当前选择的分类
  const selectedCategory = ProForm.useWatch('category', form);

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
        code: template.code,
        name: template.name,
        category: template.category,
        description: template.description,
      });
      message.success(`已加载策略模板: ${template.name}`);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      await createStrategy({
        name: values.name,
        code: values.code || '',
        description: values.description,
        category: values.category,
        params_schema: values.params_schema,
        is_template: false,
      });
      
      message.success('策略创建成功');
      history.push('/backtest/strategies');
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '创建失败');
    }
  };

  return (
    <Card title="创建策略" extra={<a onClick={() => history.push('/backtest/strategies')}>返回列表</a>}>
      <ProForm
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        <ProFormText
          name="name"
          label="策略名称"
          rules={[{ required: true, message: '请输入策略名称' }]}
          width="md"
          placeholder="请输入策略名称"
        />
        <ProFormSelect
          name="category"
          label="策略分类"
          placeholder="请选择策略分类"
          options={[
            { label: '技术分析', value: 'technical' },
            { label: '基本面', value: 'fundamental' },
            { label: '量化策略', value: 'quantitative' },
          ]}
          width="md"
          extra="选择策略所属的分类，选择后策略模板将只显示该分类的模板"
          fieldProps={{
            onChange: (value: string | undefined) => {
              handleCategoryChange(value);
            },
            allowClear: true,
          }}
        />
        <ProFormTextArea
          name="description"
          label="策略描述"
          placeholder="请输入策略描述（可选）"
          fieldProps={{
            rows: 3,
          }}
          width="md"
        />
        <ProFormSelect
          name="template_strategy"
          label="策略模板"
          placeholder="选择策略模板（可选）"
          options={filteredTemplateStrategies.map(t => ({
            label: `${t.name}${t.description ? ` - ${t.description}` : ''}`,
            value: t.id,
          }))}
          fieldProps={{
            onChange: (value: number) => {
              if (value) {
                handleSelectTemplate(value);
              }
            },
            allowClear: true,
          }}
          width="md"
          dependencies={['category']}
          extra={selectedCategory 
            ? `已筛选${filteredTemplateStrategies.length}个${selectedCategory === 'technical' ? '技术分析' : selectedCategory === 'fundamental' ? '基本面' : '量化策略'}模板` 
            : "选择模板后会自动填充策略代码、名称、分类和描述"}
        />
        <ProFormTextArea
          name="code"
          label="策略代码"
          placeholder="请输入Python策略代码"
          rules={[{ required: true, message: '请输入策略代码' }]}
          fieldProps={{
            rows: 20,
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
        <ProFormTextArea
          name="params_schema"
          label="参数Schema（JSON格式）"
          placeholder='请输入参数Schema，例如：{"param1": {"type": "number", "default": 10}}'
          fieldProps={{
            rows: 5,
          }}
          width="md"
          extra="定义策略参数的JSON Schema，用于参数配置界面（可选）"
        />
      </ProForm>
    </Card>
  );
};

export default CreateStrategy;

