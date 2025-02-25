#!/bin/bash
#ensure that your script fails fast and explicitly when something goes wrong, 
# which is especially useful for debugging and maintaining reliable scripts.
set -euo pipefail

# Pull the Neo4j image from Docker Hub
if ! docker pull noahtsang/neo4j_w_crypto_data; then
    echo "Warning: Could not pull the latest image. Using the local image instead."
fi

# Check if the container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^neo4j_w_crypto_data\$"; then
    echo "Container 'neo4j_w_crypto_data' already exists. Restarting..."
    docker restart neo4j_w_crypto_data
else
    # Run Neo4j container
    docker run -d --name neo4j_w_crypto_data \
      -p 7474:7474 -p 7687:7687 \
      -e NEO4J_AUTH=neo4j/staysovryn \
      -e NEO4J_dbms_security_procedures_unrestricted=gds.*,apoc.* \
      -v neo4j_data:/data \
      -v neo4j_plugins:/plugins \
      noahtsang/neo4j_w_crypto_data

    # Optional: wait for the container to properly initialize
    sleep 5
fi

# Copy data and plugins into the container
docker exec neo4j_w_crypto_data sh -c "cp -r /data_copy/* /data && cp -r /plugins_copy/* /plugins && rm -rf /data_copy /plugins_copy"

# Restart Neo4j container
docker restart neo4j_w_crypto_data