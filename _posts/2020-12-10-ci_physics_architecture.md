---
layout: post
redirect_from: /2020/12/10/ci_physics_architecture/
title: "CI 物理架构"
date: 2020-12-10 21:31:51 +0800
categories: [DevOps, 分享]
article_type: 1
typora-root-url: ../../github.io
---

这一篇介绍稿定客户端持续集成的物理架构。


目前整体的设计是这样的：

![](/assets/img/ci_physics_architecture-1.png)

在我们引入容器、虚拟化之前的很长一段时间，我们的 CI 基础设施都处于*雪花服务器*的状态：

- 手动管理一堆服务器
- 手动登陆每台服务器
- 手动安装众多软件
- 手动修改各种配置文件

导致每台服务器如同雪花一样独特，各服务器配置千差万别难以复制。

为了减少这些机器带来的维护成本，我们做了一些调研。

虽然我们的客户端有 Android、iOS、Flutter 三套开发环境，但是物理环境只有两种：

- Linux - 解决 Android 场景
- macOS - 解决 iOS 和 Flutter 场景

Linux 上有成熟的容器化技术可以用，但是 macOS 就不好解决了，早期的 Docker Toolbox 虽然也可以在 macOS 上跑 Docker，但是它的底层内核是基于 VirtualBox 的，也就是需要厚重的 Guest OS 层（参考上图）。

容器化相比虚拟化的好处很明显，不需要 Guest OS，节省资源，而且 Docker 技术成熟，可靠稳定。

而 macOS 只能选择虚拟化了，相比 Docker 还是存在很大差距：

- 机器资源占用较多
- 虚拟机软件的稳定性稍差
- 镜像文件更消耗磁盘空间

经过一番调研我们最终选择了以苹果原生虚拟化技术 `Hypervisor.framework` 为标准，同时支持终端运行的 VMWare 作为我们的 macOS 虚拟化解决方案，为了在使用体验上接近 Docker，我们在虚拟机内做了自动登陆、自启动脚本等基础工具，在宿主机上同样可以一行代码完成虚拟机的运行：

```bash
# 启动
vmrun start path/to/vmwarevm nogui

# 结束
vmrun stop /path/to/vmx 

# 克隆
vmrun clone /path/to/source/vmx /path/to/target/vmx full -cloneName=NewName
```

其中：

- 自动登录是 macOS 原生提供的功能
- 自启动可以通过 launchd 解决
- 机器的性能监控基于 `top` 实现
- ...

之后在整体上做一层简单的封装，比如集成到一套后台管理系统中。

目前实践下来基本上可以达到设计目标。