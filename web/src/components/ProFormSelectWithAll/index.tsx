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

import { ProFormSelect, ProFormSelectProps } from '@ant-design/pro-components';
import React, { useMemo } from 'react';
import { addAllOption, SelectOption } from '@/utils/selectUtils';

export interface ProFormSelectWithAllProps extends Omit<ProFormSelectProps, 'options'> {
  options?: SelectOption[];
  valueEnum?: Record<string | number, string | { text: string; [key: string]: any }>;
  allValue?: string | number;
  allLabel?: string;
  excludeAll?: boolean; // 是否排除"全部"选项（用于搜索类型等特殊情况）
}

/**
 * 带"全部"选项的 ProFormSelect 组件
 * 自动在选项列表第一位添加"全部"选项
 * 支持 options 和 valueEnum 两种方式
 */
const ProFormSelectWithAll: React.FC<ProFormSelectWithAllProps> = ({
  options,
  valueEnum,
  allValue = '',
  allLabel = '全部',
  excludeAll = false,
  initialValue,
  ...restProps
}) => {
  // 将 valueEnum 转换为 options（如果提供了 valueEnum）
  const convertedOptions = useMemo(() => {
    if (valueEnum) {
      return Object.entries(valueEnum).map(([value, label]) => ({
        label: typeof label === 'string' ? label : label.text,
        value: value,
      }));
    }
    return options || [];
  }, [valueEnum, options]);

  // 如果排除"全部"选项，直接使用原始选项
  const finalOptions = excludeAll ? convertedOptions : addAllOption(convertedOptions, allValue, allLabel);

  // 如果没有指定 initialValue，默认选中"全部"选项
  const finalInitialValue = initialValue !== undefined ? initialValue : allValue;

  return (
    <ProFormSelect
      {...restProps}
      options={finalOptions}
      initialValue={finalInitialValue}
    />
  );
};

export default ProFormSelectWithAll;

