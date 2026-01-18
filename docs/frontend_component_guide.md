# 前端组件开发指南

本文档介绍 ZQuant 平台前端组件的使用方法和最佳实践。

## 目录

- [概述](#概述)
- [组件介绍](#组件介绍)
- [使用方法](#使用方法)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

## 概述

为了统一用户体验，ZQuant 平台提供了带"全部"选项的下拉框组件。这些组件自动在选项列表第一位添加"全部"选项，并默认选中，用户无需手动选择即可查看全部数据。

### 优势

- ✅ **统一体验**: 所有下拉框行为一致，降低学习成本
- ✅ **提升效率**: 默认选中"全部"，减少用户操作
- ✅ **简化开发**: 封装常用逻辑，减少重复代码
- ✅ **易于维护**: 统一管理，便于后续优化

## 组件介绍

### SelectWithAll

带"全部"选项的 Ant Design Select 组件包装器。

**文件位置**: `web/src/components/SelectWithAll/index.tsx`

**特性**:
- 自动添加"全部"选项到列表第一位
- 默认选中"全部"选项
- 支持自定义"全部"选项的值和标签
- 支持排除"全部"选项（用于搜索类型等特殊场景）

### ProFormSelectWithAll

带"全部"选项的 ProFormSelect 组件包装器。

**文件位置**: `web/src/components/ProFormSelectWithAll/index.tsx`

**特性**:
- 自动添加"全部"选项到列表第一位
- 默认选中"全部"选项
- 支持 `options` 和 `valueEnum` 两种方式
- 支持自定义"全部"选项的值和标签
- 支持排除"全部"选项

### selectUtils

下拉框选项工具函数。

**文件位置**: `web/src/utils/selectUtils.ts`

**函数**:
- `addAllOption`: 为选项数组添加"全部"选项
- `getDefaultSelectValue`: 获取默认选中的值

## 使用方法

### SelectWithAll 基本用法

```tsx
import SelectWithAll from '@/components/SelectWithAll';

// 基本用法
<SelectWithAll
  placeholder="选择因子"
  style={{ width: 200 }}
  options={[
    { label: '因子A', value: 'factor_a' },
    { label: '因子B', value: 'factor_b' },
  ]}
  allValue=""
/>
```

**说明**:
- `options`: 选项数组，组件会自动在第一位添加"全部"选项
- `allValue`: "全部"选项的值，默认为空字符串 `""`
- 组件会自动设置默认值为 `allValue`，用户无需手动设置

### ProFormSelectWithAll 基本用法

```tsx
import ProFormSelectWithAll from '@/components/ProFormSelectWithAll';

// 基本用法
<ProFormSelectWithAll
  name="strategy_category"
  label="策略分类"
  options={[
    { label: '技术分析', value: 'technical' },
    { label: '基本面', value: 'fundamental' },
    { label: '量化策略', value: 'quantitative' },
  ]}
  allValue=""
  width="md"
/>
```

**说明**:
- `name`: 表单字段名
- `label`: 标签文本
- `options`: 选项数组
- `allValue`: "全部"选项的值
- 组件会自动设置 `initialValue` 为 `allValue`

### 自定义"全部"选项的值和标签

```tsx
// 使用自定义值
<ProFormSelectWithAll
  name="exchange"
  label="交易所"
  options={[
    { label: '上交所 (SSE)', value: 'SSE' },
    { label: '深交所 (SZSE)', value: 'SZSE' },
  ]}
  allValue="all"  // 自定义值
  allLabel="全部交易所"  // 自定义标签
/>
```

### 使用 valueEnum（ProFormSelectWithAll）

```tsx
// 使用 valueEnum 格式
<ProFormSelectWithAll
  name="target"
  label="监控对象"
  valueEnum={{
    0: '表一',
    1: '表二',
  }}
  allValue=""
/>
```

**说明**:
- `ProFormSelectWithAll` 支持 `valueEnum` 格式，会自动转换为 `options` 格式
- 兼容现有使用 `valueEnum` 的代码

### 排除"全部"选项

某些场景下不需要"全部"选项，例如搜索类型的下拉框：

```tsx
// 排除"全部"选项
<ProFormSelectWithAll
  name="code"
  label="股票代码"
  showSearch
  excludeAll={true}  // 排除"全部"选项
  fieldProps={{
    onSearch: handleStockSearch,
    options: stockOptions,
  }}
/>
```

**说明**:
- `excludeAll={true}`: 不添加"全部"选项
- 适用于搜索类型、必填字段等特殊场景

### 在 Form.Item 中使用 SelectWithAll

```tsx
import { Form } from 'antd';
import SelectWithAll from '@/components/SelectWithAll';

<Form.Item name="factor_name" label="因子名称">
  <SelectWithAll
    placeholder="选择因子"
    style={{ width: 200 }}
    options={factorDefinitions.map((f) => ({
      label: `${f.cn_name} (${f.factor_name})`,
      value: f.factor_name,
    }))}
    allValue=""
  />
</Form.Item>
```

## 最佳实践

### 何时使用这些组件

✅ **推荐使用**:
- 所有筛选/查询类型的下拉框
- 需要"全部"选项的场景
- 希望统一用户体验的场景

❌ **不推荐使用**:
- 搜索类型的下拉框（使用 `excludeAll={true}` 或直接使用原组件）
- 必填字段且不允许"全部"的场景
- 特殊业务逻辑需要自定义处理的场景

### 选择 allValue 的值

根据业务场景选择合适的值：

- **空字符串 `""`**: 适用于大多数场景，后端通常将空字符串视为"全部"
- **字符串 `"all"`**: 适用于需要明确标识"全部"的场景
- **数字 `0`**: 适用于数值类型的场景

**示例**:

```tsx
// 场景1: 通常使用空字符串
<ProFormSelectWithAll
  name="operation_type"
  options={[...]}
  allValue=""  // 后端将 "" 视为查询全部
/>

// 场景2: 使用 "all" 明确标识
<ProFormSelectWithAll
  name="exchange"
  options={[...]}
  allValue="all"  // 后端需要明确处理 "all" 值
/>

// 场景3: 匹配交易日使用 "all"
<ProFormSelectWithAll
  name="trading_day_filter"
  options={[
    { label: '有交易日', value: 'has_data' },
    { label: '无交易日', value: 'no_data' },
  ]}
  allValue="all"  // 保持与原有逻辑一致
/>
```

### 迁移现有代码

如果现有代码已经手动添加了"全部"选项，可以简化：

**迁移前**:

```tsx
<ProFormSelect
  name="operation_type"
  options={[
    { label: '全部', value: '' },
    { label: '插入', value: 'insert' },
    { label: '更新', value: 'update' },
  ]}
/>
```

**迁移后**:

```tsx
<ProFormSelectWithAll
  name="operation_type"
  options={[
    { label: '插入', value: 'insert' },
    { label: '更新', value: 'update' },
  ]}
  allValue=""
/>
```

**优势**:
- 代码更简洁
- 统一管理"全部"选项
- 自动处理默认值

## 常见问题

### Q1: 为什么我的下拉框没有显示"全部"选项？

**A**: 检查以下几点：
1. 确认使用了 `SelectWithAll` 或 `ProFormSelectWithAll` 组件
2. 确认没有设置 `excludeAll={true}`
3. 检查 `options` 或 `valueEnum` 是否正确传入

### Q2: 如何自定义"全部"选项的显示文本？

**A**: 使用 `allLabel` 属性：

```tsx
<ProFormSelectWithAll
  options={[...]}
  allValue=""
  allLabel="全部选项"  // 自定义标签
/>
```

### Q3: 如何禁用"全部"选项的默认选中？

**A**: 显式设置 `initialValue` 或 `defaultValue`：

```tsx
<ProFormSelectWithAll
  options={[...]}
  allValue=""
  initialValue="other_value"  // 覆盖默认值
/>
```

### Q4: 组件支持哪些 Ant Design Select 的属性？

**A**: 组件完全兼容 Ant Design Select 和 ProFormSelect 的所有属性，除了 `options` 会被自动处理。所有其他属性（如 `placeholder`、`disabled`、`onChange` 等）都可以正常使用。

### Q5: 如何在 onChange 中处理"全部"选项？

**A**: 在 `onChange` 回调中判断值是否为 `allValue`：

```tsx
<ProFormSelectWithAll
  name="category"
  options={[...]}
  allValue=""
  fieldProps={{
    onChange: (value) => {
      if (value === '') {
        // 处理"全部"选项
        console.log('选择了全部');
      } else {
        // 处理具体选项
        console.log('选择了:', value);
      }
    },
  }}
/>
```

### Q6: 为什么使用 valueEnum 时组件不工作？

**A**: 确保使用 `ProFormSelectWithAll` 而不是 `SelectWithAll`，因为只有 `ProFormSelectWithAll` 支持 `valueEnum`。

### Q7: 如何在后端处理"全部"选项的值？

**A**: 根据 `allValue` 的值进行判断：

```python
# 后端示例（Python/FastAPI）
if category == "" or category == "all":
    # 查询全部数据
    query = session.query(Model)
else:
    # 查询特定分类
    query = session.query(Model).filter(Model.category == category)
```

## 相关文件

- 组件源码: `web/src/components/SelectWithAll/index.tsx`
- 组件源码: `web/src/components/ProFormSelectWithAll/index.tsx`
- 工具函数: `web/src/utils/selectUtils.ts`
- 版本变更: [CHANGELOG.md](../CHANGELOG.md)

## 更新日志

- **0.3.0** (2025-01-XX): 新增组件，统一所有下拉框体验

---

如有问题或建议，请提交 [Issue](https://github.com/yoyoung/zquant/issues) 或联系开发团队。

