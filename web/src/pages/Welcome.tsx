// Copyright 2025 ZQuant Authors.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
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
import { history, useModel, Helmet } from '@umijs/max';
import { Card, Col, Row, Tag, theme, Typography, Collapse, Space } from 'antd';
import React from 'react';
import {
  DatabaseOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  BarChartOutlined,
  UserOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import Settings from '../../config/defaultSettings';

const { Title, Paragraph, Text } = Typography;

/**
 * 功能卡片组件
 */
const FeatureCard: React.FC<{
  title: string;
  icon: React.ReactNode;
  desc: string;
  href?: string;
  onClick?: () => void;
}> = ({ title, icon, desc, href, onClick }) => {
  const { useToken } = theme;
  const { token } = useToken();

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else if (href) {
      if (href.startsWith('http')) {
        window.open(href, '_blank');
      } else {
        history.push(href);
      }
    }
  };

  return (
    <Card
      hoverable
      onClick={handleClick}
      style={{
        height: '100%',
        cursor: 'pointer',
        transition: 'all 0.3s',
      }}
      styles={{
        body: {
          padding: '20px',
        },
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ fontSize: '32px', color: token.colorPrimary }}>
          {icon}
        </div>
        <Title level={4} style={{ margin: 0 }}>
          {title}
        </Title>
        <Paragraph
          style={{
            margin: 0,
            color: token.colorTextSecondary,
            fontSize: '14px',
            lineHeight: '1.6',
          }}
        >
          {desc}
        </Paragraph>
      </div>
    </Card>
  );
};

/**
 * 快速开始步骤卡片
 */
const QuickStartCard: React.FC<{
  step: number;
  title: string;
  content: string;
}> = ({ step, title, content }) => {
  const { useToken } = theme;
  const { token } = useToken();

  return (
    <Card
      style={{
        height: '100%',
        border: `1px solid ${token.colorBorderSecondary}`,
      }}
    >
      <div style={{ display: 'flex', gap: '16px' }}>
        <div
          style={{
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            backgroundColor: token.colorPrimary,
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 'bold',
            flexShrink: 0,
          }}
        >
          {step}
        </div>
        <div style={{ flex: 1 }}>
          <Title level={5} style={{ margin: '0 0 8px 0' }}>
            {title}
          </Title>
          <Paragraph
            style={{
              margin: 0,
              color: token.colorTextSecondary,
              fontSize: '14px',
            }}
          >
            {content}
          </Paragraph>
        </div>
      </div>
    </Card>
  );
};

/**
 * 文档链接卡片
 */
const DocCard: React.FC<{
  title: string;
  desc: string;
  href: string;
  onClick?: () => void;
}> = ({ title, desc, href, onClick }) => {
  const { useToken } = theme;
  const { token } = useToken();

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else if (href.startsWith('http')) {
      window.open(href, '_blank');
    } else {
      history.push(href);
    }
  };

  return (
    <Card
      hoverable
      onClick={handleClick}
      style={{
        height: '100%',
        cursor: 'pointer',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <Title level={5} style={{ margin: 0 }}>
          {title}
        </Title>
        <Paragraph
          style={{
            margin: 0,
            color: token.colorTextSecondary,
            fontSize: '14px',
          }}
        >
          {desc}
        </Paragraph>
        <Text
          type="secondary"
          style={{ fontSize: '12px', marginTop: '8px' }}
        >
          点击查看 {'>'}
        </Text>
      </div>
    </Card>
  );
};

const Welcome: React.FC = () => {
  const { token } = theme.useToken();
  const { initialState } = useModel('@@initialState');

  // 核心功能数据
  const features = [
    {
      title: '数据管理',
      icon: <DatabaseOutlined />,
      desc: '支持 Tushare 专业数据源，自动采集、清洗和存储股票数据。提供日线、分钟线、财务数据等多种数据类型，支持复权处理和交易日历管理。',
      href: '/data',
    },
    {
      title: '回测引擎',
      icon: <ExperimentOutlined />,
      desc: '事件驱动的回测系统，支持多种策略类型。按交易日历推进，模拟真实交易环境，包括交易成本（佣金、印花税、滑点）和涨跌停限制。',
      href: '/backtest',
    },
    {
      title: '策略管理',
      icon: <FileTextOutlined />,
      desc: '完整的策略增删改查功能，支持8种策略模板库。涵盖技术分析、基本面分析和量化策略，支持自定义策略和策略分类管理。',
      href: '/backtest/strategies',
    },
    {
      title: '绩效分析',
      icon: <BarChartOutlined />,
      desc: '全面的回测绩效指标，包括收益率、夏普比率、最大回撤、Alpha、Beta等。提供详细的回测报告和可视化图表。',
      href: '/backtest',
    },
    {
      title: '用户系统',
      icon: <UserOutlined />,
      desc: '基于 JWT 的认证和 RBAC 权限控制。支持多用户管理、角色分配、API密钥管理，保障系统安全。',
      href: '/admin/users',
    },
    {
      title: '定时任务',
      icon: <ClockCircleOutlined />,
      desc: '灵活的调度配置、实时状态监控、任务编排。支持Cron表达式和间隔调度，提供任务依赖关系和失败处理策略。',
      href: '/admin/scheduler',
    },
  ];

  // 快速开始步骤
  const quickStartSteps = [
    {
      step: 1,
      title: '安装依赖',
      content: '运行 pip install -r requirements.txt 安装项目依赖。确保Python版本为3.11或更高。',
    },
    {
      step: 2,
      title: '配置环境变量',
      content: '复制 .env.example 为 .env 并修改配置。需要配置数据库连接、Redis地址、Tushare Token等关键信息。',
    },
    {
      step: 3,
      title: '初始化数据库',
      content: '创建MySQL数据库并运行 alembic upgrade head 进行迁移。数据库字符集建议使用utf8mb4。',
    },
    {
      step: 4,
      title: '启动服务',
      content: '运行 uvicorn zquant.main:app --reload --host 0.0.0.0 --port 8000 启动后端服务。访问 http://localhost:8000/docs 查看API文档。',
    },
  ];

  // 文档链接
  const docs = [
    {
      title: '策略管理文档',
      desc: '了解如何创建、管理和使用策略模板',
      href: 'https://github.com/zquant/zquant/blob/main/docs/strategy_management.md',
    },
    {
      title: '定时任务指南',
      desc: '学习如何使用定时任务系统和任务编排',
      href: 'https://github.com/zquant/zquant/blob/main/docs/scheduler_guide.md',
    },
    {
      title: 'API 访问指南',
      desc: '了解如何正确访问和配置 API 服务',
      href: 'https://github.com/zquant/zquant/blob/main/API_ACCESS.md',
    },
    {
      title: '项目文档网站',
      desc: '访问完整的项目文档和 API 参考',
      href: 'https://docs.zquant.com',
    },
  ];

  // 技术栈
  const techStack = [
    { name: 'FastAPI', githubUrl: 'https://github.com/tiangolo/fastapi' },
    { name: 'MySQL', githubUrl: 'https://github.com/mysql/mysql-server' },
    { name: 'Redis', githubUrl: 'https://github.com/redis/redis' },
    { name: 'Celery', githubUrl: 'https://github.com/celery/celery' },
    { name: 'APScheduler', githubUrl: 'https://github.com/agronholm/apscheduler' },
    { name: 'Tushare', githubUrl: 'https://github.com/waditu/tushare' },
    { name: 'JWT' }, // JWT是标准协议，没有单一GitHub仓库
    { name: 'SQLAlchemy', githubUrl: 'https://github.com/sqlalchemy/sqlalchemy' },
  ];

  return (
    <>
      <Helmet>
        <title>欢迎{Settings.title && ` - ${Settings.title}`}</title>
      </Helmet>
      <PageContainer>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* 页面头部 */}
        <Card
          style={{
            borderRadius: 8,
          }}
          styles={{
            body: {
              backgroundImage:
                initialState?.settings?.navTheme === 'realDark'
                  ? 'linear-gradient(75deg, #1A1B1F 0%, #191C1F 100%)'
                  : 'linear-gradient(75deg, #FBFDFF 0%, #F5F7FF 100%)',
              padding: '32px',
            },
          }}
        >
          <div
            style={{
              backgroundPosition: '100% -30%',
              backgroundRepeat: 'no-repeat',
              backgroundSize: '274px auto',
              backgroundImage:
                "url('https://gw.alipayobjects.com/mdn/rms_a9745b/afts/img/A*BuFmQqsB2iAAAAAAAAAAAAAAARQnAQ')",
            }}
          >
            <Title
              level={2}
              style={{
                margin: 0,
                color: token.colorTextHeading,
              }}
            >
              欢迎使用 ZQuant量化分析平台
            </Title>
            <Paragraph
              style={{
                fontSize: '16px',
                color: token.colorTextSecondary,
                lineHeight: '1.8',
                marginTop: '16px',
                marginBottom: '16px',
                maxWidth: '65%',
              }}
            >
              ZQuant量化分析平台是一个功能完整的股票量化分析系统，基于 FastAPI
              构建，提供数据服务、回测引擎、策略管理等功能，旨在为量化分析者提供从数据采集、策略开发、回测分析到结果管理的一站式解决方案。
            </Paragraph>
            <Paragraph
              style={{
                fontSize: '14px',
                color: token.colorTextTertiary,
                lineHeight: '1.6',
                marginTop: '8px',
                maxWidth: '65%',
              }}
            >
              ✨ 开箱即用 • 📊 数据驱动 • 🔬 回测引擎 • 🎯 策略模板 • 🔐 安全可靠 • ⚡ 高性能
            </Paragraph>
            <div style={{ marginTop: '16px', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <a
                href="/legal/user-agreement"
                onClick={(e) => {
                  e.preventDefault();
                  history.push('/legal/user-agreement');
                }}
                style={{
                  color: token.colorPrimary,
                  textDecoration: 'none',
                  fontSize: '14px',
                }}
              >
                《用户协议》
              </a>
              <span style={{ color: token.colorTextSecondary }}></span>
              <a
                href="/legal/disclaimer"
                onClick={(e) => {
                  e.preventDefault();
                  history.push('/legal/disclaimer');
                }}
                style={{
                  color: token.colorPrimary,
                  textDecoration: 'none',
                  fontSize: '14px',
                }}
              >
              《免责申明》
              </a>
            </div>
          </div>
        </Card>

        {/* 项目目标 */}
        <Card title="项目目标" style={{ borderRadius: 8 }}>
          <Row gutter={[24, 24]}>
            <Col xs={24} lg={16}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <Paragraph
                  style={{
                    fontSize: '16px',
                    color: token.colorText,
                    lineHeight: '1.8',
                    margin: 0,
                  }}
                >
                  <Text strong style={{ fontSize: '18px' }}>
                    为个人用户提供轻量、开源、专业的量化分析平台。
                  </Text>
                </Paragraph>
                <Paragraph
                  style={{
                    fontSize: '16px',
                    color: token.colorText,
                    lineHeight: '1.8',
                    margin: 0,
                  }}
                >
                  <Text>
                    最小化系统成本，只需Tushare的一个token，即可搭建自己的量化分析平台。
                  </Text>
                </Paragraph>
                <Paragraph
                  style={{
                    fontSize: '16px',
                    color: token.colorTextSecondary,
                    lineHeight: '1.8',
                    margin: 0,
                    marginTop: '8px',
                  }}
                >
                  <Text>
                    ZQuant致力于降低量化分析的门槛，让个人投资者也能享受到专业级的量化工具。
                    我们提供从数据采集、策略开发、回测分析到结果管理的一站式解决方案，
                    帮助您构建属于自己的量化投资系统，实现更科学、更理性的投资决策。
                  </Text>
                </Paragraph>
                <Paragraph
                  style={{
                    fontSize: '16px',
                    color: token.colorPrimary,
                    lineHeight: '1.8',
                    margin: 0,
                    marginTop: '16px',
                    padding: '16px',
                    backgroundColor: token.colorFillTertiary,
                    borderRadius: '8px',
                  }}
                >
                  <Text>
                    💡 欢迎关注我们的公众号，添加微信好友进行咨询并参与共建。
                    我们期待与您一起完善这个量化分析平台，共同推动量化分析和投资的发展！
                  </Text>
                </Paragraph>
              </div>
            </Col>
            <Col xs={24} lg={8}>
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'row',
                  gap: '24px',
                  justifyContent: 'center',
                  alignItems: 'flex-start',
                  flexWrap: 'wrap',
                }}
              >
                <div style={{ textAlign: 'center' }}>
                  <img
                    src="/wechat/zquant.jpg"
                    alt="微信号"
                    style={{
                      width: '200px',
                      height: '200px',
                      objectFit: 'contain',
                      borderRadius: '8px',
                      border: `1px solid ${token.colorBorderSecondary}`,
                    }}
                  />
                  <div style={{ marginTop: '12px' }}>
                    <Text strong style={{ fontSize: '14px' }}>
                      微信号(zquant2005)
                    </Text>
                  </div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <img
                    src="/wechat/bdnotes.jpg"
                    alt="微信公众号"
                    style={{
                      width: '200px',
                      height: '200px',
                      objectFit: 'contain',
                      borderRadius: '8px',
                      border: `1px solid ${token.colorBorderSecondary}`,
                    }}
                  />
                  <div style={{ marginTop: '12px' }}>
                    <Text strong style={{ fontSize: '14px' }}>
                      微信公众号(bdnotes)
                    </Text>
                  </div>
                </div>
              </div>
            </Col>
          </Row>
        </Card>

        {/* 核心功能展示 */}
        <Card title="核心功能" style={{ borderRadius: 8 }}>
          <Row gutter={[16, 16]}>
            {features.map((feature, index) => (
              <Col xs={24} sm={12} lg={8} key={index}>
                <FeatureCard {...feature} />
              </Col>
            ))}
          </Row>
        </Card>

        {/* 快速开始 */}
        <Card title="快速开始" style={{ borderRadius: 8 }}>
          <Row gutter={[16, 16]}>
            {quickStartSteps.map((step) => (
              <Col xs={24} sm={12} key={step.step}>
                <QuickStartCard {...step} />
              </Col>
            ))}
          </Row>
          <Collapse
            ghost
            style={{ marginTop: '16px' }}
            items={[
              {
                key: '1',
                label: '查看详细步骤',
                children: (
                  <div style={{ padding: '16px 0' }}>
                    <Paragraph>
                      <Text strong>1. 安装依赖</Text>
                      <br />
                      <Text code>pip install -r requirements.txt</Text>
                    </Paragraph>
                    <Paragraph>
                      <Text strong>2. 配置环境变量</Text>
                      <br />
                      <Text code>cp .env.example .env</Text>
                      <br />
                      然后修改 .env 文件中的配置项
                    </Paragraph>
                    <Paragraph>
                      <Text strong>3. 初始化数据库</Text>
                      <br />
                      <Text code>
                        mysql -u root -p -e "CREATE DATABASE zquant CHARACTER
                        SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                      </Text>
                      <br />
                      <Text code>alembic upgrade head</Text>
                    </Paragraph>
                    <Paragraph>
                      <Text strong>4. 启动服务</Text>
                      <br />
                      <Text code>
                        uvicorn zquant.main:app --reload --host 0.0.0.0 --port
                        8000
                      </Text>
                      <br />
                      访问 http://localhost:8000/docs 查看 API 文档
                      <br />
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        注意：使用 --host 0.0.0.0 允许从任何IP访问，但访问时请使用 http://localhost:8000 或服务器的实际IP地址
                      </Text>
                    </Paragraph>
                    <Paragraph>
                      <Text strong>5. 验证安装</Text>
                      <br />
                      访问 http://localhost:8000/health 检查服务是否正常运行
                    </Paragraph>
                    <Paragraph>
                      <Text strong>6. 启动前端（可选）</Text>
                      <br />
                      <Text code>cd web</Text>
                      <br />
                      <Text code>npm install</Text>
                      <br />
                      <Text code>npm start</Text>
                      <br />
                      前端默认运行在 http://localhost:8001
                    </Paragraph>
                  </div>
                ),
              },
            ]}
          />
        </Card>

        {/* 使用手册 */}
        <Card title="使用手册" style={{ borderRadius: 8 }}>
          <Row gutter={[16, 16]}>
            {docs.map((doc, index) => (
              <Col xs={24} sm={12} lg={6} key={index}>
                <DocCard {...doc} />
              </Col>
            ))}
          </Row>
        </Card>

        {/* 法律声明 */}
        <Card title="法律声明" style={{ borderRadius: 8 }}>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12}>
              <DocCard
                title="用户协议"
                desc="了解平台使用条款、用户权利和义务"
                href="/legal/user-agreement"
                onClick={() => history.push('/legal/user-agreement')}
              />
            </Col>
            <Col xs={24} sm={12}>
              <DocCard
                title="免责申明"
                desc="了解投资风险提示和免责条款"
                href="/legal/disclaimer"
                onClick={() => history.push('/legal/disclaimer')}
              />
            </Col>
          </Row>
        </Card>

        {/* 技术栈 */}
        <Card title="技术栈" style={{ borderRadius: 8 }}>
          <Space size={[8, 8]} wrap>
            {techStack.map((tech) => (
              <Tag
                key={tech.name}
                color={token.colorPrimary}
                style={{
                  padding: '4px 12px',
                  fontSize: '14px',
                  borderRadius: '4px',
                  cursor: tech.githubUrl ? 'pointer' : 'default',
                }}
                onClick={() => {
                  if (tech.githubUrl) {
                    window.open(tech.githubUrl, '_blank');
                  }
                }}
              >
                {tech.name}
              </Tag>
            ))}
          </Space>
        </Card>
      </div>
    </PageContainer>
    </>
  );
};

export default Welcome;
