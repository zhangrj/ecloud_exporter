FROM python:2
LABEL maintainer="zhangrongjie"
WORKDIR /usr/src/app
EXPOSE 9199
COPY cmecloud-python-sdk-core-1.0.0.tar.gz ./
COPY ecloud_exporter.py ./
RUN pip install --no-cache-dir pysocks \
    && pip install --no-cache-dir pytz \
    && pip install --no-cache-dir prometheus_client \ 
    && pip install --no-cache-dir cmecloud-python-sdk-core-1.0.0.tar.gz
ENTRYPOINT [ "python", "./ecloud_exporter.py" ]