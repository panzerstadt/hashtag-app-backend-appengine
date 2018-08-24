FROM tiangolo/uwsgi-nginx-flask:python3.6
MAINTAINER TLQ, https://liquntang.wordpress.com/

COPY ./app /app

RUN pip install -r requirements.txt
ENV LANG C.UTF-8
CMD python main.py
