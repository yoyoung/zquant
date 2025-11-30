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

import { CheckCircleOutlined } from '@ant-design/icons';
import { createStyles } from 'antd-style';
import React from 'react';

const useStyles = createStyles(({ token }) => ({
  iconWrapper: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '40px',
    height: '40px',
    cursor: 'pointer',
    borderRadius: '4px',
    transition: 'all 0.3s',
    color: 'rgba(255, 255, 255, 0.85)',
    '&:hover': {
      backgroundColor: 'rgba(255, 255, 255, 0.1)',
      color: '#fff',
    },
  },
}));

const TaskStatus: React.FC = () => {
  const { styles } = useStyles();

  const handleClick = () => {
    // 可以跳转到任务页面或显示任务状态
    console.log('查看任务状态');
  };

  return (
    <div className={styles.iconWrapper} onClick={handleClick}>
      <CheckCircleOutlined style={{ fontSize: '18px' }} />
    </div>
  );
};

export default TaskStatus;

