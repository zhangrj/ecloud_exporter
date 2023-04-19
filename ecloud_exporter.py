#!/usr/bin/python

import argparse
import multiprocessing
from datetime import datetime, timedelta

from ecloudsdkcore.config.config import Config
from ecloudsdkmonitor.v1.client import Client
from ecloudsdkmonitor.v1.model import *
from flask import Flask, make_response, request

# 创建应用实例
app = Flask(__name__)


class EcloudMonitor:
    def __init__(self):
        pass
    # 默认响应超时时间为120秒
    # 默认连接超时时间为3秒

    @staticmethod
    def create_client(access_key, access_secret, pool_id, read_timeout=120, connect_timeout=3) -> Client:
        connect_config = Config(
            access_key=access_key,
            access_secret=access_secret,
            pool_id=pool_id,
            read_timeout=read_timeout,
            connect_timeout=connect_timeout
        )
        return Client(connect_config)

    @staticmethod
    def get_resource(client: Client, product_type) -> list:
        request = ListResourceRequest()
        list_resource_query = ListResourceQuery()
        # 设为较大值，避免结果分页
        list_resource_query.page_size = 100000
        list_resource_query.product_type = product_type
        request.list_resource_query = list_resource_query
        response = client.list_resource(request)
        if response.code == "000000" and response.entity is not None:
            return response.entity.content
        else:
            print("Get {} resource error, response: {}".format(
                product_type, response))
            return []

    @staticmethod
    def get_metric(client: Client, product_type) -> list:
        request = ListMetricIndicatorRequest()
        list_metric_indicator_query = ListMetricIndicatorQuery()
        list_metric_indicator_query.product_type = product_type
        request.list_metric_indicator_query = list_metric_indicator_query
        response = client.list_metric_indicator(request)
        if response.code == "000000" and response.entity is not None:
            return response.entity
        else:
            print("Get {} metric error, response: {}".format(
                product_type, response))
            return []

    @staticmethod
    def get_metric_node(client: Client, resource_id, metric_name) -> list:
        request = ListMetricNodeRequest()
        list_metric_node_query = ListMetricNodeQuery()
        list_metric_node_query.resource_id = resource_id
        list_metric_node_query.metric_name = metric_name
        request.list_metric_node_query = list_metric_node_query
        response = client.list_metric_node(request)
        if response.code == "000000" and response.entity is not None:
            return response.entity
        else:
            print("Get resource {} metric node error, response: {}".format(
                resource_id, response))
            return []

    @staticmethod
    def get_latest_performance(access_key, access_secret, pool_id, product_type, resource_id, resource_name) -> str:
        client = EcloudMonitor.create_client(
            access_key, access_secret, pool_id)
        request = FetchPerformanceRequest()
        fetch_performance_body = FetchPerformanceBody()
        metrics = []
        metric_list = EcloudMonitor.get_metric(client, product_type)
        if len(metric_list) == 0:
            return []
        else:
            for metric in metric_list:
                if metric.childnode == True:
                    metric_node_list = EcloudMonitor.get_metric_node(
                        client, resource_id, metric.metric_name)
                    for metric_node in metric_node_list:
                        metrics.append(FetchPerformanceRequestMetrics(
                            metric_name=metric.metric_name,
                            metric_node_name=metric_node)
                        )
                else:
                    metrics.append(FetchPerformanceRequestMetrics(
                        metric_name=metric.metric_name)
                    )
            fetch_performance_body.resource_id = resource_id
            end_time = datetime.now()
            if product_type == "floatingip" or product_type == "ipv6":
                # 公网IP数据采集上报有10分钟左右的延迟
                start_time = end_time - timedelta(minutes=12)
            else:
                # 移动云云监控取值周期大部分为5min，此处查询范围为6min以确保可得到最新的1个数据点
                start_time = end_time - timedelta(minutes=6)
            fetch_performance_body.start_time = start_time.strftime(
                "%Y-%m-%d %H:%M:%S")
            fetch_performance_body.end_time = end_time.strftime(
                "%Y-%m-%d %H:%M:%S")
            fetch_performance_body.metrics = metrics
            fetch_performance_body.product_type = product_type
            request.fetch_performance_body = fetch_performance_body
            response = client.fetch_performance(request)
            if response.code == "000000" and response.entity is not None:
                return EcloudMonitor.convert_to_prometheus_format(resource_id, resource_name, product_type, response.entity)
            else:
                print("Get {} resource {} latest performance error, response: {}".format(
                    product_type, resource_id, response))
                return ''

    @staticmethod
    def convert_to_prometheus_format(resource_id, resource_name, product_type, performance_list) -> str:
        """
        [{'avg_value': 1298.84375,
        'childnode': True,
        'datapoints': [[1297.775, 1681354500], [1299.9125, 1681354800]],
        'granularity': '5min',
        'max_value': 1299.9125,
        'metric_items': None,
        'metric_name': 'mysql_bytes_received',
        'metric_name_cn': '每秒接收字节数',
        'min_value': 1297.775,
        'polymerize_type': None,
        'resource_id': 'bb8e04e8d0ee43e0bb7272c20a1fa3be',
        'selected_metric_item': 'abb8e04e8d0-8fda201-0',
        'unit': 'Byte/s'}]
        ---convert to---->
        # HELP mysql_bytes_received mysql_bytes_received, Byte/s.
        # TYPE mysql_bytes_received gauge
        mysql_bytes_received{selected_metric_item="abb8e04e8d0-8fda201-0",resource_id="resource_id",resource_name="resource_name",product_type="product_type"} 1298.84375
        """
        prometheus_format_content = ''
        for performance in performance_list:
            if performance.childnode == True:
                prometheus_format_content += f'# HELP {performance.metric_name} {performance.metric_name_cn}, {performance.unit}.\n# TYPE {performance.metric_name} gauge\n{performance.metric_name}{{selected_metric_item="{performance.selected_metric_item}",resource_id="{resource_id}",resource_name="{resource_name}",product_type="{product_type}"}} {performance.max_value}\n'
            elif performance.childnode == False:
                prometheus_format_content += f'# HELP {performance.metric_name} {performance.metric_name_cn}, {performance.unit}.\n# TYPE {performance.metric_name} gauge\n{performance.metric_name}{{resource_id="{resource_id}",resource_name="{resource_name}",product_type="{product_type}"}} {performance.max_value}\n'
        return prometheus_format_content


@app.route("/")
@app.route("/probe")
def EcloudCollector():
    access_key = request.args.get('access_key')
    access_secret = request.args.get('access_secret')
    pool_id = request.args.get('pool_id')
    product_type = request.args.get('product_type')
    client = EcloudMonitor.create_client(access_key, access_secret, pool_id)
    query_pool = multiprocessing.Pool()
    param_list = []
    for resource in EcloudMonitor.get_resource(client, product_type):
        resource_name = resource.resource_name
        # 公网IP类型的资源ID使用IP形式，形如： 192-168-1-1
        # 共享带宽的资源ID需要使用该共享带宽绑定的IP，形如{192-168-1-1,192-168-1-2}，因SDK不返回ipList，暂不支持该产品监控
        if product_type == 'floatingip':
            resource_id = resource_name.replace('.', '-')
        else:
            resource_id = resource.resource_id
        param_list.append((access_key, access_secret, pool_id,
                          product_type, resource_id, resource_name))

    prometheus_format_content_list = query_pool.starmap(
        EcloudMonitor.get_latest_performance, param_list)
    query_pool.close()
    query_pool.join()
    prometheus_format_content = ''
    for content in prometheus_format_content_list:
        prometheus_format_content += content
    response = make_response(prometheus_format_content)
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Prometheus Exporter for China Mobile Cloud. Please run this script with python3.')
    parser.add_argument('-l', '--listenport', default=9199,
                        help='Port which the exporter listening on (default: %(default)s)')

    args = parser.parse_args()
    port = args.listenport

    app.run(host='0.0.0.0', port=int(port))
