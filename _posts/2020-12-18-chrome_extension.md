---
layout: post
title: "为 GitHub 提供 Owner 维度的文件过滤"
date: 2020-12-18 23:04:01 +0800
categories: [分享]
article_type: 1
excerpt_separator: <!--more-->
typora-root-url: ../../github.io
---

本文介绍一个通过 Chrome 插件在 GitHub 上实现 Owner 维度的文件过滤功能。

<!--more-->

# 背景

我们的代码库托管在 GitHub 企业版上，内部有一套明确的 Code Review 制度，按模块、目录、文件等不同的粒度划分具体的负责人或团队，保证所有代码的修改、变更是被允许的。

而由于 GitHub 只能以文件类型为维度过滤列表，如下图：

 ![image-20201219164446043](/assets/img/chrome_extension-1.png)

当 PR 文件过多时很难让对应的 Owner 找到自己真正关心的文件，于是我们评估并开发了一个 Chrome 插件，用于为 GitHub 提供 Owner 维度的过滤。

这个插件有如下特点：

- 一键过滤
- 不用鉴权
- 支持个人和团队两种 Owner 类型

该插件也很尊重隐私：

- 只监测代码库所在的域名
- 不会读取本机用户的隐私数据，如 Cookies、Web Storage 等

最终效果演示：

![ezgif.com-gif-maker](/assets/img/chrome_extension-2.gif)

# 实现细节

下面简单介绍几个我们的实现细节。

## Chrome 插件

Chrome 直接采用了 JSON 作为它的 DSL：

```json
{
    "manifest_version": 2,
    "version": "1.0",
    /*...*/
    "background": {
        "scripts": ["js/background.js"]
    },
    "content_scripts": [{
        "matches": ["{代码库域名}"],
        "js": ["js/jquery.min.js", "js/gaoding.js"]
    }],
    "permissions": [
        "webNavigation"
    ] 
}
```

下面介绍下为什么要使用 background、content_scripts 和 webNavigation。

> 为什么要使用 background

插件是基于事件驱动的，事件由浏览器触发，如果我们想拿到一些事件，比如导航到一个新页面、删除一个书签或关闭一个 tab 等事件，浏览器只会将它们发送给 background，另外像 Cookies 之类的读取也只能在 background 中进行。

我们使用 background 的场景正是监听导航的变化，当用于从 PR 的详情页跳到文件列表页时，通过消息传递机制告诉 content_scripts 去注入按钮并进行匹配动作。

> 为什么需要 content_scripts

content_scripts 可以访问页面上下文和操作 DOM，而且要注入脚本只能通过 content_scripts 完成，我们会在 content_scripts 初始化时（一般是 onload）和导航变化时执行注入和匹配逻辑，导航变化的监听正是基于 background 的消息传递机制实现的。

content_scripts 有两种注入方式：

- 动态注入 - 在代码里通过 `chrome.tabs.executeScript` 注入
- 申明式注入 - 我们采用的方式

> 为什么需要 webNavigation

这是唯一需要的权限，为了实现上面介绍的两点。

如果插件换一种思路实现，比如不注入按钮，而是让用户手动触发一个 [browser action](https://developer.chrome.com/docs/extensions/reference/browserAction/) 就不需要任何权限了，取而代之的是需要增加 [browser action](https://developer.chrome.com/docs/extensions/reference/browserAction/) 相关的配置。

## 跨域问题

Chrome 插件天然存在着跨域问题，在 V3 版本里很容易解决：

```javas
"host_permissions": [
  "{代码库域名}"
]
```

但 V3 需要 Chrome 88 以上版本支持，并且还没有正式发布，基于现有的 V2 只能在服务端层面解决。

GitHub App 一般会采用 probot 来开发，在 probot 或 express 里可以很容易全局处理：

```javascript
.use((_: any, res: any, next: any) => {
  res.append('Access-Control-Allow-Origin', ['*']);
  res.append('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE');
  res.append('Access-Control-Max-Age', '1000');
  res.append('Access-Control-Allow-Headers', '*');
  next()
})
```

## 免鉴权

免鉴权当然不是真正的免鉴权，而是在 Chrome 端使用该插件时不用在额外填写一些鉴权信息了，为此我们在后端 Node 服务里提供了一些服务。

> 获取 Teams

Owner 可以是个人也可以是团队，对于团队需要知道当前登录用户所在的全部团队才能进行文件匹配。

> 获取指定路径的文件内容

主要是用于获取 Owner 规则文件，如 CODEOWNERS 文件，一般在仓库的根目录下，前端获取该文件后，先解析规则再匹配文件列表，对不需要关心的文件做隐藏。

> 获取文件变更列表

GitHub 采用的分页接口加载文件列表，所以如果是通过 DOM 解析是不能在一开始得到全部文件信息的，为此我们在 Node 里提供了一个返回全部文件列表的接口。

上述所有需要鉴权的接口调用是通过 GitHub App 实现的，独立于用户权限，只要对应的仓库集成了应用即可。

# 总结

由于 GitHub 不支持以 Owner 为维度过滤文件，最终我们在团队里落地了一个 Chrome 插件来辅助我们完成 Review，对于一些特定的场景问题需要依靠自己的认知充分挖掘解决方案，最大限度的提高各个环节的效率，让研发更高效，让业务更聚焦。