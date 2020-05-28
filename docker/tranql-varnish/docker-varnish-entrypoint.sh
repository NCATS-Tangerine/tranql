#!/bin/sh
## Copied from https://github.com/varnish/docker-varnish/blob/master/stable/debian/docker-varnish-entrypoint




set -e


# this will check if the first argument is a flag
# but only works if all arguments require a hyphenated flag
# -v; -SL; -f arg; etc will work, but not arg1 arg2
# running Varnish as non root user; Using port 8080 instead
if [ "$#" -eq 0 ] || [ "${1#-}" != "$1" ]; then
    set -- varnishd -F -f /etc/varnish/default.vcl -a http=:8080,HTTP -a proxy=:8443,PROXY -s malloc,$VARNISH_SIZE "$@"
fi

exec "$@"