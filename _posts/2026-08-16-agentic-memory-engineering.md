---
layout: post
title: 从外部记忆到记忆原生模型
date: 2026-08-16 23:45:15 +0800
categories:
  - 分享
article_type: 1
typora-root-url: ../../github.io
---
![](/assets/img/agentic-memory-engineering-caption.png)

过去几年，Agent Memory 已经从 “把历史对话存起来” 变成了一个完整的系统性问题，早期工作主要关注如何保存和检索，近来的研究则开始把记忆推进到 Attention、Hidden State、专用神经模块和模型参数，让模型也参与记忆的写入、更新与遗忘。[A Survey on the Memory Mechanism of Large Language Model based Agents](https://arxiv.org/abs/2404.13501) 系统梳理了早期方法，[From Storage to Experience](https://aclanthology.org/2026.findings-acl.2069/) 则把这条演进概括为保存、反思和经验抽象三个阶段。

下面主要结合相关论文，讨论外部记忆、模型内记忆，以及两者为什么正在走向融合，对于尚未形成论文或公开实现的内容，我会单独说明来源和证据边界。

# 1. Agent 的 “记忆” 是什么

提到 Agent 的记忆，大家首先会想到聊天记录，或者模型训练时见过的知识，但这里的记忆范围则更广，业界通常从内容、载体、时间尺度和使用方式对记忆进行分类，[MemOS](https://arxiv.org/abs/2507.03724) 进一步加入了来源、版本、权限和生命周期。从工程角度看，一条信息要真正成为可用的记忆，至少要回答下面几个问题：

| 要素   | 需要回答的问题                          |
| ---- | -------------------------------- |
| 内容   | 记住了什么事实、经验、状态或规则？                |
| 表示   | 它存在参数、激活状态、文本、向量还是图结构中？          |
| 地址   | 在什么条件下能够找到它？                     |
| 生命周期 | 何时写入、更新、合并、遗忘或删除？                |
| 来源   | 它来自哪里，可信程度如何，能否追溯？               |
| 作用域  | 属于当前 Token、会话、用户、Agent、组织还是公共领域？ |

只列出这些要素还不够，它们最终要串成一条运行闭环。[Agent Memory: Characterization and System Implications of Stateful Long-Horizon Workloads](https://arxiv.org/abs/2606.06448) 把系统开销拆成记忆构建、检索和生成三个阶段，[Agentic Memory](https://aclanthology.org/2026.acl-long.981/) 则把保存、检索、更新、总结和丢弃设计成 Agent 可以学习的动作。结合这两项工作，可以把完整流程概括为写入、组织、更新、检索、使用和反馈，而不只是保存消息、再做一次向量搜索。

# 2. 记忆工程的两条实现路径

为了便于比较，先看看记忆主要由谁控制，再把现有方法分成模型驱动和应用驱动两条路线，当然了，这只是一种工程视角，两类方法不排斥。

## 2.1 模型驱动：让记忆进入模型本体

模型驱动的路线需要修改模型架构、训练方法和参数组织的方式，以便让模型能够在前向计算中直接读取或更新记忆。

代表性方向包括：

| 方向 | 代表工作 | 核心机制 |
|---|---|---|
| 推理时外部 KV 记忆 | [Memorizing Transformers](https://arxiv.org/abs/2203.08913) | 保存历史输入的内部 Key/Value 表示，在生成时通过近邻查询接入 Attention |
| 面向大记忆空间的训练 | [Focused Transformer](https://arxiv.org/abs/2307.03170) | 用对比训练减少相关和无关 Key 在记忆空间中的混淆 |
| 可更新的 Latent-space Memory Pool | [MEMORYLLM](https://arxiv.org/abs/2402.04624) | 在 Transformer 内维护固定容量、可持续更新的 Latent-space Memory Pool |
| 双参数记忆 | [WISE](https://arxiv.org/abs/2405.14768) | 主参数保存预训练知识，侧参数保存持续编辑的新知识，并通过 Router 选择 |
| Neural Long-term Memory | [Titans](https://arxiv.org/abs/2501.00663) | 在 Test-time 依据输入信息更新 Neural Long-term Memory，与 Attention 共同工作 |

模型驱动路线的价值不只是减少外部检索和上下文注入的开销，记忆表示可以进入模型的中间计算，参与 Attention、概念组合和推理，“如何使用记忆” 本身也可以通过训练来持续学习。至于最终能否带来更好的效果，还要看具体架构、训练方法和任务分布。

不过，模型驱动仍是个相对宽泛的分类，Memorizing Transformers 和 Focused Transformer 依然使用模型外部的 KV 存储，只是把读取过程接入到了模型的 Attention，真正的分界不在于数据是跟着模型参数一起存储、还是放在模型之外，而在于模型是否原生学会了寻找和使用这些记忆的能力。

## 2.2 早期的应用驱动：在模型外管理显式记忆

应用驱动的路线不修改基座模型，而是在应用层完成抽取、存储、索引、检索和上下文注入。[MemGPT](https://arxiv.org/abs/2310.08560) 用虚拟上下文管理不同层级的记忆，[Mem0](https://arxiv.org/abs/2504.19413) 从对话中动态抽取、整合和检索关键信息，[Zep](https://arxiv.org/abs/2501.13956) 则用带时间信息的知识图谱维护不断变化的事实与关系。这些方案的常见载体包括：

- 对话摘要
- Embedding 与向量索引
- 带时间信息的知识图谱
- 任务计划、工具执行结果和反馈
- 图片、音频、视频等多模态材料

这条路线不需要重新训练模型，而且写入和更新都很快，也更容易实现权限、审计、删除、版本管理和跨应用共享等组织诉求，因此很快就进入了生产环境。

它的局限也很明确：外部系统可以把信息放进 Prompt，却不能保证模型真正理解，更不能保证换一种说法或者遇到多跳问题时，模型仍能正确调用同一条知识，检索错误、上下文噪声和生成幻觉依然会在运行过程中不断累积。

## 2.3 参数、激活与明文记忆

模型驱动和应用驱动，是从记忆主要由谁控制来区分；再往下看，还要考虑记忆本身以什么形态存在。[MemOS](https://arxiv.org/abs/2507.03724) 用 “时间尺度 × 显式程度” 两个维度来组织现有的记忆机制，短期记忆可以是 Prompt Context 这样的显式信息，也可以是 KV Cache、Hidden State 和激活回路这样的隐式状态；长期记忆则包括外部非参数检索、参数知识、模块化参数适配和参数编辑。换句话说，模型内还是模型外并不是唯一的区别，记忆保留多久、内容是否显式可读，同样会影响它的使用方式：

![](/assets/img/agentic-memory-engineering-1.png)

**文献图 1：记忆类型、机制与代表工作分类。来源：[MemOS](https://arxiv.org/abs/2507.03724)，Table 1。**

| 维度     | 参数记忆             | 激活记忆                                    | 明文/结构化记忆        |
| ------ | ---------------- | --------------------------------------- | --------------- |
| 典型载体   | 模型权重、Adapter、侧参数 | KV Cache、Hidden State、Memory Token、神经记忆 | 文档、事件、向量库、知识图谱  |
| 读取     | 快，随前向计算发生        | 快，直接参与当前推理                              | 需要寻址、检索和上下文注入   |
| 写入     | 慢，通常需要训练或模型编辑    | 可在运行时更新，但容量受限                           | 快，可直接追加或修改      |
| 泛化     | 强，可能迁移到不同表达      | 能保持当前任务和轨迹状态                            | 依赖模型对检索结果的理解    |
| 精确更新   | 困难，容易产生干扰        | 状态边界和遗忘策略困难                             | 容易定位、修订和删除      |
| 可解释性   | 低                | 中低                                      | 高，可展示内容与来源      |
| 治理能力   | 弱                | 依赖运行时                                   | 强，可做权限、版本、审计和回滚 |
| 适合时间尺度 | 稳定能力与长期模式        | Token、轨迹、会话和近期经验                        | 持续变化的事实与共享知识    |

# 3. 为什么内外融合会成为必然趋势

这个趋势不是说每个应用都要部署三层记忆，简单的应用就按简单的来就行，只有当系统需要长期运行，同时还要兼顾性能、持续更新、可靠性、个性化和治理目标时，这个判断才成立，因为在这些约束下，融合往往是更现实的工程选择。

[WISE](https://arxiv.org/abs/2405.14768)、[MemOS](https://arxiv.org/abs/2507.03724) 和 [Titans](https://arxiv.org/abs/2501.00663) 从不同侧面说明了这种分工：模型侧决定记忆能否进入表示学习和推理，影响能力上限；应用侧决定记忆能否及时写入、稳定取回并受到治理，守住可用下限，一个需要长期运行的生产系统很难只靠其中一端。

![](/assets/img/agentic-memory-engineering-2.png)

**图 2：模型侧负责让记忆进入表示与推理，应用侧负责写入、取回与治理，两端共同支撑一个可以长期运行的生产系统。**

## 3.1 读写目标天然冲突

模型训练完后，学到的知识和规律已经保存在参数中，推理时通过一次 forward 就能直接使用，因此读取很快；但要修改其中一个具体知识点，往往需要继续训练或模型编辑，还要做完整的回归测试。明文记忆正好相反，一条事实可以立即修改，却必须在使用时重新检索、排序和注入，[WISE](https://arxiv.org/abs/2405.14768) 对参数编辑与检索式工作记忆的比较，正是这个冲突的一个具体例子：

![](/assets/img/agentic-memory-engineering-3.png)

**文献图 3：持续编辑中的可靠性、泛化性与局部性三角。来源：[WISE](https://arxiv.org/abs/2405.14768)，Figure 1。实验使用 LLaMA-2-7B，在 ZsRE 上连续编辑 100 次。**

在这组实验里，直接修改参数的 FT-EWC 保住了可靠性和泛化性，但局部性接近于零；检索式工作记忆 GRACE 保住了可靠性和局部性，泛化性却接近于零，WISE 通过主参数、侧参数和 Router 尝试同时兼顾三者。这个实验不能证明所有模型内或模型外记忆都会遇到同样的问题，但它把冲突画得很直观，知识写得越深，越可能影响原有能力；隔离得越彻底，又越难跨越问法。

这种取舍并不是 Agent 记忆才有，就像传统 PC 同样没有一种存储形态能够同时做到读取快、写入成本低、容量大和长期保存，因此才会把存储分成寄存器、缓存、内存和磁盘，越靠近 CPU，读取越快但容量越小；越靠近持久存储，容量越大但访问路径越长。Agent 记忆也在出现类似的分层，参数、激活和明文记忆分别优化不同目标，很难由其中一层包办所有需求。

## 3.2 世界持续变化，模型快照却天然静态

组织规则、产品能力、代码、用户偏好和运行状态都在不断变化，每次有变化就重新训练模型，在工程上行不通；但如果只把变化保存在外部，模型又会一直依赖临时拼接的 Context。

更实际的做法是，把频繁变化的信息留在容易写入的外部层，把当前任务状态放在激活层，再把经过长期验证、可以稳定复用的模式逐步巩固到模型参数或 Latent-space Memory Pool 中。[MEMORYLLM](https://arxiv.org/abs/2402.04624) 和 [Titans](https://arxiv.org/abs/2501.00663) 分别从 Latent-space Memory Pool 和 Test-time Neural Memory 两个方向探索了这种可能。

![](/assets/img/agentic-memory-engineering-4.png)

**图 4：一种按变化频率分层的实现思路。变化快的信息留在容易更新的外部层，当前任务状态由 Activation Memory 维护，经过筛选和反复验证的模式再逐步巩固到参数或 Latent-space Memory Pool。**

## 3.3 换一种问法，记忆未必还能生效

外部记忆保存的是一条记录，只要检索命中，它就能准确返回原文，但模型仍要重新判断这条记录和当前问题有什么关系。问题换一种说法、上下文发生变化，或者答案需要多步推理时，模型都要重新完成一次检索和理解，这并不是说外部记忆不能泛化，而是泛化主要依赖当下这一次检索和推理。

模型参数或 Latent-space Memory Pool 则会直接参与模型内部表示，如果更新机制有效，一条经验就不必依附原来的措辞，而是可以在改写问题、相似场景和新的推理链中继续发挥作用。[WISE](https://arxiv.org/abs/2405.14768) 把持续模型编辑的难题概括为：可靠性、泛化性和局部性很难同时满足。直接修改长期参数，可能干扰原有知识；只依赖检索结果临时激活模型，又可能缺乏泛化。WISE 引入主参数、侧参数和 Router，正是为了对记忆进行分层、路由和隔离：

![](/assets/img/agentic-memory-engineering-5.png)

**文献图 5：WISE 的 Memory Router 在连续编辑过程中的激活分数。上图为 ZsRE，下图为 SelfCheckGPT，紫线是 Router 的激活阈值。来源：[WISE](https://arxiv.org/abs/2405.14768)，Figure 3。**

上面的 ZsRE 子图里，原始编辑问题和改写后的问题虽然措辞不同，但 Activation Score 落在同一区间，因此都会进入保存新知识的侧参数；无关问题则留在主参数。下面的 SelfCheckGPT 子图也呈现出类似的分离。这至少说明，在 WISE 的这组实验里，路由依据并不是字面是否完全一致，而是输入能否激活被编辑的知识。

可以把这个差别概括为：**模型外把泛化留给每一次推理，模型内则试图提前把一部分泛化能力写进记忆表示。**

## 3.4 记住过去，不等于会改变下一次选择

对现在的 Agent 来说，能回答过去发生过什么只是最低要求，真正有价值的场景是，过往经历能否改变下一次选择，比如：

1. 一次工具调用失败后，模型会不会主动调整参数或调用顺序
2. 用户反复修改某类输出后，能不能形成稳定偏好
3. 多次任务轨迹，能不能逐渐抽象为可复用的规划策略

外部记忆是每次重新查阅经验，模型内记忆则试图把反复验证过的经验压缩成表示、策略或技能，直接影响之后的行为。[Agentic Memory](https://aclanthology.org/2026.acl-long.981/) 把记忆操作纳入可学习策略，[Nested Learning](https://arxiv.org/abs/2512.24695) 则进一步讨论能够修改自身的学习模块，它们关心的不只是如何保存，而是如何影响后续的计算过程。

两者的分工概括为：**模型外记忆更擅长保留证据，模型内记忆更擅长把经验转化为可复用的行为。**

## 3.5 模型记住了知识，不代表知识变得可治理

企业知识涉及来源、版本、权限、冲突、责任人、删除和回滚，即使模型能够在参数中记住全部内容，参数本身也不是合格的组织级事实账本。

模型内部记忆可以负责快速调用和经验泛化，但共享事实仍然需要显式、可审查的载体。[MemOS](https://arxiv.org/abs/2507.03724) 把来源、版本、生命周期、权限和审计纳入 MemCube 与调度体系。这也说明，外部的管理与治理并不是一个过渡方案，而是长期记忆能够可靠更新的必要条件。

## 3.6 不同时间尺度和作用域，不能共用一种记忆策略

Next Token 的局部状态、一次任务的执行轨迹、某个用户的长期偏好、一个团队共享的领域知识，不应使用同一种保存和更新策略，它们在保留时间、访问主体、隐私等级和一致性要求上完全不同。

参数、激活和明文记忆分别适合不同的时间尺度。[MemOS](https://arxiv.org/abs/2507.03724) 统一调度三类记忆，[Nested Learning](https://arxiv.org/abs/2512.24695) 则把模型理解为一组更新频率不同的嵌套学习过程。两者都说明，真实任务更适合分层处理，而不是把所有内容强行塞进一个超长 Context，或者全部训练进模型参数：

![](/assets/img/agentic-memory-engineering-6.png)

**图 6：记忆介质与时间尺度并非一一对应。Activation Memory 更适合 Next Token 和当前任务状态，明文或结构化记忆覆盖会话、用户与组织知识，参数或 Latent-space Memory 更适合经过长期验证的模式、策略与技能。作用域越大，权限、隐私、一致性和治理要求也越高。**

## 3.7 单一记忆介质无法兼顾所有目标

WISE、MemOS 和 Titans 并没有证明某种架构在所有场景下都是最优解，它们反而能说明的是，系统得根据知识的特点选择不同记忆介质，才能在延迟、成本、准确性、可塑性和治理之间找到合适的平衡点：

![](/assets/img/agentic-memory-engineering-7.png)

**文献图 7：明文、激活和参数记忆之间的转换路径。来源：[MemOS](https://arxiv.org/abs/2507.03724)，Figure 5。**

原图给出了三类记忆之间的双向转换路径，明文记忆可以编码为激活状态，激活状态也可以解码回明文；激活记忆可以缓存为参数记忆，参数记忆则可以通过潜在激活进入当前推理。更长期的巩固，可以通过 Fine-tuning 把明文知识写入参数，再通过 Parametric Decoding 重新转回显式内容。所以，这里的融合不是简单把三类记忆摆在一起，而是允许记忆在不同介质之间迁移。

# 4. 什么是记忆原生模型

“记忆原生模型” 目前还不是学术界统一使用的术语，这里只用它来描述一种正在形成的架构方向，记忆不再只是推理前临时接入的数据库或摘要，而是在模型架构、训练目标和运行机制中，原生支持写入、更新、寻找、调用与遗忘。

结合 [MemOS](https://arxiv.org/abs/2507.03724) 的异构记忆管理、[MEMORYLLM](https://arxiv.org/abs/2402.04624) 的 Latent-space Memory Pool、[Titans](https://arxiv.org/abs/2501.00663) 的 Test-time Neural Memory，以及 [Agentic Memory](https://aclanthology.org/abs/2026.acl-long.981/) 的可学习记忆操作，加上王昊奋在 2026 年 Agentic AICon 上海站的公开分享《面向智能体的记忆体系：理论与实践》，可以从三个方面判断一个模型是否具备 “记忆原生” 的特征：

1. **可寻址**：模型能够根据当前输入选择相关记忆，而不是依赖应用把所有内容提前拼接到 Prompt
2. **可更新**：推理过程中，模型能够判断是否需要更新记忆，并依据策略写入、巩固或遗忘
3. **可计算**：读取结果进入 Attention、Hidden State 或专用 Memory Block，影响表示和推理，而不只是作为一段前缀文本被塞进 Prompt

![](/assets/img/agentic-memory-engineering-8.png)

**图 8：记忆原生模型的一次读写循环。输入先通过 Address / Router 找到相关记忆，读取结果直接进入模型内部计算；生成结束后，更新策略再决定是否写入、巩固或遗忘。三个动作分别对应可寻址、可计算与可更新。**

## 4.1 目前能放多大的记忆

现在没有统一答案，因为不同论文对容量的定义还不一样。它可能指模型能访问多少历史 Token，也可能指一个 Latent-space Memory Pool 包含多少参数，或者连续写入多少条事实后仍能稳定工作，如果把这些口径混在一起，很容易把长 Context 当成长期知识库，也容易把更新了一百万次误读成记住了一百万条知识。

目前为止的一些工作：

| 工作                                                                                        | 记忆形态                           | 论文验证到的规模                                                | 这个数字实际代表什么                                      |
| ----------------------------------------------------------------------------------------- | ------------------------------ | ------------------------------------------------------- | ----------------------------------------------- |
| [Memorizing Transformers](https://arxiv.org/abs/2203.08913)                               | 历史 Key/Value 记忆                | 记忆扩大到 262K Token 时，语言建模效果仍在提升                           | 模型能利用较长的近期历史，不代表这些内容成为可长期更新的知识                  |
| [Focused Transformer / LongLLaMA](https://arxiv.org/abs/2307.03170)                       | 模型原生读取的外部 Key/Value 记忆         | Passkey Retrieval 在 100K Token 时准确率 94.5%，在 256K 时为 73% | 证明大规模寻址可行，但评测仍是单条信息检索                           |
| [Titans](https://arxiv.org/abs/2501.00663)                                                | Test-time Neural Memory        | Needle-in-a-Haystack 实验扩展到 2M Token 以上                  | 说明模型可以压缩并利用超长输入流，不等于保存了 2M Token 的永久事实          |
| [TTT-E2E](https://arxiv.org/abs/2512.23675)                                               | 在 Test-time 更新的 Fast Weights   | 在 3B 模型上验证到 128K Context                                | 说明当前 Context 可以被压进权重并在同一序列中继续使用，不代表已经形成跨请求的长期记忆 |
| [MEMORYLLM](https://arxiv.org/abs/2402.04624)                                             | 固定大小的 Latent-space Memory Pool | 在 7B 模型上增加 1.066B 记忆参数，并在接近一百万次更新后未观察到整体性能退化            | 一百万是更新次数，不是独立事实数；固定容量也意味着新记忆会逐步替换旧记忆            |
| [WISE](https://arxiv.org/abs/2405.14768)                                                  | 可路由的侧参数记忆                      | 连续编辑扩展到 3,000 条，额外参数约 0.64%，GPU 显存增加约 4%                | 这是最接近知识库事实写入的口径，但实验规模仍是数千条                      |
| [Conditional Memory / Deep Sparse Embedding](https://aclanthology.org/2026.acl-long.226/) | 基于 N-gram 寻址的静态参数查找            | 在总参数量 27B 的模型上验证，并可将大规模记忆参数卸载到主机内存                      | 说明静态知识查找可以随参数扩展，但它还不是可持续写入的动态知识库                |

把这些放在一起看，模型已经可以利用百万 Token 级的历史，也可以维护十亿参数级的 Latent-space Memory Pool。但如果按能够独立写入并验证的事实数来计算，公开实验还主要停留在数千条。这些数字大多来自 Passkey、Needle-in-a-Haystack 或模型编辑基准，还回答不了真实知识库最关心的问题，在指定准确率下，模型究竟能保存多少条相互独立的知识？持续写入、改写和删除之后，能不能稳定召回，同时不影响无关能力？

所以在知识库场景里，更现实的目标并不是把所有文档都训练进模型，高频、稳定、需要跨表达复用的知识和行为模式，可以进入模型参数或 Latent-space Memory Pool；长尾、经常变化、需要原文证据和精确更新的事实，仍然留在外部知识库。

## 4.2 记忆如何进入模型计算

上面的容量数字不能直接横向比较，一个重要原因是这些工作把记忆放在了不同位置，沿着记忆如何进入模型计算，可以看到几种代表性的做法。

[**Memorizing Transformers**](https://arxiv.org/abs/2203.08913) 保存历史输入的内部 Key/Value 表示，并在推理时做近邻查询。Memorizing Transformers 的实验表明，模型可以在测试阶段使用刚刚出现的新函数、定理或代码，而不必先修改参数。

[**MEMORYLLM**](https://arxiv.org/abs/2402.04624) 在 Transformer 内维护一个固定大小、可以持续更新的 Latent-space Memory Pool。它希望模型能够不断吸收新的文本知识，同时尽量保住旧记忆和原有能力。

[**WISE**](https://arxiv.org/abs/2405.14768) 把预训练知识和后续编辑的知识分别放在主参数与侧参数中，再由 Router 判断当前问题该走哪一侧。它说明，即使都属于参数记忆，仍然需要分区、路由和冲突管理。

[**MEMOIR**](https://arxiv.org/abs/2506.07899) 同样不直接覆盖原模型参数，而是在旁边增加专门的 Residual Memory。写入新知识时，它先根据输入激活生成稀疏掩码，只修改残差记忆中的一小部分参数；推理时，再根据查询的激活模式找到相关编辑。这样既可以减少连续编辑之间的相互覆盖，也能尽量保留对改写问题的泛化能力：

![](/assets/img/agentic-memory-engineering-10.png)

**文献图 9：MEMOIR 的残差参数记忆及其持续编辑过程。来源：[MEMOIR](https://arxiv.org/abs/2506.07899)，Figure 2。**

[**Titans**](https://arxiv.org/abs/2501.00663) 把 Attention 看作精确但容量有限的短期记忆，再增加一个能在 Test-time 更新的 Neural Long-term Memory。在 Memory as Context 架构中，历史信息先写入 Neural Long-term Memory；处理当前序列时，模型再读出相关的内部表示，与 Persistent Memory 一起参与推理。

[**Conditional Memory / Deep Sparse Embedding**](https://aclanthology.org/2026.acl-long.226/) 则把静态知识查找做成 Transformer 的原生能力。它先对局部 N-gram 做确定性 Hash，从大型 Embedding 表中找到对应内容，再根据当前 Hidden State 调整这些静态记忆并注入模型。这项工作说明，“模型原生记忆”也可以是一个和 Attention、MoE 并列的独立组件：

![](/assets/img/agentic-memory-engineering-11.png)

**文献图 10：Deep Sparse Embedding 的 Conditional Memory 架构。来源：[Conditional Memory via Scalable Lookup](https://aclanthology.org/2026.acl-long.226/)，Figure 1。**

[**Nested Learning / HOPE**](https://arxiv.org/abs/2512.24695) 进一步把神经网络理解为多个更新频率不同、彼此嵌套的学习过程。普通 Transformer 的 Attention 可以随当前 Context 快速变化，但 FFN 和投影参数在预训练结束后基本固定；HOPE 则把 Self-Modifying Titans 与 Continuum Memory System 组合起来，让不同层级按照各自的时间尺度持续更新：

![](/assets/img/agentic-memory-engineering-12.png)

**文献图 11：Nested Learning 视角下 HOPE 与普通 Transformer 的更新层级对比。来源：[Nested Learning](https://arxiv.org/abs/2512.24695)，Figure 5。**

[**MemOS**](https://arxiv.org/abs/2507.03724) 的公开工作先把参数、激活和明文记忆统一成可管理的资源；MemOS 2.0 又尝试通过 Local Memory Block 和 Hyper Memory Block，让记忆进一步进入模型内部。从已经披露的结构图看，它仍然以普通 Transformer 为主体，再加入专用记忆模块。至于是否需要联合训练整个模型、训练成本多高、能够扩展到多大容量，还要等待公开实现和评测。

## 4.3 MemOS 2.0：从统一管理到 Memory Block

[MemOS](https://arxiv.org/abs/2507.03724) 的公开论文先从统一记忆单元 MemCube 做起，每个 MemCube 都用相同的 Metadata Header 记录来源、生命周期、使用情况、优先级、权限和存储策略，Payload 则可以是明文、激活状态或参数补丁。收到 Prompt 后，MemScheduler 负责匹配记忆、确定加载优先级、执行访问控制和运行时注入，同时处理版本合并与过期淘汰：

![](/assets/img/agentic-memory-engineering-9.png)

**文献图 12：异构记忆的统一封装结构 MemCube。来源：[MemOS](https://arxiv.org/abs/2507.03724)，Figure 6。**

这张图里有三个值得注意的地方：

- 明文、激活和参数记忆不再是三套彼此独立的系统，它们可以共享生命周期、访问控制和调度接口
- “原生” 不等于全部存进模型权重，明文记忆仍然是完整记忆体系的一部分；区别在于，模型可以原生寻找、读取和写回记忆，而不是每次都由应用临时拼进 Prompt
- 外部检索不一定要成为每次请求的必经环节，但寻找记忆这件事不会消失，而是会进入模型内部的 Attention、Router、Memory Block 或神经记忆读取过程

### 从 MemOS 1.0 到 MemOS 2.0

在 MemOS 1.0 的公开论文中，重点是把参数、激活和明文记忆纳入统一的表示、调度与转换体系，而到了 MemOS 2.0，目标从优化记忆层次进一步推进到了管理 Agent 的运行状态，系统不再只是管理一条条记忆条目，还要维护用户、任务、环境、经验和组织状态，并支持这些状态在长期运行中不断演化。

版本对比：

| | MemOS 1.0 | MemOS 2.0 |
|---|---|---|
| 主要目标 | 统一管理异构记忆，优化读写与调度 | 管理 Agent 的长期状态与持续演化 |
| 核心对象 | 参数、激活和明文记忆 | 用户、任务、环境、经验和组织状态 |
| 核心机制 | MemCube、MemScheduler 与跨层转换 | Common Transformer、Local Memory Block 与 Hyper Memory Block |
| 公开证据 | 论文和核心系统实现均可核验 | 2.0 框架已经开源；记忆原生模型由公开演讲披露，对应实现尚未公开 |

### 在一次请求里，记忆是怎么工作的

把记忆放进模型不是把所有资料都重新训练进模型权重，Memory Block 是插在 Transformer 里的专用记忆模块，它保存的未必是可以直接阅读的文字，也可能是向量、Hidden State 或一小组可以更新的参数：

| 组件                 | 先理解为          | 主要作用                      |
| ------------------ | ------------- | ------------------------- |
| Common Transformer | 正在完成任务的大脑     | 理解当前输入并生成结果               |
| Local Memory Block | 放在手边的工作台      | 在当前推理和任务轨迹中维护目标、中间状态与近期经验 |
| Hyper Memory Block | 任务结束后的整理与巩固机制 | 在一轮生成之后提交或更新更长期的记忆        |

把一次模型请求展开，大致会经过下面五步：

1. 用户输入先被转换成 Token 和隐藏向量，Common Transformer 仍然负责主要的理解与生成
2. 生成过程中，Local Memory Block 持续维护当前任务的状态，让模型不必只依赖眼前这一小段输入
3. Local Memory 的结果进入模型计算，可能放在额外的输入位置、Hidden State、FFN 或 Attention 参数中，从而直接影响后续生成
4. 一轮生成完成后，Hyper Memory Block 提交或更新需要长期保留的状态
5. 下一次请求到来时，相关记忆再次进入模型计算，影响模型如何理解问题和采取行动

![](/assets/img/agentic-memory-engineering-13.png)

**图 13：根据公开架构信息整理的一次模型请求内记忆流程。Common Transformer 负责主干计算，Local Memory Block 在生成过程中维护并读写当前状态；生成结束后，Hyper Memory Block 提交或更新长期状态，并在下一次请求中重新进入模型计算。**

可以用一个简单例子来理解。假设用户说：“以后给我的代码示例都使用 Python”，普通 RAG 会把这句话保存在模型外，等下一次请求到来时先搜索，再把原文拼回 Prompt。记忆原生模型想做的则是：先把这条偏好放进当前任务的 Local Memory；如果需要长期保留，再交给 Hyper Memory 巩固成更持久的状态，下一次即使用户没有重复原话，这段记忆也可以直接参与模型计算。模型保存的可能不再是原句，而是它对这个用户偏好 Python 的内部表示。

这里也能看出模型内记忆最重要的两个潜在优势，第一，记忆进入表示空间后，有机会摆脱原始措辞，在问题换一种说法时继续生效；第二，经过反复验证的经验可以逐渐变成行为，模型不必每次都重新阅读一份说明。代价也恰恰来自这里，向量或参数不像原文那样容易查看、修改和删除，一旦写错，还可能影响无关问题。

真正困难的并不是加上两个 Block，而是让模型学会三件事：

- 写什么：从一段很长的交互中压缩出值得保留的信息
- 怎么读：根据当前问题找到相关记忆，而不是把所有记忆都带进计算
- 如何更新：新信息到来时能够覆盖、合并或遗忘旧信息，同时不破坏无关能力

要学会这些能力，通常需要专门的训练任务和更新目标，但不一定要从头训练一个新基模。WISE、MEMOIR 都保留了主模型，只训练或更新额外的参数记忆。MemOS 2.0 的结构图也把普通 Transformer 和专用记忆模块画成相对独立的部分，因此有可能只训练记忆模块。不过，公开材料没有说明是否冻结基模，也没有披露具体训练方法，所以这目前还只是对实现方式的推测。

王昊奋在这次公开分享中列出了记忆进入模型的几种可能位置，包括额外的输入位置、Hidden State、FFN 和 Attention 参数，但这不代表 MemOS 2.0 已经同时实现了四种方案。目前能够确定的是，它想让记忆直接参与模型内部计算和持续更新，而不再只是模型外部的一项资源。

这里还要区分已经开源的 MemOS 2.0 框架，以及这次公开分享中披露的 MemOS 2.0 记忆原生模型。后者目前只公布了架构，公开材料没有给出所用基模、Checkpoint、训练方法、训练成本、记忆容量和系统评测；[MemOS 开源仓库](https://github.com/MemTensor/MemOS) 也没有提供 Local Memory Block 或 Hyper Memory Block 的对应实现，官方文档中的[参数记忆](https://memos-docs.openmem.net/open_source/modules/memories/parametric_memory/)仍标为开发中。

## 4.4 Test-time Training：模型在推理过程中继续学习

MemOS 2.0 选择了一条比较直观的路径：在 Common Transformer 旁边加入 Local Memory Block 和 Hyper Memory Block，分别处理当前任务状态与更长期的记忆巩固。从已经披露的结构看，持续变化的内容主要交给专门的记忆模块；主干参数是否也会更新，目前还没有公开信息。

沿着这个问题继续往下走，下一步自然是：模型能不能在处理输入的同时继续学习？[Titans](https://arxiv.org/abs/2501.00663) 已经让专门的 Neural Long-term Memory 在 Test-time 持续更新，[TTT-E2E](https://arxiv.org/abs/2512.23675) 则进一步把长 Context 问题重新定义为 Continual Learning：模型一边读取 Context，一边根据刚刚读到的内容更新 Fast Weights。

### TTT-E2E 怎么把 Context 写进 Fast Weights

TTT-E2E 的主干仍然是 Transformer，Attention 使用固定大小的 Sliding Window，真正的变化发生在运行时更新机制上。TTT-E2E 在 128K Context 的主要实验中使用 8K 的 Attention Window，并把输入分成 1K Token 一组的 TTT Mini-batch。每处理完一组，模型才执行一次梯度更新：

1. 使用当前权重处理这一组 Token，Sliding-window Attention 负责提供窗口内的直接上下文
2. 在模型最终输出处计算标准的 Next-token Prediction Loss
3. 反向传播只进入最后四分之一 Transformer Blocks，并且只更新其中的 MLP
4. 下一组 Token 使用更新后的 MLP 继续计算，上一组信息因此被压进了 Fast Weights

如果用一个公式表示，这一步就是 `Wᵢ = Wᵢ₋₁ - η∇Lᵢ`。`Wᵢ₋₁` 是处理当前 Mini-batch 前的权重，`Lᵢ` 是这一组 Token 的 Next-token Prediction Loss，更新后的 `Wᵢ` 会直接参与下一组 Token 的计算：

![](/assets/img/agentic-memory-engineering-14.png)

**文献图 14：左侧是 TTT-E2E 的计算结构，梯度只穿过最后四分之一 Blocks，并更新每个 Block 中的一个 MLP；右侧是采用 Layer-wise Key-Value Binding Loss 的 TTT-KVB。来源：[End-to-End Test-Time Training for Long Context](https://arxiv.org/abs/2512.23675)，Figure 3。**

Embedding、Normalization 和 Sliding-window Attention 在 Test-time 都被冻结，TTT-E2E 作者发现更新这些部分会让 Outer Loop 不稳定。其次，每个需要更新的 Block 都保留了另一个静态 MLP，用来保存预训练阶段学到的知识，避免 Fast Weights 的连续变化直接覆盖原有能力。为了让比较公平，作者缩小了 MLP 的 Hidden Dimension，使模型总参数量与 Baseline 保持一致。

这样就形成了两种时间尺度：8K 的 Sliding-window Attention 保留当前局部 Context，更新后的 MLP 则把更早的信息压缩成参数状态。TTT-E2E 将前者理解为 Short-term Memory，将后者理解为 Long-term Memory。不过，这里的 Long-term 指跨越当前 Attention Window，并不等于跨请求、跨用户长期保存。

### 这不是普通的边读边 Fine-tuning

如果一个模型一直按推理时参数不变的方式训练，到了 Test-time 再突然修改权重，更新未必有用。TTT-E2E 在训练阶段就会完整模拟这些 Test-time Update，再根据更新之后的预测效果反过来优化初始权重。TTT-E2E 把 Test-time 的更新称为 Inner Loop，把训练初始权重的过程称为 Outer Loop；后者需要计算 Gradients of Gradients，本质上是在训练模型如何在推理时学习。

[TTT-E2E 论文《End-to-End Test-Time Training for Long Context》](https://arxiv.org/abs/2512.23675)的 Table 1 给出了一个 760M 模型上的对比，数值是 DCLM 上的 Test Loss，越低越好：

| 方法 | Test Loss |
|---|---:|
| Sliding-window Attention Baseline | 2.827 |
| TTT-KVB | 2.818 |
| TTT-KVB Simplified | 2.819 |
| TTT-E2E All Layers MH | 2.806 |
| TTT-E2E | 2.805 |

实验使用 760M 模型在 DCLM 上预训练和评测，TTT-E2E 作者将小于 0.001 的差异视为没有统计显著性。

真正带来明显变化的，不是简单多加一层 MLP，而是把每层单独使用的 Key-Value Binding Loss 换成模型最终输出的 Next-token Prediction Loss，并在训练时针对更新后的效果优化初始权重。最终版本只更新最后四分之一 Blocks 中容量更大的 MLP，与更新所有层的 Multi-head MLP 相比，Fast Weights 从 18M 增加到 88M，H100 上每 1K Prefill Token 的延迟则从 0.017 秒降到 0.0086 秒。

### TTT-E2E 的实验数据说明了什么

TTT-E2E 论文中最大的模型实际是 2.7B 参数，正文按 3B 统计，共 32 个 Transformer Blocks、2560 Hidden Dimension 和 32 个 Attention Heads。TTT-E2E 论文 Figure 1 中的模型都训练了 164B Token，先在 DCLM 上用 8K Context 预训练，再在 Books 数据上分别扩展到 8K、16K、32K、64K 和 128K：

![](/assets/img/agentic-memory-engineering-15.png)

**文献图 15：不同模型随 Context Length 增长的 Test Loss 与 Prefill Latency。左图以 Full Attention 为零点，数值越低越好；右图为单张 H100 上处理每 1K Token 的时间。来源：[End-to-End Test-Time Training for Long Context](https://arxiv.org/abs/2512.23675)，Figure 1。**

这组实验有三个重要结果：

- 在 8K 到 128K Context 上，TTT-E2E 的 Test Loss 始终比 Full Attention 低约 0.012，而普通 Sliding-window Attention 和其他压缩型模型在 Context 变长后明显退化
- 在单张 H100 上，TTT-E2E 的 Prefill Latency 基本不随 Context Length 增长；到 128K 时比 Full Attention 快 2.7 倍
- 在 [TTT-E2E 论文 Figure 4](https://arxiv.org/abs/2512.23675) 的 760M、24 层模型消融实验中，只更新最后 1 层或 3 层无法保持 Context Scaling；更新 6 层和 12 层都可以，而 12 层没有继续带来明显收益，因此 TTT-E2E 最终选择最后四分之一

这些结果证明 Fast Weights 可以压缩并利用长 Context，但压缩也意味着会丢失细节，TTT-E2E 论文在 128K Context 上的 S-NIAH 精确召回结果很能说明这个问题：

| 128K S-NIAH 任务     | Full Attention | TTT-E2E |
| ------------------ | -------------: | ------: |
| Pass-key Retrieval |            99% |      6% |
| Number in Haystack |            86% |      5% |
| UUID in Haystack   |            64% |      3% |

Full Attention 保存了所有历史 Key/Value，因此可以回到原位置精确读取；TTT-E2E 则把历史压进有限的 MLP 权重，适合吸收有助于后续预测的分布和模式，却很难保留一串与上下文无关的随机数字或 UUID。

### 边思考边训练还有多远

TTT-E2E 确实会在生成过程中继续更新，每当新生成的 Token 填满一个 1K Mini-batch，模型就执行一次更新，再用新权重继续生成。但 TTT-E2E 论文对长输出的验证仍然有限，只是在 3B Base Model 上先输入 8K Books Token，再续写 8K Token，并用 Qwen3-8B-Base 评价生成结果；Instruction Tuning、Reinforcement Learning 和真实的长 Chain of Thought 都不在实验范围内。

因此，模型在读取和生成过程中更新 Fast Weights 已经有 TTT-E2E 论文和[开源代码](https://github.com/test-time-training/e2e)支撑，但推理模型一边思考一边训练自己，并因此获得更强推理能力还没有被 TTT-E2E 证明。

2026 年 8 月，[量子位](https://www.qbitai.com/2026/08/471701.html)和 [AI Midday](https://aimidday.com/ssis-first-model-reportedly-trains-itself-while-it-thinks/) 相继报道称 SSI 正在探索基于 TTT 的推理模型，TTT 正在从长 Context 研究向推理与持续学习场景延伸，但是否已经成为 SSI 的实际技术路线，还需要等待模型发布、论文或评测。

# 最后

记忆原生模型真正落地之前，仍有一些基础问题没有解决：什么值得写入，参数、激活和明文记忆发生冲突时以谁为准，错误记忆能否撤销和追溯，不同用户与 Agent 的记忆如何隔离，以及这些能力该如何评测。这些问题贯穿从写入到遗忘的整个生命周期，并不会因为引入模型内记忆自动消失。

研究已经从组织 Prompt 和 Context，推进到处理跨时间的状态、更新和遗忘。现有工作已经把可访问的历史推到百万 Token 级，把可更新的 Latent-space Memory Pool 扩展到十亿参数级，也把连续事实编辑验证到数千条，但这些结果仍然不能说明模型内部已经可以替代大型知识库。

外部记忆更擅长保存完整、可以核验和更新的事实；模型内记忆则更有机会跨越原始问法，在新的问题和场景中继续生效，并把反复验证过的经验转化为之后的行为。对于需要长期运行、同时兼顾泛化与治理的系统，两者结合更现实。

# 参考论文

1. Zhang et al., [A Survey on the Memory Mechanism of Large Language Model based Agents](https://arxiv.org/abs/2404.13501), arXiv 2024
2. Luo et al., [From Storage to Experience: A Survey on the Evolution of LLM Agent Memory Mechanisms](https://aclanthology.org/2026.findings-acl.2069/), Findings of ACL 2026
3. Omri et al., [Agent Memory: Characterization and System Implications of Stateful Long-Horizon Workloads](https://arxiv.org/abs/2606.06448), arXiv 2026
4. Yu et al., [Agentic Memory: Learning Unified Long-Term and Short-Term Memory Management for Large Language Model Agents](https://aclanthology.org/2026.acl-long.981/), ACL 2026
5. Packer et al., [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560), arXiv 2023
6. Chhikara et al., [Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory](https://arxiv.org/abs/2504.19413), arXiv 2025
7. Rasmussen et al., [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956), arXiv 2025
8. Lewis et al., [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401), NeurIPS 2020
9. Wu et al., [Memorizing Transformers](https://arxiv.org/abs/2203.08913), ICLR 2022
10. Tworkowski et al., [Focused Transformer: Contrastive Training for Context Scaling](https://arxiv.org/abs/2307.03170), NeurIPS 2023
11. Wang et al., [MEMORYLLM: Towards Self-Updatable Large Language Models](https://arxiv.org/abs/2402.04624), arXiv 2024
12. Wang et al., [WISE: Rethinking the Knowledge Memory for Lifelong Model Editing of Large Language Models](https://arxiv.org/abs/2405.14768), NeurIPS 2024
13. Behrouz et al., [Titans: Learning to Memorize at Test Time](https://arxiv.org/abs/2501.00663), arXiv 2025
14. Li et al., [MemOS: A Memory OS for AI System](https://arxiv.org/abs/2507.03724), arXiv 2025
15. Wang et al., [MEMOIR: Lifelong Model Editing with Minimal Overwrite and Informed Retention for LLMs](https://arxiv.org/abs/2506.07899), NeurIPS 2025
16. Cheng et al., [Conditional Memory via Scalable Lookup: A New Axis of Sparsity for Large Language Models](https://aclanthology.org/2026.acl-long.226/), ACL 2026
17. Behrouz et al., [Nested Learning: The Illusion of Deep Learning Architectures](https://arxiv.org/abs/2512.24695), NeurIPS 2025
18. Tandon et al., [End-to-End Test-Time Training for Long Context](https://arxiv.org/abs/2512.23675), arXiv 2025
