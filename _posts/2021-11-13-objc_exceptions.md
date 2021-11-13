---
layout: post
title: "为什么 OC 不推荐使用 try-catch？"
date: 2021-11-13 09:15:14 +0800
categories: [分享]
article_type: 1
typora-root-url: ../../github.io
---

第一次认真注意到 try-catch 的实现细节还是在几年前，那会儿在 Stackoverflow 某一个问题上被大神 [Richard J. Ross III](https://stackoverflow.com/users/427309/richard-j-ross-iii) 教育了：Try catch is not a good solution, as ARC does not play nicely with it, unless you turn on that compiler flag, which bloats your binary size immensely.

根据 *ARC* 和*异常*关键字找到并认真阅读了 [Objective-C Automatic Reference Counting (ARC)](https://clang.llvm.org/docs/AutomaticReferenceCounting.html#objective-c-automatic-reference-counting-arc)，在 Exceptions 里有一段介绍：

> The standard Cocoa convention is that exceptions signal programmer error and are not intended to be recovered from. Making code exceptions-safe by default would impose severe runtime and code size penalties on code that typically does not actually care about exceptions safety. Therefore, ARC-generated code leaks by default on exceptions, which is just fine if the process is going to be immediately terminated anyway. Programs which do care about recovering from exceptions should enable the option.

里面提到了 try-catch 的两个副使用：

- 包体积变大
- ARC 对象会出现内存泄漏

再根据 [Exception Handling in LLVM](https://llvm.org/docs/ExceptionHandling.html) 可以知道 32 位 OS X、iOS 默认采用 SJLJ（Set Jump Long Jump）实现异常处理， 而 SJLJ 的副作用很明显，它是通过 setjmp 和 longjmp 来实现跨函数的无条件跳转，它会把每个异常处理函数注册到全局的帧列表，所以要插入很多代码来处理跳转期间各种对象的生命周期问题，导致生成代码的体积变得巨大，而且性能也有损耗。

在 arm64 下，SJLJ 被 Itanium-derived Zero Cost 实现替换了，不过要注意一点，所谓的零开销是指没有发生异常时，正常的逻辑性能没有丝毫降低，但在异常发生时，根据 [Itanium C++ ABI](https://itanium-cxx-abi.github.io/cxx-abi/abi-eh.html)，由于它是 stack unwind 机制，它采用了压缩的栈帧信息表，遇到异常的时候通过栈回溯的方式一层一层地处理每一层调用栈在异常处理时的相关逻辑，所以它也会有性能损失，一是查压缩表，二是逐层处理调用栈。当然这个损耗仅仅在发生异常的时候存在，无异常时没有任何损耗。

stack unwind 为什么能做到零开销？实际上还是以空间换时间，其增加了二进制代码段大小超过了 **50%**。

除了包体积变大还有内存泄漏的问题，ARC 从实现层面就没有考虑过从异常恢复的场景，这一点苹果也说的很清楚，Cocoa 的约定就是出了异常直接挂掉，压根不考虑从异常中恢复这件事。

再者就算使用 try-catch 也捕获不到 OC 的全部异常，比如在 OC 里，要读取的目录或文件不存在，这是 error 而不是 exception，OC 的错误类型多，不统一，这使其使用价值不高。

所以总结下来为什么不在 OC 里使用 try-catch：

- 使用价值不高
- 存在内存泄漏风险
- 包体积变大
