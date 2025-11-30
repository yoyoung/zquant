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
import { Card, Row, Col, Statistic, Button, Space, message, Spin, Divider, Tooltip } from 'antd';
import { ReloadOutlined, CheckCircleOutlined, CloseCircleOutlined, DatabaseOutlined, TableOutlined, CheckOutlined, CloseOutlined, PlusOutlined, EditOutlined, InfoCircleOutlined, CalendarOutlined, ClockCircleOutlined } from '@ant-design/icons';
import React, { useState, useEffect, useCallback } from 'react';
import { getSyncStatus, getTaskStats, getLocalDataStats } from '@/services/zquant/dashboard';
import { Helmet } from '@umijs/max';
import Settings from '../../../config/defaultSettings';
import dayjs from 'dayjs';

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [syncStatus, setSyncStatus] = useState<ZQuant.SyncStatusResponse | null>(null);
  const [taskStats, setTaskStats] = useState<ZQuant.TaskStatsResponse | null>(null);
  const [localDataStats, setLocalDataStats] = useState<ZQuant.LocalDataStatsResponse | null>(null);
  const [currentTime, setCurrentTime] = useState<dayjs.Dayjs>(dayjs());
  const [lastRefreshTime, setLastRefreshTime] = useState<dayjs.Dayjs | null>(null);

  // 获取同步状态
  const fetchSyncStatus = useCallback(async () => {
    try {
      const response = await getSyncStatus();
      setSyncStatus(response);
    } catch (error: any) {
      message.error(`获取同步状态失败: ${error.message || '未知错误'}`);
    }
  }, []);

  // 获取任务统计
  const fetchTaskStats = useCallback(async () => {
    try {
      const response = await getTaskStats();
      setTaskStats(response);
    } catch (error: any) {
      message.error(`获取任务统计失败: ${error.message || '未知错误'}`);
    }
  }, []);

  // 获取本地数据统计
  const fetchLocalDataStats = useCallback(async () => {
    try {
      const response = await getLocalDataStats();
      setLocalDataStats(response);
    } catch (error: any) {
      message.error(`获取本地数据统计失败: ${error.message || '未知错误'}`);
    }
  }, []);

  // 获取所有数据
  const fetchAllData = useCallback(async () => {
    setLoading(true);
    try {
      await Promise.all([fetchSyncStatus(), fetchTaskStats(), fetchLocalDataStats()]);
      setLastRefreshTime(dayjs());
    } finally {
      setLoading(false);
    }
  }, [fetchSyncStatus, fetchTaskStats, fetchLocalDataStats]);

  // 初始加载
  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  // 5分钟自动刷新
  useEffect(() => {
    const interval = setInterval(() => {
      fetchAllData();
    }, 5 * 60 * 1000); // 5分钟

    return () => clearInterval(interval);
  }, [fetchAllData]);

  // 实时更新时间（每秒更新一次）
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(dayjs());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // 格式化日期显示
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '无数据';
    return dateStr;
  };

  // 格式化日期（年月日）
  const formatDateDisplay = (date: dayjs.Dayjs) => {
    return date.format('YYYY年MM月DD日');
  };

  // 格式化时间（时:分:秒）
  const formatTimeDisplay = (date: dayjs.Dayjs) => {
    return date.format('HH:mm:ss');
  };

  // 获取星期几（中文）
  const getWeekday = (date: dayjs.Dayjs) => {
    const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
    return `星期${weekdays[date.day()]}`;
  };

  // 判断开市/闭市状态
  const getTradingStatus = (isTradingDay: boolean | null, currentTime: dayjs.Dayjs) => {
    // 如果不是交易日，直接返回闭市
    if (!isTradingDay) {
      return { status: '闭市', color: '#faad14' };
    }

    const hour = currentTime.hour();
    const minute = currentTime.minute();
    const timeInMinutes = hour * 60 + minute;

    // A股交易时间：上午 9:30-11:30，下午 13:00-15:00
    const morningStart = 9 * 60 + 30; // 9:30
    const morningEnd = 11 * 60 + 30; // 11:30
    const afternoonStart = 13 * 60; // 13:00
    const afternoonEnd = 15 * 60; // 15:00

    if (
      (timeInMinutes >= morningStart && timeInMinutes < morningEnd) ||
      (timeInMinutes >= afternoonStart && timeInMinutes < afternoonEnd)
    ) {
      return { status: '开市', color: '#52c41a' };
    } else {
      return { status: '闭市', color: '#faad14' };
    }
  };

  return (
    <>
      <Helmet>
        <title>系统大盘{Settings.title && ` - ${Settings.title}`}</title>
      </Helmet>
      <PageContainer 
        title="系统大盘" 
        subTitle="实时监控系统关键指标"
        extra={
          <Space>
            {lastRefreshTime && (
              <span style={{ color: 'rgba(0, 0, 0, 0.45)', fontSize: '14px' }}>
                最后刷新：{lastRefreshTime.format('YYYY-MM-DD HH:mm:ss')}
              </span>
            )}
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={fetchAllData}
              loading={loading}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Spin spinning={loading}>
          {/* 时间信息展示 */}
          <Card title="时间信息" style={{ marginBottom: 24 }}>
            <Row gutter={[16, 16]} style={{ display: 'flex', flexWrap: 'nowrap' }}>
              {/* 当前日期 */}
              <Col flex={1}>
                <Card
                  bordered={false}
                  title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>当前日期</span>}
                  headStyle={{ borderBottom: 'none' }}
                  bodyStyle={{ textAlign: 'center' }}
                >
                  <Statistic
                    value={formatDateDisplay(currentTime)}
                    prefix={<CalendarOutlined style={{ color: '#1890ff' }} />}
                    valueStyle={{ color: '#1890ff' }}
                    style={{ marginTop: '-12px' }}
                  />
                </Card>
              </Col>

              {/* 北京时间 */}
              <Col flex={1}>
                <Card
                  bordered={false}
                  title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>北京时间</span>}
                  headStyle={{ borderBottom: 'none' }}
                  bodyStyle={{ textAlign: 'center' }}
                >
                  <Statistic
                    value={formatTimeDisplay(currentTime)}
                    prefix={<ClockCircleOutlined style={{ color: '#1890ff' }} />}
                    valueStyle={{ color: '#1890ff', fontSize: '24px' }}
                    style={{ marginTop: '-12px' }}
                  />
                </Card>
              </Col>

              {/* 星期 */}
              <Col flex={1}>
                <Card
                  bordered={false}
                  title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>星期</span>}
                  headStyle={{ borderBottom: 'none' }}
                  bodyStyle={{ textAlign: 'center' }}
                >
                  <Statistic
                    value={getWeekday(currentTime)}
                    valueStyle={{ color: '#722ed1' }}
                    style={{ marginTop: '-12px' }}
                  />
                </Card>
              </Col>

              {/* 交易日状态 */}
              <Col flex={1}>
                <Card
                  bordered={false}
                  title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>交易日状态</span>}
                  headStyle={{ borderBottom: 'none' }}
                  bodyStyle={{ textAlign: 'center' }}
                >
                  <Statistic
                    value={syncStatus ? (syncStatus.is_trading_day ? '交易日' : '非交易日') : '加载中...'}
                    prefix={
                      syncStatus ? (
                        syncStatus.is_trading_day ? (
                          <CheckCircleOutlined style={{ color: '#52c41a' }} />
                        ) : (
                          <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                        )
                      ) : null
                    }
                    valueStyle={{
                      color: syncStatus
                        ? syncStatus.is_trading_day
                          ? '#52c41a'
                          : '#ff4d4f'
                        : '#8c8c8c',
                    }}
                    style={{ marginTop: '-12px' }}
                  />
                </Card>
              </Col>

              {/* 开市状态 */}
              <Col flex={1}>
                <Card
                  bordered={false}
                  title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>开市状态</span>}
                  headStyle={{ borderBottom: 'none' }}
                  bodyStyle={{ textAlign: 'center' }}
                >
                  {(() => {
                    const tradingStatus = getTradingStatus(syncStatus?.is_trading_day ?? null, currentTime);
                    return (
                      <Statistic
                        value={tradingStatus.status}
                        prefix={
                          tradingStatus.status === '开市' ? (
                            <CheckCircleOutlined style={{ color: '#52c41a' }} />
                          ) : tradingStatus.status === '闭市' ? (
                            <CloseCircleOutlined style={{ color: '#faad14' }} />
                          ) : null
                        }
                        valueStyle={{ color: tradingStatus.color }}
                        style={{ marginTop: '-12px' }}
                      />
                    );
                  })()}
                </Card>
              </Col>
            </Row>
          </Card>

          <Card
            title="数据同步"
            style={{ marginBottom: 24 }}
          >
            <Row gutter={[16, 16]}>
              {/* Tushare同步链路状态 */}
              <Col xs={24} sm={12} lg={6}>
                <Card
                  bordered={false}
                  title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>Tushare同步链路</span>}
                  headStyle={{ borderBottom: 'none' }}
                  bodyStyle={{ textAlign: 'center' }}
                  extra={
                    <Tooltip title="显示Tushare数据同步链路的状态信息，包括连接状态等">
                      <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                    </Tooltip>
                  }
                >
                  <Statistic
                    value={syncStatus ? (syncStatus.tushare_connection_status ? '正常' : '异常') : '加载中...'}
                    prefix={
                      syncStatus ? (
                        syncStatus.tushare_connection_status ? (
                          <CheckCircleOutlined style={{ color: '#52c41a' }} />
                        ) : (
                          <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                        )
                      ) : null
                    }
                    valueStyle={{
                      color: syncStatus
                        ? syncStatus.tushare_connection_status
                          ? '#52c41a'
                          : '#ff4d4f'
                        : '#8c8c8c',
                    }}
                    style={{ marginTop: '-12px' }}
                  />
                </Card>
              </Col>

              {/* 当日是否交易日 */}
              <Col xs={24} sm={12} lg={6}>
                <Card
                  bordered={false}
                  title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>当日是否交易日</span>}
                  headStyle={{ borderBottom: 'none' }}
                  bodyStyle={{ textAlign: 'center' }}
                  extra={
                    <Tooltip title="显示当日是否为交易日，用于判断是否需要进行数据同步">
                      <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                    </Tooltip>
                  }
                >
                  <Statistic
                    value={syncStatus ? (syncStatus.is_trading_day ? '是' : '否') : '加载中...'}
                    prefix={
                      syncStatus ? (
                        syncStatus.is_trading_day ? (
                          <CheckCircleOutlined style={{ color: '#52c41a' }} />
                        ) : (
                          <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                        )
                      ) : null
                    }
                    valueStyle={{
                      color: syncStatus ? (syncStatus.is_trading_day ? '#52c41a' : '#ff4d4f') : '#8c8c8c',
                    }}
                    style={{ marginTop: '-12px' }}
                  />
                </Card>
              </Col>

              {/* Tushare接口最新日线数据日期 */}
              <Col xs={24} sm={12} lg={6}>
                <Card
                  bordered={false}
                  title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>Tushare最新日线数据日期</span>}
                  headStyle={{ borderBottom: 'none' }}
                  bodyStyle={{ textAlign: 'center' }}
                  extra={
                    <Tooltip title="显示Tushare接口返回的最新日线行情数据的交易日期">
                      <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                    </Tooltip>
                  }
                >
                  <Statistic
                    value={
                      syncStatus
                        ? formatDate(syncStatus.latest_trade_date_from_api) || '无数据'
                        : '加载中...'
                    }
                    valueStyle={{
                      color: syncStatus && syncStatus.latest_trade_date_from_api ? '#1890ff' : '#8c8c8c',
                    }}
                    style={{ marginTop: '-12px' }}
                  />
                </Card>
              </Col>

              {/* 当日数据准备状态 */}
              <Col xs={24} sm={12} lg={6}>
                <Card
                  bordered={false}
                  title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>当日数据准备状态</span>}
                  headStyle={{ borderBottom: 'none' }}
                  bodyStyle={{ textAlign: 'center' }}
                  extra={
                    <Tooltip title="显示当日日线行情数据是否已准备就绪，可用于交易分析">
                      <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                    </Tooltip>
                  }
                >
                  <Statistic
                    value={syncStatus ? (syncStatus.today_data_ready ? '已就绪' : '未就绪') : '加载中...'}
                    prefix={
                      syncStatus ? (
                        syncStatus.today_data_ready ? (
                          <CheckCircleOutlined style={{ color: '#52c41a' }} />
                        ) : (
                          <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                        )
                      ) : null
                    }
                    valueStyle={{
                      color: syncStatus ? (syncStatus.today_data_ready ? '#52c41a' : '#ff4d4f') : '#8c8c8c',
                    }}
                    style={{ marginTop: '-12px' }}
                  />
                </Card>
              </Col>
            </Row>

            {/* 额外信息：数据库中最新日线数据日期 */}
            {syncStatus && (
              <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                <Col xs={24}>
                  <Card bordered={false} size="small">
                    <Space>
                      <span style={{ fontWeight: 500 }}>数据库中最新日线数据日期：</span>
                      <span>{formatDate(syncStatus.latest_trade_date_in_db) || '无数据'}</span>
                    </Space>
                  </Card>
                </Col>
              </Row>
            )}
          </Card>

          {/* 定时任务区块 */}
          <Card
            title="定时任务"
            style={{ marginBottom: 24 }}
          >
            <Row gutter={[16, 16]}>
              {/* 当日总任务数 */}
              <Col xs={24} sm={12} lg={5}>
                <Card
                  bordered={false}
                  title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>当日总任务数</span>}
                  headStyle={{ borderBottom: 'none' }}
                  bodyStyle={{ textAlign: 'center' }}
                  extra={
                    <Tooltip title="显示当日所有定时任务的总数量">
                      <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                    </Tooltip>
                  }
                >
                  <Statistic
                    value={taskStats?.total_tasks ?? 0}
                    valueStyle={{ color: '#1890ff' }}
                    style={{ marginTop: '-12px' }}
                  />
                </Card>
              </Col>

              {/* 进行中任务数 */}
              <Col xs={24} sm={12} lg={5}>
                <Card
                  bordered={false}
                  title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>进行中任务数</span>}
                  headStyle={{ borderBottom: 'none' }}
                  bodyStyle={{ textAlign: 'center' }}
                  extra={
                    <Tooltip title="显示当前正在执行中的定时任务数量">
                      <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                    </Tooltip>
                  }
                >
                  <Statistic
                    value={taskStats?.running_tasks ?? 0}
                    prefix={<CheckCircleOutlined style={{ color: '#1890ff' }} />}
                    valueStyle={{ color: '#1890ff' }}
                    style={{ marginTop: '-12px' }}
                  />
                </Card>
              </Col>

              {/* 已完成任务数 */}
              <Col xs={24} sm={12} lg={5}>
                <Card
                  bordered={false}
                  title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>已完成任务数</span>}
                  headStyle={{ borderBottom: 'none' }}
                  bodyStyle={{ textAlign: 'center' }}
                  extra={
                    <Tooltip title="显示当日已成功完成的定时任务数量">
                      <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                    </Tooltip>
                  }
                >
                  <Statistic
                    value={taskStats?.completed_tasks ?? 0}
                    prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
                    valueStyle={{ color: '#52c41a' }}
                    style={{ marginTop: '-12px' }}
                  />
                </Card>
              </Col>

              {/* 待运行任务数 */}
              <Col xs={24} sm={12} lg={4}>
                <Card
                  bordered={false}
                  title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>待运行任务数</span>}
                  headStyle={{ borderBottom: 'none' }}
                  bodyStyle={{ textAlign: 'center' }}
                  extra={
                    <Tooltip title="显示等待执行的定时任务数量">
                      <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                    </Tooltip>
                  }
                >
                  <Statistic
                    value={taskStats?.pending_tasks ?? 0}
                    valueStyle={{ color: '#faad14' }}
                    style={{ marginTop: '-12px' }}
                  />
                </Card>
              </Col>

              {/* 出错任务数 */}
              <Col xs={24} sm={12} lg={5}>
                <Card
                  bordered={false}
                  title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>出错任务数</span>}
                  headStyle={{ borderBottom: 'none' }}
                  bodyStyle={{ textAlign: 'center' }}
                  extra={
                    <Tooltip title="显示执行失败的定时任务数量">
                      <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                    </Tooltip>
                  }
                >
                  <Statistic
                    value={taskStats?.failed_tasks ?? 0}
                    prefix={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
                    valueStyle={{ color: '#ff4d4f' }}
                    style={{ marginTop: '-12px' }}
                  />
                </Card>
              </Col>
            </Row>
          </Card>

          {/* 本地数据区块 */}
          <Card
            title="本地数据"
            style={{ marginBottom: 24 }}
          >
            {/* 数据操作日志数据 */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ marginBottom: 16, fontSize: '16px', fontWeight: 500, color: '#1890ff' }}>
                数据操作日志
              </div>
              <Row gutter={[16, 16]} style={{ display: 'flex', flexWrap: 'nowrap' }}>
                {/* 总表数 */}
                <Col flex={1}>
                  <Card
                    bordered={false}
                    title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>总表数</span>}
                    headStyle={{ borderBottom: 'none' }}
                    bodyStyle={{ textAlign: 'center' }}
                    extra={
                      <Tooltip title="显示数据操作日志中的总表数量">
                        <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                      </Tooltip>
                    }
                  >
                    <Statistic
                      value={localDataStats?.total_tables ?? 0}
                      prefix={<TableOutlined style={{ color: '#1890ff' }} />}
                      valueStyle={{ color: '#1890ff' }}
                      style={{ marginTop: '-12px' }}
                    />
                  </Card>
                </Col>

                {/* 成功操作数 */}
                <Col flex={1}>
                  <Card
                    bordered={false}
                    title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>成功操作数</span>}
                    headStyle={{ borderBottom: 'none' }}
                    bodyStyle={{ textAlign: 'center' }}
                    extra={
                      <Tooltip title="显示数据操作日志中成功执行的操作数量">
                        <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                      </Tooltip>
                    }
                  >
                    <Statistic
                      value={localDataStats?.success_operations ?? 0}
                      prefix={<CheckOutlined style={{ color: '#52c41a' }} />}
                      valueStyle={{ color: '#52c41a' }}
                      style={{ marginTop: '-12px' }}
                    />
                  </Card>
                </Col>

                {/* 失败操作数 */}
                <Col flex={1}>
                  <Card
                    bordered={false}
                    title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>失败操作数</span>}
                    headStyle={{ borderBottom: 'none' }}
                    bodyStyle={{ textAlign: 'center' }}
                    extra={
                      <Tooltip title="显示数据操作日志中执行失败的操作数量">
                        <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                      </Tooltip>
                    }
                  >
                    <Statistic
                      value={localDataStats?.failed_operations ?? 0}
                      prefix={<CloseOutlined style={{ color: '#ff4d4f' }} />}
                      valueStyle={{ color: '#ff4d4f' }}
                      style={{ marginTop: '-12px' }}
                    />
                  </Card>
                </Col>

                {/* 总插入记录数 */}
                <Col flex={1}>
                  <Card
                    bordered={false}
                    title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>总插入记录数</span>}
                    headStyle={{ borderBottom: 'none' }}
                    bodyStyle={{ textAlign: 'center' }}
                    extra={
                      <Tooltip title="显示数据操作日志中所有插入操作的总记录数">
                        <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                      </Tooltip>
                    }
                  >
                    <Statistic
                      value={localDataStats?.total_insert_count ?? 0}
                      prefix={<PlusOutlined style={{ color: '#1890ff' }} />}
                      valueStyle={{ color: '#1890ff' }}
                      style={{ marginTop: '-12px' }}
                    />
                  </Card>
                </Col>

                {/* 总更新记录数 */}
                <Col flex={1}>
                  <Card
                    bordered={false}
                    title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>总更新记录数</span>}
                    headStyle={{ borderBottom: 'none' }}
                    bodyStyle={{ textAlign: 'center' }}
                    extra={
                      <Tooltip title="显示数据操作日志中所有更新操作的总记录数">
                        <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                      </Tooltip>
                    }
                  >
                    <Statistic
                      value={localDataStats?.total_update_count ?? 0}
                      prefix={<EditOutlined style={{ color: '#1890ff' }} />}
                      valueStyle={{ color: '#1890ff' }}
                      style={{ marginTop: '-12px' }}
                    />
                  </Card>
                </Col>
              </Row>
            </div>

            <Divider />

            {/* 数据表统计数据 */}
            <div>
              <div style={{ marginBottom: 16, fontSize: '16px', fontWeight: 500, color: '#722ed1' }}>
                数据表统计
              </div>
              <Row gutter={[16, 16]}>
                {/* 分表数量 */}
                <Col xs={24} sm={12} lg={6}>
                  <Card
                    bordered={false}
                    title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>分表数量</span>}
                    headStyle={{ borderBottom: 'none' }}
                    bodyStyle={{ textAlign: 'center' }}
                    extra={
                      <Tooltip title="显示数据表统计中的分表数量">
                        <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                      </Tooltip>
                    }
                  >
                    <Statistic
                      value={localDataStats?.split_tables_count ?? 0}
                      prefix={<DatabaseOutlined style={{ color: '#722ed1' }} />}
                      valueStyle={{ color: '#722ed1' }}
                      style={{ marginTop: '-12px' }}
                    />
                  </Card>
                </Col>

                {/* 总记录数 */}
                <Col xs={24} sm={12} lg={6}>
                  <Card
                    bordered={false}
                    title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>总记录数</span>}
                    headStyle={{ borderBottom: 'none' }}
                    bodyStyle={{ textAlign: 'center' }}
                    extra={
                      <Tooltip title="显示数据表统计中的总记录数">
                        <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                      </Tooltip>
                    }
                  >
                    <Statistic
                      value={localDataStats?.total_records_sum ?? 0}
                      prefix={<DatabaseOutlined style={{ color: '#1890ff' }} />}
                      valueStyle={{ color: '#1890ff' }}
                      style={{ marginTop: '-12px' }}
                    />
                  </Card>
                </Col>

                {/* 日记录数 */}
                <Col xs={24} sm={12} lg={6}>
                  <Card
                    bordered={false}
                    title={<span style={{ color: 'rgba(0, 0, 0, 0.45)', fontWeight: 'normal' }}>日记录数</span>}
                    headStyle={{ borderBottom: 'none' }}
                    bodyStyle={{ textAlign: 'center' }}
                    extra={
                      <Tooltip title="显示数据表统计中的日记录数">
                        <InfoCircleOutlined style={{ color: '#8c8c8c', cursor: 'pointer' }} />
                      </Tooltip>
                    }
                  >
                    <Statistic
                      value={localDataStats?.daily_records_sum ?? 0}
                      prefix={<DatabaseOutlined style={{ color: '#52c41a' }} />}
                      valueStyle={{ color: '#52c41a' }}
                      style={{ marginTop: '-12px' }}
                    />
                  </Card>
                </Col>
              </Row>
            </div>
          </Card>
        </Spin>
      </PageContainer>
    </>
  );
};

export default Dashboard;
