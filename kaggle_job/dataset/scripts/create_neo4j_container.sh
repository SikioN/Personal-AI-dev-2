#!/bin/bash

echo "Creating fresh Neo4j container for Wikidata KG..."

# Remove old volume if it exists
echo "Removing old volume..."
docker volume rm 446656c9994e47e42620c93af7b9087ecdc288cdf9b138d3f06c91da32b23665 2>/dev/null || true

# Create new Neo4j container
# Using Community Edition to avoid cluster state issues
echo "Creating Neo4j container..."
docker run -d \
  --name neo4j_kg \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4J_ACCEPT_LICENSE_AGREEMENT=yes \
  -e NEO4J_dbms_memory_heap_initial__size=1G \
  -e NEO4J_dbms_memory_heap_max__size=2G \
  -e NEO4J_dbms_memory_pagecache_size=1G \
  neo4j:5.21.0

echo ""
echo "Waiting for Neo4j to start (20 seconds)..."
sleep 20

echo ""
echo "Checking Neo4j status..."
docker logs neo4j_kg --tail 10

echo ""
echo "✓ Container created!"
echo "Neo4j Browser: http://localhost:7474"
echo "Username: neo4j"
echo "Password: password"
echo ""
echo "Next step: Run 'python3 scripts/ingest_neo4j_only.py' to load wikidata"
