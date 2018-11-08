import argparse
import networkx
import re
import requests
import sys

spyonweb_access_token  = "SPYONWEBAPI"
spyonweb_url           = "https://api.spyonweb.com/v1/"

google_adsense_pattern   = re.compile("pub-[0-9]{1,}",re.IGNORECASE)
google_analytics_pattern = re.compile("ua-\d+-\d+",re.IGNORECASE)

# setup the commandline argument parsing
parser = argparse.ArgumentParser(description='Generate visualizations based on tracking codes.')

parser.add_argument("--graph",help="Output filename of the graph file. Example: bellingcat.gexf",default="connections.gexf")
parser.add_argument("--domain", help="A domain to try to find connections to.",)
parser.add_argument("--file",help="A file that contains domains, one per line.")

args = parser.parse_args()

#
# Clean tracking code
#
def clean_tracking_code(tracking_code):
    
    if tracking_code.count("-") > 1:
        
        return tracking_code.rsplit("-",1)[0]
    
    else:
        
        return tracking_code

#
# Extract tracking codes from a target domain.
#
def extract_tracking_codes(domains):
    
    tracking_codes = []
    connections    = {}
    
    for domain in domains:
        
        # send a request off to the website
        try:
    
            print "[*] Checking %s for tracking codes." % domain
            
            if not domain.startswith("http:"):
                site = "http://" + domain
                
            response = requests.get(site)
            
        except:
            
            print "[!] Failed to reach site."
            
            continue
        
        # extract the tracking codes
        extracted_codes = []
        extracted_codes.extend(google_adsense_pattern.findall(response.content))
        extracted_codes.extend(google_analytics_pattern.findall(response.content))
        
        # loop over the extracted tracking codes
        for code in extracted_codes:

            # remove the trailing dash and number
            code = clean_tracking_code(code)
            
            if code.lower() not in tracking_codes:
                
                print "[*] Discovered: %s" % code.lower()
                
                if code not in connections.keys():
                    connections[code] = [domain]
                else:
                    connections[code].append(domain)
                
    
    return connections

#
# Send a request off to Spy On Web
#
def spyonweb_request(data,request_type="domain"):
    
    params = {}
    params['access_token'] = spyonweb_access_token
    
    response = requests.get(spyonweb_url+request_type+"/"+data,params=params)

    if response.status_code == 200:
        
        result = response.json()
        
        if result['status'] != "not_found":
            
            return result
        
    return None

#
# Function to check the extracted analytics codes with Spyonweb
#
def spyonweb_analytics_codes(connections):
    
    
    # use any found tracking codes on Spyonweb
    for code in connections:
        
        # send off the tracking code to Spyonweb
        if code.lower().startswith("pub"):
            
            request_type = "adsense"
        
        elif code.lower().startswith("ua"):
            
            request_type = "analytics"
            
        print "[*] Trying code: %s on Spyonweb." % code
        
        results = spyonweb_request(code,request_type)
            
        if results:
            
            for domain in results['result'][request_type][code]['items']:
                
                print "[*] Found additional domain: %s" % domain
                
                connections[code].append(domain)

    return connections    

#
# Use Spyonweb to grab full domain reports.
#
def spyonweb_domain_reports(connections):
    
    # now loop over all of the domains and request a domain report
    tested_domains = []
    all_codes      = connections.keys()
    
    for code in all_codes:
        
        for domain in connections[code]:
            
            if domain not in tested_domains:
                
                tested_domains.append(domain)
                
                print "[*] Getting domain report for: %s" % domain
                
                results = spyonweb_request(domain)
                
                if results:
                    
                    # loop over adsense results
                    adsense = results['result'].get("adsense")
                    
                    if adsense:
                        
                        for code in adsense:
                            
                            code = clean_tracking_code(code)
                            
                            if code not in connections:
                                
                                connections[code] = []
                                
                            for domain in adsense[code]['items'].keys():
                                
                                if domain not in connections[code]:
                                    
                                    print "[*] Discovered new domain: %s" % domain
                                    
                                    connections[code].append(domain)
                    
                    analytics = results['result'].get("analytics")
                    
                    if analytics:
                        
                        for code in analytics:

                            code = clean_tracking_code(code)
                            
                            if code not in connections:
                                
                                connections[code] = []
                            
                            for domain in analytics[code]['items'].keys():
                                
                                if domain not in connections[code]:
                                    
                                    print "[*] Discovered new domain: %s" % domain
                                    
                                    connections[code].append(domain)

    return connections    

#
# Graph the connections so we can visualize in Gephi or other tools
#
def graph_connections(connections,domains,graph_file):
    
    graph = networkx.Graph()
    
    for connection in connections:
        
        # add the tracking code to the graph
        graph.add_node(connection,{"type":"tracking_code"})
        
        for domain in connections[connection]:
            
            # if it was one of our original domains we set the attribute appropriately
            if domain in domains:
                
                graph.add_node(domain,{"type":"source_domain"})
                
            else:
                
                # this would be a discovered domain so the attribute is different
                graph.add_node(domain,{"type":"domain"})
                
            # now connect the tracking code to the domain
            graph.add_edge(connection,domain)
            
    
    networkx.write_gexf(graph,graph_file)
    
    print "[*] Wrote out graph to %s" % graph_file
    
    return

# build a domain list either by the file passed in
# or create a single item list with the domain passed in
if args.file:
    
    with open(args.file,"rb") as fd:
        
        domains = fd.read().splitlines()
        
else:
    
    domains = [args.domain]
    
# extract the codes from the live domains
connections = extract_tracking_codes(domains)

if len(connections.keys()):

    # use Spyonweb to find connected sites via their tracking codes
    connections = spyonweb_analytics_codes(connections)

    # request full domain reports from Spyonweb to tease out any other connections
    connections = spyonweb_domain_reports(connections)
    
    # now create a graph of the connections
    graph_connections(connections,domains,args.graph)
    
else:
    
    print "[!] No tracking codes found!"
    sys.exit(0)


print "[*] Finished! Open %s in Gephi and have fun!" % args.graph