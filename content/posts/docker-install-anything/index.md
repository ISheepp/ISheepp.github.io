---
title: "Docker安装各种环境"
date: "2021-04-18T09:49:00.000Z"
slug: "docker-install-anything"
summary: "使用docker安装一些中间件"
tags: ["tech"]
draft: false
---

> 由[Portainer](https://www.portainer.io/)管理容器

## 安装Redis
### 首先去官网下载redis.conf文件并且编辑

修改redis.conf配置文件：
 主要配置的如下：
```shell
 bind 127.0.0.1 #注释掉这部分，使redis可以外部访问
 daemonize no #用守护线程的方式启动（设置为yes会导致redis一启动就马上停止）
 requirepass 你的密码#给redis设置密码
 appendonly yes#redis持久化　　默认是no
 tcp-keepalive 300 #防止出现远程主机强迫关闭了一个现有的连接的错误 默认是300
```
### 创建本地与docker映射的目录，即本地存放的位置
创建本地存放redis的位置;

 可以自定义，因为我的docker的一些配置文件都是存放在/mydata目录下面的，所以我依然在/mydata目录下创建一个redis目录，这样是为了方便后期管理。
`mkdir /data/redis`
`mkdir /data/redis/data`
把配置文件拷贝到刚才创建好的文件里
### 文件授权
`chmod 777 redis.conf`
### 启动redis
```shell
docker run -p 6379:6379 --name redis -v /mydata/redis/redis.conf:/etc/redis/redis.conf  -v /mydata/redis/data:/data -d redis redis-server /etc/redis/redis.conf --appendonly yes
```
参数解释：
>  -p 6379:6379:把容器内的6379端口映射到宿主机6379端口
 -v /data/redis/redis.conf:/etc/redis/redis.conf：把宿主机配置好的redis.conf放到容器内的这个位置中
 -v /data/redis/data:/data：把redis持久化的数据在宿主机内显示，做数据备份
 redis-server /etc/redis/redis.conf：这个是关键配置，让redis不是无配置启动，而是按照这个redis.conf的配置启动
 –appendonly yes：redis启动后数据持久化
 


## 安装Elasticsearch7.9.3

> Kibana选择了安装在本地（不想吃服务器资源）

1. 拉取镜像

```shell
docker pull elasticsearch:7.9.3
```

2. 创建所需文件夹和文件

```shell
mkdir -p /mydata/elasticsearch/config
mkdir -p /mydata/elasticsearch/data
echo "http.host: 0.0.0.0">>/mydata/elasticsearch/config/elasticsearch.yml
```

3. 文件夹赋权限

```shell
chmod -R 777 /mydata/elasticsearch/
```

4. 创建并启动elasticsearch容器

```shell
docker run --name elasticsearch -p 9200:9200 \
 -p 9300:9300 \
 -e "discovery.type=single-node" \
 -e ES_JAVA_OPTS="-Xms64m -Xmx128m" \
 -v /mydata/elasticsearch/config/elasticsearch.yml:/usr/share/elasticsearch/config/elasticsearch.yml \
 -v /mydata/elasticsearch/data:/usr/share/elasticsearch/data \
 -v /mydata/elasticsearch/plugins:/usr/share/elasticsearch/plugins \
 -d elasticsearch:7.9.3
```

5. 设置容器自启动

```shell
docker update elasticsearch --restart=always
```

6. 安装IK中文分词器

```shell
cd /mydata/elasticsearch/plugins/
wget https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v7.9.3/elasticsearch-analysis-ik-7.9.3.zip
mkdir ik
unzip -d ik/ elasticsearch-analysis-ik-7.9.3.zip 
docker restart elasticsearch
```

7. 放行端口号

```shell
firewall-cmd --zone=public --add-port=9200/tcp --permanent
systemctl  restart firewalld.service
```

## 安装Kafka和Zookeeper

[掘金教程](https://juejin.cn/post/6844903829624848398)
安装kafka
```shell
docker run  -d --name kafka -p 9092:9092 -e KAFKA_BROKER_ID=0 -e KAFKA_ZOOKEEPER_CONNECT=服务器ip:2181 -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://服务器ip:9092 -e KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092 -e KAFKA_HEAP_OPTS="-Xmx256M -Xms128M" -t wurstmeister/kafka
```
