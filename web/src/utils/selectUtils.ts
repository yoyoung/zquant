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

/**
 * 下拉框选项工具函数
 */

export interface SelectOption {
  label: string;
  value: string | number;
  [key: string]: any;
}

/**
 * 为选项数组添加"全部"选项
 * @param options 原始选项数组
 * @param allValue "全部"选项的值，默认为空字符串
 * @param allLabel "全部"选项的显示文本，默认为"全部"
 * @returns 添加了"全部"选项的新数组（"全部"选项在第一位）
 */
export function addAllOption(
  options: SelectOption[] = [],
  allValue: string | number = '',
  allLabel: string = '全部'
): SelectOption[] {
  // 检查是否已经存在"全部"选项
  const hasAllOption = options.some((opt) => opt.value === allValue);
  if (hasAllOption) {
    // 如果已存在，确保它在第一位
    const otherOptions = options.filter((opt) => opt.value !== allValue);
    return [{ label: allLabel, value: allValue }, ...otherOptions];
  }
  // 如果不存在，添加"全部"选项到第一位
  return [{ label: allLabel, value: allValue }, ...options];
}

/**
 * 获取默认选中的值（返回"全部"选项的值）
 * @param allValue "全部"选项的值，默认为空字符串
 * @returns 默认值
 */
export function getDefaultSelectValue(allValue: string | number = ''): string | number {
  return allValue;
}


