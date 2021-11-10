#
#
# Script that extracts a dashboard (given the slug as an argument) into a directory that contains the queries and 
#   json file. This file is then suitable for importing back into redash. 
# The json file has to be in the directory above the sql files. 
#

# TODO: pass in key (or log in)
#   Get order to work correctly
#   Fix missing parameter size_gb issue for problem-areas dashboard
#   Does not support dashboard parameters with multiple queries

import os
import ssl
import json
import requests
import logging
import sys
import argparse

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("requests").setLevel("ERROR")

# The Redash instance you're copying from:
ORIGIN = "http://localhost:5002"

ORIGIN_API_KEY = "noTarkGRudp4BWpNfDezNL1mSnBs0g4Mnn4WVjvK"  # admin API key

# The Redash account you're copying into:

DIRPATH = "sql/"
DATA_SOURCEi = {
    1: 5
}

meta = {
    "queries": [],
    "visualization": {},
    "dashboards": {}
}


def api_request(api, api_key):
    response = requests.get(ORIGIN + api, headers=auth_headers(api_key))
    response.raise_for_status()

    return response.json()


def auth_headers(api_key):
    return {
        "Authorization": "Key {}".format(api_key)
    }


def extract_query_from_widget(widget, dirpath):
    query = widget['visualization']['query']

    print "   exporting query of: {}".format(query['name'])

    data = {
        "is_archived": query['is_archived'],
        #"schedule": query['schedule'],
    	"schedule": 86400,
        "description": query['description'],
        "name": query['name'],
        "report_id": query['name'],

        "redash_query_sql_filename":   dirpath+'/'+query['name'].lower().replace(" ", "_").replace("/", "__").replace(":", "-") + "_redash_query.sql",
    }
    sql = open(data['redash_query_sql_filename'], "w")
    sql.write(query['query'])
    sql.close
    extract_visualization(widget, data, query['id'])

    return query['id']


def extract_visualization(viz, qdata, query_id):
    v = viz['visualization']
    data_arr = []

    order = viz['options']['position']['row'] * 10 + viz['options']['position']['col']

    if v['type'] == "TABLE":
	   meta['queries'].append((order, qdata))
	   return

    par_arr = []

    v['options'].pop('customCode', None)
    v['options'].pop('valuesOptions', None)
    v['options'].pop('seriesOptions', None)

    v['options']['visualization_id'] = v['name'].replace(" ", "_")+"{}".format(v['id'])

    local_data = qdata
# Figure out how to get the order of the widgets in
#   if 'position' in viz['options']:
    local_data['options'] = viz['options']

    data = {
                "name": v['name'],  # .lower().replace(" ", "_"),
                "description": v['description'],
                "options": v['options'],
                "type": v['type']
    }
#    if viz['options']['position']['sizeX'] < 4 : 
#	    local_data['width'] = viz['width']
#	    data['widget_width'] = "half"

    if 'parameters' in v['query']['options'] and len(v['query']['options']['parameters']) >0:
        # print v['query']['options']['parameters']

        for param in v['query']['options']['parameters']:

            pardata = {
                "title": param['title'],
                "name":  param['name'],
                "value": param['value'],
                "type": "number"
            }
            if pardata['name'] == "volume":
                pardata['type'] = "text"
            #if param['type'] == "widget-level":
            pardata['global'] = False
# Force it widget level
            #else:
            #    pardata['global'] = True

            par_arr.append(pardata)


#        if 'parameterMappings' in viz['options']:
# Never entered

#            for param, val in viz['options']['parameterMappings'].items():

#                parmap = {
#                    "title": param,
#                    "name":  val['name'],
#                    "value": pardata['value'],
#                    "type": "number"
#                }
#                if parmap['name'] == "volume":
#                    pardata['type'] = "text"

#                par_arr.append(parmap)
	     

        local_data['parameters'] = par_arr

    local_data['report_id'] = local_data['report_id']+"{}".format(v['id']) # fix up report id to cover for duplicates



    data_arr.append(data)
    local_data['visualization'] = data_arr
    meta['queries'].append((order, local_data))


def import_dashboard(dashname, api_key):


    try:
       path = "/api/dashboards/{}".format(meta['dashboards'])
       d = api_request(path , api_key)

    except Exception as ex:
       print "Cannot connect, or no such dashboard: ", meta['dashboards']
       sys.exit(1)

    # Echo dashboard
    # print json.dumps(d, indent=3)

    data = {'name': d['name']}

    for widget in d['widgets']:
        data = {
            'name': d['name'],
            'dashboard_id': d['slug'],
            'options': widget['options'],
            'visualization': None,
            'report_id': None,
	    'redash_query_sql_filename': None
        }

        if 'visualization' in widget:
            data['visualization'] = meta['visualization'].get(widget['visualization']['id'])

            qid = extract_query_from_widget(widget, dirpath)


def export_dashboard(dirpath):
    print "Exporting   " + dirpath
    first_item = True
	
    with open(dirpath+'/'+dirpath+'.json', "w") as dash:
	dash.write("[\n")
	for query in sorted(meta['queries'], key=lambda _ordered_query_tuple: _ordered_query_tuple[0]):

	    if first_item:
		first_item = False
		json.dump(query[1], dash, indent=3, sort_keys=True)
 	    else:
		dash.write(",\n ")
		json.dump(query[1], dash, indent=3, sort_keys=True)
	dash.write("]\n")



def import_all(dirpath, api_key):
    try:
        ssl._create_default_https_context= ssl._create_unverified_context


    #    print ( dirpath)
        if not os.path.exists(dirpath):
          try:
             os.mkdir(dirpath, 0755)
          except Exception as ex:
             logging.exception(ex)

        import_dashboard(dirpath, api_key)
    except Exception as ex:
        logging.exception(ex)
    export_dashboard(dirpath)


if __name__ == '__main__':

   parser = argparse.ArgumentParser(description='Pass a dashboard name.')
   parser.add_argument('dashboard',  help='Dashboard nanem to export')
   parser.add_argument('api_key',  help='API Key for redash')
#   parser.add_argument('--list', action='store_true', help='List dashboard slugs')
   args = parser.parse_args()
   print "Looking for dashboard: "+args.dashboard
   
   dirpath = args.dashboard.replace(' ', '_').title()
   meta['dashboards'] = args.dashboard

   import_all(dirpath, args.api_key) 
