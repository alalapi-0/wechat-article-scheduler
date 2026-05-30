# 调度设计

## 现状

- 已实现：单进程轮询调度、到期任务执行、失败重试计数
- 已实现：`scheduler/policies.py`（重试/DRY_RUN）、`scheduler/domain.py`（任务执行）、`scheduler/runtime.py`（轮询入口）
- 风险：无多实例互斥、无分布式锁、无任务抢占

## 目标架构

- `scheduler/runtime`：轮询与执行器
- `scheduler/domain`：任务状态机与策略
- `scheduler/policies`：重试、退避、节流、窗口规则

## 状态机（建议）

`pending -> running -> done`  
`pending/running -> failed -> pending(retry)`  
`pending/running -> cancelled`

## 非目标（本轮）

- 不做分布式调度
- 不做复杂优先级抢占
