# AWS Public IP Addresses to Docker ELK

## Description

These scripts allow you to easily import various AWS log types into an Elasticsearch cluster running locally on your computer in a docker container.  

This Python script grabs the latest list of [AWS public IP addresses][ip-list] and imports it into Elasticsearch.  After this it imports a custom dashboard in order to visualize the data.

## Steps Automated

The scripts configure everything that is needed in the ELK stack: 

 - Elasticsearch:
   - indices
   - mappings
   
 - Kibana:
   - index-patterns
   - importing dashboards, visualizations, and dashboards
   - custom link directly to the newly created dashboard
 

## Installation Steps

 - Install [Docker for Windows][docker-for-windows] or [Docker for Mac][docker-for-mac]
 - Clone this git repository:
 
   ` git clone https://github.com/mike-mosher/AWS-Public-IP-Addresses-to-ELK.git && cd AWS-Public-IP-Addresses-to-ELK `

 - Install requirements:
 
   ` pip install -r ./requirements.txt `
  
 - Bring the docker environment up:
 
   ` docker-compose up -d `
  
 - Verify that the containers are running:
 
   ` docker ps `
  
 - Verify that Elasticsearch is running:
 
   ` curl -XGET localhost:9200/_cluster/health?pretty `
  
 - Move to the scripts directory and run the script:
 
   ```
   cd scripts
   python importAmazonIPAddressesToELK.py
   ```
  
 - Browse to the link provided in the output by using `cmd + double-click`, or browse directly to the default Kibana page:
 
   ` http://localhost:5601 `
   
 - When done, you can shutdown the containers:
 
   ` docker-compose down -v `
  

## Dashboard

![Dashboard][dashboard]
 

 

[docker-for-windows]: https://docs.docker.com/docker-for-windows/install/#download-docker-for-windows
[docker-for-mac]: https://docs.docker.com/docker-for-mac/install/#download-docker-for-mac
[ip-list]: https://ip-ranges.amazonaws.com/ip-ranges.json
[dashboard]: screenshot/dashboard.jpg?raw=true
