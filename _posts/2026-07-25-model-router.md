---
layout: post
title: Model Router 该怎么做
date: 2026-07-26 21:54:16 +0800
categories:
  - 分享
article_type: 1
typora-root-url: ../../github.io
---

![](/assets/img/model-router-caption.png)

7.22，Cursor 正式发布了 [Cursor Router](https://cursor.com/blog/router)。一个月前，论文 [Agent-as-a-Router](https://arxiv.org/abs/2606.22902) 提出了 ACRouter（Agentic Coding Router），并开放了[代码和 Benchmark](https://github.com/LanceZPF/agent-as-a-router)。

一个是已经进入真实产品的 Router，一个是可以看到实现细节的研究原型，把它们放在一起看，Model Router 的轮廓会清晰很多。

# Cursor Router 做了什么

Cursor 对 Router 的描述很直接：在模型运行前对每个请求分类，再把请求发给更合适的模型。

官方披露，分类时会考虑用户 Query、当前上下文、任务复杂度、任务领域，以及 Cursor 已知的各模型行为。简单工作会交给更具价格优势的模型，UI 修改倾向更有设计感的模型，复杂、长周期的问题则交给前沿推理模型。

Router 提供三种模式：

| 模式 | 目标 |
| --- | --- |
| Intelligence | 尽量接近最强模型的质量 |
| Balance | 在日常可用的前沿质量和成本之间取平衡 |
| Cost | 保持基本质量，优先降低 Token 支出 |

三种模式更像同一条 Cost–Intelligence Pareto Frontier 上的不同策略点或者 effort 等级。

Cursor Router 使用 60 万+真实请求训练，并在数百万请求中做线上 A/B。评估不只看 Token，还会观察用户是否继续纠正 Agent，以及 Agent 生成的代码后来有没有留在代码库中，也就是 Keep Rate。

缓存也被算进了路由成本。模型切换通常会造成 Cache Miss，所以一个孤立请求上的最优选择，放进长会话里未必仍然最优。Cursor 表示，其训练数据和线上节省结果都包含这部分损失。

官方公布的结果包括：

- 线上 A/B 中，在保持前沿质量的同时节省约 60% 成本
- 三个高流量企业账号相比全部使用 Opus 4.8，节省约 30%～50%，质量没有下降
- 每次 Commit 成本分别为：Balance 4.63 美元、Intelligence 6.76 美元、Opus 4.8 7.34 美元、Fable 5 12.69 美元

这些数字来自 Cursor 自己的用户、任务分布和指标体系，不是第三方 Benchmark，不能直接拿来预估其他产品的收益。Cursor 也没有公开分类器结构、特征权重、模型流量分布和满意度 Reward 的具体训练方式。

所以能确认的是：Cursor Router 是一个由真实数据训练、按请求分类、感知缓存并接受线上反馈的系统。至于它内部是否使用长期 Memory，或者用什么算法更新策略，公开资料不足以判断。

Cursor 最难复制的并不是分类器，而是数据。Cursor 每周处理数亿次跨模型编码请求，可以观察同类任务在不同模型上的行为、用户是否满意，以及代码最终有没有被保留，分类器只是把这些信息变成线上决策的最后一步。

# ACRouter 提供了另一个视角

ACRouter 先用实验回答了一个基础问题：不同模型之间，究竟有没有值得路由的能力差异？

论文构建了 CodeRouterBench，包含约 1 万个任务、10 个编码维度和 8 个前沿模型。其中 9 个维度是代码生成、算法设计、Bug 修复、测试生成、数据科学等单轮任务；另一个维度由 176 个需要多步规划、文件导航和迭代调试的 Agentic Programming 任务组成，用来测试分布外泛化。

实验中没有一个模型在所有维度上占优。Claude Opus 4.6 的平均成绩最高，但 GLM-5 更擅长算法设计，Qwen3-Max 在测试生成上更好，Kimi-K2.5 则在数据科学上领先。9 个单轮维度里，共有 5 个不同模型分别成为最优选择。

比模型排名更有意思的是一次消融实验。

论文让 Claude Sonnet 4.6 充当 Router，根据任务 Prompt 从 8 个模型中做选择。AvgPerf 表示平均任务表现，Perf/$ 表示每美元换回的平均表现，实验结果如下：

| 设置 | Router 获得的信息 | AvgPerf | Perf/$ |
| --- | --- | ---: | ---: |
| 理论最优 | 事后知道每个任务的最优模型，作为理论上限 | 57.00 | 8.20 |
| DimensionBest | 按任务维度选择历史最优模型 | 47.50 | 3.69 |
| Vanilla | 只看任务 Prompt | 41.41 | 1.97 |
| +Dimension | 在 Prompt 之外增加任务维度 | 41.18 | 1.81 |
| +Perf stats | 再增加各模型的历史表现 | 47.74 | 1.71 |

只把任务维度告诉 Router，结果几乎没有改善；加入各模型在不同任务维度上的历史表现后，AvgPerf 从 41.41 上升到 47.74，相对提升 15.3%。

这里也要注意，`+Perf stats` 提高了性能，却没有提高 Perf/$。这组消融实验说明「更多有效信息能改善路由决策」，并不代表让 Sonnet 4.6 充当 Router 本身更省钱。

论文据此认为，Router 的主要瓶颈是信息不足，而不是推理能力不足。换句话说，它不是不会判断，而是不知道候选模型过去做得怎么样。

ACRouter 因此没有停在一次性的 `Prompt → Model` 分类，而是把路由做成一个循环：

```text
Context → Action → Feedback → Context
```

它包含三个主要组件：

| 组件 | 做什么 |
| --- | --- |
| Orchestrator | 综合任务信息、维度先验和相似历史任务，选择模型 |
| Verifier | 使用 AST、测试、规则和沙盒执行验证模型产出 |
| Memory | 保存模型选择、验证成绩、成本与失败轨迹，供后续任务检索 |

![](/assets/img/model-router-acrouter-loop.png)

论文实现中的 Orchestrator 使用微调后的 Qwen3.5-0.8B，再结合启发式规则投票；Memory 会检索 Top-10 相似任务，最多保留 20K 条经验。每完成一个任务，Verifier 都会产生新信息并写入 Memory，下一次选择也随之变化。

这种 Router 不太适合只用准确率评估。一个任务可能有多个模型都能完成，只是质量和成本不同。ACRouter 使用累积遗憾值，也就是每次实际选择与事后最优模型之间的差距。差距越小，说明长期路由越接近逐任务最优策略。

论文结果中，ACRouter 在分布内任务的 AvgPerf 为 49.98，在 OOD Agentic Programming 上为 62.50；固定使用 Opus 4.6 的结果分别是 43.83 和 57.14。几种静态 Router 在分布内表现接近，但到了 OOD 任务上明显退化。

这组结果同样有边界。CodeRouterBench 有三个维度仍使用代理指标和 LLM Judge；OOD 部分只有 176 个任务，而且把最大执行步数限制在 40；论文也无法观察供应商侧的真实缓存命中率。ACRouter 的 Perf/$ 也不是所有方案中最高，它追求的是更高性能和更低累积遗憾值，而不是最低调用成本。ACRouter 证明了执行反馈和在线 Memory 的价值，但还不能等同于大规模生产验证。

# 两者放在一起看

从目前公开的资料来看，Cursor Router 和 ACRouter 可以分别视为 Model Router 在工业界与学术界的两个代表性工作，前者有真实产品流量和线上结果，后者公开了系统设计、评测集与消融实验。

它们并不是同一种实现，Cursor 面向高吞吐的真实请求，强调轻量分类、缓存、用户反馈、线上 A/B 和组织策略；ACRouter 面向任务流，强调沙盒验证、相似经验和在线适应。

![](/assets/img/model-router-comparison.png)

但它们指向了同一件事：Router 的效果不取决于一次分类有多聪明，而取决于系统是否知道各模型过去的真实表现，并能不能把这次结果变成下一次选择的依据。

# 为什么 Router 看起来很简单

做完这个分析后，我就在想：为什么大家（包括我自己），第一反应会觉得 Router 是一件很简单的事，只要选出最好的模型就行？

这种错觉或许来自：我们只看到了最后选出的模型，却没有看到背后的决策过程。生产环境中的 Router 往往是一个高维、多目标优化系统，需要同时权衡质量、成本和耗时，每一次 Request 级的决策，都在消耗真金白银做一次 Cost–Intelligence Pareto 权衡。

真正看不见的，是背后庞大、维护成本极高的数据与反馈闭环。

因此，实现的起点不应该是训练一个任务难度分类器，而是先把「选择—执行—验证—回流」这条链路接起来。

# 如果要实现 Model Router

## 我会从两个模型开始

第一版只需要一个日常使用的高性价比模型，以及一个处理复杂任务的强模型。Router 暂时只回答一个问题：

> 当前任务是否值得直接使用强模型？

先用明确规则就够了：

- 合规、上下文长度或工具协议不满足，直接排除对应模型
- 高风险修改、复杂规划、多文件重构使用强模型
- 搜索、分类、格式转换和局部修改使用高性价比模型
- 结果无法可靠验证时，质量优先
- 当前会话已经建立大量缓存时，尽量保持原模型
- 供应商超时或不可用时，使用备用模型

规则不聪明，但可解释、可回放。出错时至少能知道是哪条判断不合理。

## 在任务开始时路由

第一版没有必要让每个 Agent Loop 都重新选模型。

不同模型可能使用不同的 Prompt、工具和编辑协议，切换 Provider 还会丢失缓存。新模型接手旧模型生成的上下文，也可能出现行为不一致。

更稳妥的方式是在任务开始时选一次，并在任务内保持模型粘性。只有连续调用工具却没有缩小错误范围、测试反复出现同一种失败、实际修改范围远超预估，或者当前模型无法使用必要工具时，才允许升级一次。

如果子任务可以独立完成，为它新开一段 Context 往往比在原会话中途换模型更干净。

## 最小实现

系统可以先收敛成四个模块：

| 模块 | 作用 |
| --- | --- |
| Model Registry | 记录模型能力、价格、上下文、区域、工具支持和可用性 |
| Policy & Router | 过滤硬约束，根据规则选择模型和备用模型 |
| Agent Runtime | 执行任务，保持模型粘性，并在明确条件下升级 |
| Outcome Store | 记录实际成本、验证结果、用户是否接受以及路由原因 |

![](/assets/img/model-router-minimal-architecture.png)

一次决策至少要包含：

```text
RouteDecision {
    model
    harness_version
    reason
    fallback_model
    policy_version
}
```

执行结束后写回：

```text
RouteOutcome {
    task_id
    model
    harness_version
    input_tokens
    cached_tokens
    output_tokens
    tool_calls
    loops
    latency
    validation_result
    user_corrected
    accepted
}
```

`reason` 和版本信息用于回放决策，Outcome 则是以后改进 Router 的依据。没有这两部分，Router 选得好不好都说不清楚。

## 先以影子模式运行，再训练

规则写好后，可以先让 Router 只生成决策，不真正改变流量。

影子模式阶段主要确认几件事：路由所需的特征能不能及时拿到，决策能不能解释，规则能不能覆盖主要任务，以及 Router 自身增加了多少延迟。

不过，影子模式只能证明系统会做决定，不能证明另一个模型会做得更好。跨模型结果仍然需要少量 Replay，或者在可验证、低风险任务上保留受控探索流量。

有了同类任务在不同模型上的真实结果，才值得训练 Router。与其让分类器直接输出模型名称，我更倾向分别预测：

```text
P(accepted | task, model, harness)
预计成本
预计延迟
```

然后在满足质量底线的候选模型中，选择预计总成本最低的一个。

早期用逻辑回归、GBDT 或 Embedding 检索就够了。Router 必须比被路由的模型更快、更便宜，也要能解释。为了节省一次调用，先调用另一个昂贵 LLM 判断该用谁，未必划算。

历史经验也可以做成一个简单的 Memory：根据 Task Embedding 检索相似任务，查看不同模型的验证结果、成本和失败原因，再把它作为 Router 的额外输入。Memory 必须绑定 Model、Harness 和 Toolset 版本，否则模型升级后，旧经验会被错误地当成当前能力。

## 验证器决定反馈是否可信

编码任务相对幸运，可以使用编译、单元测试、静态分析、补丁可应用性和代码 Keep Rate 作为反馈。

这些信号的时效不同。测试可以立即得到，用户是否接受和 Keep Rate 则需要更久。Router 需要同时保留即时结果和延迟结果，不能用一次测试通过代替最终接受。

如果任务没有可靠验证器，便宜模型是否真的完成了工作就很难判断。这类任务应该更保守，也不适合只用 LLM Judge 形成自我评价闭环。

## 有些问题只能实际运行后回答

第一是反事实。任务交给模型 A 并成功，不代表模型 B 不能用更低成本完成。只看生产日志，新 Router 很容易复制旧策略。多模型 Replay、受控探索和线上 A/B 只能缓解，不能彻底消除这个问题。

第二是 Model 与 Harness 的耦合。同一个模型换一套 Prompt、工具或上下文策略，结果可能完全不同。Router 实际选择的不是裸模型，而是 `Model Version × Harness Version × Toolset Version`。

第三是缓存。不同供应商的计价和可观测性并不一致，中途切换造成的真实损失，只能从自己的长会话里测量。

最后是持续变化。模型版本、价格、延迟和供应商容量都会变，历史结果必须按版本隔离，并随着时间降低权重。

## 不建议一开始就做的事情

- 一开始接入大量模型
- 每个 Agent Loop 都重新路由
- 用一个昂贵 LLM 充当 Router
- 在没有验证结果时训练分类器
- 只统计单次请求的 Token 成本
- 便宜模型失败后无限重试
- 用离线 Benchmark 直接推断线上收益

# 最后

Cursor Router 说明 Model Router 可以在真实工作流中带来可观测的成本收益，也说明产品化 Router 必须考虑缓存、用户反馈和组织策略。

ACRouter 则进一步表明，路由效果的上限不只由分类器能力决定。没有经过验证的模型表现、失败经验和持续更新的 Memory，再强的 Router 也可能在任务分布变化后失效。

Model Router 的核心壁垒不是「知道哪个模型更强」，而是持续知道「哪个模型刚刚在什么任务上，以多少成本获得了怎样的结果」。分类算法决定一次选择，数据与反馈闭环决定 Router 能否长期工作。

# 参考资料

- [Introducing Cursor Router](https://cursor.com/blog/router)
- [Cursor Router Changelog](https://cursor.com/changelog/router)
- [Continually improving our agent harness](https://cursor.com/blog/continually-improving-agent-harness)
- [Agent-as-a-Router: Agentic Model Routing for Coding Tasks](https://arxiv.org/abs/2606.22902)
- [ACRouter 官方开源实现](https://github.com/LanceZPF/agent-as-a-router)
- [RouteLLM: Learning to Route LLMs with Preference Data](https://arxiv.org/abs/2406.18665)

> 注：Cursor Router 的训练规模、节省比例、满意度和每次 Commit 成本来自 Cursor 官方披露；ACRouter 的实验数字来自论文及其 CodeRouterBench，本文没有独立复现这些结果
