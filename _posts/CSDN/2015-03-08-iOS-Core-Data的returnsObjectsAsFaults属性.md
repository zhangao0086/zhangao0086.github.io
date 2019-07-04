---
layout: post
title: "iOS Core Data的returnsObjectsAsFaults属性"
date: 2015-03-08 10:15:29
categories: [iOS,Swift]
---


﻿来自论坛的一个问题：[[CoreData] returnsObjectsAsFaults是什么用的](http://bbs.csdn.net/topics/390891590%20%5BCoreData%5D%20returnsObjectsAsFaults%E6%98%AF%E4%BB%80%E4%B9%88%E7%94%A8%E7%9A%84)。

这个属性是用来做优化的，但是有时候反而会降低性能，打个简单的比方，假如你有一个Department对象，它和Employee对象是一对多的关系（比如一个部门有100个员工），当你加载Department的时候，它包含的所有Employee也被加载了，此时如果returnsObjectsAsFaults为YES，则员工们不会被添加到内存中，而是被放在了row cache里，Department对象里的员工们只是一个指针（也称之为fault managed object），只有当你真正要用到Department里的员工数据的时候，Core Data才会再次从row cache中读取出来：

```objective-c
// returnsObjectsAsFaults 为YES
// 打印Department对象
NSLog(@"%@", department);
```

看到的输出：
```objective-c
<Department 0x123456
  employees : <NSSet data:fault>
>
```

否则看到的`employees`输出就是一个完整的列表。

row cache虽然是一张缓存表，但是也有可能因为数据太多而变得很大，如果你要遍历Department的所有员工（或者说你确定你会访问通过NSFetchRequest返回的对象的属性），这种情况下就会有额外的性能开销，此时设置returnsObjectsAsFaults为NO会是更好的选择。
