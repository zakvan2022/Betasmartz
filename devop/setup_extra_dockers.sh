#!/bin/bash

# Run redis docker
docker run --name redis -d redis

# Run highcharts docker
docker pull onsdigital/highcharts-export-node
docker run -d --name highcharts --net=betasmartz-local onsdigital/highcharts-export-node
