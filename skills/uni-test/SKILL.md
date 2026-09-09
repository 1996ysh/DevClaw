---
name: uni-test
description: 当需要为订单服务的函数或接口编写、补充单元测试时使用本规范(pytest风格、命名、覆盖要点)
---

# 单元测试编写规范


## 框架与结构

- 用pytest；测试文件命名 test_<module>.py,放在tests/下
- 一个测试只验证一件事，采用Arrange-Act-Assert三段式。

## 命名

- 测试函数名描述场景，如test_calc_order_total_with_multiple_items.

## 覆盖要点

- 正常路径 + 边界(空列表、qty=0) + 异常输入
- 用pytest.raises 验证错误路径
