from elasticsearch import Elasticsearch, helpers
from netaddr import IPNetwork
import optparse
import requests
import urllib
import json
import os
import sys


def createIndexAndMapping():
    # Mapping Name: options.index_name
    print "Creating mapping in ES for index: %s" % (options.index_name)

    #open mappings file
    with open('ipv4_prefixes-mapping.json') as f:
        mapping = json.load(f)

    es.indices.create(index=options.index_name, ignore=400, body=mapping['ipv4_prefixes'])

def updateKibanaIndexMapping():
    # Update mappings for .kibana index
    print "Updating mapping for .kibana index"

    # pull payload from mapping file
    with open('prefix_kibana-index-mapping.json') as f:
        mappingdata = json.load(f)

    # update search mappings
    url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/_mapping/search'
    payload = json.dumps(mappingdata['.kibana']['mappings']['search'])
    headers = { 'kbn-version': '5.4.0' }
    r = requests.put(url, data=payload, headers=headers)

    # update visualization mappings
    url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/_mapping/visualization'
    payload = json.dumps(mappingdata['.kibana']['mappings']['visualization'])
    headers = { 'kbn-version': '5.4.0' }
    r = requests.put(url, data=payload, headers=headers)

    # update dashboard mappings
    url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/_mapping/dashboard'
    payload = json.dumps(mappingdata['.kibana']['mappings']['dashboard'])
    headers = { 'kbn-version': '5.4.0' }
    r = requests.put(url, data=payload, headers=headers)

def createKibanaIndexPattern():
    print "Creating new index-pattern in .kibana index"

    # Create the index pattern
    url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/index-pattern/' + options.index_name
    payload = '{ "title":"' + options.index_name + '" }'
    params_payload = { 'op_type': 'create' }
    headers = { 'kbn-version': '5.4.0' }
    r = requests.post(url, data=payload, params=params_payload, headers=headers)

def setKibanaIndexDefaultIndex():
    print "Setting index-pattern as default index"

    # Set the index as default
    url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/config/5.4.0/_update'
    payload = '{ "doc": { "defaultIndex": "' + options.index_name + '" } }'
    headers = { 'kbn-version': '5.4.0' }
    r = requests.post(url, data=payload, headers=headers)

def deleteKibanaIndexIndexPatterns():
    print "Deleting useless index-patterns in .kibana index"

    print "Deleting index-pattern: .ml-anomalies-*"
    # build request
    url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/index-pattern/.ml-anomalies-*'
    headers = { 'kbn-version': '5.4.0' }
    r = requests.delete(url, headers=headers)

    print "Deleting index-pattern: .ml-notifications"
    # build request
    url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/index-pattern/.ml-notifications'
    headers = { 'kbn-version': '5.4.0' }
    r = requests.delete(url, headers=headers)

def importObjectsToKibana():
    print "importing saved objects into Kibana"
    elbDashboardId = ""

    #open file with objects
    with open('prefix_kibana-index-data.json') as f:
        data = json.load(f)

        for i in data['hits']['hits']:
            if i['_type'] in ['search', 'visualization', 'dashboard']:
                #Import items
                url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/' + i['_type'] + '/' + i['_id']
                payload = json.dumps(i['_source'])
                headers = { 'kbn-version': '5.4.0' }
                requests.post(url, data=payload, headers=headers)

            if i['_type'] == 'dashboard':
                # Need to grab the dashboard ID, so that I can create a direct link at the end
                elbDashboardId = i['_id']

    return elbDashboardId

def loadPrefixes():
    print "Adding IPv4 Prefixes to ELK ... "

    # get the ip ranges
    response = urllib.urlopen("https://ip-ranges.amazonaws.com/ip-ranges.json")
    data = json.loads(response.read())

    for block in data['prefixes']:
        ip = IPNetwork(block['ip_prefix'])
        block['total_ip_addresses'] = ip.size
        block['cidr'] = block['ip_prefix'].split('/')[1]

        # add to ES
        es.index(index=options.index_name,doc_type=options.index_name,body=block)

    print "Prefixes added to ELK"



#Input Parsing
parser = optparse.OptionParser(
                    usage="Send Amazon Public IP Addresses to ES",
                    version="0.1"
                  )

parser.add_option('-i',
                  '--index',
                  dest="index_name",
                  default="ipv4_prefixes",
                  help="name of the index to create if not default of ipv4_prefixes"
                  )

parser.add_option('-s',
                  '--servername',
                  dest="es_host",
                  default="localhost",
                  help='specify an alternate ES IP address if not localhost'
                  )

parser.add_option('-p',
                  '--port',
                  dest="port",
                  default="9200",
                  help='specify an alternate ES port if not 9200'
                  )

parser.add_option('-b',
                  '--bulk',
                  dest="bulk_limit",
                  default=5000,
                  help='specify an bulk limit to batch requests to Elasticsearch'
                  )

(options,args) = parser.parse_args()

#sanitize
options.bulk_limit = int(options.bulk_limit)

# Hard-set the index name
options.index_name = "ipv4_prefixes"


print ""
print "Beginning import process"

#Create elasticsearch object
es = Elasticsearch(options.es_host)

# Create index and set mapping
createIndexAndMapping()

# Update .kibana index mappings
updateKibanaIndexMapping()

# Create a new index-pattern in .kibana index for elb_logs
createKibanaIndexPattern()

# Set new index-pattern to default index
setKibanaIndexDefaultIndex()

# delete useless index-patterns in .kibana index that we will never use
deleteKibanaIndexIndexPatterns()

# Import search / visualizations / dashboards into Kibana
# we will be returned the dashboard ID, so that we can put it in the URL at the end
elbDashboardId = importObjectsToKibana()

# Load files into ES
loadPrefixes()


# Build the URL

url = ""

if elbDashboardId:
    # If elbDashboardId has been set, then send them directly to the dashboard URL
    url = 'http://' + options.es_host + ':5601/app/kibana#/dashboard/' + elbDashboardId
else:
    # I was unable to grab the dashboard ID for some reason.  Just give them the default URL
    url = 'http://' + options.es_host + ':5601/'


#Time to end this.  Give them the blurb
print ""
print "=========================================================="
print "Done!"
print "=========================================================="
print ""
print "Next Step:"
print "Browse to Kibana by opening the following link:"
print ""
print url
print ""
print "Hint: you can use cmd + double-click on the above link to open it from the terminal"
print ""
print "=========================================================="
print ""
