# 什么是 **Agent Skill** 思想？

简短回答：**Agent Skill（技能）思想** 是把智能代理（Agent）的能力拆成若干可复用、独立、明确接口的小模块（skill），让一个中央的“规划/决策层”（通常是大模型）按需调用这些技能来完成复杂任务。它把“会做事情”的能力从“大脑”中解耦出来，变成一组可组合的工具/能力单元。

------

## 核心要点（直观理解）

* **Skill = 一个具体能力**：比如「搜索网页」「发送邮件」「读取日历」「执行计算」「生成图像」「翻译」「数据库查询」等，每个 skill 有明确输入、输出和错误/限制说明。
* **Agent = 一个协调者**：负责理解用户意图、把任务拆成子任务、选择并串接合适的 skills、验证结果并返回给用户。
* **接口化 & 可组合**：skills 有统一的调用接口（schema/contract），可以被动态加载、替换或并行调用。
* **降低复杂度 & 提高安全性**：把危险或昂贵的操作放进受控 skill，便于权限校验、审计和限流。

------

## 为什么这么做（优点）

* **模块化**：易于开发、测试、维护。新能力只需新增 skill，不改核心 agent。
* **可组合性**：不同 skills 串联可以完成复杂任务（例如：安排会议 = 查日历 + 推荐时段 + 发邮件）。
* **安全与隔离**：把有风险的操作（例如资金转账、系统命令）封装并加权限控制。
* **可观测性**：每次 skill 调用都可记录、回放、审计，利于调试与合规。
* **性能优化**：对高频短操作可单独优化、缓存或并行执行。

------

## 典型组成（实现层面）

1. **Skill 接口（contract）**
   * 名称、描述、输入 schema、输出 schema、错误码、权限需求、幂等性说明。
2. **Skill 实现**
   * 真正的代码或外部服务（REST API、数据库、脚本、第三方 SDK）。
3. **Planner / Orchestrator（由 LLM 或规则引擎承担）**
   * 将用户意图转成调用序列（which skills, with which args）。
4. **Router（技能选择器）**
   * 根据上下文/策略选择最合适的 skill 实例（例如多个搜索引擎）。
5. **Validator / Verifier**
   * 验证 skill 输出是否符合 schema，检测异常或潜在的错误（及早回滚或补救）。
6. **Policy / Safety 层**
   * 权限、速率限制、输入/输出过滤、审计日志。
7. **Memory / Context**
   * 为跨多个 skill 的对话维持状态与上下文信息。

------

## 简单示例（伪代码，Python 风格）

```python
class Skill:
    name: str
    def execute(self, input: dict) -> dict:
        raise NotImplementedError

class SearchSkill(Skill):
    name = "web_search"
    def execute(self, input):
        q = input["query"]
        # call search API, return list of results
        return {"results": [...]}

# Planner (LLM) 会输出一个 plan，比如：
plan = [
    {"skill": "web_search", "args": {"query": "附近最好的意大利餐厅"}},
    {"skill": "summarize", "args": {"text": "$previous.results"}}
]
# Orchestrator 依次执行并把结果传给下一步
```

------

## 设计原则 & 好实践

* **明确定义 schema**（输入输出必须可验证）——减少 hallucination 导致的错误调用。
* **保持技能幂等或可回滚**（重要操作要可撤销或有确认流程）。
* **最小权限**：skill 权限只给它执行所需操作的最小权限。
* **可测性**：为每个 skill 写单元测试、集成测试与失败注入测试。
* **观察与审计**：记录每次 skill 被谁、为什么、何时调用及返回值（或摘要）。
* **超时与降级策略**：外部服务失败时，优雅降级或告知用户。
* **版本管理**：skill 接口变更时要向后兼容或使用版本号。

------

## 常见模式与变体

* **Function-calling（LLM 函数调用）**：将 skill 映射成函数签名，让 LLM 直接选择并填参数。
* **Planner + Executor**：LLM 负责高层规划，具体执行由 rule-based executor 或 workflow 引擎完成。
* **Hybrid（人机混合）**：一些关键步骤需要人工确认（例如大额转账的确认环节）。
* **Chain-of-Thought → Skill**：将 LLM 的思路输出为一系列 skill 调用（更可靠的“思考→行动”分离）。

------

## 风险与局限

* **错误组合与偏差**：skill 的不准确输出会连锁影响后续步骤。
* **过度依赖 LLM**：如果 planner 不健壮，可能产生不合理调用序列。
* **安全风险**：若 skill 权限管理不严格，可能被滥用。
* **维护成本**：大量 skill 需要版本管理和文档支持，否则会混乱。

------

## 何时采用 Agent Skill 思想？

* 任务需要访问多种系统或外部资源（API、数据库、设备等）。
* 想要复用能力并加快新功能开发（把新能力做成 skill 即可上线）。
* 需要强可观测性、安全审计或权限控制的场景（金融、企业自动化）。
* 希望把「会思考」和「会操作」明确分离以降低错误率。

------

如果你想，我可以：

* 给你一个**技能接口模板**（OpenAPI / JSON Schema）和一个示例 skill 项目结构；
* 演示如何把一个 LLM planner（例如函数调用）对接到 skill 层，包含校验与回退策略；
* 或者基于你具体的用例（比如企业邮件自动化或交易下单 agent）给出设计建议和权限/安全方案。

你想先看哪个？