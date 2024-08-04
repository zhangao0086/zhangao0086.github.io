---
layout: post
title: "Naive RAG and Advanced RAG"
date: 2024-08-04 23:51:32 +0800
categories: [分享]
article_type: 1
typora-root-url: ../../github.io
---

# 什么是 RAG

在业界提出 RAG 以前，我们使用 LLM 的方式是这样的：

![](/assets/img/rag-4.png)

为了获得更好的输出，可以搭配上思维框架，不仅能提升模型在理解、生成、推理等方面的能力，还能增强用户交互体验。

CoT 示例：

```python
# Chain-of-Thought（CoT）提示词
prompt = """
你是一位商业分析师，正在帮助公司进入一个新市场。

请按照目标市场的地理位置和人口統计、市场需求和购买力、
产品特性、竞争力等要素来按部就班的分析并调整策略。

请详细说明每一步的分析结果和具体策略。
"""
```

> 让模型一步一步的思考

让模型提供代码：

![](/assets/img/rag-2.jpg)

> 让 LLM 提供可运行代码的方式，也被称作 ***Program-of-Thought***，通过运行代码得到更加正确的答案

用一张图汇总起来就是这样：

![](/assets/img/rag-1.jpg)

有用，但不总是有用，许多应用场景中的信息是动态变化的，例如新闻、科技发展趋势等，传统生成模型由于训练数据是静态的，无法及时反映最新的信息：

- 今天天气怎么样 --- *时效性知识*
- 欧洲杯今天有哪几场比赛 --- *时效性知识*
- fischer rc4 speed 2020 的板腰长度是多少 --- *长尾知识*

以及 To B 场景下：

- 我入职 3 年，今年有多少天年假 --- *私域知识*
- 金融、汽车、信息安全、能源等方面的知识 --- *领域知识*

RAG 能解决在实际应用过程中的这些问题：

1. 通过引入外部文档库，可以在生成文本时检索到最新和最相关的信息，从而**提高生成内容的准确性、减少幻觉**
2. 外部资源的知识一方面**提高了知识的丰富度**，也代表着不同的视角，使生成的内容**更加多样化**
3. 不用为了完成任务训练一个高性能的生成模型，减少了对大规模训练数据的依赖，也就**减少了应用成本**
4. 能应对动态变化的信息需求，及时**反映最新的信息**
5. 传统生成模型缺乏的**特定领域知识**，RAG 可以通过检索专业文献和数据库来弥补这一不足
6. 通过检索到最新和最相关的文档，RAG 可以减少生成过程中出现的不准确或编造的信息。

RAG（Retrieval Augmented Generation）= RA + G，RA 代表 [Re-Imagen](https://arxiv.org/abs/2209.14491)、[RA-NER](https://www.amazon.science/publications/ra-ner-retrieval-augmented-ner-for-knowledge-intensive-named-entity-recognition) 这类检索增强系统，G 则代表 LLM：

![](/assets/img/rag-3.png)

# Naive RAG

上图是 RAG 的雏形，被称为 *Naive RAG*，其最大的特点是**数据单向流通**，易于实现：

1. 准备一个由文档组成的知识库，这些文档可以是结构化的（如数据库记录）或非结构化的（如网页内容、PDF 文件等）
2. 将文档（通常比较长）分割为较少的片段，称为 chunks，每个 chunks 是一个独立的短单元，可以是一个段落、几句话或者固定长度的字符串
3. 利用 Embedding Model 将 chunks 处理成向量并存储到向量数据库中
4. 当用户输入 query 时，首先用相同的 Embedding Model 将 query 转换为向量表示，然后在文档库中检索与查询最相似的 Top-K 个 chunks
5. 将检索到的 K 个相关 chunks 与原始 query 一起输入到生成模型中，常见的方法包括直接拼接查询，或使用更复杂的融合策略，如加权平均
6. 得到生成模型的返回

下图是一个从 PDF 文档中检索内容的过程示例：

![](/assets/img/rag-5.jpg)

# Advanced RAG

相比 Naive RAG，Advanced RAG 通过引入两个新的处理阶段优化了检索效果：

![](/assets/img/rag-6.png)

> Comparison between the three paradigms of RAG ([Gao et al. 2024](https://arxiv.org/abs/2312.10997))

不要小瞧了这两个阶段，它们实际上是一组用于构建智能搜索解决方案的工具集，下面我们将详细描述下里面主要的工具 / 方法。

## Chunking & Vectorization

将文本划分为多个 chunks 至关重要，因此 Transformer 模型具有最大输入长度，实现 chunking 的手段有很多，除了按固定文本长度切片外，还有一些高级的方法：

1. **按句子分割**：使用 [NLTK](https://www.nltk.org/) 或者 [spaCy](https://spacy.io/) 库提供的句子分割功能，主流开发框架如 LangChain、LlamaIndex 都有集成
2. **递归分割**：通过重复地应用 chunking 规则递归地分解文本，比如在 LangChain 中会先通过段落换行符（`\n\n`）进行分割，然后检查这些 chunk 的大小，如果大小不超过一定阈值，则保留；如超过阈值，使用单个换行符（`\n`）再次分割，以此类推，不断根据 chunk 大小应用更小的 chunking 规则（如空格、句号等）。这种方法提供了一种统一的、灵活地方式调整 chunk 的大小，对于文本中信息密集的段落，需要更细的分割来捕捉细节
3. **按语义分割**：计算向量化后的文本的相似度，并在相似度降低到某个阈值后进行分割，保持高度的语义相似性
4. **利用特殊结构分割**：针对特定结构化内容（Markdown、LaTex、JSON 之类的）的分割器，这些分割器经过特别设计来处理这些类型的文档，以确保正确地保留其结构

简而言之，Chunking 是为了有效地对文本进行分割，并确保每个部分都保留其语义完整性、避免提供无关的信息，Chunking 的质量直接影响了检索的质量。

拿到 chunks 之后就是向量化，用 “动态” 的 Embedding Model 替换掉 “静态”。

以 “我买了一张光盘” 为例，这里 “光盘” 指的是具体的圆形盘片，而在 “光盘行动” 中，“光盘” 则指的是把餐盘里的食物吃光，是一种倡导节约的行为。语义完全不一样，但使用 ”静态“ Embedding Model 其向量是固定的，就像一个 look-up 操作；相比之下，以 [BERT](https://arxiv.org/abs/1810.04805) 模型为代表的引入 Self-Attention 机制的模型，能够提供 ”动态“ 的词义理解，这意味着它可以根据上下文动态地调整词义，使得同一个词在不同语境下有不同的向量表示

对于最新、最有效的模型，可以参考 MTEB 排行榜，该排行榜定期更新性能最高的 Embedding 模型。

## Hierarchical Indices

![](/assets/img/rag-7.png)

相比扁平的、用一个向量数据库存储所有的 chunks 向量，Hierarchical Indices 通过建立多层索引以显著提高搜索效率：

1. 先将文档分割为多个 chunks，上图中，每个 chunk 的 size 是 512
2. 继续将 “parent” chunk 分割为更小的 chunk，上图中，每个 child chunk 的 size 是 128
3. 当检索时，先基于向量检索相似度最高的叶子（最小的）chunk
4. 当一个 “parent” 的大多数 children 都被选为相似度最高时，返回 “parent”，反之则返回 child chunk

最终将这些 chunk 合并为 context，提供给 LLM。

## HyDE (Hypothetical Document Embeddings)

![](/assets/img/rag-8.png)

用 LLM 生成一个 “假设” 答案，将其和问题一起进行检索。

HyDE 的核心思想是接收用户提问后，先让 LLM 在没有外部知识库的情况下生成一个假设性的回复，然后将这个假设性回复和原始 query 一起用于向量检索，虽然假设回复可能包含虚假信息，但也蕴含着 LLM 认为有相关性的信息，也有助于在知识库中寻找文档。

## Multi-Query

![](/assets/img/rag-9.png)

Multi-Query 技术涉及获取用户查询并使用 LLM 生成 “N” 个类似查询，然后将这些查询中的每一个（包括原始查询）都向量化并接受检索，从而产生更多的chunks。由于检索到的信息量增加，可以使用 RRF 或者 ReRank 模型，合并来自不同问题的检索结果。

比如对这个问题 “哪些最重要的因素促成了今年收入的增长？”，基于原始问题，提示 LLM 从不同角度产生多个新问题或者子问题：

- 公司今年的主要收入来源是什么？

- 市场条件的变化如何影响公司的收入增长？

- 是否有任何新产品发布或收购推动了收入增长？

- 实施了哪些定价策略来增加收入？

- 客户需求的变化如何影响创收？

然后对每一个新问题（加上原始问题）进行检索。

## Step-back Prompting

让 LLM 生成一个更抽象的问题，然后将这个问题和原始问题一起检索，以提高召回率。

此方法在面对复杂问题时，比如 “Estella Leopold 在1954 年 8 月至 11 月期间上了哪所学校？”，由于涉及到很多和时间有关的限制条件，很难检索，但如果 “后退” 一步，问 “Estella Leopold 的教育经历怎么样的？”，则有助于系统的检索。

Step-back Prompting 也是属于 Query Rewriting 的一种实现方式。

Query Rewriting 的理论：为了回答用户的问题，我们的 RAG 系统将根据 query 检索适当的内容。它将在向量数据库中找到与用户询问的内容相似的 chunks，其他知识库（搜索引擎等）也适用。但问题是，答案所在的 chunks 可能与用户询问的内容毫不相似。用户可能没有提出一个好问题，或者表达方式与我们的期望不同：

1. 我的 ECS 无法远程连接了 --- *可能是 22 端口没开放*
2. 我的电脑连不上 WiFi -- *可能是代理设置不正确*
3. ...

显然，RAG 在这种情况下找不到回答问题所需的信息，它就无法正确回答。

简而言之，Query Rewriting 意味着我们将用我们自己的话改写用户查询，这样我们的 RAG 就最了解如何回答，它的流程从 「检索 -> 阅读」变成了「重写 -> 检索 -> 阅读」。

## Chat Engine

![](/assets/img/rag-10.png)

Chat Engine 可以让 RAG 结合用户的会话历史优化 query，比如：

```
Q：最新的苹果手机是哪一代？
A：iPhone15
Q：多少钱
```

如果只检索 “多少钱“，根本不可能得到正确的问题，但如果改写为 “iPhone15多少钱” 就能正确处理了。

## Query Routing

如果我们提供了多种数据源（比如 Web 在线检索、私有知识库问答），那么让 LLM 判断用户意图，以此确定最有效的后续操作极为重要，这可能包括总结信息、搜索特定数据、执行特定任务等，不同的数据源或索引往往意味着是不同的任务。

比如 “你好”、“今天天气怎么样” 就是完全不一样的任务。

在实现上，有两种方式 Routing：

1. 通过字符串检查
2. 通过向量检查

假如我们有三个编程语言的知识库：python_docs、js_docs、golang_docs，要根据用户的 query 决定使用哪一个。

字符串检查很简单，类似一条普通的条件判断 "if 'langchain' in query.lower()"：

```python
def choose_route(result):
    if "python_docs" in result.lower():
        ### Logic here 
        return "chain for python_docs"
    elif "js_docs" in result.datasource.lower():
        ### Logic here 
        return "chain for js_docs"
    else:
        ### Logic here 
        return "chain for golang_docs"
```

result 可以来自 query，也可以来自 LLM 的输出，让 LLM 判断用户的 query 和哪个编程语言最相关。

向量检查则是借助 Embedding Model 完成条件判断：

```python
# Setting up the various prompts for different topics
physics_template = """You are a very smart physics professor. \
You are great at answering questions about physics in a concise and easy to understand manner. \
When you don't know the answer to a question you admit that you don't know.

Here is a question:
{query}"""

math_template = """You are a very good mathematician. You are great at answering math questions. \
You are so good because you are able to break down hard problems into their component parts, \
answer the component parts, and then put them together to answer the broader question.

Here is a question:
{query}"""

# Embedding the different prompt templates which can later be compared with the
# user query embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
prompt_templates = [physics_template, math_template]
prompt_embeddings = embeddings.embed_documents(prompt_templates)

# Route question to prompt 
def prompt_router(input):
    # Embed the question
    query_embedding = embeddings.embed_query(input)
    # Compute similarity between the query and the prompts
    similarity = cosine_similarity([query_embedding], prompt_embeddings)[0]
    # fetch the prompt with the maximum score as the relavant prompt
    most_similar = prompt_templates[similarity.argmax()]
    # Chosen prompt 
    print("Using MATH" if most_similar == math_template else "Using PHYSICS")
    # setup the prompt_template object
    template = PromptTemplate.from_template(most_similar)
    # return the refined prompt
    return template.invoke({'query':input})
```

当然也可以通过 LangChain、 LlamaIndex 框架让实现更简单：

```python
from typing import List

class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""

    datasources: List[Literal["python_docs", "js_docs", "golang_docs"]] = Field(
        ...,
        description="Given a user question choose which datasources would be most relevant for answering their question",
    )

llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0)
structured_llm = llm.with_structured_output(RouteQuery)
router = prompt | structured_llm
router.invoke(
    {
        "question": "is there feature parity between the Python and JS implementations of OpenAI chat models"
    }
)

# Output:
# RouteQuery(datasources=['python_docs', 'js_docs'])
```

Query Routing 通过选择最合适的索引进行数据检索，从而提升检索质量和响应速度。

# 最后

这两年 RAG 技术发展迅速，为自然语言处理领域带来了诸多创新和突破。通过将检索模块与生成模块相结合，RAG 在提高文本生成的准确性、一致性和多样性方面表现出色。无论是 Naive RAG、Advanced RAG，还有我们后续会继续聊的 Modular RAG、Self-RAG，各种变体和改进版本不断涌现，满足了不同应用场景的需求。

这项技术不仅显著提升了问答系统、对话系统和内容创作等任务的性能，还在专业领域如医疗、法律等展现出巨大的潜力，其高效的信息整合能力使得模型能够提供更加全面和详细的答案，同时减少了幻觉问题，提高了用户信任度。

随着技术的不断演进，未来我们可以预见 RAG 将在更多复杂、多样化的应用中发挥关键作用，为各行各业带来更多创新解决方案。
