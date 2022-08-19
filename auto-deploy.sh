#!/bin/bash
sudo docker build -t derailed-api .
sudo docker run -p 5000:5000 -d derailed-api