FROM python:3.6.9-alpine3.9 as build

RUN apk add --no-cache \
        jq==1.6-r0 \
        build-base==0.5-r1 \
        gcc==8.3.0-r0

COPY ./Pipfile.lock /src/Pipfile.lock
WORKDIR /src
RUN jq -r '.default \
        | to_entries[] \
        | .key + .value.version' \
    Pipfile.lock > requirements.txt
RUN echo 'manylinux1_compatible = True' > /usr/local/lib/python3.6/site-packages/_manylinux.py
RUN pip3 install -r requirements.txt

RUN apk del jq build-base gcc

COPY . /src/

FROM python:3.6.9-alpine3.9
COPY --from=build / /
WORKDIR /src
EXPOSE 8080
CMD ["python", "-m", "aiohttp.web", "-H", "0.0.0.0", "-P", "8080", "webapp.webapp:main"]
