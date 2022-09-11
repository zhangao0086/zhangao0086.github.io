---
layout: post
title: "为什么苹果在 Xcode 14 中废弃了 Bitcode"
date: 2022-09-11 02:28:55 +0800
categories: [分享]
article_type: 1
typora-root-url: ../../github.io
---

苹果在 Xcode 14 里正式废弃了 Bitcode，从大肆推广到如今落幕，这些年的变化还是挺大的。我们从 Bitcode 的介绍开始说起，尝试探索苹果背后的想法。

# 什么是 Bitcode

Bitcode 是 LLVM bytecode 文件格式，它其实隐含了两个东西：

- 用于承载 bitstream 的容器
- LLVM IR

更通常的说法，是将 Bitcode 称为 LLVM 的中间语言，当你用 LLVM 工具链编译源代码时，源代码被翻译为中间语言（Bitcode），然后基于中间语言进行分析、优化后，最终翻译为可在目标 CPU 上执行的指令。

> [LLVM Bitcode File Format](https://llvm.org/docs/BitCodeFormat.html)

# Bitcode 的优势是什么

这样做的好处是所有基于 LLVM 的前端（比如 clang），都只需要完成源代码到 Bitcode 即可，之后的过程都被统一掉了，LLVM 工具链不关心生成的 Bitcode 是来自于 C、C++、Objective-C、Rust 或任何其他语言，一旦有了 Bitcode，其余的工作流程总是一样的：

![](/assets/img/bitcode-1.png)

基于这个流程，Bitcode 可以做到：

- 不用重新编译源代码，可以直接基于已有的 Bitcode 生成目标 CPU 的指令
- 按需生成或懒生成
- 保留开发者的原始意图

这意味着只要保存一份 Bitcode，就能随时用它生成任何已有架构和未来新架构的可执行文件，就像一开始以这些架构为目标编写代码一样。如果没有 Bitcode，要么重新基于源代码编译，要么通过技术手段对可执行文件进行翻译，而后者会丢掉开发者写代码时的原始意图，这导致翻译后的代码很糟糕。

# 苹果想通过 Bitcode 实现什么

苹果如果持有了应用程序的 Bitcode，那么就能：

- 根据用户的设备不同，提供特定的版本，既减少了下载量，又能提高特定优化版本的性能
- 不发版的情况下，实现编译优化

比如 RISC-V 架构，相比 Intel 超过 1500 个指令来说，RISC-V 只有 40-50 个指令，绝对算得上 small and simple，那借助 Bitcode 的能力，就算应用程序的开发者从未听说过 RISC-V，也能实现对 RISC-V 的原生支持，因为所有带 Bitcode 的应用都可以在苹果后台编译为 RISC-V：

![](/assets/img/bitcode-2.jpg)

# 苹果忽视了什么

首先 Bitcode 并不是一个稳定的格式，因为在 LLVM 的设计里，它只是一个临时产生的文件，并不期望被长期存储，这导致它的兼容性很差，几乎 LLVM 每次版本更新时都会修改它；其次是对生态的要求很高，如果应用的任何一个依赖没有支持 Bitcode，那最终就无法使用：

![](/assets/img/bitcode-3.png)

要么整体关闭 Bitcode，要么找到对应的 Bitcode 版本，如果库中包含了 i386、x86_64 架构，还需要通过 `lipo` 指令移除，就像这样：

```bash
lipo -remove i386 -o /path/to/macho
lipo -remove x86_64 -o /path/to/macho
```

除了外部因素，苹果自身的架构统一进程也比想象中要快。Apple Watch Series 3 是最后一个不支持 64 位的设备，从 watchOS 9 开始也不再支持该设备，意味着 armv7/armv7s/i386 彻底退出了历史舞台，Bitcode 是要解决不同目标 CPU 的问题，现在敌人不存在了，还怎么打？所有的设备都是 arm64 了。

Xcode 14 开始，不仅废弃了 Bitcode，也不再支持构建 armv7、armv7s 以及 i386 架构的项目，不再支持构建部署目标早于 macOS 10.13、iOS 11、tvOS 11 以及 watchOS 4 的应用程序，前一个版本的 Xcode 可是最低支持到 iOS 9，苹果这一次显然要玩个大的。

# 废弃 Bitcode 会带来什么影响

几乎没什么影响，因为开发者目前提交到 iTunes Connect 上的仍然是 Fat-MachO，开发者不能直观感受到优化，而经由 App Store 下发时，确实是能减少用户的下载量，不过这要归结为 App Thinning 和 App Slicing 的功劳。简单说，它可以将应用制作成不同的变体，比如按架构维度拆分为 32 位、 64 位，资源维度将图片资源拆分为 2x、3x 等，不同的维度相互组合就成了一个简化版的 App：

![](/assets/img/bitcode-5.png)

以 iPhone 5C 为例，它是 32 位的机型，且不支持 Metal API，那它就只下载自己能用得上的代码和文件即可，不仅加快了下载效率，还节约了存储空间。

我们通过 iTunes Connect 后台的报告页面可以查看各个变体的下载大小和安装大小：

![](/assets/img/bitcode-4.png)

> [Reducing Your App’s Size](https://developer.apple.com/documentation/xcode/reducing-your-app-s-size)

也就是说没有 Bitcode，苹果也能通过剪枝为用户提供特定架构类型的代码。

其次 Rosetta 2 的发布，也侧面说明了 “不用编译，直接基于 Bitcode 将 Intel 切换成 M1” 的可行性还有待商榷，相对来说，由开发者提供 Fat-MachO，然后由 App Thinning 来做剪枝的方案既有效、又简单。

# 总结

最后总结一下废弃的原因：

- 生态支持度不高，大部分应用选择关闭了该功能
- 架构统一了，提出问题的人（armv7 等）被解决了
- Fat-MachO + App Thinning 经过验证，被证明简单好用

从苹果强推 Bitcode 到如今正式宣布废弃，大概经过了 7 年，或许 LLVM Bitcode 本身并不是一个好的可分发格式，它还是做好编译期间的工作就好。

> ps: 社区已经在推动 Bitcode 的移除工作了，比如 Flutter: [[iOS] Remove bitcode support](https://github.com/flutter/flutter/issues/105501)。
