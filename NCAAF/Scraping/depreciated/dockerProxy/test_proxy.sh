#!/bin/bash
# test_proxy.sh - Test script to verify proxy rotation is working

cd ~/odds-monitoring/NCAAF/Scraping/dockerProxy
echo "🧪 Testing proxy rotation setup..."

# Start proxy rotator
echo "Starting proxy rotator..."
docker-compose up -d proxy-rotator

# Wait for proxy to be ready
echo "Waiting for proxy rotator to be ready..."
sleep 15

# Test proxy connection
echo "Testing proxy connection..."
docker run --rm --network dockerproxy_scraping-network curlimages/curl:latest \
  curl -x http://proxy-rotator:8080 -s -o /dev/null -w "HTTP Status: %{http_code}\n" \
  https://httpbin.org/ip

echo "✅ Proxy rotation test completed!"
echo "You can now run: ./build_and_run.sh"
