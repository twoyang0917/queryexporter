FROM python:3-alpine
LABEL Author="twoyang_0917@qq.com"

RUN mkdir /queryexporter
ADD . /queryexporter/
RUN pip3 install -r /queryexporter/requirements.txt

CMD ["python3", "/queryexporter/queryexporter.py"]
