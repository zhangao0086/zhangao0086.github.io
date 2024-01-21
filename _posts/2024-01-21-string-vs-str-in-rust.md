---
layout: post
title: "String vs &str in Rust"
date: 2024-01-21 21:28:14 +0800
categories: [分享]
article_type: 1
typora-root-url: ../../github.io
---

![](/assets/img/string-vs-str-in-rust-caption.jpg)

刚上手 Rust 的字符串时一定遇到过这种情况，你看起来使用了字符串，并在函数间传递，但编译器无情地给了你一个错误，因为它觉得实际上不是字符串。

比如下面这个超级简单的例子，它接受一个类型为 `String` 的 `name`，并打印在控制台：

```rust
fn main() {
  let my_name = "xifan";
  greet(my_name);
}

fn greet(name: String) {
  println!("Hello, {}!", name);
}
```

编译、运行，你会看到这样的错误提示：

```
error[E0308]: mismatched types
  --> src/main.rs:3:11
   |
21 |     greet(my_name);
   |     ----- ^^^^^^^- help: try using a conversion method: `.to_string()`
   |     |     |
   |     |     expected `String`, found `&str`
   |     arguments to this function are incorrect
   |
note: function defined here
  --> src/main.rs:6:4
   |
14 | fn greet(name: String) {
   |    ^^^^^ ------------
```

好在 Rust 编译器体贴地告诉你如何解决这个问题，显然，这里有两个不同的类型：

- `String`
- `&str`

`greet` 方法期望接收一个 `String`，而我们给了一个 `&str`，把 `let my_name = "xifan";` 改成 `let my_name = "xifan".to_string();` 即可解决问题。

Rust 为什么要这么设计？`&str` 是什么？为什么我们需要通过 `to_string` 显式转换？

## 理解 String 类型

要回答这些问题，最好的方法是理解 Rust 如何在内存中存储字符串，从内存布局上看，`my_name` 是这样的：

```
                     buffer
                   /   capacity
                 /   /  length
               /   /   /
            +–––+–––+–––+
stack frame │ • │ 8 │ 5 │ <- my_name: String
            +–│–+–––+–––+
              │
            [–│–––––––– capacity –––––––––––]
              │
            +–V–+–––+–––+–––+–––+–––+–––+–––+
       heap │ x │ i │ f │ a │ n │   │   │   │
            +–––+–––+–––+–––+–––+–––+–––+–––+

            [––––––– length ––––––––]
```

Rust 在栈中创建了 String，然后用一个指针（buffer）指向了堆中的内存地址：

- buffer：指向堆中实际存储对象的内存地址
- capacity：存储对象占用的容量
- length：存储对象实际的长度

String 在栈中是固定的三个字长。

这样设计的好处是 String 可以动态调整它的内存空间，比如以下代码：

```rust
let mut my_name = "xifan".to_string();
my_name.push_str( " gaoding");
```

还是那个 `my_name`，还是相同的栈中对象，但是它的堆内容已经变更了。

## 理解字符串切片

与 `String` 不同，`str` 是字符串切片，假如我们从 `my_name` 取出后面那段：

```rust
let mut my_name = "xifan".to_string();
my_name.push_str( " gaoding");

let last_name = &my_name[6..];
```

那么 `last_name` 就是 `str`，在内存中是这样的：

```
            my_name: String   last_name: &str
            [––––––––––––]    [–––––––]
            +–––+––––+––––+–––+–––+–––+
stack frame │ • │ 16 │ 13 │   │ • │ 7 │ 
            +–│–+––––+––––+–––+–│–+–––+
              │                 │
              │                 +–––––+
              │                       │
              │                       │
              │                     [–│––––––– str –––––––––]
            +–V–+–––+–––+–––+–––+–––+–V–+–-–+–––+–––+–––+–––+–––+–––+–––+–––+
       heap │ x │ i │ f │ a │ n │   │ g │ a │ o │ d │ i │ n │ g  │   │   │
            +–––+–––+–––+–––+–––+–––+–––+–––+–––+–––+–––+–––+–––+–––+–––+–––+
```

可以看到，`last_name` 没有 capacity，它只是一个切片，和 `my_name` 使用了同一份堆内存，也因此，`str` 是 *unsized* 的类型，我们用 str 时总是需要用 `&str`（引用）而不是 `str`。

以上就是 `String` 和 `&str` 的区别，但是在我们的例子中，我们并没有像 `last_name` 那样从一个 `String` 中创建切片，`str` 是如何生成的呢？

range 是生成 `str` 的常见方式，此外字面量是另一种常见方式：

```rust
let my_name = "xifan gaoding"; // 这是一个 `&str` 而不是 `String`
```

既然 `str` 是一个切片，它并不 owned 字符串本身，那么字面量的 `str` 指向的数据是由谁 owned 呢？

## 理解字符串字面量

字面量有点特殊，它不是运行时动态在堆中分配内存，而是属于编译期预分配的文本，被存放在二进制的静态存储区中（**read-only**）。在程序执行时是像这样：

```
            my_name: &str
            [–––––––––––]
            +–––+–––+
stack frame │ • │ 5 │ 
            +–│–+–––+
              │                 
              +––+                
                 │
 preallocated  +–V–+–––+–––+–––+–––+
 read-only     │ x │ i │ f │ a │ n │
 memory        +–––+–––+–––+–––+–––+
```

理解了字面量的也就更好的理解了 `String` 和 `&str` 之间的区别。

那么你可能又有了下一个问题。

## 在使用时应该使用哪一个？

由许多条件决定，但一般来说，如果你不需要拥有或者改变字符串，那么采用 `&str` 更好，`greet` 的改进版本是使用 `&str`：

```rust
fn greet(name: &str) {
  println!("Hello, {}!", name);
}
```

那如果调用方用的是 `String`，会不会带来不便，比如转换很麻烦或者因未知原因无法转换？没问题，Rust 的 **deref coercing** 功能允许通过借用运算符将 `String` 引用（即 `&String`）自动转换为 `&str`。

所以下面两种调用 greet 的方法是等价的：

```rust
fn main() {
  let first_name = "xifan";
  let last_name = "xifan".to_string();

  greet(first_name);
  greet(&last_name); // `last_name` is passed by reference
}

fn greet(name: &str) {
  println!("Hello, {}!", name);
}
```

Done.
