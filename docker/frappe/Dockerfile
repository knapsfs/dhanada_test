ARG FRAPPE_VERSION=v15
FROM frappe/erpnext:${FRAPPE_VERSION}

USER root
# Ensure proper permissions and install any required OS dependencies
RUN apt-get update && apt-get install -y iputils-ping && rm -rf /var/lib/apt/lists/*

USER frappe
# Pre-install the CRM app inside the image.
# Dhanada app will be mounted over during local development, but in a true prod build,
# it could also be fetched here.
# RUN bench get-app crm

# Provide an entrypoint script to handle startup tasks
COPY docker/frappe/entrypoint.sh /usr/local/bin/entrypoint.sh
USER root
RUN chmod +x /usr/local/bin/entrypoint.sh
USER frappe

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["bench", "worker"]
