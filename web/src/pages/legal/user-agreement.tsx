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
import { history } from '@umijs/max';
import { Button, Card, Typography } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import React from 'react';

const { Title, Paragraph, Text } = Typography;

const UserAgreement: React.FC = () => {
  return (
    <PageContainer
      title="用户协议"
      extra={[
        <Button
          key="back"
          icon={<ArrowLeftOutlined />}
          onClick={() => history.back()}
        >
          返回
        </Button>,
      ]}
    >
      <Card>
        <Typography>
          <Title level={2}>ZQuant量化分析平台用户协议</Title>
          
          <Paragraph>
            <Text strong>生效日期：</Text>2025年12月1日
          </Paragraph>
          
          <Paragraph>
            <Text strong>最后更新：</Text>2025年12月1日
          </Paragraph>

          <Title level={3}>一、协议范围</Title>
          <Paragraph>
            欢迎使用 ZQuant量化分析平台（以下简称"本平台"或"我们"）。本用户协议（以下简称"本协议"）是您与 ZQuant 之间关于使用本平台服务的法律协议。
          </Paragraph>
          <Paragraph>
            在使用本平台服务之前，请您仔细阅读本协议的全部内容。当您点击"同意"或开始使用本平台服务时，即表示您已充分理解并同意接受本协议的全部内容。如果您不同意本协议的任何内容，请立即停止使用本平台服务。
          </Paragraph>

          <Title level={3}>二、服务说明</Title>
          <Paragraph>
            <Text strong>2.1 平台服务内容</Text>
            <br />
            本平台是ZQuant量化分析平台，主要提供以下服务：
            <ul>
              <li>股票数据采集、清洗和存储服务</li>
              <li>量化策略开发和管理工具</li>
              <li>策略回测引擎和绩效分析</li>
              <li>数据可视化展示</li>
              <li>其他相关技术服务</li>
            </ul>
          </Paragraph>
          <Paragraph>
            <Text strong>2.2 股票列表说明</Text>
            <br />
            本平台展示的股票列表是基于公开市场数据和分析工具得出的结果，包括但不限于：
            <ul>
              <li>股票基础信息（代码、名称、行业等）</li>
              <li>技术指标和因子数据</li>
              <li>财务数据和分析结果</li>
              <li>其他通过量化分析得出的数据</li>
            </ul>
            这些股票列表和数据仅供参考，不构成任何投资建议。
          </Paragraph>

          <Title level={3}>三、用户权利和义务</Title>
          <Paragraph>
            <Text strong>3.1 用户权利</Text>
            <ul>
              <li>使用本平台提供的各项服务</li>
              <li>查看和管理自己的账户信息</li>
              <li>创建和管理量化策略</li>
              <li>查看回测结果和绩效分析</li>
              <li>获取平台提供的技术支持</li>
            </ul>
          </Paragraph>
          <Paragraph>
            <Text strong>3.2 用户义务</Text>
            <ul>
              <li>提供真实、准确、完整的注册信息</li>
              <li>妥善保管账户密码，对账户下的所有行为负责</li>
              <li>遵守相关法律法规和本协议约定</li>
              <li>不得利用本平台从事违法违规活动</li>
              <li>不得干扰、破坏本平台的正常运行</li>
              <li>不得未经授权访问或尝试访问本平台的任何系统或数据</li>
            </ul>
          </Paragraph>

          <Title level={3}>四、数据使用规范</Title>
          <Paragraph>
            <Text strong>4.1 数据来源</Text>
            <br />
            本平台使用的数据主要来源于第三方数据服务商（如 Tushare 等），我们不对数据的准确性、完整性、及时性做出任何保证。
          </Paragraph>
          <Paragraph>
            <Text strong>4.2 数据使用限制</Text>
            <ul>
              <li>用户仅可将本平台提供的数据用于个人研究和学习目的</li>
              <li>未经授权，不得将数据用于商业用途或向第三方提供</li>
              <li>不得对数据进行恶意篡改、删除或破坏</li>
              <li>遵守数据服务商的使用条款和限制</li>
            </ul>
          </Paragraph>
          <Paragraph>
            <Text strong>4.3 数据存储</Text>
            <br />
            用户在使用本平台过程中产生的策略、回测结果等数据，将存储在我们的服务器上。我们承诺采取合理的安全措施保护用户数据，但不保证数据的绝对安全。
          </Paragraph>

          <Title level={3}>五、账户安全</Title>
          <Paragraph>
            <Text strong>5.1 账户安全责任</Text>
            <br />
            用户有责任维护账户信息的安全，包括但不限于：
            <ul>
              <li>使用强密码并定期更换</li>
              <li>不向他人泄露账户信息</li>
              <li>发现账户异常及时通知我们</li>
              <li>妥善保管 API 密钥等敏感信息</li>
            </ul>
          </Paragraph>
          <Paragraph>
            <Text strong>5.2 账户安全措施</Text>
            <br />
            我们采用行业标准的安全措施保护用户账户，包括但不限于：
            <ul>
              <li>密码加密存储</li>
              <li>JWT 令牌认证</li>
              <li>API 密钥管理</li>
              <li>访问日志记录</li>
            </ul>
          </Paragraph>

          <Title level={3}>六、服务变更和终止</Title>
          <Paragraph>
            <Text strong>6.1 服务变更</Text>
            <br />
            我们有权根据业务发展需要，对服务内容、功能、界面等进行调整、更新或升级。我们会尽可能提前通知用户，但不对因此给用户造成的任何损失承担责任。
          </Paragraph>
          <Paragraph>
            <Text strong>6.2 服务终止</Text>
            <br />
            在以下情况下，我们有权终止向用户提供服务：
            <ul>
              <li>用户违反本协议或相关法律法规</li>
              <li>用户长期未使用账户（超过一年）</li>
              <li>因不可抗力导致无法继续提供服务</li>
              <li>其他合理原因</li>
            </ul>
          </Paragraph>

          <Title level={3}>七、知识产权</Title>
          <Paragraph>
            本平台的所有内容，包括但不限于软件、代码、界面设计、文字、图片、数据等，均受知识产权法保护。未经我们书面许可，用户不得复制、传播、修改或用于其他商业目的。
          </Paragraph>

          <Title level={3}>八、其他条款</Title>
          <Paragraph>
            <Text strong>8.1 协议修改</Text>
            <br />
            我们有权根据法律法规变化和业务发展需要，对本协议进行修改。修改后的协议将在本平台公布，用户继续使用服务即视为接受修改后的协议。
          </Paragraph>
          <Paragraph>
            <Text strong>8.2 法律适用</Text>
            <br />
            本协议的订立、执行和解释均适用中华人民共和国法律。如发生争议，双方应友好协商解决；协商不成的，任何一方均可向我们所在地有管辖权的人民法院提起诉讼。
          </Paragraph>
          <Paragraph>
            <Text strong>8.3 联系方式</Text>
            <br />
            如您对本协议有任何疑问，可通过以下方式联系我们：
            <ul>
              <li>邮箱：kevin@vip.qq.com</li>
              <li>微信：zquant2025</li>
              <li>Issues：https://github.com/zquant/zquant/issues</li>
            </ul>
          </Paragraph>

          <Paragraph style={{ marginTop: '32px', textAlign: 'center' }}>
            <Text type="secondary">
              感谢您使用 ZQuant量化分析平台！
            </Text>
          </Paragraph>
        </Typography>
      </Card>
    </PageContainer>
  );
};

export default UserAgreement;

