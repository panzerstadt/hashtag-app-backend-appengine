FROM tiangolo/uwsgi-nginx-flask:python3.6
MAINTAINER TLQ, https://liquntang.wordpress.com/

COPY ./app /app
EXPOSE 8080  
# google app engine demands 8080

RUN pip install -r requirements.txt
ENV LANG C.UTF-8
CMD python main.py
