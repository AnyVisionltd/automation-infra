#!/usr/bin/env bash

case "$1" in
   "password" )
        echo "$2:$3" | chpasswd ;;
   "pem" )
        # TODO: I cancelled this, params should always be password root pass
        # If we need it in future we can figure this out.
        mkdir /home/${2}/.ssh
        echo "ssh-rsa ${3} ${2}" > /home/${2}/.ssh/authorized_keys ;;
   * )
        echo "invalid authentication type"
        echo "syntax: [password user1 password1]" ;;

esac

aws configure set aws_access_key_id AKIAZQJT5HXO4YTJSHHL
aws configure set aws_secret_access_key 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
aws configure set default.region eu-central-1


/usr/sbin/sshd -D
