---
title: "AWS EC2 Linux 实例进入紧急模式该如何不删除实例并恢复"
date: "2024-01-03T11:26:30.704Z"
slug: "recovery-aws-ec2-emergency-mode"
draft: false
---

> [正确处理重启实例自动挂载卷的方式](https://docs.aws.amazon.com/zh_cn/AWSEC2/latest/UserGuide/ebs-using-volumes.html#ebs-mount-after-reboot)

## 起因
1. 操作系统Amazon Linux 2023
2. 实例类型t2.micro

想给EC2挂载一个新卷，但是重启实例的时候发现挂载的卷不见了，然后网上找了下如何重启自动挂载。试了下修改`/etc/fstab`文件，然后重启发现ssh一直连不上，看了下日志才发现进入紧急模式...交互界面也进不去了「很明显第一次就改坏了」

![image](./attachments/Qmcua5nThgJTaa3Hiv6ev2gShKhLYPzD31LDVqH5KtwJ5e)
一开始我以为是我的proxy出了问题，不过关闭之后还是连不上

![image](./attachments/QmZdWiyaxwwTCpMzpvb8aqvvFn3eobqSMxjNPx298DHGdr)

打开系统日志

![image](./attachments/QmNNM3Se2dxnyY52ceu5QB4e8aQu6BBfV25XX5Xq3eyn5X)


![image](./attachments/QmRZoZSQGSEEnJNkbExafjomJGpHqt6jpCjBesBBdkahhK)

但是AWS也提供了启动失败的解决方案，下面有一行小字

![image](./attachments/QmWDy3QHPVqiMjgQFtjSYHQJ5ocyQNg2PHe1J139EKHcg3)

结果

![image](./attachments/QmbyheZ91wACkYg7QCsYTGLw2E1WFFZPdSD8rJF82QCsjH)

一开始我一直在看文档，查找哪种类型能支持，去更改实例类型，但是不知道为什么还是连接不上...最后找到了一种通过临时启动一个用于恢复的实例来把改坏的文件修改回去的方法。


## 恢复方式

基本上分为这几步
1.停止启动失败的实例
2. 从启动失败的实例分离root卷
3. 在同个区内创建新的EC2实例
4. 挂载root卷到新的实例
5. 修改`/etc/fstab`文件

### 停止实例
等待停止即可，目的是为了分离卷
![image](./attachments/QmcVZxSVcutWLaKikz9twFK76a8VAmXnEv9Lap5SkZwXL8)

### 分离卷

找到挂载在根「/」目录下的卷，点击分离

![image](./attachments/QmTxwDExyeEPLVgNsYpoTp8iwdYUUjuusDm26W5PJBCuwx)

### 启动一个新的实例

配置就最简单的就行，目的只是为了挂载上一步分离出来的卷

记得要指定子网「目的是选择和卷一样的可用区，比如我的就是us-west-1b」

![image](./attachments/QmTfyac18hCVcdow9LtLCCHDuTdDC265uvR3vRFwm6aqBQ)

### 挂载卷

在AWS管理页面挂载刚刚分离的卷到新的实例上，并ssh到新的实例挂载


![image](./attachments/QmYL5iDc1Dvio5Jm4Q6NuEkiG8LEkR3jef82Lkk8VEakjo)

这里就能看到我们刚刚改错的内容了

![image](./attachments/QmVKPW37AGLcZ2tsvooussPWoh7TyZ2Wqs4zw4TkCThf5q)

使用vim直接修改fstab文件，改好之后分离卷，挂载回启动不了的实例。注意挂载回去的时候名字输入xvda「与之前一样，目前我看到的AWS默认根卷都是这个名字」


![image](./attachments/QmaZKcS28GdNN33rRQEFjhk47vggj5pzWq2ZHbdwfSjXSo)

最后启动老的实例，刚刚新建的实例可以删除了

![image](./attachments/QmUWGc7asoUnKe2Fkyqo6nKf9sEWMNfnYmrJYki9MGJp75)
成功！

## 参考

[排查 EC2 Linux 实例处于紧急模式的问题 | AWS ](https://repost.aws/zh-Hans/knowledge-center/ec2-linux-emergency-mode)
