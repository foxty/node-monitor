# Master
FROM python:2-slim
LABEL maintainer="foxty@163.com"
ENV APP_BASE=/opt/node-monitor
WORKDIR /opt/node-monitor

COPY requirements.txt ./
COPY conf ./conf
COPY nodemonitor ./nodemonitor
COPY web/dist ./web/dist

RUN pip install -r requirements.txt
RUN chmod +x ./nodemonitor/master_cli.py

EXPOSE 30079 30080
CMD [ "python", "./nodemonitor/master_cli.py", "-m" ]