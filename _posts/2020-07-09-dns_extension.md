---
layout: post
redirect_from: /2020/07/09/dns_extension/
title: "DNS 的用武之地"
date: 2020-07-09 23:12:51 +0800
categories: [DNS]
article_type: 1
---

DNS 除了做域名解析，还能干啥


# 思维导图：

# ![](https://github.com/zhangao0086/mind/blob/master/DNS%20%E7%9A%84%E7%94%A8%E6%AD%A6%E4%B9%8B%E5%9C%B0/DNS%20%E7%9A%84%E7%94%A8%E6%AD%A6%E4%B9%8B%E5%9C%B0.png?raw=true)

*[xmind](https://github.com/zhangao0086/mind/blob/master/DNS%20%E7%9A%84%E7%94%A8%E6%AD%A6%E4%B9%8B%E5%9C%B0/DNS%20%E7%9A%84%E7%94%A8%E6%AD%A6%E4%B9%8B%E5%9C%B0.xmind)*

# 文字资料

- 域名解析
  - 通过 DNS 服务器返回对应的 IP 地址
- 智能 DNS
  - 资源的就近访问
    - 根据用户 IP 返回最近的服务器地址
  - 实现方式
    - DNS 服务商通过提供智能 DNS 解析策略为用户的多个主机的映射。通常情况下，用户需要登陆服务商的管理后台配置各种域名记录，包括域名A记录、CNAME记录和MX记录
- 反向代理的水平拓展
  - nginx 的水平拓展
    - 基于智能 DNS，突破 nginx 的性能极限

- web-server 的负载均衡
  - 直接将流量发到对应的服务器主机
    - 优点
      - 服务器架构无感知
      - 少了一层网络请求
    - 缺点
      - DNS 只具备解析（静态），无法保证对外的可用性，当主机挂掉时，不能自动迁移流量
      - 实时性差，DNS 存在缓存，生效需要较长的时间，扩容不及时

- 参考
  - [DNS 域名解析 - DNSPod](https://www.dnspod.cn/Products/dns)
  - [除了解析域名，DNS还能干吗？](https://mp.weixin.qq.com/s/LKPSbD35NQ-Kb9w8LEsLQA)