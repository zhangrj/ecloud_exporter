#!/usr/bin/python

import argparse
from datetime import datetime, timedelta

from ecloudsdkcore.config.config import Config
from ecloudsdkmonitor.v1.client import Client
from ecloudsdkmonitor.v1.model import *
from flask import Flask, make_response, request

# 创建应用实例
app = Flask(__name__)

class EcloudMonitor(object):
    # 默认响应超时时间为120秒
    # 默认连接超时时间为3秒
    def __init__(self, access_key, access_secret, pool_id, read_timeout="120", connect_timeout="3"):
        self.client = None
        self.access_key = access_key
        self.access_secret = access_secret
        self.pool_id = pool_id
        if read_timeout is not None:
            self.read_timeout = read_timeout
        if connect_timeout is not None:
            self.connect_timeout = connect_timeout

    def create_client(self):
        """
        ecloudsdkmonitor-1.0.5.tar.gz client.py 301-305行
        _request_timeout = ()
        if self.config.connect_timeout is not None:
            _request_timeout[0] = self.config.connect_timeout
        if self.config.read_timeout is not None:
            _request_timeout[1] = self.config.read_timeout
        此处尝试修改元组元素，会导致报错，因此这两个参数暂时无法指定
        --------------------------
        20230417-在与移动云反馈后，此处的问题已经修复，重新安装ecloudsdkcore、ecloudsdkmonitor即可，版本号不变
        """
        connect_config = Config(
            access_key = self.access_key,
            access_secret = self.access_secret,
            pool_id = self.pool_id,
            # read_timeout = self.read_timeout,
            # connect_timeout = self.connect_timeout
        )
        self.client = Client(connect_config)   

    def get_resource(self, product_type):
        request = ListResourceRequest()
        list_resource_query = ListResourceQuery()
        # 设为较大值，避免结果分页
        list_resource_query.page_size = 100000
        list_resource_query.product_type = product_type
        request.list_resource_query = list_resource_query
        response =  self.client.list_resource(request)
        if response.code == "000000" and response.entity is not None:
            # list
            return response.entity.content
        else:
            print("Get {} resource error, response: {}".format(product_type, response))
            return []

    def get_metric(self, product_type):
        request = ListMetricIndicatorRequest()
        list_metric_indicator_query = ListMetricIndicatorQuery()
        list_metric_indicator_query.product_type = product_type
        request.list_metric_indicator_query = list_metric_indicator_query
        response = self.client.list_metric_indicator(request)
        if response.code == "000000" and response.entity is not None:
            # list
            return response.entity
        else:
            print("Get {} metric error, response: {}".format(product_type, response))
            return []

    def get_metric_node(self, resource_id, metric_name):
        request = ListMetricNodeRequest()
        list_metric_node_query = ListMetricNodeQuery()
        list_metric_node_query.resource_id = resource_id
        list_metric_node_query.metric_name = metric_name
        request.list_metric_node_query = list_metric_node_query
        response = self.client.list_metric_node(request)
        if response.code == "000000" and response.entity is not None:
            # list
            return response.entity
        else:
            print("Get resource {} metric node error, response: {}".format(resource_id, response))
            return []

    def get_latest_performance(self, product_type, resource_id):
        request = FetchPerformanceRequest()
        fetch_performance_body = FetchPerformanceBody()
        metrics = []
        metric_list = self.get_metric(product_type)
        if len(metric_list) == 0:
            return []
        else:
            for metric in metric_list:
                if metric.childnode == True:
                    metric_node_list = self.get_metric_node(resource_id, metric.metric_name)
                    for metric_node in metric_node_list:
                        metrics.append(FetchPerformanceRequestMetrics(
                            metric_name = metric.metric_name,
                            metric_node_name = metric_node)
                        )
                else:
                    metrics.append(FetchPerformanceRequestMetrics(
                        metric_name = metric.metric_name)
                    )
            fetch_performance_body.resource_id = resource_id
            # end_time = datetime.now(pytz.timezone("Asia/Shanghai"))
            end_time = datetime.now()
            # 移动云云监控取值周期为5min，此处查询范围为6min以确保只得到最新的1个数据点
            start_time = end_time - timedelta(minutes = 6)
            fetch_performance_body.start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
            fetch_performance_body.end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")
            fetch_performance_body.metrics = metrics
            fetch_performance_body.product_type = product_type
            request.fetch_performance_body = fetch_performance_body
            response = self.client.fetch_performance(request)
            if response.code == "000000" and response.entity is not None:
                # list
                return response.entity
            else:
                print("Get {} resource {} latest performance error, response: {}".format(product_type, resource_id, response))
                return []

    @staticmethod
    def convert_to_prometheus_format(resource_id, resource_name, product_type, performance_list):
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
    # http://localhost:8000/probe?access_key=xx&access_secret=xx&pool_id=CIDC-RP-31&product_type=mysql
    access_key = request.args.get('access_key')
    access_secret = request.args.get('access_secret')
    pool_id = request.args.get('pool_id')
    product_type = request.args.get('product_type')
    ecloudmonitor = EcloudMonitor(access_key, access_secret, pool_id)
    ecloudmonitor.create_client()
    prometheus_format_content = ''
    for resource in ecloudmonitor.get_resource(product_type):
        resource_id = resource.resource_id
        resource_name = resource.resource_name
        performance_list = ecloudmonitor.get_latest_performance(product_type, resource_id)
        prometheus_format_content += ecloudmonitor.convert_to_prometheus_format(resource_id, resource_name, product_type, performance_list)
    response = make_response(prometheus_format_content)
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prometheus Exporter for China Mobile Cloud. Please run this script with python3.')
    parser.add_argument('-l', '--listenport', default=9199, help='Port which the exporter listening on (default: %(default)s)')

    args = parser.parse_args()
    port = args.listenport

    app.run(debug = True, host = '0.0.0.0', port = int(port))
