#!/usr/bin/python
# encoding:utf-8

from ecloudsdkcore import EcloudClient, EcloudRequest
from ecloudsdkcore.acs_exception.exceptions import ServerException, ClientException
import traceback
import json
import sys
import ast
from datetime import datetime, timedelta
import pytz
import time
from prometheus_client import Gauge, start_http_server

# 移动云api返回值不符合python规范, 需转换
global false, true, null
false = False
true = True
null = None

AccessKey = sys.argv[1]
Secretkey = sys.argv[2]
RecourceSet = []
for arg in sys.argv[3:]:
    resourceInfo = {}
    resourceInfo["Pool-Id"] = arg.split(":")[0]
    resourceInfo["productType"] = arg.split(":")[1]
    RecourceSet.append(resourceInfo)

LabelsSet = {"vm": ["resourceId", "resourceName", "imageOsType", "poolId", "privateIp", "childnode"],
             "onest": ["resourceId", "resourceName", "childnode"]}

client = EcloudClient.AcsClient(AccessKey, Secretkey)


# 根据产品类型和资源池查询当前用户下的资源列表
def get_resourceList(pool_id, product_type):
    request = EcloudRequest.AcsRequest(
        "GET", "/api/edw/openapi/v1/dawn/monitor/resources")
    request.add_query_param("productType", product_type)
    request.add_query_param("pageSize", 100000)
    request.add_header("Pool-Id", pool_id)
    try:
        response = client.do_action(request)
        if json.loads(response["response_txt"])["code"] == "000000" and json.loads(response["response_txt"])["entity"]["total"] > 0:
            return(json.loads(response["response_txt"])["entity"]["content"])
        else:
            print("no resource found in {}/{}(Pool-Id/productType or api system error, return [])".format(pool_id, product_type))
            return []
    except ServerException as e:
        print(e)
        traceback.print_stack()
    except ClientException as e:
        print(e)
        traceback.print_stack()


# 根据产品类型和资源池查询产品性能指标
def get_metricList(pool_id, product_type):
    request = EcloudRequest.AcsRequest(
        "GET", "/api/edw/openapi/v1/dawn/monitor/metricindicators")
    request.add_header("Pool-Id", pool_id)
    request.add_query_param("productType", product_type)
    try:
        response = client.do_action(request)
        return(json.loads(response["response_txt"])["entity"])
    except ServerException as e:
        print(e)
        traceback.print_stack()
    except ClientException as e:
        print(e)
        traceback.print_stack()


# 查询性能指标子节点名称, 例如磁盘使用率的子节点名称为["/data","/"]
def get_metric_childnodeList(pool_id, metric_name, resource_id):
    request = EcloudRequest.AcsRequest(
        "GET", "/api/edw/openapi/v1/dawn/monitor/metricnode")
    request.add_header("Pool-Id", pool_id)
    request.add_query_param("metricName", metric_name)
    request.add_query_param("resourceId", resource_id)
    try:
        response = client.do_action(request)
        return(json.loads(response["response_txt"])["entity"])
    except ServerException as e:
        print(e)
        traceback.print_stack()
    except ClientException as e:
        print(e)
        traceback.print_stack()


# 查询资源对应指标的最新值
def get_metric_latestData(pool_id, metric_name, metric_nodeName, product_type, resource_id):
    request = EcloudRequest.AcsRequest(
        "GET", "/api/edw/openapi/v1/dawn/monitor/fetch")
    request.add_header("Pool-Id", pool_id)
    end_time = datetime.now(pytz.timezone("Asia/Shanghai"))
    start_time = end_time - timedelta(minutes=10)
    request.add_body_param(
        "startTime", start_time.strftime("%Y-%m-%d %H:%M:%S"))
    request.add_body_param("endTime", end_time.strftime("%Y-%m-%d %H:%M:%S"))
    request.add_body_param(
        "metrics", [{"metricName": metric_name, "metricNodeName": metric_nodeName}])
    request.add_body_param("productType", product_type)
    request.add_body_param("resourceId", resource_id)
    try:
        response = client.do_action(request)
        if len(json.loads(response["response_txt"])["entity"]) > 0 and len(json.loads(response["response_txt"])["entity"][0]["datapoints"]) > 0:
            return(json.loads(response["response_txt"])["entity"][0]["datapoints"][-1][0])
        else:
            print("no data found for {}/{}/{}(resourceId/metricName/metricNodeName),return 0".format(
                resource_id, metric_name, metric_nodeName))
            return 0
    except ServerException as e:
        print(e)
        traceback.print_stack()
    except ClientException as e:
        print(e)
        traceback.print_stack()


# 查询资源对应指标集合的最新值，待写
def get_metricSet_latestData(pool_id, metricSet, product_type, resource_id):
    pass


if __name__ == "__main__":
    # 初始化指标
    for resourceInfo in RecourceSet:
        resourceList = get_resourceList(
            resourceInfo["Pool-Id"], resourceInfo["productType"])
        if len(resourceList) == 0:
            sys.exit()
        metricList = get_metricList(
            resourceInfo["Pool-Id"], resourceInfo["productType"])
        LabelsSetList = LabelsSet[resourceInfo["productType"]]
        for metric in metricList:
            exec("{} = Gauge('{}', u'{}', {})".format(metric["metricName"].replace(".", "_").replace("-", "_"), metric["metricName"].replace(
                ".", "_").replace("-", "_"), metric["metricNameCn"].encode('unicode-escape').decode('string_escape'), LabelsSetList))
    start_http_server(9199)
    # 循环更新指标值
    while True:
        for resourceInfo in RecourceSet:
            resourceList = get_resourceList(
                resourceInfo["Pool-Id"], resourceInfo["productType"])
            if len(resourceList) == 0:
                continue
            metricList = get_metricList(
                resourceInfo["Pool-Id"], resourceInfo["productType"])
            LabelsSetList = LabelsSet[resourceInfo["productType"]]
            # 指标及标签赋值
            for metric in metricList:
                for resource in resourceList:
                    if metric["childnode"] == True:
                        childnodeList = get_metric_childnodeList(
                            resourceInfo["Pool-Id"], metric["metricName"], resource["resourceId"])
                        labelsValueList = []
                        for i in range(len(LabelsSetList) - 1):
                            labelsValueList.append(resource[LabelsSetList[i]])
                        for childnode in childnodeList:
                            labelsValueList.append(childnode)
                            metric_latestData = get_metric_latestData(
                                resourceInfo["Pool-Id"], metric["metricName"], childnode, resourceInfo["productType"], resource["resourceId"])
                            exec("{}.labels{}.set({})".format(metric["metricName"].replace(
                                ".", "_").replace("-", "_"), tuple(labelsValueList), metric_latestData))
                            labelsValueList.pop()
                    else:
                        labelsValueList = []
                        for i in range(len(LabelsSetList) - 1):
                            labelsValueList.append(resource[LabelsSetList[i]])
                        labelsValueList.append("")
                        metric_latestData = get_metric_latestData(
                            resourceInfo["Pool-Id"], metric["metricName"], "", resourceInfo["productType"], resource["resourceId"])
                        exec("{}.labels{}.set({})".format(metric["metricName"].replace(
                            ".", "_").replace("-", "_"), tuple(labelsValueList), metric_latestData))
        time.sleep(60)
