# build like:
# docker build -t automation-tests:0.1 .
# and then run docker-compse up -d

FROM ubuntu:18.04
LABEL maintainer="orielh@anyvision.co"

RUN apt-get update && apt-get install -y openssh-server vim iputils-ping
RUN mkdir /var/run/sshd
RUN echo 'root:pass' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config

# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

ENV NOTVISIBLE "in users profile"
RUN echo "export VISIBLE=now" >> /etc/profile

RUN useradd -ms /bin/bash user
RUN echo 'user:pass' | chpasswd

EXPOSE 2222
CMD ["/usr/sbin/sshd", "-D"]
