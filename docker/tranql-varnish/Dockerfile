FROM debian:9.5
# Varnish image with POST request caching
# more info on varnish can be found at http://varnish-cache.org/

ENV VARNISH_MOD=varnish-modules-0.15.0

#  Install varnish 6.0 and dependencies
RUN apt-get update -y
RUN	apt-get install -y build-essential automake libtool curl git python-docutils wget
RUN curl -s https://packagecloud.io/install/repositories/varnishcache/varnish60/script.deb.sh | bash
RUN apt-get install -y varnish-dev

# Build varnishMOD from source

# Download and untar
RUN wget https://download.varnish-software.com/varnish-modules/${VARNISH_MOD}.tar.gz
RUN mkdir -p /tmp/varnish-mods
RUN tar -xf ${VARNISH_MOD}.tar.gz -C /tmp/varnish-mods/
RUN rm ${VARNISH_MOD}.tar.gz

# Start building VarnishMOD

WORKDIR /tmp/varnish-mods/${VARNISH_MOD}
RUN ./configure && make &&  make check && make install
WORKDIR /
RUN rm -r /tmp/varnish-mods

# Add cache post request .vcl config
# Note: this is not the default config. Using this image still requires use to create a default.vcl in
# /lib/varnish/default.vcl
# The 'cache_post_requests.vcl' can be included in our default.vcl, to support caching post request.

COPY cache_post_requests.vcl /etc/varnish/cache_post_requests.vcl

# Set file permission for varnish user

RUN mkdir -p /var/lib/varnish
RUN chown varnish:varnish /var/lib/varnish

# Activate the varnish user
USER varnish

# add entrypoint
COPY docker-varnish-entrypoint.sh /

ENTRYPOINT ["/docker-varnish-entrypoint.sh"]

EXPOSE 8080 8443
CMD []