#!/bin/bash
sudo docker build -t recorder-api .
sudo docker run -p 5000:5000 -d recorder-api