# build like:
# docker build -t automation-tests:0.1 .
# and then run docker-compse up -d

FROM ubuntu:18.04
LABEL maintainer="orielh@anyvision.co"

RUN apt-get update && apt-get install -y openssh-server vim iputils-ping
RUN mkdir /var/run/sshd && mkdir /root/.ssh
RUN echo 'root:pass' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config
# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd
RUN echo 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDuyTkW+neD5/xhyw8WAuTL+COkRch/wTi1UGFBbF0UYZO9TiC1DLeyKMR+EQNai34LVy/DxoVYL/BWUwK0TSlS6bxzKOobIsFxW2wqxOGqScEVvucFrKTcAX+oWY67hzgBp9+sZ+7n5IuHlBaZWnbvljAV8AlJhuzldaHxw7CS1Z6c04h5Vv7jWbsOjs/g7+LuqsRmrcxlMGzUgCpSkcKza4JSGv4WUA376f9pm3beubEkv6h3jdLTown3NiTNLQIyHkuj+xqKq63mp4YeyUlH/0DE6G5lwc93lwbqcrQ1q68i1F4YQkVZptcs+/bSP2/xyMYuHMpIWW1qPaP1Z6jN root@monster' > /root/.ssh/authorized_keys


ENV NOTVISIBLE "in users profile"
RUN echo "export VISIBLE=now" >> /etc/profile

RUN useradd -ms /bin/bash user
RUN echo 'user:pass' | chpasswd

EXPOSE 2222
CMD ["/usr/sbin/sshd", "-D"]
