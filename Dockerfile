ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG VERSION
ARG NAME
ARG REMOVE_BUILD_PACKAGE

LABEL maintainer="infra team" \
      org.label-schema.build-date="${BUILD_DATE}" \
      org.label-schema.name="pawnlib-docker" \
      org.label-schema.description="Docker images for operating Infra." \
      org.label-schema.url="https://www.iconloop.com/" \
      org.label-schema.vcs-ref="${VCS_REF}" \
      org.label-schema.vcs-url="https://github.com/jinwoo-j/pawnlib" \
      org.label-schema.vendor="ICONLOOP Inc." \
      org.label-schema.version="${VERSION}-${VCS_REF}"

ENV IS_DOCKER=true \
    NAME=${NAME} \
    VERSION=${VERSION} \
    REMOVE_BUILD_PACKAGE=${REMOVE_BUILD_PACKAGE:-"true"} \
    LIB_PACKAGE="libcurl4-openssl-dev jq telnet pkg-config" \
    BUILD_PACKAGE=""
#    PYCURL_SSL_LIBRARY=openssl \

COPY . /pawnlib/
WORKDIR /pawnlib

RUN apt update && apt install -y ${BUILD_PACKAGE} ${LIB_PACKAGE} && \
    if [ $(arch) == 'aarch64' ]; then apt install -y gcc make pkg-config; fi && \
    python3 setup.py bdist_wheel && \
    pip3 install dist/pawnlib-*.whl --force-reinstall && \
    if [ "$REMOVE_BUILD_PACKAGE" = "true" ]; then \
        echo "REMOVE_BUILD_PACKAGE" ; \
        apt-get purge -y --auto-remove ${BUILD_PACKAGE} && \
        rm -rf /var/lib/apt/lists/* ; \
    fi;

RUN pip install --no-cache-dir eth_keyfile secp256k1

RUN echo 'export PS1=" \[\e[00;32m\]${NAME}: ${VERSION}\[\e[0m\]\[\e[00;37m\]@\[\e[0m\]\[\e[00;31m\]\H:\\$\[\e[0m\] "' >> /root/.bashrc
