#!/usr/bin/bash

EXISTING_CONTAINERS=$(docker container ls -q --filter name="personalai_mmenschikov")

echo "Stoping containers..."
docker container stop ${EXISTING_CONTAINERS}
echo "Done."

echo "Removing containers..."
docker container rm ${EXISTING_CONTAINERS}
echo "Done."