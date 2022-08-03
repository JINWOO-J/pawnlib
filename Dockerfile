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
    REMOVE_BUILD_PACKAGE=${REMOVE_BUILD_PACKAGE:-"true"}
#    PYCURL_SSL_LIBRARY=openssl \
#    LIB_PACKAGE="libcurl4-openssl-dev" \
#    BUILD_PACKAGE="libssl-dev gcc"


COPY . /pawnlib/
WORKDIR /pawnlib


RUN apt update && apt install -y ${BUILD_PACKAGE} ${LIB_PACKAGE} && \
#    pip install --no-cache-dir -r /pawnlib/requirements.txt && \
#    pip install --no-cache-dir -r /pawnlib/requirements.dev.txt && \
    python3 setup.py bdist_wheel && \
    pip3 install dist/pawnlib-*.whl --force-reinstall && \
    if [ "$REMOVE_BUILD_PACKAGE" = "true" ]; then \
        echo "REMOVE_BUILD_PACKAGE" ; \
        apt-get purge -y --auto-remove ${BUILD_PACKAGE} && \
        rm -rf /var/lib/apt/lists/* ; \
    fi;

#RUN pip install --no-cache-dir -r /pawnlib/requirements.txt
#RUN pip install --no-cache-dir -r /pawnlib/requirements.dev.txt
#
#RUN python3 setup.py bdist_wheel
#RUN pip install dist/pawnlib-*.whl --force-reinstall

RUN echo 'export PS1=" \[\e[00;32m\]${NAME}: ${VERSION}\[\e[0m\]\[\e[00;37m\]@\[\e[0m\]\[\e[00;31m\]\H:\\$\[\e[0m\] "' >> /root/.bashrc
