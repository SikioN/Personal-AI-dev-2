#!/bin/bash

echo "=== Neo4j Cluster State Fix ==="
echo "This script will unbind the Neo4j cluster state to fix the corruption issue."
echo ""

# Step 1: Start the container (if not already running)
echo "Step 1: Starting container..."
docker start neo4j_kg 2>/dev/null
sleep 5

# Step 2: Run unbind command inside container
echo "Step 2: Running neo4j-admin server unbind..."
docker exec neo4j_kg neo4j-admin server unbind

if [ $? -eq 0 ]; then
    echo "✓ Unbind successful!"
    echo ""
    echo "Step 3: Restarting container..."
    docker restart neo4j_kg
    echo ""
    echo "Waiting for Neo4j to start (15 seconds)..."
    sleep 15
    echo ""
    echo "Check if Neo4j is running:"
    docker logs neo4j_kg --tail 10
else
    echo "✗ Unbind failed. Container might not be running."
    echo "Trying alternative approach: removing corrupted volume..."
    echo ""
    echo "WARNING: This will DELETE all Neo4j data!"
    echo "To proceed, run manually:"
    echo "  docker stop neo4j_kg"
    echo "  docker rm neo4j_kg"
    echo "  docker volume rm 446656c9994e47e42620c93af7b9087ecdc288cdf9b138d3f06c91da32b23665"
    echo "  # Then recreate container with docker-compose or docker run"
fi
