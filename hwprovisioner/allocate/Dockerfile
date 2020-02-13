FROM python:3.6.9-alpine3.9 as build

RUN apk add --no-cache \
        build-base==0.5-r1 \
        gcc==8.3.0-r0 \
        python3-dev==3.6.9-r2

RUN pip3 install \
        pipenv==2018.11.26
COPY ./Pipfile /src/Pipfile
WORKDIR /src
RUN echo 'manylinux1_compatible = True' > /usr/local/lib/python3.6/site-packages/_manylinux.py
RUN pipenv lock && pipenv install --dev --system
RUN apk del build-base gcc python3-dev && \
    pip3 uninstall -y pipenv

COPY . /src/

FROM python:3.6.9-alpine3.9
LABEL maintainer "Peter McConnell <peterm@anyvision.co>"
COPY --from=build / /
WORKDIR /src
EXPOSE 8080
CMD ["python", "-m", "webapp.app", "serve"]
