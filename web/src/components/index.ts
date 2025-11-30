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

/**
 * 这个文件作为组件的目录
 * 目的是统一管理对外输出的组件，方便分类
 */
/**
 * 布局组件
 */
import Footer from './Footer';
import { Question, SelectLang, RightContent } from './RightContent';
import { AvatarDropdown, AvatarName } from './RightContent/AvatarDropdown';
import SidebarUserInfo from './SidebarUserInfo';
import MenuSearch from './MenuSearch';
import GlobalTabs from './GlobalTabs';
import { GlobalTabsProvider, useGlobalTabsContext } from './GlobalTabsProvider';
import TopNavLinks from './TopNavLinks';

export { 
  AvatarDropdown, 
  AvatarName, 
  Footer, 
  Question, 
  SelectLang,
  RightContent,
  SidebarUserInfo,
  MenuSearch,
  GlobalTabs,
  GlobalTabsProvider,
  useGlobalTabsContext,
  TopNavLinks,
};
