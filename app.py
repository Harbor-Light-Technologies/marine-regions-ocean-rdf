import datetime
import json
import logging
import requests
import sys
import unicodedata
import yaml

from datetime import timedelta
from rdflib import BNode, ConjunctiveGraph, Graph, Literal, Namespace, RDF, URIRef, plugin
from rdflib.namespace import DCTERMS, RDFS, XSD
from rdflib.serializer import Serializer
from urllib.parse import urlparse
from SPARQLWrapper import SPARQLWrapper, JSON

logging.basicConfig(
    level=logging.INFO # allow DEBUG level messages to pass through the logger
)

# {TypeID} : {Type Name}
MR_TYPES = {
    #22: 'Island',
    #28: 'Strait',
    #30: 'Ridge',
    #31: 'Channel',
    #37: 'Deep',
    #42: 'Island Group',
    #45: 'Lake',
    #46: 'River',
    #47: 'Lagoon',
    #48: 'Fjord',
    #49: 'General Region',
    #52: 'Estuary',
    #54: 'Canal',
    #70: 'EEZ',
    #81: 'Seachannel',
    #128: 'Cape',
    #129: 'Sampling Station',
    #172: 'Sea floor',
    #243: 'Realm',
    #244: 'Marine Province',
    #245: 'Marine Ecoregion of the World (MEOW)',

    19: 'Ocean',
    20: 'Sea',
    24: 'Gulf',
    25: 'Basin',
    39: 'Bay',
    56: 'Sound',
    57: 'Seamount(s)',
    69: 'Coast',
    75: 'General Sea Area',
    79: 'Bank',
    88: 'Reef',
    112: 'Shoal',
    157: 'Beach',
    168: 'Glacier',
    170: 'Cove',
    272: 'IHO Sea Area',  
}

RDF_FORMAT = 'turtle'
RDF_EXT = 'ttl'

OUTPUT = '/output/'

HTTP_STATUS_OK = 200
HTTP_STATUS_NOT_FOUND = 404

GET_TYPES = 'https://marineregions.org/rest/getGazetteerTypes.json/'
GET_RECORD_BY_TYPE = 'https://marineregions.org/rest/getGazetteerRecordsByType.json/{typename}/?offset={offset}'
GET_RECORD_METADATA = 'https://marineregions.org/rest/getGazetteerRecordByMRGID.jsonld/{mrid}/'
GET_GEOMETRY = 'https://marineregions.org/rest/getGazetteerGeometries.jsonld/{mrid}/'


def writeRDFFile(graph, format, filename):
  logging.debug(graph.serialize(format='ttl'))
  if not os.path.exists(OUTPUT):
    os.makedirs(OUTPUT)
  dest = "{dir}{filename}".format(dir=OUTPUT, filename=filename)
  graph.serialize(destination=dest, format=format)
  logging.info('Wrote file:' + dest)
    
def getRecordMetadata(mrid):
  res = requests.get(GET_RECORD_METADATA.format(mrid=mrid))
  record = res.json()
  return Graph().parse(data=record, format='json-ld')

def getRecordGeometry(mrid):
  res = requests.get(GET_GEOMETRY.format(mrid=mrid))
  record = res.json()
  return Graph().parse(data=record, format='json-ld')
  
def getMRTypes():
  res = requests.get(GET_TYPES)
  if HTTP_STATUS_OK == res.status_code:
    return res.json()
  else:
    logging.error("Error({code}): {msg}".format(code=res.status_code, msg=res.content))
  return None
  
def getMRTypeRecords(type):
  LIMIT = 100 #https://marineregions.org/gazetteer.php?p=webservices&type=rest#!/getGazetteerTypes/getGazetteerTypes
  records = []
  offset=0

  length = None
  while length is None or length >= LIMIT:
    res = requests.get(GET_RECORD_BY_TYPE.format(typename=type, offset=(LIMIT * offset)))
    json = res.json()
    length = len(json)
    if HTTP_STATUS_OK == res.status_code:

      for region in res.json():
        logging.info("{id} - {name} (status={status})".format(id=region['MRGID'], name=region['preferredGazetteerName'], status=region['status']))

      records.extend(res.json())
      offset += 1
    elif HTTP_STATUS_NOT_FOUND == res.status_code:
      logging.debug("No more records, so just ignore")
    else:
      logging.error("Error({code}): {msg}".format(code=res.status_code, msg=res.content))
      return None
    
  return records


for type in MR_TYPES:
  logging.info()
  logging.info("*** {type} ***".format(type=MR_TYPES[type]))
  logging.info()
  records = getMRTypeRecords(MR_TYPES[type])

  for record in records:
    logging.debug("{stat} = {r}".format(r=record, stat=record['status']))
    if 'deleted' != record['status']:

      type_id = "{n}_{t}_{i}".format(n=MR_TYPES[type], t=type, i=record['MRGID'])
      meta = getRecordMetadata(mrid=record['MRGID'])
      writeRDFFile(graph=meta, format=RDF_FORMAT, filename="{id}_{name}.{ext}".format(id=type_id, name='metadata', ext=RDF_EXT)
      
      geom = getRecordGeometry(mrid=record['MRGID'])
      writeRDFFile(graph=geom, format=RDF_FORMAT, filename="{id}_{name}.{ext}".format(id=type_id, name='geometry', ext=RDF_EXT)
    else:
      logging.warning("*** Skipping deleted record: {r}".format(r=record['MRGID'])
    
