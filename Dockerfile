ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG VERSION

LABEL maintainer="infra team" \
      org.label-schema.build-date="${BUILD_DATE}" \
      org.label-schema.name="pawnlib-docker" \
      org.label-schema.description="Docker images for operating Infra." \
      org.label-schema.url="https://www.iconloop.com/" \
      org.label-schema.vcs-ref="${VCS_REF}" \
      org.label-schema.vcs-url="https://github.com/jinwoo-j/pawnlib" \
      org.label-schema.vendor="ICONLOOP Inc." \
      org.label-schema.version="${VERSION}-${VCS_REF}"

ENV IS_DOCKER=true
COPY . /pawnlib/
WORKDIR /pawnlib

RUN pip install --no-cache-dir -r /pawnlib/requirements.txt
RUN pip install --no-cache-dir -r /pawnlib/requirements.dev.txt

RUN python3 setup.py bdist_wheel
RUN pip install dist/pawnlib-*.whl --force-reinstall

RUN echo 'export PS1=" \[\e[00;32m\]${NAME}: ${VERSION}\[\e[0m\]\[\e[00;37m\]@\[\e[0m\]\[\e[00;31m\]\H :\\$\[\e[0m\]"' >> /root/.bashrc
