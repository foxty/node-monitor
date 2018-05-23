# Master
FROM python:2-slim
LABEL maintainer="foxty@163.com"
ENV APP_BASE=/opt/node-monitor
WORKDIR /opt/node-monitor

COPY requirements.txt ./
COPY nodemonitor ./nodemonitor
COPY web ./web

RUN pip install -r requirements.txt
RUN chmod +x ./nodemonitor/master_cli.py

EXPOSE 7890 8080
CMD [ "python", "./nodemonitor/master_cli.py", "-m" ]