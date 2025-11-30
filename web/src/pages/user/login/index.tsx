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

import {
  LockOutlined,
  UserOutlined,
} from '@ant-design/icons';
import {
  LoginForm,
  ProFormCheckbox,
  ProFormInstance,
  ProFormText,
} from '@ant-design/pro-components';
import {
  FormattedMessage,
  Helmet,
  useIntl,
  useModel,
  history,
} from '@umijs/max';
import { Alert, App } from 'antd';
import { createStyles } from 'antd-style';
import React, { useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { Footer } from '@/components';
import { login as zquantLogin } from '@/services/zquant/auth';
import { getCurrentUser } from '@/services/zquant/users';
import { ADMIN_ROLE_ID } from '@/constants/roles';
import Settings from '../../../../config/defaultSettings';

const useStyles = createStyles(({ token }) => {
  return {
    action: {
      marginLeft: '8px',
      color: 'rgba(0, 0, 0, 0.2)',
      fontSize: '24px',
      verticalAlign: 'middle',
      cursor: 'pointer',
      transition: 'color 0.3s',
      '&:hover': {
        color: token.colorPrimaryActive,
      },
    },
    container: {
      display: 'flex',
      height: '100vh',
      overflow: 'hidden',
      '@media (max-width: 768px)': {
        flexDirection: 'column',
      },
    },
    leftPanel: {
      flex: '0 0 66.666%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      backgroundImage:
        "url('https://mdn.alipayobjects.com/yuyan_qk0oxh/afts/img/V-_oS6r-i7wAAAAAAAAAAAAAFl94AQBr')",
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      position: 'relative',
      '@media (max-width: 768px)': {
        flex: '0 0 40%',
        minHeight: '300px',
      },
      '&::before': {
        content: '""',
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.3)',
        zIndex: 1,
      },
    },
    leftContent: {
      position: 'relative',
      zIndex: 2,
      textAlign: 'center',
      color: '#fff',
      padding: '40px',
    },
    leftTitle: {
      fontSize: '48px',
      fontWeight: 'bold',
      marginBottom: '16px',
      textShadow: '2px 2px 4px rgba(0, 0, 0, 0.3)',
      '@media (max-width: 768px)': {
        fontSize: '32px',
      },
    },
    leftSubtitle: {
      fontSize: '20px',
      opacity: 0.9,
      textShadow: '1px 1px 2px rgba(0, 0, 0, 0.3)',
      '@media (max-width: 768px)': {
        fontSize: '16px',
      },
    },
    leftLogo: {
      width: '120px',
      height: '120px',
      margin: '0 auto 24px',
      filter: 'drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3))',
      '@media (max-width: 768px)': {
        width: '80px',
        height: '80px',
      },
    },
    rightPanel: {
      flex: '0 0 33.333%',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: '#fff',
      overflow: 'auto',
      '@media (max-width: 768px)': {
        flex: '1 1 auto',
      },
    },
    rightContent: {
      flex: '1',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '32px 24px',
      '@media (max-width: 768px)': {
        padding: '24px 16px',
      },
    },
    formItem: {
      marginBottom: '20px',
    },
    checkboxWrapper: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '12px',
      flexWrap: 'nowrap',
    },
    checkboxLabel: {
      whiteSpace: 'nowrap',
      marginLeft: '8px',
    },
    forgotPasswordLink: {
      whiteSpace: 'nowrap',
      marginLeft: '8px',
    },
  };
});

const LoginMessage: React.FC<{
  content: string;
}> = ({ content }) => {
  return (
    <Alert
      style={{
        marginBottom: 24,
      }}
      message={content}
      type="error"
      showIcon
    />
  );
};

// localStorage key
const REMEMBERED_USERNAME_KEY = 'remembered_username';
const REMEMBERED_PASSWORD_KEY = 'remembered_password';

// 简单的 base64 编码/解码（不是真正的加密，只是避免明文存储）
const encodePassword = (password: string): string => {
  return btoa(unescape(encodeURIComponent(password)));
};

const decodePassword = (encoded: string): string => {
  try {
    return decodeURIComponent(escape(atob(encoded)));
  } catch {
    return '';
  }
};

const Login: React.FC = () => {
  const [loginError, setLoginError] = useState<string>('');
  const { initialState, setInitialState } = useModel('@@initialState');
  const { styles } = useStyles();
  const { message } = App.useApp();
  const intl = useIntl();
  const formRef = useRef<ProFormInstance>();

  // 页面加载时，从 localStorage 读取保存的账号密码并填充
  useEffect(() => {
    const rememberedUsername = localStorage.getItem(REMEMBERED_USERNAME_KEY);
    const rememberedPassword = localStorage.getItem(REMEMBERED_PASSWORD_KEY);

    if (rememberedUsername && rememberedPassword) {
      // 使用 setTimeout 确保 formRef 已经初始化
      setTimeout(() => {
        if (formRef.current) {
          const decodedPassword = decodePassword(rememberedPassword);
          formRef.current.setFieldsValue({
            username: rememberedUsername,
            password: decodedPassword,
            rememberCredentials: true,
          });
        }
      }, 100);
    }
  }, []);

  const fetchUserInfo = async () => {
    try {
      console.log('[Login] fetchUserInfo: 开始获取用户信息');
      // 检查token是否存在
      const token = localStorage.getItem('access_token');
      console.log('[Login] fetchUserInfo: token存在?', !!token);
      
      // 直接调用getCurrentUser，避免使用initialState?.fetchUserInfo（它会在失败时清除token）
      const userInfo = await getCurrentUser();
      console.log('[Login] fetchUserInfo: 用户信息获取成功', userInfo);
      
      // 根据role_id判断是否为管理员
      const isAdmin = userInfo.role_id === ADMIN_ROLE_ID;
      
      // 转换用户信息格式以适配ProLayout
      const currentUser = {
        name: userInfo.username,
        avatar: undefined,
        userid: userInfo.id.toString(),
        email: userInfo.email,
        access: isAdmin ? 'admin' : 'user',
        role_id: userInfo.role_id, // 保存role_id以便后续使用
      };
      
      console.log('[Login] fetchUserInfo: 更新initialState');
      flushSync(() => {
        setInitialState((s) => ({
          ...s,
          currentUser,
        }));
      });
      console.log('[Login] fetchUserInfo: initialState已更新');
      return currentUser;
    } catch (error) {
      console.error('[Login] fetchUserInfo: 获取用户信息失败', error);
      // 登录成功后获取用户信息失败，抛出错误
      throw error;
    }
  };

  const handleSubmit = async (values: { 
    username: string; 
    password: string; 
    rememberCredentials?: boolean;
  }) => {
    try {
      console.log('[Login] 开始登录流程', values.username);
      setLoginError('');
      
      // 调用zquant登录接口
      console.log('[Login] 调用登录API...');
      const tokenData = await zquantLogin({
        username: values.username,
        password: values.password,
      });
      console.log('[Login] 登录API成功，收到token:', {
        hasAccessToken: !!tokenData.access_token,
        hasRefreshToken: !!tokenData.refresh_token,
      });
      
      // 保存token到localStorage
      localStorage.setItem('access_token', tokenData.access_token);
      localStorage.setItem('refresh_token', tokenData.refresh_token);
      console.log('[Login] Token已保存到localStorage');
      
      // 处理记住账号密码
      if (values.rememberCredentials) {
        // 保存用户名和密码（密码使用base64编码）
        localStorage.setItem(REMEMBERED_USERNAME_KEY, values.username);
        localStorage.setItem(REMEMBERED_PASSWORD_KEY, encodePassword(values.password));
        console.log('[Login] 账号密码已保存');
      } else {
        // 清除保存的账号密码
        localStorage.removeItem(REMEMBERED_USERNAME_KEY);
        localStorage.removeItem(REMEMBERED_PASSWORD_KEY);
        console.log('[Login] 已清除保存的账号密码');
      }
      
      // 获取用户信息
      console.log('[Login] 开始获取用户信息...');
      await fetchUserInfo();
      console.log('[Login] 用户信息获取成功');
      
      const defaultLoginSuccessMessage = intl.formatMessage({
        id: 'pages.login.success',
        defaultMessage: '登录成功！',
      });
      message.success(defaultLoginSuccessMessage);
      
      // 获取跳转目标
      const urlParams = new URL(window.location.href).searchParams;
      const redirect = urlParams.get('redirect') || '/welcome';
      console.log('[Login] 准备跳转到:', redirect);
      console.log('[Login] 当前路径:', window.location.pathname);
      console.log('[Login] initialState.currentUser:', initialState?.currentUser);
      console.log('[Login] token存在?', !!localStorage.getItem('access_token'));
      
      // 使用setTimeout确保状态更新完成后再跳转
      // 使用history.push跳转
      setTimeout(() => {
        console.log('[Login] 执行跳转，目标:', redirect);
        history.push(redirect);
        console.log('[Login] history.push已执行');
      }, 50);
    } catch (error: any) {
      console.error('[Login] 登录失败:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || '登录失败，请重试！';
      setLoginError(errorMessage);
      const defaultLoginFailureMessage = intl.formatMessage({
        id: 'pages.login.failure',
        defaultMessage: '登录失败，请重试！',
      });
      message.error(errorMessage || defaultLoginFailureMessage);
    }
  };

  // 处理记住账号密码复选框变化
  const handleRememberChange = (checked: boolean) => {
    if (!checked) {
      // 取消勾选时，清除保存的账号密码
      localStorage.removeItem(REMEMBERED_USERNAME_KEY);
      localStorage.removeItem(REMEMBERED_PASSWORD_KEY);
    }
  };

  return (
    <div className={styles.container}>
      <Helmet>
        <title>
          {intl.formatMessage({
            id: 'menu.login',
            defaultMessage: '登录页',
          })}
          {Settings.title && ` - ${Settings.title}`}
        </title>
      </Helmet>
      
      {/* 左侧图片区域 - 2/3 */}
      <div className={styles.leftPanel}>
        <div className={styles.leftContent}>
          <img src="/logo.svg" alt="ZQuant Logo" className={styles.leftLogo} />
          <div className={styles.leftTitle}>ZQuant</div>
          <div className={styles.leftSubtitle}>ZQuant量化分析平台</div>
          <div className={styles.leftSubtitle} style={{ marginTop: '16px', fontSize: '16px' }}>
            数据管理 · 策略回测 · 绩效分析
          </div>
        </div>
      </div>

      {/* 右侧登录表单区域 - 1/3 */}
      <div className={styles.rightPanel}>
        <div className={styles.rightContent}>
          <LoginForm
            formRef={formRef}
            contentStyle={{
              minWidth: 320,
              maxWidth: '100%',
              width: '100%',
            }}
            logo={<img alt="logo" src="/logo.svg" style={{ width: '48px', height: '48px' }} />}
            title="欢迎登录"
            subTitle="ZQuant量化分析平台"
            initialValues={{
              rememberCredentials: false,
              agreeToTerms: true,
            }}
            layout="horizontal"
            labelCol={{ style: { width: '60px' } }}
            wrapperCol={{ style: { flex: 1 } }}
            onFinish={async (values) => {
              await handleSubmit(values as { 
                username: string; 
                password: string; 
                rememberCredentials?: boolean;
                agreeToTerms?: boolean;
              });
            }}
          >
            {loginError && <LoginMessage content={loginError} />}
            
            <ProFormText
              name="username"
              label="用户名"
              className={styles.formItem}
              fieldProps={{
                size: 'large',
                prefix: <UserOutlined />,
                placeholder: '请输入用户名',
              }}
              rules={[
                {
                  required: true,
                  message: '请输入用户名',
                },
              ]}
            />
            <ProFormText.Password
              name="password"
              label="密码"
              className={styles.formItem}
              fieldProps={{
                size: 'large',
                prefix: <LockOutlined />,
                placeholder: '请输入密码',
              }}
              rules={[
                {
                  required: true,
                  message: '请输入密码',
                },
              ]}
            />
            <div className={styles.checkboxWrapper}>
              <ProFormCheckbox 
                name="rememberCredentials"
                onChange={(e) => handleRememberChange(e.target.checked)}
                style={{ margin: 0 }}
              >
                <span className={styles.checkboxLabel}>
                  <FormattedMessage
                    id="pages.login.rememberCredentials"
                    defaultMessage="记住账号密码"
                  />
                </span>
              </ProFormCheckbox>
              <a
                className={styles.forgotPasswordLink}
                onClick={(e) => {
                  e.preventDefault();
                  message.info('账号问题，请联系管理员！');
                }}
              >
                <FormattedMessage
                  id="pages.login.forgotPassword"
                  defaultMessage="忘记密码"
                />
              </a>
            </div>
            <ProFormCheckbox
              name="agreeToTerms"
              rules={[
                {
                  validator: (_, value) => {
                    if (!value) {
                      return Promise.reject(new Error('请先阅读并同意用户协议和免责申明'));
                    }
                    return Promise.resolve();
                  },
                },
              ]}
              style={{ marginBottom: '20px' }}
            >
              <span>
                我已阅读并同意
                <a
                  href="/legal/user-agreement"
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => {
                    e.stopPropagation();
                  }}
                  style={{ margin: '0 4px' }}
                >
              《用户协议》
                </a>
                和
                <a
                  href="/legal/disclaimer"
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => {
                    e.stopPropagation();
                  }}
                  style={{ margin: '0 4px' }}
                >
              《免责申明》
                </a>
              </span>
            </ProFormCheckbox>
          </LoginForm>
        </div>
        <Footer />
      </div>
    </div>
  );
};

export default Login;
