FROM ubuntu:18.04

LABEL maintainer="orielh@anyvision.co"

# install apt packages
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
    && apt-get install -y --no-install-recommends \
    openssh-server \
    vim \
    iputils-ping \
    awscli \
    iptables \
    ffmpeg \
    curl \
    net-tools \
    libsm6 \
    libxext6 \
    libxrender-dev \
    python3-pip \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# prepare root user for ssh login
RUN mkdir /var/run/sshd \
    && mkdir /root/.ssh \
    && chmod 0700 /root/.ssh \
    && echo "root:pass" | chpasswd

# configure sshd daemon for ssh connections
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/#PidFile \/var\/run\/sshd.pid/PidFile .\/sshd.pid/' /etc/ssh/sshd_config \
    && sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config \
    && sed -i 's/#ClientAliveInterval 0/ClientAliveInterval 300/' /etc/ssh/sshd_config \
    && sed -i 's/#UseDNS no/UseDNS yes/' /etc/ssh/sshd_config \
    && sed -i 's/#PermitTunnel no/PermitTunnel yes/' /etc/ssh/sshd_config \
    # SSH login fix. Otherwise user is kicked off after login
    && sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

# run as a different user

# RUN groupadd --gid 5000 user \
#     && useradd --home-dir /home/user --create-home --uid 5000 \
#         --gid 5000 --shell /bin/bash --skel /dev/null user \
#     && mkdir -p /home/user/.ssh && chmod 0700 /home/user/.ssh \
#     && chown -R user:user /home/user/ /etc/ssh/ \
#     && echo "user:password" | chpasswd

# USER user

# Install pip3 requirements.txt
ADD requirements.txt  /home/user/requirements.txt
RUN python3 -m pip install -r /home/user/requirements.txt


WORKDIR /home/user

EXPOSE 2222

ENTRYPOINT ["/usr/sbin/sshd"]
CMD ["-D","-e"]
