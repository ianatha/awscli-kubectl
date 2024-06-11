FROM python:3.12.4-alpine3.20

ARG KUBE_VERSION="v1.29.2"

RUN apk add --update --no-cache ca-certificates curl libffi-dev libc-dev gcc 
RUN pip3 install --no-cache jwt requests
RUN curl --silent -L https://storage.googleapis.com/kubernetes-release/release/${KUBE_VERSION}/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl \
 && chmod +x /usr/local/bin/kubectl 

ADD main.py /main.py
RUN chmod +x /main.py