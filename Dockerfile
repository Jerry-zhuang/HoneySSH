FROM python:3.8

COPY . /root/HoneySSH/

WORKDIR /root/HoneySSH/

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "run.py"]