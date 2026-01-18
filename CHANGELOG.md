# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/).

## [0.3.0] - 2025-01-XX

### Added

- **前端组件**: 新增 `SelectWithAll` 组件，自动为 Ant Design Select 添加"全部"选项
- **前端组件**: 新增 `ProFormSelectWithAll` 组件，自动为 ProFormSelect 添加"全部"选项，支持 `options` 和 `valueEnum` 两种方式
- **工具函数**: 新增 `selectUtils.ts` 工具函数，提供 `addAllOption` 和 `getDefaultSelectValue` 函数
- **统一体验**: 所有下拉框统一添加"全部"选项，提升用户体验

### Changed

- **UI改进**: 约30+个页面的下拉框已更新，统一使用新的组件
  - 数据页面：fundamentals、calendar、daily、daily-basic、factor、factor-pro、stocks、sync-logs、operation-logs
  - 因子页面：results、configs、definitions、models
  - 回测页面：create、strategies/create、strategies/[id]/edit
  - 自选股页面：strategy-stocks、stock-filter
  - 管理页面：scheduler、users、permissions
  - 其他页面：table-list/components/UpdateForm
- **默认行为**: 所有下拉框默认选中"全部"选项，用户无需手动选择即可查看全部数据
- **一致性**: "全部"选项统一显示文本为"全部"，统一放在选项列表第一位

### Technical Details

- 组件支持自定义"全部"选项的值（`allValue`）和标签（`allLabel`）
- 组件支持 `excludeAll` 属性，用于排除搜索类型等特殊场景的下拉框
- `ProFormSelectWithAll` 支持 `valueEnum` 格式，兼容现有代码
- 所有组件保持与原有 API 的兼容性，迁移成本低

---

## [0.2.0] - 2024-XX-XX

### Added

- 初始版本功能

---

## [0.1.0] - 2024-XX-XX

### Added

- 项目初始版本

[0.3.0]: https://github.com/yoyoung/zquant/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/yoyoung/zquant/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/yoyoung/zquant/releases/tag/v0.1.0

