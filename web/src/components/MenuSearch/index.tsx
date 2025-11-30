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

import { SearchOutlined } from '@ant-design/icons';
import { Input } from 'antd';
import { createStyles } from 'antd-style';
import React, { useState } from 'react';

const { Search } = Input;

const useStyles = createStyles(({ token }) => {
  return {
    container: {
      padding: '12px 16px',
      borderBottom: `1px solid ${token.colorBorderSecondary}`,
    },
    searchInput: {
      width: '100%',
    },
  };
});

interface MenuSearchProps {
  onSearch?: (value: string) => void;
  placeholder?: string;
  collapsed?: boolean;
}

const MenuSearch: React.FC<MenuSearchProps> = ({
  onSearch,
  placeholder = '搜索菜单',
  collapsed = false,
}) => {
  const { styles } = useStyles();
  const [searchValue, setSearchValue] = useState('');

  const handleSearch = (value: string) => {
    setSearchValue(value);
    onSearch?.(value);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchValue(value);
    onSearch?.(value);
  };

  // 折叠时隐藏搜索框
  if (collapsed) {
    return null;
  }

  return (
    <div className={styles.container}>
      <Search
        className={styles.searchInput}
        placeholder={placeholder}
        allowClear
        prefix={<SearchOutlined />}
        value={searchValue}
        onChange={handleChange}
        onSearch={handleSearch}
      />
    </div>
  );
};

export default MenuSearch;

