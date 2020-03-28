# see hooks/build and hooks/.config
ARG BASE_IMAGE_PREFIX
FROM ${BASE_IMAGE_PREFIX}python:3-alpine

# see hooks/post_checkout
ARG ARCH
COPY qemu-${ARCH}-static /usr/bin

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN apk add --no-cache alpine-sdk autoconf automake libtool libffi-dev openssl-dev
RUN pip3 install -r requirements.txt

ADD ./src /app

CMD [ "python", "./SMI260MQTTGateway.py" ]