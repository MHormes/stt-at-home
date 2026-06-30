#!/bin/sh
mkdir -p /etc/nginx/ssl
if [ ! -f /etc/nginx/ssl/cert.pem ]; then
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/key.pem \
        -out /etc/nginx/ssl/cert.pem \
        -subj "/CN=stt-at-home"
fi
exec nginx -g 'daemon off;'
