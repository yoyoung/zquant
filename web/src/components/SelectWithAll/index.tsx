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

import { Select, SelectProps } from 'antd';
import React from 'react';
import { addAllOption, SelectOption } from '@/utils/selectUtils';

export interface SelectWithAllProps extends Omit<SelectProps, 'options'> {
  options?: SelectOption[];
  allValue?: string | number;
  allLabel?: string;
  excludeAll?: boolean; // 是否排除"全部"选项（用于搜索类型等特殊情况）
}

/**
 * 带"全部"选项的 Select 组件
 * 自动在选项列表第一位添加"全部"选项，并设置默认值
 */
const SelectWithAll: React.FC<SelectWithAllProps> = ({
  options = [],
  allValue = '',
  allLabel = '全部',
  excludeAll = false,
  value,
  defaultValue,
  ...restProps
}) => {
  // 如果排除"全部"选项，直接使用原始选项
  const finalOptions = excludeAll ? options : addAllOption(options, allValue, allLabel);

  // 如果没有指定 value 和 defaultValue，默认选中"全部"选项
  const finalValue = value !== undefined ? value : defaultValue !== undefined ? defaultValue : allValue;
  const finalDefaultValue = defaultValue !== undefined ? defaultValue : allValue;

  return (
    <Select
      {...restProps}
      options={finalOptions}
      value={finalValue}
      defaultValue={finalDefaultValue}
    />
  );
};

export default SelectWithAll;


