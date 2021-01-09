---
layout: post
redirect_from: /2020/07/10/swift_memory_management/
title: "Swift 内存管理"
date: 2020-07-10 21:12:05 +0800
categories: [iOS, Swift]
article_type: 1
excerpt_separator: <!--more-->
---

从编译器的视角看 Swift 的内存管理

<!--more-->

# 思维导图：

![](https://github.com/zhangao0086/mind/blob/master/Swift%20%E5%86%85%E5%AD%98%E7%AE%A1%E7%90%86/Swift%20%E5%86%85%E5%AD%98%E7%AE%A1%E7%90%86.png?raw=true)
*[xmind](https://github.com/zhangao0086/mind/blob/master/Swift%20%E5%86%85%E5%AD%98%E7%AE%A1%E7%90%86/Swift%20%E5%86%85%E5%AD%98%E7%AE%A1%E7%90%86.xmind)*

# 文字资料

## Swift 4-

### ARC

- 原理

  - 在 SIL 阶段插入 swift_retain()、 swift_release() 完成内存管理
  - weak 引用会转换成 swift_weakAssign()
  - unowned 引用会转换成 unowned_retain()、unowned_release()
  - 纯 Swift 对象不支持 autorelease
  - 主要指令

    - unowned_retain

      - 增加 HeapObject 的 unowned 计数

    - strong_retain_unowned

      - 断言对象的 strong 计数是否是正数（对象是否还活着），然后将计数 +1

    - strong_retain

      - 增加对象的 strong 计数

    - load_weak

      - 增加 Optional 引用对象的 strong 计数

    - strong_release

      - 减少对象的 strong 计数，如果为0则销毁对象；当 strong 和 unowned 同时为0时则释放对象内存

    - unowned_release

      - 减少对象的 unowned 计数；当 strong 和 unowned 同时为0时则释放对象内存

- 管理策略

  - Strong

    - 对应 strong counter
    - 保持对象存活
    - 有一个额外的计数：物理值为0时逻辑值表示1

  - Weak

    - 对应 weak counter
    - 无主引用，zeroing
    - 当对象不存在时，返回 nil

  - Unowned

    - 对应 unowned counter
    - 无主引用，non-zeroing
    - 当对象不存在时，触发一个断言
    - 当 strong 为0，而 unowned 大于0时对象不会被完全释放（对象及其父类的 deinit 会被调用，然而对象头信息还在，通过头信息可以取到计数，验证以及完成后续的释放流程）

### 对象内存布局

- 引用计数采用内联方式布局，访问更快

## Swift 4+

### 旧版本的缺点

- strong 为 0 而 weak 不为 0 时无法释放对象，作为僵尸对象可能会存活很长时间

### 修改了内存布局

- 独立于对象之外内存区域存放对象相关的信息

### 引入了 Side Table

- Side Table 和 Object 有一个指针指向彼此
- 出于节约内存的目的，只在需要时才创建

  - 当对象被 weak 引用时
  - 当 strong 或 unowned counter 值溢出时

- 支持后续可以拓展出其他的玩法

### Weak 指向 Side Table，而不是真正的对象

- 由于不直接指向对象，允许保留 Weak 访问的同时提前销毁对象

## Swift 对象生命周期

### 对象不立即销毁，而是经过 live -> deiniting -> deinited -> freed -> dead 这五个阶段

### 当 strong 为0时

- 对象进入 deinited 状态；Unowned 访问触发断言；Weak 访问返回 nil

## 参考资料

- [Discover Side Tables - Weak Reference Management Concept in Swift](https://maximeremenko.com/swift-arc-weak-references)
- [Advanced iOS Memory Management with Swift: ARC, Strong, Weak and Unowned Explained](https://www.vadimbulavin.com/swift-memory-management-arc-strong-weak-and-unowned/)
- [Does ARC hold a count for unowned reference](https://stackoverflow.com/questions/54836745/does-arc-hold-a-count-for-unowned-reference)
- [Unowned or Weak? Lifetime and Performance](https://www.uraimo.com/2016/10/27/unowned-or-weak-lifetime-and-performance/)

