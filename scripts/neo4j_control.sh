#!/bin/bash

# Neo4j KG Control Script
# Usage: ./neo4j_control.sh [start|stop|restart|status|logs|clean]

COMPOSE_FILE="docker-compose.neo4j.yml"

case "$1" in
    start)
        echo "Starting Neo4j KG..."
        docker-compose -f "$COMPOSE_FILE" up -d
        echo "Waiting for Neo4j to be ready..."
        sleep 15
        docker-compose -f "$COMPOSE_FILE" logs --tail 10
        echo ""
        echo "✓ Neo4j started!"
        echo "Browser: http://localhost:7474"
        echo "Username: neo4j"
        echo "Password: password"
        ;;
    
    stop)
        echo "Stopping Neo4j KG..."
        docker-compose -f "$COMPOSE_FILE" stop
        echo "✓ Neo4j stopped"
        ;;
    
    restart)
        echo "Restarting Neo4j KG..."
        docker-compose -f "$COMPOSE_FILE" restart
        echo "Waiting for Neo4j to be ready..."
        sleep 15
        docker-compose -f "$COMPOSE_FILE" logs --tail 10
        echo "✓ Neo4j restarted"
        ;;
    
    status)
        echo "Neo4j KG Status:"
        docker-compose -f "$COMPOSE_FILE" ps
        echo ""
        echo "Health check:"
        docker inspect neo4j_kg --format='{{.State.Health.Status}}' 2>/dev/null || echo "Not running or no healthcheck"
        ;;
    
    logs)
        LINES="${2:-50}"
        docker-compose -f "$COMPOSE_FILE" logs --tail "$LINES" -f
        ;;
    
    clean)
        echo "⚠️  WARNING: This will DELETE all Neo4j data!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            docker-compose -f "$COMPOSE_FILE" down -v
            echo "✓ Neo4j data cleaned"
        else
            echo "Cancelled"
        fi
        ;;
    
    *)
        echo "Neo4j KG Control Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  start    - Start Neo4j container"
        echo "  stop     - Stop Neo4j container"
        echo "  restart  - Restart Neo4j container"
        echo "  status   - Show container status and health"
        echo "  logs     - Show container logs (optional: number of lines)"
        echo "  clean    - Remove container and all data volumes"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 logs 100"
        exit 1
        ;;
esac
