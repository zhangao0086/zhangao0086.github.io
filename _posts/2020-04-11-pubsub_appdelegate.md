---
layout: post
redirect_from: /2020/04/11/pubsub_appdelegate/
title: "提供 Pub/Sub 服务的 AppDelegate"
date: 2020-04-11 15:50:10 +0800
categories: [iOS, ARTS]
article_type: 1
excerpt_separator: <!--more-->
---

在最近的一次 App 架构调整中，为了：

- 减少 App 之间代码同步的复杂度
- 减少胶水代码的复杂度（如 `AppDelegate`）
- 解决潜在的应用跳转回调错误

<!--more-->

我们将代码的组织方式进行了较大的调整，采用的方案主要有：

- Sidecar + Launch 的组合：
  - Sidecar 为 App 们提供统一的能力，如日志、监控、加密等
  - Launch 作为一个启动项管理组件，方便业务方实现一些可以自包含的配置逻辑
- “干掉” `AppDelegate`：
  - 移除 App 们的 AppDelegate，在运行时采用消息转发的方式实现一个虚拟的角色
  - 将传统 AppDelegate 中操作视图层的逻辑单独封装成一个角色，提供创建 `window`、`rootViewController`  之类的行为
- 为 `UIApplicationDelegate` 的所有接口提供两种类型的 Pub/Sub 服务：
  - 观察者 - 按注册顺序调用，保证一定调用
  - 拦截器 - 按注册顺序反序调用，只要有一个拦截器表示成功拦截，则调用中断，否则继续找下一个拦截器
- 保存 `UIApplicationDelegate` 方法调用中的状态，如 `didFinish` 中的 options 和 `openURL` 中的 options，给其他组件在任意时刻访问这些状态的能力