# CookieConfig

CookieConfig 类定义 AmritaCore 的安全 cookie 配置。

## 属性

- `enable_cookie` (bool)：默认 `True`。是否启用 Cookie 泄漏检测机制
- `cookie` (str)：随机 16 位字母数字字符串。用于安全检测的 cookie 字符串

## 描述

CookieConfig 类继承自 BaseModel，通过 `AmritaConfig.cookie` 公开。它控制用于安全检查的 cookie 泄漏检测机制。未显式提供时，cookie 字符串通过 `random_alnum_string(16)` 自动生成。
