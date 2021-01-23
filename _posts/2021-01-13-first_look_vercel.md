---
layout: post
title: "尝试 Vercel"
date: 2021-01-13 18:05:21 +0800
categories: [分享]
article_type: 1
excerpt_separator: <!--more-->
typora-root-url: ../../github.io
---

最近在手机上访问 GitHub Page 时遇到完全打不开的情况，感觉已经无法忍受了。

<!--more-->

上次尝试将 Jekyll 静态生成的内容同步到 Netlify 上，但没有取得太好的效果：

![](/assets/img/69-1.png)



于是就想重新找个镜像站点，发现了 Vercel，部署好后效果很明显：

![](/assets/img/first_look_vercel-1.jpg)

Vercel 也是一个静态网站托管平台，支持 GitHub、GitLab、Bitbucket 以及一键导入，使用上和 Netlify 差不多。

除此之外 Vercel 还支持 Serverless Functions，我部署了一个子域名用于测试：

```shell
$ curl https://www.api.codingtour.com/api/hello
{"name":"John Doe"}
```

这样一来像文章阅读数、评论之类的数据除了用 GitHub 存储之外还有了其他选择，前提是额度够用：

|                                                 | Hobby | Pro  | Enterprise |
| :---------------------------------------------- | :---- | :--- | :--------- |
| Deployments Created per Day                     | 100   | 3000 | Custom     |
| Serverless Functions Created per Deployment     | 12    | 24   | Custom     |
| Serverless Functions Deployed per Month         | 160   | 640  | Custom     |
| Serverless Function Execution Timeout (Seconds) | 10    | 60   | 900        |
| Deployments Created from CLI per Week           | 2000  | 2000 | Custom     |
| Team Members per Team                           | -     | 10   | Custom     |
| Vercel Projects Connected per Git Repository    | 3     | 10   | Custom     |
| Build Time per Deployment (Minutes)             | 45    | 45   | 45         |

> 日常使用是够了，更详细的限制条件见：https://vercel.com/docs/platform/limits。

个人博客作为展示自己的一个窗口，还是值得花一些功夫持续做优化。

![](/assets/img/official_accounts-1.png)