---
layout: post
title: "Bignum in Python: 内存中的存储"
date: 2021-03-12 22:44:14 +0800
categories: [Python, Bignum]
article_type: 1
typora-root-url: ../../github.io
---

这篇文章主要记录 Python 是如何在从内存中表示 Bignum 的，由于 Python 使用 Bignum 表示所有的整型，所以这也是 Python 对整型的实现方式。

我们知道 Bignum 可以表示任意长度的数字，在内存上表示为一个数组，如数字：

```
51090942171709440000
```

可以表示为：

```
[5, 1, 0, 9, 0, 9, 4, 2, 1, 7, 1, 7, 0, 9, 4, 4, 0, 0, 0, 0]
```

这是以 10 为 Base 存储的结果，由于每个字节可以表示 0~255，这样的存储方式无疑会造成巨大的内存浪费，因为只有 $$10 \over 255$$ 的值是有效的。为了提高内存使用效率，Python 会根据 64位、32位平台选择 $$2^{30}$$、$$2^{15}$$ 作为 Base，Base 越大意味着存储所需要的位数越少，但也不能无限大，要平衡 Bignum 的算法。

由于 Python 默认使用 Bignum 表示所有的整型，我们先直接看看 Python 用于表示整形的数据结构是怎样的。

首先，Python 用 `PyLongObject` 存储一个 Bignum，我们将它完全展开：

```c
typedef struct _longobject PyLongObject; /* Revealed in longintrepr.h */

/* ----- */

struct _longobject {
    PyVarObject ob_base; // expansion of PyObject_VAR_HEAD macro
    digit ob_digit[1];
};

/* ----- */

typedef struct {
    PyObject ob_base;
    Py_ssize_t ob_size; /* Number of items in variable part */
} PyVarObject;

/* ----- */

#if PYLONG_BITS_IN_DIGIT == 30
typedef uint32_t digit;
#elif PYLONG_BITS_IN_DIGIT == 15
typedef unsigned short digit;
#endif

/* ----- */

/* If PYLONG_BITS_IN_DIGIT is not defined then we'll use 30-bit digits if all
   the necessary integer types are available, and we're on a 64-bit platform
   (as determined by SIZEOF_VOID_P); otherwise we use 15-bit digits. */
#ifndef PYLONG_BITS_IN_DIGIT
#if SIZEOF_VOID_P >= 8
#define PYLONG_BITS_IN_DIGIT 30
#else
#define PYLONG_BITS_IN_DIGIT 15
#endif
#endif
```

关键成员有两个：

- `ob_digit` - 一个指向 digit 数组的指针，其中每个 digit 根据平台有不同的最大值：
  - 64位：$$2^{30}-1$$
  - 32位： $$2^{15}-1$$
- `ob_size` - 记录 ob_digit 的长度，这是一个有符号的数字，它的符号位决定了 Bignum 是正还是负，如果 ob_size 为 0，则整个数字也是 0

`ob_digit` 是以小端序存储的，意味着 `ob_digit[0]` 表示最低位，`ob_digit[abs(ob_size)-1]` 表示最高位。所以整个数字的计算公式为：

$$val=ob\_digit[0]*(2^{30})^0+ob\_digit[1]*(2^{30})^1 + ... + ob\_digit[|ob\_size|-1]*(2^{30})^{|ob\_size|-1}$$

> 以 64 位为例

举例：

- `ob_digit` 为 `[3, 5, 1]`
- `ob_size` 为 `-3`

```python
base = 2**30
-(3 * base**0 + 5 * base**1 + 1 * base**2)
# -1152921509975556099
```

在写个反向的转换来验证：

```python
import ctypes

MAX_DIGITS = 1000

# This is a class to map a C `PyLongObject` struct to a Python object
class PyLongObject(ctypes.Structure):
    _fields_ = [
        ("ob_refcnt", ctypes.c_ssize_t),
        ("ob_type", ctypes.c_void_p),
        ("ob_size", ctypes.c_ssize_t),
        ("ob_digit", MAX_DIGITS * ctypes.c_uint32)
    ]
    
def get_digits_and_size(num):
    obj = PyLongObject.from_address(id(num))
    digits_len = abs(obj.ob_size)
    return obj.ob_digit[:digits_len], obj.ob_size
  
get_digits_and_size(-1152921509975556099)
# ([3, 5, 1], -3)
```

这就是 Bignum 在 Python 中的存储方式，不算太复杂。