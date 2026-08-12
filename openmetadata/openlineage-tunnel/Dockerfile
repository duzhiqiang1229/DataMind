FROM alpine:3.22

RUN apk add --no-cache openssh-client

COPY entrypoint.sh /usr/local/bin/openlineage-tunnel
RUN chmod 755 /usr/local/bin/openlineage-tunnel

ENTRYPOINT ["/usr/local/bin/openlineage-tunnel"]
