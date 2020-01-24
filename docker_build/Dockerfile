# build like:
# docker build -t  orihab/ubuntu_ssh:2.0 .
# docker push orihab/ubuntu_ssh:2.0 (to docker hub)

FROM ubuntu:18.04
LABEL maintainer="orielh@anyvision.co"

COPY ./entrypoint.sh /

RUN apt-get update && apt-get install -y openssh-server vim iputils-ping awscli
RUN mkdir /var/run/sshd && mkdir /root/.ssh

RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config
# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

EXPOSE 2222
ENTRYPOINT ["/entrypoint.sh"]
CMD []
