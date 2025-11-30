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

import { PageContainer } from '@ant-design/pro-components';
import { Result } from 'antd';
import { ConstructionOutlined } from '@ant-design/icons';
import React from 'react';

const UnderConstruction: React.FC = () => {
  return (
    <PageContainer>
      <Result
        icon={<ConstructionOutlined style={{ color: '#1890ff' }} />}
        title="功能建设中"
        subTitle="该功能正在开发中，敬请期待..."
      />
    </PageContainer>
  );
};

export default UnderConstruction;

