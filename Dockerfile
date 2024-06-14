FROM python:3.10

ADD . /home

WORKDIR /home

RUN pip install -r requirements.txt

CMD ["python", "./main.py"]