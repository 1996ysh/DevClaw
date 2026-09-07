from main import build_agent
from scripts.common import print_all
import asyncio
#复杂多步任务
MULTI_STEP_TASK = (
    "为订单服务实现一个折扣计算模块，放在 discount.py：\n"
    "1. calc_subtotal(items) 计算小计（items 形如 [{'price':10.0,'qty':2}, ...]）；\n"
    "2. apply_coupon(subtotal, coupon) 应用优惠券，支持'满减'和'打折'两种类型；\n"
    "3. calc_final_total(items, coupon, vip_level) 综合计算最终应付，VIP 等级越高额外折扣越多；\n"
    "每个函数都要类型注解、docstring，并处理边界情况（空列表、无效优惠券）。"
    "上诉任务你应该列出计划再执行效果会比较好"
)
#简单任务
SIMPLE_TASK = (
    "为订单服务写一个计算订单总价的函数 calc_order_total(items)，"
    "items 形如 [{'price': 10.0, 'qty': 2}, ...]，返回所有条目 price*qty 之和。"
    "放在 pricing.py 里，带类型注解和 docstring。"
)
async def main():
    agent = build_agent()   # 创建：同步工厂 create_deep_agent

    task = MULTI_STEP_TASK   # 想对照"简单任务不列计划"，改成 SIMPLE_TASK 即可

    # 调用：异步 await agent.ainvoke(...)
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": task}]}
    )

    print_all(result)        # 统一用 _common 的打印工具

if __name__ == "__main__":
    asyncio.run(main())