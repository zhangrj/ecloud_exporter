FROM python:3.9-slim
LABEL maintainer="zhangrongjie"
WORKDIR /usr/src/app
EXPOSE 9199
COPY ecloud_exporter.py ./
RUN pip config set global.index-url https://ecloud.10086.cn/api/query/developer/nexus/repository/python-sdk/simple \
    && pip install --no-cache-dir ecloudsdkmonitor==1.0.5 \
    && pip install --no-cache-dir flask
ENTRYPOINT [ "python", "./ecloud_exporter.py" ]