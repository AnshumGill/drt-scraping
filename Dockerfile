FROM python:3.9-slim-buster
WORKDIR /flask
RUN apt-get update
RUN apt-get install software-properties-common -y
RUN add-apt-repository ppa:alex-p/tesseract-ocr-devel -y
# Required for mysqlclient pip package
RUN apt-get install -y gcc libmariadb-dev tesseract-ocr
COPY app/ .
RUN pip3 install -r requirements.txt
# Required in unix based systems
RUN pip3 install cryptography
