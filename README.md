# ecloud_exporter
通过api导出账号下各类资源的监控数据.

prometheus端点: `http://${IP}:9199/metrics`.
## 使用方法
### 直接运行ecloud_exporter.py
```
python ecloud_exporter.py "AccessKey" "Secretkey" "Pool-Id1:productType1" "Pool-Id2:productType2" ...
```
其中AccessKey、Secretkey通过移动云控制台"AccessKey管理"获取, "Pool-Id1:productType1"表示资源池ID:产品类型.

资源池Pool-Id: <https://ecloud.10086.cn/op-help-center/doc/article/47731>, 全局类产品统一使用CIDC-RP-25.

产品类型表: <https://ecloud.10086.cn/op-help-center/doc/article/47792>
### docker运行
```
docker run -dP -e TZ=Asia/Shanghai zhangrongjie/ecloud_exporter:v0.1.0-beta1 AccessKey Secretkey Pool-Id1:productType1 Pool-Id2:productType2 ...
```
### kubernetes运行
修改install_in_kubernetes.yaml文件中的参数
```
kubectl apply -f install_in_kubernetes.yaml
```
## 移动云api python sdk的一些问题
下载地址: <https://ecloud.10086.cn/op-help-center/doc/article/24286>
### bug1-代码错误
EcloudRequest.py第17行
```python
    def __int__(self, method_type, server_path):
```
需修改为
```python
    def __init__(self, method_type, server_path):
```
### bug2-api返回内容中的中文显示为乱码
EcloudClient.py第153行
```python
        acs_response = request(method_type, url, headers=headers, json=payload, params=query_string, timeout=self._timeout)
```
需修改为
```python
        acs_response = request(method_type, url, headers=headers, json=payload, params=query_string, timeout=self._timeout)
        acs_response.encoding='utf-8'
```
**本项目中提供的sdk是修改过的, 如需测试请使用本项目中的sdk**
### 查询资源列表api偶现返回空值
### 签名算法
签名算法中使用了时间参数, 因此运行程序的环境时区必须为Asia/Shanghai, 否则会报错
```json
{
    "errorMessage":"Invalid parameter Timestamp ",
    "errorCode":"INVALID_PARAMETER",
    "state":"ERROR",
    "requestId":"reqId-7a62eb21f2b19621250ca-8749d9a9-9"
}
```
## 后续改进方向
- python3适配: 目前只支持python2
- 降低程序复杂度
- 参数校验
- 异常处理
- 多线程处理: 目前大量指标处理慢, 目前为了数据处理方便, 每次请求只获取一个指标点数据，但api是支持一次性获取多个指标数据的.
- 支持资源类型拓展: 目前只支持了云主机ECS和对象存储onest, 拓展支持只需要拓展程序中的LabelsSet变量即可, 通过该变量指定各资源类型所需指标标签(参考: <https://ecloud.10086.cn/op-help-center/doc/article/53616>, 应选取值不变的字段作为标签). 因此api返回的内容中包含值会变化的字段, 如通过返回字段自动获取标签集, 会导致监控中的数据不连续(因为标签值不断变化).
- 日志打印
