---
layout: post
title: "TorchScript 初窥"
date: 2024-09-22 23:38:32 +0800
categories: [分享]
article_type: 1
typora-root-url: ../../github.io
---

![](/assets/img/torchscript-first-look-caption.png)

> 在长汀遛娃拍的反差照，一个好吃又好玩的县城，消费也不高~

`TorchScript` 是一种从 `PyTorch` 代码创建可序列化和可优化模型的解决方法，任何 `TorchScript` 程序都可以从 `Python` 进程中保存导出，并在非 `Python` 环境中加载。

`PyTorch` 官方提供了工具能将模型从纯 `Python` 程序转换为可以独立于 `Python` 运行的 `TorchScript` 程序，例如在独立的 `C++` 程序中运行，这使得在训练侧，可以用机器学习领域熟悉的 `Python` 工具在 `PyTorch` 中训练模型，然后通过 `TorchScript` 将模型导出到生产环境中，避免在生产环境中，`Python` 程序因其性能和多线程等原因而降低了性能。

所以相比传统的 `pth` 文件，`TorchScript` 有如下优势：

1. **独立性**：`TorchScript` 模型是自包含的，包括模型架构和权重，因此它可以在没有 `Python` 的环境中运行
2. **跨平台**：可以在不同平台上运行，包括移动设备（iOS 和 Android）和嵌入式系统
3. **推理优化**：`TorchScript` 可以通过 JIT 编译器进行优化，能提高模型的执行速度
4. **部署方便**：由于其独立性、无依赖和优化特性，`TorchScript` 更适合用于生产环境中的部署
5. **支持 C++ 前端**：虽然 `TorchScript` 能在多平台上运行，但对 C++ 的直接支持（一等公民）能为那些需要高效、低延迟执行的特定场景提供额外的优势

在 `C++` 中加载 `TorchScript` 模型：

```c++
#include <torch/script.h> // One-stop header.

#include <iostream>
#include <memory>

int main(int argc, const char* argv[]) {
  if (argc != 2) {
    std::cerr << "usage: example-app <path-to-exported-script-module>\n";
    return -1;
  }


  torch::jit::script::Module module;
  try {
    // Deserialize the ScriptModule from a file using torch::jit::load().
    module = torch::jit::load(argv[1]);
  }
  catch (const c10::Error& e) {
    std::cerr << "error loading the model\n";
    return -1;
  }

  std::cout << "ok\n";
}
```

执行推理：

```c++
// Create a vector of inputs.
std::vector<torch::jit::IValue> inputs;
inputs.push_back(torch::ones({1, 3, 224, 224}));

// Execute the model and turn its output into a tensor.
at::Tensor output = module.forward(inputs).toTensor();
std::cout << output.slice(/*dim=*/1, /*start=*/0, /*end=*/5) << '\n';
```

PhotoRoom 在今年的 GTC 大会上分享其对模型优化方法时（ [Scaling Generative AI Features to Millions of Users Thanks to Inference Pipeline Optimizations](https://resources.nvidia.com/en-us-ai-inference-content/gtc24-s62726) ），也用到了 `TorchScript`：

![](/assets/img/torchscript-first-look-1.png)

不过，将模型编译为 `TorchScript` 时，虽然有工具链的支持，但仍然会遇到如下挑战： 

1. **动态特性限制**：`Python` 的动态特性（如动态类型、反射等），在 `TorchScript` 中不被支持，需要重构代码以适应静态类型
2. **不支持的操作**：某些 `Python` 操作或库函数可能不被 `TorchScript` 支持，需要找到替代方法
3. **控制流**：复杂的控制流结构（如条件判断和循环）可能需要调整，以确保 `TorchScript` 能正确解析
4. **调试困难**：错误信息不够直观，调试 `TorchScript` 代码可能比纯 `Python` 更具挑战性
5. **第三方库兼容性**：使用第三方库的自定义操作可能无法直接转换，需要实现自定义的 `TorchScript` 操作
6. **模型依赖**：如果模型依赖于外部状态或全局变量，这些依赖需要在转换前进行处理。 这些挑战要求开发者在转换过程中仔细审视代码，并做出必要的修改以确保模型正确编译和运行

这是我尝试将一个小模型转换成 `TorchScript` 时遇到的问题：

> List Comprehensions With Ifs not Supported

相对来说简单，`List Comprehensions` 本身也是语法糖而已，大不了改写掉。

> SetComp aren't supported

同上，但能感觉，这些常见的 `Python` 操作都不支持的话，对日常编码的要求是有点高的。

> jit 不支持 set 类型

用 `dict` 替换 `set`，value 就固定写 `True` 吧，也没啥好办法，这是它支持的类型列表：[supported-type](https://pytorch.org/docs/stable/jit_language_reference.html#supported-type)，是个相当小的子集。

> forward 函数的实现，避免使用非 tensor 类型
>
> Module 'xxx' has no attribute 'xx' (This attribute exists on the Python module, but we failed to convert Python type: 'list' to a TorchScript type. Could not infer type of list element: Only tensors and (possibly nested) tuples of tensors, lists, or dictsare supported as inputs or outputs of traced functions, but instead got value of type xxxx.. Its type was inferred; try adding a type annotation for the attribute.):

`TorchScript` 对 `forward` 函数实现的要求极高，最终我是把其中部分实现移出去，比如一次性的计算能放在 `__init__` 的就放在 `__init__` 里，才解决的，具体的解法得 case by case，要注意的是 `TorchScript` 错误信息非常不明显，你得用一些更 **hacky** 的调试手段。

> OSError: could not get source code

跟上面差不多，一般和某个特定类型有关，在我的例子里是 `EmbeddingConfig`，最终我在 `forward` 里移除了对它的依赖。

> Expected integer literal for index but got a variable or non-integer. ModuleList/Sequential indexing is only supported with integer literals. For example, 'i = 4; self.layers' will fail because i is not a literal. Enumeration is supported, e.g. 'for index, v in enumerate(self): out = v(inp)':

只能用字面量做索引，不支持动态数组，开解循环可以解决，但不是一个好的解决方案。

> Unable to extract string literal index. ModuleDict indexing is only supported with string literals. For example, 'i = "a"; self.layers' will fail because i is not a literal. Enumeration of ModuleDict is supported, e.g. 'for k, v in self.items(): out = v(inp)':

动态字典也不行，但加上类型注解后基本上就行了，由于我的 `ModuleDict` 中的 value 是一个自定义的 `nn.Module`，得显式的调用它的 `forward`，通过 `__call__` 间接调用会被识别为创建实例。

> Unsupported value kind: Tensor

和上面差不多，难在找到真正出错的代码块。

> '__torch__.beacon_torch.modules.attention.AttentionSequencePoolingLayer (of Python compilation unit at: 0x592c370)' object has no attribute or method '__call__'. Did you forget to initialize an attribute in __init__()?

和上上差不多，显式调用 `forward` 可解决。

最后的感受：**开发者要在转换过程中仔细审视代码，并做出必要的修改以确保模型正确编译和运行**。

以上就是对 `TorchScript` 的第一印象，接下来会尝试模型的服务化（Triton & TorchServe），然后继续感受感受 AI 领域的工具，期待在这个过程中获得新的见解和成长。
