# ecloud_exporter V0.2.0
移动云云监控数据导出
## 使用方法
### 直接运行ecloud_exporter.py
注意：需使用python3

安装必要依赖：
```shell
pip config set global.index-url https://ecloud.10086.cn/api/query/developer/nexus/repository/python-sdk/simple
pip install ecloudsdkmonitor==1.0.5
pip install flask
```
```
python ecloud_exporter.py -h
usage: ecloud_exporter.py [-h] [-l LISTENPORT]

Prometheus Exporter for China Mobile Cloud. Please run this script with python3.

optional arguments:
  -h, --help            show this help message and exit
  -l LISTENPORT, --listenport LISTENPORT
                        Port which the exporter listening on (default: 9199)
```
例如：
```
python ecloud_exporter.py -l 9199
```
### docker运行
```
docker run -d -p 9199:9199 -e TZ=Asia/Shanghai registry.cn-hangzhou.aliyuncs.com/zhangrongjie/ecloud_exporter:0.2.0
```
### kubernetes运行
修改install_in_kubernetes.yaml文件中的参数
```
kubectl apply -f install_in_kubernetes.yaml
```
## Prometheus Configuration
exporter采用multi-target模式（类似blackbox exporter），示例配置如下：
```yaml
  - job_name: ecloud
    metrics_path: /probe
    scrape_interval: 1m
    scrape_timeout: 20s
    file_sd_configs:
    - refresh_interval: 1m
      files:
      - ecloud_targets.yaml
    relabel_configs:
    - source_labels: [__address__]
      target_label: __param_product_type
    - source_labels: [access_key]
      target_label: __param_access_key
    - source_labels: [access_secret]
      target_label: __param_access_secret
    - source_labels: [pool_id]
      target_label: __param_pool_id
    - regex: access_key|access_secret
      action: labeldrop
    - target_label: __address__
      replacement: localhost:9199  # The Ecloud exporter's real hostname:port.
```
ecloud_targets.yaml示例如下：
```yaml
- targets:
  - mysql # 需要监控的产品类型
  - ekafka # 需要监控的产品类型
  labels:
    access_key: xx # 必填
    access_secret: xx # 必填
    pool_id: xx # 必填
    xx: xx
```
其中`target`请填写产品类型，默认采集该产品所有资源的数据，产品类型可通过移动云OpenApi获取 https://ecloud.10086.cn/op-oneapi-static/#/platform/52/52?apiId=6989 ，为返回结果中的`productType`字段。

`access_key`、`access_secret`获取方法：https://ecloud.10086.cn/op-help-center/doc/article/49739

`pool_id`获取方法：https://ecloud.10086.cn/op-help-center/doc/article/54462

## 指标释义
详见：https://ecloud.10086.cn/op-help-center/doc/article/51690

暂不支持对象存储专属资源池：https://ecloud.10086.cn/op-help-center/doc/article/47731