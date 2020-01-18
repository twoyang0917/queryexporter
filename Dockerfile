FROM python:3-alpine
LABEL Author="twoyang_0917@qq.com"

RUN mkdir /queryexporter
ADD . /queryexporter/
RUN pip3 install --no-cache-dir -r /queryexporter/requirements.txt -i https://mirrors.ustc.edu.cn/pypi/web/simple

CMD ["python3", "/queryexporter/queryexporter.py"]
