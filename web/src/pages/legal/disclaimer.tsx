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
import { history, Helmet } from '@umijs/max';
import { Button, Card, Typography } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import React from 'react';
import Settings from '../../../config/defaultSettings';

const { Title, Paragraph, Text } = Typography;

const Disclaimer: React.FC = () => {
  return (
    <>
      <Helmet>
        <title>免责申明{Settings.title && ` - ${Settings.title}`}</title>
      </Helmet>
      <PageContainer
        title="免责申明"
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
          <Title level={2}>ZQuant量化分析平台免责申明</Title>
          
          <Paragraph>
            <Text strong>生效日期：</Text>2025年12月1日
          </Paragraph>
          
          <Paragraph>
            <Text strong>最后更新：</Text>2025年12月1日
          </Paragraph>

          <Paragraph style={{ marginTop: '24px' }}>
            <Text strong style={{ fontSize: '16px' }}>
              重要提示：在使用本平台之前，请您仔细阅读本免责申明。使用本平台即表示您已充分理解并同意接受本免责申明的全部内容。
            </Text>
          </Paragraph>

          <Title level={3}>一、投资风险提示</Title>
          <Paragraph>
            <Text strong>1.1 市场风险</Text>
            <br />
            股票投资存在固有风险，包括但不限于：
            <ul>
              <li>市场波动风险：股票价格可能因市场因素大幅波动</li>
              <li>流动性风险：某些股票可能存在流动性不足的情况</li>
              <li>政策风险：政策变化可能对股票市场产生重大影响</li>
              <li>经济风险：宏观经济环境变化可能影响股票表现</li>
            </ul>
            投资有风险，入市需谨慎。本平台不对任何投资损失承担责任。
          </Paragraph>
          <Paragraph>
            <Text strong>1.2 投资决策责任</Text>
            <br />
            本平台提供的所有信息、数据、分析结果、策略建议等，仅供用户参考，不构成任何投资建议或推荐。用户应基于自己的独立判断做出投资决策，并自行承担所有投资风险和损失。
          </Paragraph>

          <Title level={3}>二、数据准确性免责</Title>
          <Paragraph>
            <Text strong>2.1 数据来源</Text>
            <br />
            本平台使用的数据主要来源于第三方数据服务商（如 Tushare 等），我们不对数据的准确性、完整性、及时性做出任何保证或承诺。
          </Paragraph>
          <Paragraph>
            <Text strong>2.2 数据使用风险</Text>
            <ul>
              <li>数据可能存在延迟、错误或不完整的情况</li>
              <li>数据可能因技术故障、网络问题等原因中断或缺失</li>
              <li>数据服务商可能变更数据格式或停止提供服务</li>
              <li>我们不对因数据问题导致的任何损失承担责任</li>
            </ul>
          </Paragraph>
          <Paragraph>
            <Text strong>2.3 数据更新</Text>
            <br />
            我们努力确保数据的及时更新，但不保证所有数据都能实时更新。用户在使用数据时应自行验证数据的准确性。
          </Paragraph>

          <Title level={3}>三、策略回测结果免责</Title>
          <Paragraph>
            <Text strong>3.1 回测结果说明</Text>
            <br />
            本平台提供的策略回测功能是基于历史数据进行的模拟测试，回测结果仅反映策略在历史数据上的表现，不代表未来实际投资结果。
          </Paragraph>
          <Paragraph>
            <Text strong>3.2 回测结果局限性</Text>
            <ul>
              <li>历史表现不代表未来收益：过去的表现不能保证未来的结果</li>
              <li>回测环境与实盘环境存在差异：滑点、手续费、市场冲击等因素可能影响实际表现</li>
              <li>数据偏差：回测使用的历史数据可能存在偏差或异常值</li>
              <li>策略过拟合：策略可能在历史数据上表现良好，但在未来表现不佳</li>
            </ul>
          </Paragraph>
          <Paragraph>
            <Text strong>3.3 实盘交易风险</Text>
            <br />
            用户应充分理解，将回测结果用于实盘交易存在重大风险。实盘交易可能因各种因素（如市场环境变化、执行成本、流动性问题等）产生与回测结果显著不同的结果，甚至造成重大损失。
          </Paragraph>

          <Title level={3}>四、系统故障免责</Title>
          <Paragraph>
            <Text strong>4.1 系统可用性</Text>
            <br />
            我们努力确保本平台的稳定运行，但不保证系统不会出现故障、中断、延迟或其他技术问题。因系统故障导致的任何损失，我们不承担责任。
          </Paragraph>
          <Paragraph>
            <Text strong>4.2 系统维护</Text>
            <br />
            我们有权进行系统维护、升级或更新，期间可能暂停服务。我们会尽可能提前通知用户，但不对维护期间的服务中断承担责任。
          </Paragraph>
          <Paragraph>
            <Text strong>4.3 网络安全</Text>
            <br />
            虽然我们采取了合理的安全措施，但无法保证系统绝对安全。因网络攻击、病毒、恶意软件等导致的任何损失，我们不承担责任。
          </Paragraph>

          <Title level={3}>五、第三方服务免责</Title>
          <Paragraph>
            <Text strong>5.1 第三方数据服务</Text>
            <br />
            本平台依赖第三方数据服务商提供数据。如果第三方服务中断、变更或停止，可能影响本平台的正常使用。我们不对第三方服务的问题承担责任。
          </Paragraph>
          <Paragraph>
            <Text strong>5.2 第三方链接</Text>
            <br />
            本平台可能包含指向第三方网站的链接。我们不对第三方网站的内容、服务或隐私政策负责。访问第三方网站的风险由用户自行承担。
          </Paragraph>

          <Title level={3}>六、用户行为责任</Title>
          <Paragraph>
            <Text strong>6.1 用户决策责任</Text>
            <br />
            用户在使用本平台时做出的所有决策，包括但不限于策略选择、参数设置、投资决策等，均由用户自行负责。我们不对用户的决策结果承担责任。
          </Paragraph>
          <Paragraph>
            <Text strong>6.2 违规使用责任</Text>
            <br />
            如果用户违反本协议、相关法律法规或平台规则，导致任何损失或法律责任，由用户自行承担。我们有权采取必要措施，包括但不限于暂停或终止服务、追究法律责任等。
          </Paragraph>

          <Title level={3}>七、责任限制</Title>
          <Paragraph>
            <Text strong>7.1 责任范围</Text>
            <br />
            在法律允许的最大范围内，我们对因使用或无法使用本平台而产生的任何直接、间接、偶然、特殊或后果性损失不承担责任，包括但不限于：
            <ul>
              <li>投资损失或利润损失</li>
              <li>数据丢失或损坏</li>
              <li>业务中断损失</li>
              <li>商誉损失</li>
              <li>其他经济损失</li>
            </ul>
          </Paragraph>
          <Paragraph>
            <Text strong>7.2 责任上限</Text>
            <br />
            即使我们被认定对某些损失承担责任，我们的责任总额也不应超过用户在过去12个月内向我们支付的费用总额（如有）。
          </Paragraph>

          <Title level={3}>八、其他说明</Title>
          <Paragraph>
            <Text strong>8.1 免责申明修改</Text>
            <br />
            我们有权根据法律法规变化和业务发展需要，对本免责申明进行修改。修改后的免责申明将在本平台公布，用户继续使用服务即视为接受修改后的免责申明。
          </Paragraph>
          <Paragraph>
            <Text strong>8.2 法律适用</Text>
            <br />
            本免责申明的订立、执行和解释均适用中华人民共和国法律。如发生争议，双方应友好协商解决；协商不成的，任何一方均可向我们所在地有管辖权的人民法院提起诉讼。
          </Paragraph>
          <Paragraph>
            <Text strong>8.3 联系方式</Text>
            <br />
            如您对本免责申明有任何疑问，可通过以下方式联系我们：
            <ul>
              <li>邮箱：kevin@vip.qq.com</li>
              <li>微信：zquant2025</li>
              <li>Issues：https://github.com/zquant/zquant/issues</li>
            </ul>
          </Paragraph>

          <Paragraph style={{ marginTop: '32px', textAlign: 'center' }}>
            <Text type="secondary" strong>
              再次提醒：投资有风险，入市需谨慎。请理性投资，量力而行。
            </Text>
          </Paragraph>
        </Typography>
      </Card>
    </PageContainer>
    </>
  );
};

export default Disclaimer;

