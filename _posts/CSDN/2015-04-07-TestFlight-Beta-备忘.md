---
layout: post
title: 'TestFlight Beta 备忘'
date: 2015-04-07 13:30:36 +0800
categories: [iOS]
csdn_read_num: 3235
article_type: 1
---


﻿用iTunes Connect提供的TestFlight功能可以确保我们在设备上测试的版本和App Store上将要发行的版本是同一个。
TestFlight仅支持iOS 8及后续版本，并且需要从App Store里安装TestFlight app。
分为内部测试和外部测试两种：
> 内部测试

每个应用最多25位测试者，需要把测试者的Apple ID添加到开发者账号里，苹果为会测试者创建一个iTunes Connect账号并与主账号关联。
只有Admin、Legal 、Technical角色才能测试，内部测试者在接收到邮件后，必须用iOS设备打开该邮件才能测试，不用等Apple审核。
每个账号能测试 10 个设备，但是每条邀请只能使用一次，我是通过反复邀请来添加每个账号的测试设备：
> Devices (2)
> iPhone 6 Plus (iOS 8.3)
> iPhone 5 (iOS 8.3)

---

> 外部测试

最多能邀请1000个测试者，预发布版本的第一个Build必须被Apple完全审核通过后才能测试，之后的同一个版本的其他Build不需要完全审核。
注意：
一个Apple ID，不能同时是内部、外部测试者。
安装的测试App名称旁有个橙色小点。

官方参考资料，有详细步骤：<a target="_blank" href="https://developer.apple.com/library/ios/documentation/LanguagesUtilities/Conceptual/iTunesConnect_Guide/Chapters/BetaTestingTheApp.html">BetaTestingTheApp</a>
