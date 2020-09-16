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
    rsync \
    pigz \
    && curl -sL https://deb.nodesource.com/setup_10.x | bash \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# prepare root user for ssh login
RUN mkdir /var/run/sshd \
    && mkdir /root/.ssh \
    && chmod 0700 /root/.ssh \
    && echo "root:pass" | chpasswd

# RUN groupadd --gid 5000 user \
#     && useradd --home-dir /home/user --create-home --uid 5000 \
#         --gid 5000 --shell /bin/bash --skel /dev/null user \
#     && mkdir -p /home/user/.ssh && chmod 0700 /home/user/.ssh \
#     && chown -R user:user /home/user/ /etc/ssh/ \
#     && echo "user:password" | chpasswd

# USER user


# Configure npm registry
RUN npm config set registry https://anyvision.jfrog.io/anyvision/api/npm/npm/

# Install pip3 requirements.txt
ADD requirements.txt  /home/user/requirements.txt
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r /home/user/requirements.txt

COPY etc/  /etc/
# run as a different user

WORKDIR /home/user

EXPOSE 2222

ENTRYPOINT ["/usr/sbin/sshd"]
CMD ["-D","-e"]
