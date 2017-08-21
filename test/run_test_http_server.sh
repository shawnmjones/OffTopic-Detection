#!/bin/bash

echo "Starting test http server"

cd test_http_docroot
python3 -m http.server 9900 &

echo "Done starting test http server"
