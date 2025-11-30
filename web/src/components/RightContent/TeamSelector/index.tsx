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

import { DownOutlined } from '@ant-design/icons';
import { Dropdown } from 'antd';
import { createStyles } from 'antd-style';
import React, { useState } from 'react';
import type { MenuProps } from 'antd';

const useStyles = createStyles(({ token }) => ({
  teamSelector: {
    display: 'flex',
    alignItems: 'center',
    padding: '0 12px',
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
  teamName: {
    fontSize: '14px',
    marginRight: '8px',
  },
}));

interface Team {
  id: string;
  name: string;
}

// 模拟团队数据
const mockTeams: Team[] = [
  { id: '1', name: 'Team1' },
  { id: '2', name: 'Team2' },
  { id: '3', name: 'Team3' },
];

const TeamSelector: React.FC = () => {
  const { styles } = useStyles();
  const [currentTeam, setCurrentTeam] = useState<Team>(mockTeams[0]);

  const handleTeamChange: MenuProps['onClick'] = ({ key }) => {
    const team = mockTeams.find((t) => t.id === key);
    if (team) {
      setCurrentTeam(team);
      // 这里可以触发团队切换的逻辑
      console.log('切换团队:', team.name);
    }
  };

  const menuItems: MenuProps['items'] = mockTeams.map((team) => ({
    key: team.id,
    label: team.name,
  }));

  return (
    <Dropdown
      menu={{ items: menuItems, onClick: handleTeamChange }}
      trigger={['click']}
      placement="bottomRight"
    >
      <div className={styles.teamSelector}>
        <span className={styles.teamName}>{currentTeam.name}</span>
        <DownOutlined style={{ fontSize: '12px' }} />
      </div>
    </Dropdown>
  );
};

export default TeamSelector;

