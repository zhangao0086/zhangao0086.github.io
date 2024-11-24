---
layout: post
title: "什么是 CUDA Graphs"
date: 2024-11-24 21:49:28 +0800
categories: [分享]
article_type: 1
typora-root-url: ../../github.io
---

![](/assets/img/cuda_graphs_caption.jpg)

> 用 CUDA Graphs 加速 PyTorch 模型~

CUDA Graphs 是 NVIDIA CUDA 10 引入的一项高级特性，它能够将一系列 CUDA 内核定义并封装为一个单一的操作图，而不是逐个启动操作。这种机制通过一个 CPU 操作启动多个 GPU 操作，从而**减少 GPU 任务的启动开销**。

在传统的 GPU 编程中，每当需要让 GPU 执行任务时，CPU 都必须发送指令，并等待 GPU 完成任务后再发送下一条指令。这种 “逐个发送” 的方式效率较低，因为每个 GPU 操作（例如内核调用或内存复制）所花费的时间以微秒为单位，而提交每个操作给 GPU 也会产生微秒级的开销。因此 CPU 和 GPU 之间频繁的通信导致了时间浪费，这在实际应用中变得越来越显著。

CUDA Graphs 的核心优势在于能有效减少这种通信开销。

在启动 GPU 任务时，CPU 需要进行一系列的设置和初始化操作。而 CUDA Graphs 通过将多个任务组合成一个图结构，一次性提交给 GPU，使其能够自行安排任务的执行顺序，而不需每次都等待 CPU 的指令，从而大幅提高效率：

1. **减少 CPU 和 GPU 的通信开销**：传统 CUDA 编程模型需要 CPU 逐个提交 GPU 任务，而 CUDA Graphs 允许将多个任务组成一个图结构并一次性提交；CUDA Graphs 减少了通信开销，提高了执行效率
2. **提高并行性**：传统模型需要开发者手动管理任务的依赖关系和执行顺序；而 CUDA Graphs 通过图结构清晰地表达了计算逻辑，减少了潜在的错误和性能瓶颈，GPU 可以并行处理多个没有依赖关系的任务，进一步提高效率
3. **优化长时间运行的任务**：对于需要重复执行的任务，CUDA Graphs 可以将其录制为图并反复运行，避免每次都重新提交的开销

典型的应用场景有三个：

- **深度学习训练**：在深度学习训练任务中，CUDA Graphs 可以将多个计算和数据传输任务组织成一个图结构并一次性提交给 GPU 执行，显著减少了 CPU 和 GPU 之间的通信开销，提高训练速度并降低功耗
- **大规模分布式计算**：在大规模分布式计算场景中，CUDA Graphs 有助于优化任务调度和执行顺序，提高计算资源的利用率和整体性能
- **实时渲染等高性能计算场景**：在实时渲染等高性能计算场景中，CUDA Graphs 通过优化任务并行性和减少启动开销来提高渲染速度和图像质量

使用 CUDA Graphs 并不复杂，它主要由 C++ 的 API 组成：

1. **创建图**：使用 `cudaGraphCreate` 函数创建一个空的图对象
2. **添加节点和依赖关系**：使用 `cudaGraphAddKernelNode` 等函数向图中添加节点（如核函数调用、内存拷贝等），并使用 `cudaGraphAddDependencies` 函数设置节点之间的依赖关系
3. **实例化图**：使用 `cudaGraphInstantiate` 函数创建图的可执行实例
4. **执行图**：使用 `cudaGraphLaunch` 等函数将图提交给 GPU 执行

PyTorch 也提供了 `torch.cuda.CUDAGraph` 类和两个封装好的接口 `torch.cuda.graph`、`torch.cuda.make_graphed_callables` 来简化用户使用：

```python
import torch

# 准备模型和数据
model = Model().cuda()
static_input = torch.randn(16, 3, 224, 224, device='cuda')
static_output = torch.zeros(16, 1000, device='cuda')

# 预热
s = torch.cuda.Stream()
s.wait_stream(torch.cuda.current_stream())
with torch.cuda.stream(s):
    for _ in range(3):
        static_output = model(static_input)
torch.cuda.current_stream().wait_stream(s)

# 创建 CUDA graph
g = torch.cuda.CUDAGraph()
with torch.cuda.graph(g):
    static_output = model(static_input)

# 重放 graph
g.replay()
```

除了 CUDA Graph 捕获，PyTorch 还支持使用[流捕获](https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#creating-a-graph-using-stream-capture)构建 CUDA Graph：

```python
import torch

# 定义一个简单的模型
class SimpleModel(torch.nn.Module):
    def __init__(self):
        super(SimpleModel, self).__init__()
        self.fc = torch.nn.Linear(3 * 224 * 224, 1000)

    def forward(self, x):
        x = x.view(x.size(0), -1)
        return self.fc(x)

# 初始化模型和数据
model = SimpleModel().cuda()
input_tensor = torch.randn(16, 3, 224, 224, device='cuda')

# 创建 CUDA 流
stream = torch.cuda.Stream()

# 捕获操作到 CUDA Graph
g = torch.cuda.CUDAGraph()
with torch.cuda.stream(stream):
    with torch.cuda.graph(g):
        output_tensor = model(input_tensor)

# 在主流中重放图形
torch.cuda.synchronize(stream)
g.replay()
```

在捕获模式下，操作不会在 GPU 上实际运行，而是被记录在图中。捕获完成后，图可以多次启动以执行 GPU 工作，每次重放都会使用相同的内核和参数。

但是要注意，由于 **CUDA Graphs 不支持动态控制流**（如条件语句和循环），因此在设计算法时应尽量避免使用这些结构，如果必须使用动态控制流，可以考虑使用 PyTorch 提供的 `torch.cuda.make_graphed_callables` 接口来自动处理不支持放入 Graph 里的操作；其次，**确保输入张量的形状在图创建时是固定的**，因为 CUDA Graphs 的设计是基于静态形状的张量结构，创建 Graph 时，所有操作及其输入输出的形状必须在图创建时确定，而像 Ragged Tensors 这种允许不同的输入具有不同形状的动态结构，是不被直接支持的。
