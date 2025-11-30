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

import { history, useLocation } from '@umijs/max';
import { createStyles } from 'antd-style';
import React from 'react';

const useStyles = createStyles(({ token }) => ({
  navLinks: {
    display: 'flex',
    alignItems: 'center',
    gap: '24px',
    marginLeft: '24px',
  },
  navLink: {
    color: 'rgba(255, 255, 255, 0.85)',
    fontSize: '14px',
    cursor: 'pointer',
    padding: '4px 8px',
    borderRadius: '4px',
    transition: 'all 0.3s',
    textDecoration: 'none',
    '&:hover': {
      color: '#fff',
      backgroundColor: 'rgba(255, 255, 255, 0.1)',
    },
  },
  activeLink: {
    color: '#fff',
    fontWeight: 500,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
  },
}));

interface NavLinkItem {
  path: string;
  label: string;
}

const navLinks: NavLinkItem[] = [
  { path: '/dashboard', label: '量化分析' },
];

const TopNavLinks: React.FC = () => {
  const { styles } = useStyles();
  const location = useLocation();

  const handleClick = (path: string, e: React.MouseEvent) => {
    e.preventDefault();
    history.push(path);
  };

  return (
    <div className={styles.navLinks}>
      {navLinks.map((link) => {
        const isActive = location.pathname.startsWith(link.path);
        return (
          <a
            key={link.path}
            href={link.path}
            className={`${styles.navLink} ${isActive ? styles.activeLink : ''}`}
            onClick={(e) => handleClick(link.path, e)}
          >
            {link.label}
          </a>
        );
      })}
    </div>
  );
};

export default TopNavLinks;

