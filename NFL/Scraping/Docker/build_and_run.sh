docker build -t nfl-scraper .
docker run --rm --name nfl-scraper-container -v $(pwd)/data:/app/data nfl-scraper
# docker run --rm -it --name nfl-scraper-container -v $(pwd)/data:/app/data nfl-scraper /bin/bash ### Interactive

# */2 * * * * docker start nfl-scraper-container ### Cron