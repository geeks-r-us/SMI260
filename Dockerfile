FROM amd64/python:3-alpine

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install -r requirements.txt

ADD ./src /app

CMD [ "python", "./SMI260MQTTGateway.py" ]