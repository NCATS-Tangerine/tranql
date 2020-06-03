FROM quaddo/artillery

COPY ./performance-tests/* /work/


ARG UID=1000
ARG GID=1000
RUN groupadd -o -g $GID artillery
RUN useradd -m -u $UID -g $GID -s /bin/bash artillery

USER artillery

ENTRYPOINT artillery
