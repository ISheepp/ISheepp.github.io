---
title: "vegeta压测使用"
date: "2024-01-10T12:31:34.642Z"
slug: "vegeta"
draft: false
---

vegeta是一个HTTP压力测试工具，使用Go编写，用命令行交互，并且可以生成汇总和图表作为结果分析。

https://github.com/tsenart/vegeta

## 基本使用

详细使用方式可以参考README里的内容。可以分为两种方式使用：命令行交互和作为库引入Go程序。我这边使用了brew安装了vegeta，整个测试过程是使用Go编写了一个脚本来进行测试，具体可以参考[代码片段](https://gist.github.com/ISheepp/90cbe89c78d855e22185dc5703c77803)

我并没有使用库的形式来引入，而是使用`exec.Command()`函数来执行命令行。

具体使用到的vegeta命令

1. attack: 调用API的命令，rate代表每秒调用次数，duration表示调用几秒，body指的是post请求的请求体，name是指为这次测试命名「可不填」，tee是生成bin原始文件「类似raw格式照片，可以用bin转换成很多别的格式」，report是生成报告，这里是在命令行输出。

```sh
echo "POST http://172.17.1.36:30898/hello" | vegeta attack -rate=2000 -duration=1s -body=query.json -timeout=0 -name=hello | tee ./result/results-null.bin | vegeta report
```

2. 生成报告文件，这里是根据bin原始文件生成txt文件

```sh
vegeta report -type=text results-query.bin > repost.txt
```

3. 生成分析图表，使用plot可以生成可交互的图表，需要将多个结果合并到一个图表的时候需要注意，在使用第一个命令的时候务必加上-name参数为其命名。

```sh
vegeta plot results-null.bin results-sleep.bin results-query.bin > plot-all.html
```

![image](./attachments/QmfUgVAmUTEmXt7Y7oUy12B2RKBADMNzxDM7wpr8PfB7cm)


## 测试场景

使用Java和Go编写两个REST服务，分别测试3个API，在k8s中单副本和5副本的情况。API信息如下：
1. 直接返回
2. sleep 2秒再返回
3. 查询Elasticsearch的10000条数据，每条数据500字节

Elasticsearch集群信息
+ 节点数量：2
+ 版本：7.4.1
+ CPU：8个Intel(R) Xeon(R) Silver 4114 CPU @ 2.20GHz，每个1 core
+ 内存：31G

Kubernetes信息
+ 版本：1.16.15
+ 节点数量：7「1 master, 6 worker」


指定Deployment调度到同一个节点，两个Deploymnet都分配了2G的内存

## 测试步骤

将Go脚本打包好后，在同目录下创建配置文件`config.ini`

```ini
[address]
null = "POST http://172.17.1.36:30898/hello"
sleep = "POST http://172.17.1.36:30898/sleep"
query = "POST http://172.17.1.36:30898/es"
[param]
rate = 2000
```

其中address指的是要调用的API地址和方法，rate指的是每秒调用的次数「我这里是只调用了1s」

执行脚本，等待……

![image](./attachments/QmXhwAMxjKz6SuoRcd9cLVnNewhKMDcz4puNVfWn3uMfdT)



## 测试结果

每个API生成了3个文件

1. results-*.bin文件：测试原始文件
2. report-*.txt文件：报告文件
3. plot-*.html文件：单个结果图表文件

首先是Java

1. 空接口

```sh
Requests      [total, rate, throughput]         2000, 2004.21, 1996.25
Duration      [total, attack, wait]             1.002s, 997.9ms, 3.98ms
Latencies     [min, mean, 50, 90, 95, 99, max]  2.114ms, 28.492ms, 11.283ms, 77.584ms, 90.305ms, 111.482ms, 150.836ms
Bytes In      [total, mean]                     10000, 5.00
Bytes Out     [total, mean]                     0, 0.00
Success       [ratio]                           100.00%
Status Codes  [code:count]                      200:2000
```
字段解释
Requests（请求数）：

+ total 表示总请求数，这里是 2000。
+ rate 表示每秒发起的请求数，这里是 2004.21。
+ throughput 表示每秒成功完成的请求数，这里是 1996.25。

Duration（持续时间）：

+ total 表示测试总时间，这里是 1.002 秒。
+ attack 表示攻击时间，即实际发送请求的时间，这里是 997.9 毫秒。
+ wait 表示在攻击期间所有请求的总等待时间，这里是 3.98 毫秒。


Latencies（响应时间）：

+ min 表示最小响应时间
+ mean 表示平均响应时间
+ 50, 90, 95, 99 表示[分位数](https://juejin.cn/post/6915022688746471432)「不是很懂这个指标表示的是什么」，分别是 50%，90%，95%，99% 的响应时间
+ max 表示最大响应时间

Bytes In（接收字节数）：

+ total 表示所有请求的总接收字节数
+ mean 表示每个请求的平均接收字节数

Bytes Out（发送字节数）：

+ total 表示所有请求的总发送字节数
+ mean 表示每个请求的平均发送字节数

Success（成功率）：

+ ratio 表示成功的请求占总请求的百分比

Status Codes（状态码）：

+ code:count 表示每个状态码出现的次数。

当我把3个结果合并在一起的时候，响应时间基本上是一个线性增长，且查询时间最后涨到了3m多

![vegeta-plot (1)](./attachments/QmPgbCjAtxgCAm2uHNxDY1ZAop5P27hxzTMSHDxuERja44)

2. Go

sleep和空接口都相当稳定，查询接口的响应时长也比Java好了很多

![vegeta-plot (2)](./attachments/QmTHpybLtRNEpvrX3DdX2RWDiws2cAgyZAt3U4zZEw3aJy)


接下里是把两个服务都添加到5个副本之后的结果

1. Java

只能说sleep接口的稳定性得到了提升，不会线性增长，但是查询接口的响应时间还是有点离谱

![vegeta-plot (4)](./attachments/Qmc3HwMoofVjaibeSfJLzpkmeu7j3FLvJUdC7eD2obkufo)



2. Go

查询接口的响应时长并没有太大的提升

![vegeta-plot (3)](./attachments/QmaaLHCnYKdmZM5yLqBghyo7kGjC4oUAYM62rnJA66oGgv)


## 总结

对于查询接口而言，可能瓶颈会出现在Elasticsearch端，这里先不测试了。

从图表来看，Go处理并发能力确实略胜一筹。

vegeta这个工具还有很多玩法没有去使用，相对于Jmeter，虽然命令行不是很友好，但是生成的结果相当的直观。
