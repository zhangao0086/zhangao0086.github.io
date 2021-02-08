---
layout: post
title: "CPython 中的超级大锁"
date: 2021-02-08 18:32:55 +0800
categories: [分享]
article_type: 1
typora-root-url: ../../github.io
---

多才多艺的 Python 被应用在网络开发、机器学习、数据科学、数据工程、数据分析和人工智能等各个领域，以至于近些年总是可以在各种榜单的前排看到它的身影：

![](/assets/img/python_gil-tcl-202007.jpg)

Python 有如今的成就，全靠它易于使用、结构简单的特点，产生了极高的开发效率，越来越多的开发人员正在或开始使用它。

# 初识 GIL

即便如此，Python 还是有一些问题在社区里被反复提及，最典型的问题就是 Python 的执行性能不高，无法发挥出 CPU 多核的优势。

我们知道程序执行的任务可以分为两种：

- CPU 密集型
- I/O 密集型

对于 I/O 密集型的程序多数时间是在等待 I/O 共享锁，Python 对此的影响并不大。

而 CPU 密集型的程序可以在多核环境下通过多线程编程技术提高执行效率，但 Python 是个例外，考虑如下代码：

```python
# single_threaded.py
import time
from threading import Thread

COUNT = 50000000

def countdown(n):
    while n>0:
        n -= 1

start = time.time()
countdown(COUNT)
end = time.time()

print('Time taken in seconds -', end - start)
# Time taken in seconds - 6.651549816131592
```

这是一个单线程的程序，在我的电脑上执行所需时间为 6.65 秒左右，同样的任务用多线程试试：

```python
# multi_threaded.py
import time
from threading import Thread

COUNT = 50000000

def countdown(n):
    while n>0:
        n -= 1

t1 = Thread(target=countdown, args=(COUNT//2,))
t2 = Thread(target=countdown, args=(COUNT//2,))

start = time.time()
t1.start()
t2.start()
t1.join()
t2.join()
end = time.time()

print('Time taken in seconds -', end - start)
# Time taken in seconds - 6.878478765487671
```

比单线程执行**更慢**，需要 6.87 秒左右。

> 以上代码的执行环境都是基于 CPython。

导致这种情况发生的罪魁祸首是 GIL(Global Interpreter Lock)，它是一把互斥锁(mutex)，作用是只有**持有该锁**的线程才能控制 Python 解析器，换句话说，不管有没有使用多线程技术，只要 Python 解析器是共享的，那就是单线程的，这就是一把语言级的超级大锁。

# GIL 的好处

它带来了什么好处呢？

Python 采用了引用计数为主、GC 为辅的内存管理策略：

```python
import sys
a = []
b = a
sys.getrefcount(a)
# 3
```

> a、b、getrefcount 的参数传递增加了 a 的引用计数。

为了保证引用计数可以在多线程下正常工作，防止资源竞争导致的内存泄漏或重复释放等问题，需要对引用计数变量加锁保证它的安全性，这样一来会有两种实现方式：

- 为每个对象单独配备一把锁
- 全局共享一把锁

前者会带来大量的锁切换开销，而且多锁的环境有产生死锁的风险，同时锁的管理也会给开发者带来很大的维护成本，综合考虑后，最终 Python 选择了后者：

- 语言级的锁，只有取得锁的线程才能执行，变成单线程，完全避免多线程下的所有问题
- 单线程下的执行性能变得更高
- **开发者可以总是假设线程安全**

GIL 下的多线程执行流程：

![](/assets/img/python_gil-flow.jpg)

线程被调度的同时还需要拿到 GIL 锁。

# 线程切换

为了防止 GIL 锁长时间不释放导致其他线程得不到调用的机会，比如下面的代码：

```python
while True:
  pass
```

GIL 引入了 ticks 的设计：

![](/assets/img/python_gil-tick.jpg)

线程取得 GIL 锁的同时，还需要保证 ticks 大于 0，这样可以强制让出锁，以便给其他线程执行的机会。

ticks 的值可以通过代码修改：

```python
import sys
# The interval is set to 100 instructions:
>>> sys.getcheckinterval()
# 100
>>> sys.setcheckinterval(200)
>>> sys.getcheckinterval()
# 200
```

默认值 100 表示每执行 100 个指令后切换一次线程。

> 关于 ticks，可以看看这篇 [The Python GIL Visualized](http://dabeaz.blogspot.com/2010/01/python-gil-visualized.html)。

GIL 在 Python 3.2 又进一步做了优化，将指令间隔优化成了时间间隔(单位为秒)，所以在 Python3 中要通过 `setswitchinterval` 来设置时长：

```python
import sys
# The interval is set to 5 milliseconds:
>>> sys.getswitchinterval()
# 0.005
>>> sys.setswitchinterval(0.5)
>>> sys.getswitchinterval()
# 0.5
```

值越大，CPU 密集型程序执行效率越高，但 I/O 密集型程序越不容易拿到锁，需要权衡该值。

# 多进程

那在 Python 里是否就真的无法实现多线程呢？其实还是有的。

之前我们说过，如果 Python 解析器是共享的话多线程是没有意义的，但多进程是可以的：

```python
from multiprocessing import Pool
import time

COUNT = 50000000
def countdown(n):
    while n>0:
        n -= 1

if __name__ == '__main__':
    pool = Pool(processes=2)
    start = time.time()
    r1 = pool.apply_async(countdown, [COUNT//2])
    r2 = pool.apply_async(countdown, [COUNT//2])
    pool.close()
    pool.join()
    end = time.time()
    print('Time taken in seconds -', end - start)
    # Time taken in seconds - 4.629117012023926
```

由于进程管理也有开销，而且进程本身比线程更重，所以不能期望执行性能降低一半。

# 总结

虽然 GIL 使 Python 的执行性能打了折扣，但在 Python 诞生的那个年代，操作系统还没有线程的概念，设计者很难预测未来的科技发展，早年 Python 的作者曾写了[一篇文章](https://www.artima.com/weblogs/viewpost.jsp?thread=214235)介绍这个背景，以及移除 GIL 的前提，即不影响单线程下的性能，但经过这么多年的使用，想达到这个标准挺难的。

虽然历史原因没办法很快卸下这个包袱，但好在 Python 确实达到了它的设计目标：易于使用，一门易于使用、线程安全的语言不管在过去，还是在现在，或者是未来，相信它都有很大的吸引力。

参考链接：

- https://realpython.com/python-gil
- https://www.datacamp.com/community/tutorials/python-global-interpreter-lock