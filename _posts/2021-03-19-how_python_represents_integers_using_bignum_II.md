---
layout: post
title: "Bignum in Python: 加减法运算"
date: 2021-03-19 23:32:21 +0800
categories: [Python, Bignum]
article_type: 1
typora-root-url: ../../github.io
---

这篇文章记录 Bignum 的加减法运算规则，理解它的最好方式就是直接阅读 Python 源码，我所查阅的版本是 Python-3.9.2，下文引用的代码和分析都基于该版本。

从 `Objects/longobject.c` 文件里可以找到全部相关的代码，在我们往下之前，先介绍一个预备知识。

一个加法函数可以表示为两个处理绝对值的函数：

1. 绝对值相加的函数
2. 绝对值相减的函数

这是因为：

$$-|a|+(-|b|)=-(|a|+|b|)$$

$$|a|+(-|b|)=|a|-|b|$$

$$-|a|+|b|=|b|-|a|$$

Python 的实现正是采用了该规则：

```c
static PyObject *
long_add(PyLongObject *a, PyLongObject *b)
{
    PyLongObject *z;

    CHECK_BINOP(a, b);
		
  	/* 优化点 */
    if (Py_ABS(Py_SIZE(a)) <= 1 && Py_ABS(Py_SIZE(b)) <= 1) {
        return PyLong_FromLong(MEDIUM_VALUE(a) + MEDIUM_VALUE(b));
    }
	  
    if (Py_SIZE(a) < 0) { /* a 是负数 */
        if (Py_SIZE(b) < 0) { /* b 是负数 */
          	/* 两个负数相加，符合规则 -|a|+(-|b|)=-(|a|+|b|) */
            z = x_add(a, b); 
            if (z != NULL) {
                /* x_add received at least one multiple-digit int,
                   and thus z must be a multiple-digit int.
                   That also means z is not an element of
                   small_ints, so negating it in-place is safe. */
                assert(Py_REFCNT(z) == 1);
                Py_SET_SIZE(z, -(Py_SIZE(z))); /* 设置符号 */
            }
        }
        else
          	/* a 是负数，b 是正数，符合规则 -|a|+|b|=|b|-|a| */
            z = x_sub(b, a);
    }
    else {
        if (Py_SIZE(b) < 0)
          	/* a 是正数，b 是负数 */
            z = x_sub(a, b);
        else
          	/* 两个正数相加 */
            z = x_add(a, b);
    }
    return (PyObject *)z;
}
```
`long_add` 只是一层 wrapper，核心的实现在 `x_add` 和 `x_sub` 两个函数里。

两个 Bignum 本质上是两个序列，`x_add` 逐位相加并记录进位即可：

```c
/* Add the absolute values of two integers. */

static PyLongObject *
x_add(PyLongObject *a, PyLongObject *b)
{
    Py_ssize_t size_a = Py_ABS(Py_SIZE(a)), size_b = Py_ABS(Py_SIZE(b));
    PyLongObject *z;
    Py_ssize_t i;
    digit carry = 0;

    /* Ensure a is the larger of the two: */
    if (size_a < size_b) {
        { PyLongObject *temp = a; a = b; b = temp; }
        { Py_ssize_t size_temp = size_a;
            size_a = size_b;
            size_b = size_temp; }
    }
  
  	/* Python 数字不可变，需要创建一块新的区域 */
    z = _PyLong_New(size_a+1);
    if (z == NULL)
        return NULL;
  
    for (i = 0; i < size_b; ++i) {
        carry += a->ob_digit[i] + b->ob_digit[i];
        z->ob_digit[i] = carry & PyLong_MASK;
        carry >>= PyLong_SHIFT;
    }
    for (; i < size_a; ++i) {
        carry += a->ob_digit[i];
        z->ob_digit[i] = carry & PyLong_MASK;
        carry >>= PyLong_SHIFT;
    }
    z->ob_digit[i] = carry;
  
  	/* 最高位没用上时将 shrink 掉 */
    return long_normalize(z);
}
```

如果你做过 [Add Two Numbers](https://leetcode.com/problems/add-two-numbers/) 就会很容易理解这个实现，两者的区别只是 Base 不同而已。

`x_sub` 的实现也类似，先找到两数中较大的数，逐位比较执行减法，进位变成了借位：

```c
/* Subtract the absolute values of two integers. */

static PyLongObject *
x_sub(PyLongObject *a, PyLongObject *b)
{
    Py_ssize_t size_a = Py_ABS(Py_SIZE(a)), size_b = Py_ABS(Py_SIZE(b));
    PyLongObject *z;
    Py_ssize_t i;
    int sign = 1;
    digit borrow = 0;

    /* Ensure a is the larger of the two: */
    if (size_a < size_b) {
        sign = -1; /* a 比 b 小，结果为负数，记录符号 */
        { PyLongObject *temp = a; a = b; b = temp; }
        { Py_ssize_t size_temp = size_a;
            size_a = size_b;
            size_b = size_temp; }
    }
    else if (size_a == size_b) {
        /* Find highest digit where a and b differ: */
        i = size_a;
        while (--i >= 0 && a->ob_digit[i] == b->ob_digit[i])
            ;
        if (i < 0) /* 两数相等，返回 0 */
            return (PyLongObject *)PyLong_FromLong(0);
        if (a->ob_digit[i] < b->ob_digit[i]) {
            sign = -1; /* a 比 b 小，结果为负数，记录符号 */
            { PyLongObject *temp = a; a = b; b = temp; }
        }
        size_a = size_b = i+1; /* 忽略高位相同的部分 */
    }
    z = _PyLong_New(size_a);
    if (z == NULL)
        return NULL;
    for (i = 0; i < size_b; ++i) {
        /* The following assumes unsigned arithmetic
           works module 2**N for some N>PyLong_SHIFT. */
        borrow = a->ob_digit[i] - b->ob_digit[i] - borrow;
        z->ob_digit[i] = borrow & PyLong_MASK;
        borrow >>= PyLong_SHIFT;
        borrow &= 1; /* Keep only one sign bit */
    }
    for (; i < size_a; ++i) {
        borrow = a->ob_digit[i] - borrow;
        z->ob_digit[i] = borrow & PyLong_MASK;
        borrow >>= PyLong_SHIFT;
        borrow &= 1; /* Keep only one sign bit */
    }
    assert(borrow == 0);
    if (sign < 0) {
        Py_SET_SIZE(z, -Py_SIZE(z)); /* 设置符号 */
    }
    return maybe_small_long(long_normalize(z)); /* 去除不需要的高位 */
}
```

至此 Bignum 的加法运算就全部完成了，与 `long_add` 类似，Python 使用函数 `long_sub` 包装减法运算，核心实现同样是 `x_add` 和 `x_sub`：

```c
static PyObject *
long_sub(PyLongObject *a, PyLongObject *b)
{
    PyLongObject *z;

    CHECK_BINOP(a, b);

  	/* 优化点 */
    if (Py_ABS(Py_SIZE(a)) <= 1 && Py_ABS(Py_SIZE(b)) <= 1) {
        return PyLong_FromLong(MEDIUM_VALUE(a) - MEDIUM_VALUE(b));
    }
  
    if (Py_SIZE(a) < 0) {
        if (Py_SIZE(b) < 0) {
          	/* 两个负数相减，等同于 |b|-|a| */
            z = x_sub(b, a);
        }
        else {
            z = x_add(a, b);
            if (z != NULL) {
                assert(Py_SIZE(z) == 0 || Py_REFCNT(z) == 1);
                Py_SET_SIZE(z, -(Py_SIZE(z)));
            }
        }
    }
    else {
        if (Py_SIZE(b) < 0)
            z = x_add(a, b);
        else
            z = x_sub(a, b);
    }
    return (PyObject *)z;
}
```

以上就是 Bignum 在 Python 中的加减法运算实现，注意到 `long_add` 、`long_sub` 里的优化点了吗？就是这两段：

```c
/* 优化点：加法 */
if (Py_ABS(Py_SIZE(a)) <= 1 && Py_ABS(Py_SIZE(b)) <= 1) {
    return PyLong_FromLong(MEDIUM_VALUE(a) + MEDIUM_VALUE(b));
}


/* 优化点：减法 */
if (Py_ABS(Py_SIZE(a)) <= 1 && Py_ABS(Py_SIZE(b)) <= 1) {
    return PyLong_FromLong(MEDIUM_VALUE(a) - MEDIUM_VALUE(b));
}
```

由于 Bignum 在运算的过程中需要大量的内存访问，所以其运算效率比 CPU 直接计算要慢得多，因此 Python 采用了优化策略：**当两个数字的位数不超过1时，直接使用 CPU 计算**。而且因为每个 digit 的取值远小于 CPU 的字长，所以也不会有溢出的风险。

> digit 根据平台有不同的最大值：
>
> 64位：$$2^{30}-1$$
>
> 32位： $$2^{15}-1$$

整体看下来还算是很优雅的实现。