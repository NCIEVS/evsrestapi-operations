# Local-development Jena/Fuseki image (see docs/jena-fuseki.md). Servers use the native
# install managed by bin/jena.service instead.
# The floating Java 25 tag picks up the latest Java 25 patch release at each build.
FROM bellsoft/liberica-openjre-alpine:25

# Set environment variables
ENV FUSEKI_VERSION=5.3.0
ENV JENA_HOME=/opt/jena
ENV FUSEKI_HOME=/opt/fuseki
ENV FUSEKI_BASE=/opt/fuseki/run

# Install necessary packages
RUN apk add --no-cache curl unzip bash

# Create directories
RUN mkdir -p ${FUSEKI_HOME} ${FUSEKI_BASE} ${JENA_HOME}

# Download and unzip Fuseki and Jena, checking each against the SHA-512 Apache publishes beside it
COPY verify-sha512.sh /tmp/verify-sha512.sh
RUN set -e; \
    base=https://archive.apache.org/dist/jena/binaries; \
    for name in apache-jena-fuseki apache-jena; do \
      zip=${name}-${FUSEKI_VERSION}.zip; \
      curl -fsSL -o /tmp/${zip} ${base}/${zip}; \
      curl -fsSL -o /tmp/${zip}.sha512 ${base}/${zip}.sha512; \
      sh /tmp/verify-sha512.sh /tmp/${zip} /tmp/${zip}.sha512; \
      unzip -q /tmp/${zip} -d /tmp; \
    done; \
    mv /tmp/apache-jena-fuseki-${FUSEKI_VERSION}/* ${FUSEKI_HOME}; \
    mv /tmp/apache-jena-${FUSEKI_VERSION}/* ${JENA_HOME}; \
    rm -rf /tmp/apache-jena* /tmp/verify-sha512.sh

## Expose the default Fuseki port
#EXPOSE 3030

# Set the working directory
WORKDIR ${FUSEKI_HOME}
COPY ./shiro.ini ${FUSEKI_HOME}/run/shiro.ini
# Start Fuseki
#CMD ["./fuseki-server", "--update", "--loc=/opt/fuseki/run/databases","/NCIT2"]
#CMD ["./fuseki", "start"]
#CMD ["./fuseki-server", "--update"]
COPY entrypoint.sh /opt/fuseki/entrypoint.sh
RUN chmod +x /opt/fuseki/entrypoint.sh
ENTRYPOINT ["/opt/fuseki/entrypoint.sh"]
