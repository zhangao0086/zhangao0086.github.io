---
layout: post
redirect_from: /2019/09/25/exposure/detection/
title: "关于坑位曝的光检测方案"
date: 2019-09-25 16:09:20 +0800
categories: [iOS, ARTS]
article_type: 1
---

# 需求简述

> 用户曝光模板后触发，曝光需要满足以下条件：
>
> 1、在屏幕展示大于等于2/3被曝光对象；
>
> 2、在屏幕的停留时间大于等于1.5秒；
>
> 3、一个页面对于同一个内容仅曝光一次。仅当重新进入页面后会继续上报。


# 技术拆解

对“同一个页面”的定义

- 栈中的 `UIViewController`、`Activity` 是同一个实例

同一个页面内不需要重新曝光的动作：

1. 顶部 tab 切换
2. 下拉刷新
3. 下一页、上一页
4. 移出屏幕再移进屏幕
5. 从子页面返回

需要重新曝光的动作：

1. 底部 tab 切换
2. 在后台超过30秒

## 方案一

初步考虑了一个模板曝光的技术方案：

1. 增加一个 `UIView` 的类别，包含一个设置曝光数据的接口，调用该接口的 `UIView` 将被自动注册到全局的一个容器中，容器采用弱引用的方式
2. hook `didMoveToWindow`，判断当前 view 是否需要记录曝光，然后通过 window 参数判断当前 view 是否在显示状态，并记录 visible、invisible 的时间点，用于判断曝光时长
3. 曝光成功后上传事件

方案优点：

1. 易落地
2. 易集成
3. 松耦合

方案缺点：

1. 曝光事件检测不及时，依赖于 `didMoveToWindow` 的调用
2. 暂不支持曝光面积的计算(后续可在该方案上拓展)
3. 已曝光过 -> 新的曝光 需要根据规则在 View 层手动重置(后续可自动重置)

"暂不支持曝光面积的计算"的后续拓展方案：

1. 可通过一个 Runloop 持续检查容器+当前已显示的 View 的交集
2. 记录满足面积的 View

"已曝光过 -> 新的曝光"的后续自动重置方案：

1. 通过 hook 一些事件，如下拉刷新、tab 切换，来实现自动重置
2. 覆盖不到的地方还是手动



## 方案二

在实现方案一的过程中发现了一些问题：

1. `didMoveWindow` 调用不及时，具体的：window 非空时调用的太早，此时 view 还没有暴露给用户；window 为空时调用的太晚或者没有调用，特别是在 TableView 和 CollectionView 中时，view 虽然没有在显示，但 TableView 和 CollectionView 仍然没将它从视图层级上移除，hidden 之类的属性也没有设置，需要找其他方案
2. Runloop 配合定时器感觉不太好，主要是在 暂停 -> 继续 这两种状态下切换的时候，我们特别需要"即时暂停"

针对问题1的分析，以频道页面为例，ScrollView - TableView - CollectionView 互相嵌套太深，布局分析极其复杂：

![Image 1](/assets/img/image2019-8-21_17-21-22.png)

由于 CollectionView 是全尺寸展示，这带来了两个后果：

1. 失去了 Cell 可复用的特点，内存消耗大
2. `didMoveToWindow` 等事件不准确

虽然重构这个页面是很自然的事情，不过这不是眼下的重点，我们还是把重点放在了无痕检测上，保证业务方布局的灵活性。

由于我们不能依赖 `didMoveToWindow` 去记录时间，我们需要在运行时手动计算哪些视图是真正可见的，从而记录时间。实时 Runloop 对效率影响太大，而且不能有效的节省资源，所以方案二的思路重点是：

1. 基于 dispatch_queue 和 dispatch_timer  来代替 Runloop 
2. 曝光面积的算法通过在父视图或 window 裁剪掉子视图多余的部分来实现
3. 增加了一个 `layoutSubviews` 的 hook，在 `didMoveToWindow` 和 `layoutSubviews` 的时机检测曝光面积和曝光时间
4. 采用状态管理，内部分为了四种：
   1. exposureViews - 需要检测曝光的视图
   2. viewsForCheckingArea - 需要检测曝光面积的视图
   3. viewsForCheckingTiming - 需要检测曝光时间的视图
   4. viewsForExposed - 已曝光的视图，避免重复曝光



## 方案三

方案二基本上已经能够实现，但是逻辑控制代码还有优化的空间，我们希望：

1. 尽量减少资源，减少对主线程的干扰
2. 保持代码干净，维护性强

最终方案三做出的改进有：

1. 基于 `CADisplayLink` 在滚动时检测曝光面积，不再需要 dispatch_queue + timer 的配置，而且时效性更强（目前是 30fps 检测一次）
2. 去掉了两个状态：viewsForCheckingTiming 和 viewsForExposed
3. 引入了 page 的概念，可以轻松控制是否需要重复曝光
4. 曝光成功的的时机增加了滚动时，更快记录

完整的方案如下：

1. hook `UIView` 的几个方法：
   1. `didMoveToWindow` - 映射到内部的 `viewDidMoveToWindow`，判断+记录，同时 page 的设置也在这个时机
   2. `willMoveToWindow` - 映射到内部的 `viewWillMoveOutWindow`，在 UIView 即将从 window 上移除前，再计算一次曝光面积和时间，如果 window 没了，就无法判断了
   3. `layoutSubviews` - 防止视图 size 变化影响曝光面积的计算
2. 内部基于 `CADisplayLink` 高效的在滚动时持续检测曝光面积和时间；非滚动时仅在上述 hook 的方法触发时检测一次
3. 已曝光的记录随 page 的生命周期，可由外部清除记录
4. 前、后台的处理通过 `UIApplicationDidEnterBackgroundNotification`、`UIApplicationWillEnterForegroundNotification` 处理
5. 曝光成功后上传事件

方案优点：

1. 易落地
2. 易集成
3. 松耦合

方案缺点：

1. 曝光面积的判断会有误差，特别是在被毛玻璃覆盖下



# 其他

如果有额外的要求，比如：

- 对于同一个页面、同一个模板，不同的资源位，按多次曝光处理

有一个简单的 trick，就是业务方设置曝光数据时，加上一个固定的前缀(特殊字符)，这样内部就能当作是不同的曝光数据来处理，然后在上传时去掉这个前缀。

这个特殊字符可以用零宽字符。