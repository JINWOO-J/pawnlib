ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG VERSION
ARG NAME
ARG REMOVE_BUILD_PACKAGE

LABEL maintainer="infra team" \
      org.label-schema.build-date="${BUILD_DATE}" \
      org.label-schema.name="pawnlib-docker" \
      org.label-schema.description="Docker images for operating Infra." \
      org.label-schema.url="https://www.parametacorp.com/" \
      org.label-schema.vcs-ref="${VCS_REF}" \
      org.label-schema.vcs-url="https://github.com/jinwoo-j/pawnlib" \
      org.label-schema.vendor="PARAMETA" \
      org.label-schema.version="${VERSION}-${VCS_REF}"

ENV IS_DOCKER=true \
    NAME=${NAME} \
    VERSION=${VERSION} \
    REMOVE_BUILD_PACKAGE=${REMOVE_BUILD_PACKAGE:-"true"} \
    LIB_PACKAGE="libcurl4-openssl-dev jq telnet" \
    BUILD_PACKAGE="" \
    COLUMNS=100
#    PYCURL_SSL_LIBRARY=openssl \

COPY . /pawnlib/
WORKDIR /pawnlib

RUN ARCH="$(dpkg --print-architecture)" ; \
    apt update && apt install -y ${BUILD_PACKAGE} ${LIB_PACKAGE} && \
    if [ "${ARCH}" = 'aarch64' ]; then apt install -y gcc make pkg-config tzdata; fi && \
    if [ "${ARCH}" = 'arm64' ]; then apt install -y gcc make pkg-config tzdata; fi && \
    ln -fs /usr/share/zoneinfo/Asia/Seoul /etc/localtime && \
    dpkg-reconfigure --frontend noninteractive tzdata  &&\
    python3 setup.py bdist_wheel && \
    pip3 install dist/pawnlib-*.whl --force-reinstall && \
    pip3 install -r requirements-full.txt && \
    if [ "$REMOVE_BUILD_PACKAGE" = "true" ]; then \
        echo "REMOVE_BUILD_PACKAGE" ; \
        apt-get purge -y --auto-remove ${BUILD_PACKAGE} && \
        rm -rf /var/lib/apt/lists/* ; \
    fi;

#ENTRYPOINT ["/bin/bash", "-c", "if [ \"$1\" = \"bash\" ]; then exec \"$@\"; else exec pawns \"$@\"; fi", "bash"]

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

RUN echo 'export PS1=" \[\e[00;32m\]${NAME}: ${VERSION}\[\e[0m\]\[\e[00;37m\]@\[\e[0m\]\[\e[00;31m\]\H:\\$\[\e[0m\] "' >> /root/.bashrc
