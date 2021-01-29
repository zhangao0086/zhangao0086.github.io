---
layout: post
redirect_from: /2020/08/27/swift_weak/
title: "Swift: weak 的 strong 时机"
date: 2020-08-27 20:24:10 +0800
categories: [Swift]
article_type: 1
typora-root-url: ../../github.io
---

# 前言

早前在[Swift 内存管理]({% post_url 2020-07-10-swift_memory_management%})中整理过一张思维导图，当时主要是通过官方资料和前人的经验得出的结论，不过内心里有2个疑问一直没有得到答案：

- Swift 的 weak 变量会在使用前尝试 +1 strong，但是具体的时机是什么时候呢？

- Objective-C 中的 Weak-Strong Dance 在 Swift 中是否还需要?

今天就通过 `SIL` 探寻其中的答案。


# 探索

先写一个简单的 Swift 测试代码：

```swift
/// test.swift

class aClass{
    var value = 1
    func log() {
        print(self.value)
    }
}

var c2 = aClass()
var fSpec = { [weak c2] in
    c2?.log()
    c2?.log()
}
fSpec()
```

我们主要通过闭包内的两条 `log` 语句寻找其中的答案。

用以下命令将 Swift 源码转成 SIL：

```shell
swiftc -emit-sil test.swift >> ./sil.swift
```

生成的 SIL 很长，但是没有关系，因为 SIL 很好理解，它和我们印象中的程序执行流程完全一样，比如我们的程序往往会有一个 `main` 方法，SIL 也不例外，你可以通过 `@main` 快速找到它：

```swift
// main
sil @main : $@convention(c) (Int32, UnsafeMutablePointer<Optional<UnsafeMutablePointer<Int8>>>) -> Int32 {
bb0(%0 : $Int32, %1 : $UnsafeMutablePointer<Optional<UnsafeMutablePointer<Int8>>>):
  alloc_global @$s4test2c2AA6aClassCvp            // id: %2
  %3 = global_addr @$s4test2c2AA6aClassCvp : $*aClass // users: %7, %12
  %4 = metatype $@thick aClass.Type               // user: %6
  // function_ref aClass.__allocating_init()
  %5 = function_ref @$s4test6aClassCACycfC : $@convention(method) (@thick aClass.Type) -> @owned aClass // user: %6
  %6 = apply %5(%4) : $@convention(method) (@thick aClass.Type) -> @owned aClass // user: %7
  store %6 to %3 : $*aClass                       // id: %7
  alloc_global @$s4test5fSpecyycvp                // id: %8
  %9 = global_addr @$s4test5fSpecyycvp : $*@callee_guaranteed () -> () // users: %22, %24
  %10 = alloc_box ${ var @sil_weak Optional<aClass> }, var, name "c2" // users: %23, %21, %20, %11
  %11 = project_box %10 : ${ var @sil_weak Optional<aClass> }, 0 // user: %17
  %12 = begin_access [read] [dynamic] %3 : $*aClass // users: %13, %15
  %13 = load %12 : $*aClass                       // users: %16, %14
  strong_retain %13 : $aClass                     // id: %14
  end_access %12 : $*aClass                       // id: %15
  %16 = enum $Optional<aClass>, #Optional.some!enumelt.1, %13 : $aClass // users: %18, %17
  store_weak %16 to [initialization] %11 : $*@sil_weak Optional<aClass> // id: %17
  release_value %16 : $Optional<aClass>           // id: %18
  // function_ref closure #1 in 
  %19 = function_ref @$s4testyycfU_ : $@convention(thin) (@guaranteed { var @sil_weak Optional<aClass> }) -> () // user: %21
  strong_retain %10 : ${ var @sil_weak Optional<aClass> } // id: %20
  %21 = partial_apply [callee_guaranteed] %19(%10) : $@convention(thin) (@guaranteed { var @sil_weak Optional<aClass> }) -> () // user: %22
  store %21 to %9 : $*@callee_guaranteed () -> () // id: %22
  strong_release %10 : ${ var @sil_weak Optional<aClass> } // id: %23
  %24 = begin_access [read] [dynamic] %9 : $*@callee_guaranteed () -> () // users: %25, %27
  %25 = load %24 : $*@callee_guaranteed () -> ()  // users: %29, %28, %26
  strong_retain %25 : $@callee_guaranteed () -> () // id: %26
  end_access %24 : $*@callee_guaranteed () -> ()  // id: %27
  %28 = apply %25() : $@callee_guaranteed () -> ()
  strong_release %25 : $@callee_guaranteed () -> () // id: %29
  %30 = integer_literal $Builtin.Int32, 0         // user: %31
  %31 = struct $Int32 (%30 : $Builtin.Int32)      // user: %32
  return %31 : $Int32                             // id: %32
} // end sil function 'main'
```

在这个 `main` 方法里有一些我们熟悉和不熟悉的东西：

- `enum` - `Optional` 实际上就是枚举
- `function_ref` - 表示对 SIL 函数的引用

通过上下文和注释可以知道闭包调用就是执行了 `@$s4testyycfU_` 函数：

```swift
  // function_ref closure #1 in 
  %19 = function_ref @$s4testyycfU_ : $@convention(thin) (@guaranteed { var @sil_weak Optional<aClass> }) -> () // user: %21
```

再通过 `@$s4testyycfU_` 找到具体的 SIL 实现：

```swift
// closure #1 in 
sil private @$s4testyycfU_ : $@convention(thin) (@guaranteed { var @sil_weak Optional<aClass> }) -> () {
// %0                                             // user: %1
bb0(%0 : ${ var @sil_weak Optional<aClass> }):
  %1 = project_box %0 : ${ var @sil_weak Optional<aClass> }, 0 // users: %33, %30, %3, %2
  debug_value_addr %1 : $*@sil_weak Optional<aClass>, var, name "c2", argno 1 // id: %2
  %3 = begin_access [read] [dynamic] %1 : $*@sil_weak Optional<aClass> // users: %20, %13, %5
  %4 = alloc_stack $Optional<aClass>              // users: %6, %24, %19, %16, %12, %11, %9
  %5 = load_weak %3 : $*@sil_weak Optional<aClass> // user: %6
  store %5 to %4 : $*Optional<aClass>             // id: %6
  %7 = integer_literal $Builtin.Int1, -1          // user: %9
  %8 = integer_literal $Builtin.Int1, 0           // user: %9
  %9 = select_enum_addr %4 : $*Optional<aClass>, case #Optional.some!enumelt.1: %7, default %8 : $Builtin.Int1 // user: %10
  cond_br %9, bb2, bb1                            // id: %10
```

我们看到 `%9` 的位置通过 `select_enum_addr` 读取了枚举值：

> **select_enum_addr**
>
> Selects one of the "case" or "default" operands based on the case of the referenced enum value. This is the address-only counterpart to [select_enum](https://github.com/apple/swift/blob/master/docs/SIL.rst#select-enum).

这个指令是这里实际上读取了 `some`，然后执行 `cond_br`，它是带条件的 `br` 指令，意为当 `%9` 为1时执行**bb2**，为0时执行**bb1**：

> 注：SIL 会将方法分解成连续的 building blocks
>
> bb = building block

接下来看看**bb2**和**bb1**这两个 blocks 的实现：

```swift
bb1:                                              // Preds: bb0
  destroy_addr %4 : $*Optional<aClass>            // id: %11
  dealloc_stack %4 : $*Optional<aClass>           // id: %12
  end_access %3 : $*@sil_weak Optional<aClass>    // id: %13
  %14 = enum $Optional<()>, #Optional.none!enumelt // user: %15
  br bb3(%14 : $Optional<()>)                     // id: %15

bb2:                                              // Preds: bb0
  %16 = unchecked_take_enum_data_addr %4 : $*Optional<aClass>, #Optional.some!enumelt.1 // user: %17
  %17 = load %16 : $*aClass                       // users: %23, %21, %22, %18
  strong_retain %17 : $aClass                     // id: %18
  destroy_addr %4 : $*Optional<aClass>            // id: %19
  end_access %3 : $*@sil_weak Optional<aClass>    // id: %20
  %21 = class_method %17 : $aClass, #aClass.log!1 : (aClass) -> () -> (), $@convention(method) (@guaranteed aClass) -> () // user: %22
  %22 = apply %21(%17) : $@convention(method) (@guaranteed aClass) -> ()
  strong_release %17 : $aClass                    // id: %23
  dealloc_stack %4 : $*Optional<aClass>           // id: %24
  %25 = tuple ()                                  // user: %26
  %26 = enum $Optional<()>, #Optional.some!enumelt.1, %25 : $() // user: %27
  br bb3(%26 : $Optional<()>)                     // id: %27
```

可以看到无论是哪个执行，最终都会 `br bb3`，整个流程是线性的，而 **bb1** 和 **bb2** 的区别就是：

- bb1 直接做了清理工作就跳到了 **bb3**
- bb2 在通过 `some` 拿到值后，在访问前对引用计数+1，调用对象方法，然后清理前再对引用计数-1

后续 bb3 的执行过程和 bb0 很像，也是通过 `Optional` 的 `some` 值条件跳转 bb5 or bb4：

```swift
%39 = select_enum_addr %34 : $*Optional<aClass>, case #Optional.some!enumelt.1: %37, default %38 : $Builtin.Int1 // user: %40
  cond_br %39, bb5, bb4
```

bb4、bb5 略过，逻辑和 bb1、bb2 一样。

# 结论

通过这次简单的分析，可以发现对 weak 增加引用计数是在访问前，访问后就减少了，只对单条指令有效，但是不像 `Objective-C` 方法参数中的 `self` 是 `__unsafe_unretained`，Swift 是强引用过的，相对来说更安全。

Weak-Strong Dance 在 Swift 中同样有意义，考虑如下代码：

```swift
var fSpec = { [weak c2] in
    c2?.saveToMemory()
    c2?.saveToDB()
}
```

由于无法保证两条语句执行时 c2 都有相同的值，所以会有不一致的情况发生。而我们可能希望要么全都执行，全么全都不执行，所以用 Weak-Strong Dance 能符合我们的预期：

```swift
var fSpec = { [weak c2] in
    if let c2 = c2 {
        c2.saveToMemory()
        c2.saveToDB()
    }
}
```

此时产生的 SIL 为：

```swift
bb0(%0 : ${ var @sil_weak Optional<aClass> }):
  %1 = project_box %0 : ${ var @sil_weak Optional<aClass> }, 0 // users: %3, %2
  debug_value_addr %1 : $*@sil_weak Optional<aClass>, var, name "c2", argno 1 // id: %2
  %3 = begin_access [read] [dynamic] %1 : $*@sil_weak Optional<aClass> // users: %5, %4
  %4 = load_weak %3 : $*@sil_weak Optional<aClass> // user: %6
  end_access %3 : $*@sil_weak Optional<aClass>    // id: %5
  switch_enum %4 : $Optional<aClass>, case #Optional.some!enumelt.1: bb2, case #Optional.none!enumelt: bb1 // id: %6

bb1:                                              // Preds: bb0
  br bb3                                          // id: %7

// %8                                             // users: %14, %12, %13, %10, %11, %9
bb2(%8 : $aClass):                                // Preds: bb0
  debug_value %8 : $aClass, let, name "c2"        // id: %9
  %10 = class_method %8 : $aClass, #aClass.log!1 : (aClass) -> () -> (), $@convention(method) (@guaranteed aClass) -> () // user: %11
  %11 = apply %10(%8) : $@convention(method) (@guaranteed aClass) -> ()
  %12 = class_method %8 : $aClass, #aClass.log!1 : (aClass) -> () -> (), $@convention(method) (@guaranteed aClass) -> () // user: %13
  %13 = apply %12(%8) : $@convention(method) (@guaranteed aClass) -> ()
  strong_release %8 : $aClass                     // id: %14
  br bb3                                          // id: %15
```

不仅有了一致性，产生的指令也更少了。