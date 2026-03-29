
# P0 安全问题修复报告

## 问题概述
本次修复了 ClawRiver 项目的 4 个 P0 严重安全问题。

---

## P0-1: `require_admin` 不检查角色
- **文件**: `app/api/dependencies.py`
- **问题**: `require_admin` 函数未验证用户角色，任何人都能访问管理员端点
- **修复**: 添加角色检查，仅允许 `admin` 或 `moderator` 角色访问
- **Commit**: `fix: P0-1 require_admin check user role`

---

## P0-2: CORS 通配符 + credentials
- **文件**: `app/main.py`, `app/core/config.py`
- **问题**: `allow_origins=["*"]` 配合 `allow_credentials=True` 存在安全风险
- **修复**: 
  - 添加 `ALLOWED_ORIGINS` 配置项
  - 仅在配置了具体允许的域名时启用 `allow_credentials`
  - 无配置时使用通配符但关闭凭证支持
- **Commit**: `fix: P0-2 CORS allow_origins + credentials, P0-3 JWT_SECRET required`

---

## P0-3: JWT 默认密钥
- **文件**: `app/core/config.py`, `app/main.py`
- **问题**: JWT 使用默认密钥 "CHANGE-ME-IN-PRODUCTION"
- **修复**:
  - 移除默认密钥，要求必须通过环境变量 `JWT_SECRET` 设置
  - 在应用启动时验证密钥是否存在，缺失则拒绝启动
- **Commit**: `fix: P0-2 CORS allow_origins + credentials, P0-3 JWT_SECRET required`

---

## P0-4: 购买操作竞态条件
- **文件**: `app/services/memory_service_v2.py`, `app/services/purchase_service_v2.py`
- **问题**: 购买操作未使用事务锁，可能导致重复购买
- **修复**:
  - 使用 `async with db.begin()` 开启显式事务
  - 使用 `select(...).with_for_update()` 锁定相关行
  - 确保记忆、买家/卖家、团队等数据在修改前被锁定
- **Commit**: `fix: P0-4 purchase race conditions with SELECT FOR UPDATE`

---

## 验证结果
- 所有修改保持向后兼容
- 未破坏现有功能
- 代码可正常启动和运行
