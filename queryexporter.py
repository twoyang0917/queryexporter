#!/usr/bin/env python3

import os
import json
import requests
import schedule
import time
import pickledb
import logging
import logging.handlers
import sys
import traceback

from datetime import datetime
from elasticsearch import Elasticsearch
from pytimeparse import parse
from humanfriendly import parse_size

import urllib3
urllib3.disable_warnings()

class QueryExporter(object):
    def __init__(self):
        # get absolute path of this file
        self.prefix_path=os.path.dirname(os.path.realpath(__file__))

        # load configuration
        with open(os.path.join(self.prefix_path, 'config.json')) as f:
            self.config = json.load(f)
            f.close()

        # initial logging
        self.logger = logging.getLogger()
        numeric_level = getattr(logging, self.config['log']['level'].upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % self.config['log']['level'])
        self.logger.setLevel(numeric_level)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)-8s] [%(name)-15s] %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # initial elasticsearch connection
        self.es = Elasticsearch(
            hosts = self.config['elasticsearch']['hosts'],
            scheme = self.config['elasticsearch']['scheme'],
            port = self.config['elasticsearch']['port'],
            http_auth=(self.config['elasticsearch']['username'], self.config['elasticsearch']['password']),
        )

        # initial key-value cache
        self.cache = pickledb.load(os.path.join(self.prefix_path, self.config['cache_file']), False)

    def handle_output(self, query):
        middle_result = self._remove_useless_details(query)
        return self._human_readable_to_number(middle_result)

    # convert human readable time & size to number for sorting.
    def _human_readable_to_number(self, query):
        query['queryStats']['elapsedTime'] = parse(query['queryStats']['elapsedTime']) or 0
        query['queryStats']['queuedTime'] = parse(query['queryStats']['queuedTime']) or 0
        query['queryStats']['resourceWaitingTime'] = parse(query['queryStats']['resourceWaitingTime']) or 0
        query['queryStats']['executionTime'] = parse(query['queryStats']['executionTime']) or 0
        query['queryStats']['analysisTime'] = parse(query['queryStats']['analysisTime']) or 0
        query['queryStats']['totalPlanningTime'] = parse(query['queryStats']['totalPlanningTime']) or 0
        query['queryStats']['finishingTime'] = parse(query['queryStats']['finishingTime']) or 0
        query['queryStats']['totalScheduledTime'] = parse(query['queryStats']['totalScheduledTime']) or 0
        query['queryStats']['totalCpuTime'] = parse(query['queryStats']['totalCpuTime']) or 0
        query['queryStats']['totalBlockedTime'] = parse(query['queryStats']['totalBlockedTime']) or 0

        query['queryStats']['userMemoryReservation'] = parse_size(query['queryStats']['userMemoryReservation']) or 0
        query['queryStats']['totalMemoryReservation'] = parse_size(query['queryStats']['totalMemoryReservation']) or 0
        query['queryStats']['peakUserMemoryReservation'] = parse_size(query['queryStats']['peakUserMemoryReservation']) or 0
        query['queryStats']['peakTotalMemoryReservation'] = parse_size(query['queryStats']['peakTotalMemoryReservation']) or 0
        query['queryStats']['peakTaskUserMemory'] = parse_size(query['queryStats']['peakTaskUserMemory']) or 0
        query['queryStats']['peakTaskTotalMemory'] = parse_size(query['queryStats']['peakTaskTotalMemory']) or 0
        query['queryStats']['rawInputDataSize'] = parse_size(query['queryStats']['rawInputDataSize']) or 0
        query['queryStats']['processedInputDataSize'] = parse_size(query['queryStats']['processedInputDataSize']) or 0
        query['queryStats']['outputDataSize'] = parse_size(query['queryStats']['outputDataSize']) or 0
        query['queryStats']['physicalWrittenDataSize'] = parse_size(query['queryStats']['physicalWrittenDataSize']) or 0
        query['queryStats']['logicalWrittenDataSize'] = parse_size(query['queryStats']['logicalWrittenDataSize']) or 0
        query['queryStats']['spilledDataSize'] = parse_size(query['queryStats']['spilledDataSize']) or 0
        return query

    # no need such kind information only when debugging a SQL.
    # it will exceed the limitation if keep these information.
    # Limit of total fields [1000] in index has been exceeded.
    def _remove_useless_details(self, query):
        if 'outputStage' in query:
            del query['outputStage']
        if 'operatorSummaries' in query['queryStats']:
            del query['queryStats']['operatorSummaries']
        if 'stageGcStatistics' in query['queryStats']:
            del query['queryStats']['stageGcStatistics']

        return query

    def get_resp(self, url):
        resp = ''
        while resp == '':
            try:
                if 'auth' in self.config['presto']:
                    resp = requests.get(url, verify=False,
                        auth=(self.config['presto']['auth']['username'], self.config['presto']['auth']['password']))
                else:
                    resp = requests.get(url)
                break
            except Exception as e:
                self.logger.warn("Connection refused by the server..")
                self.logger.debug((repr(e)))
                self.logger.debug("traceback.format_exc():\n%s" % traceback.format_exc())
                time.sleep(5)
                self.logger.warn("Retring to connect to %s", url)
                continue

        return resp

    def get_query(self, queryId):
        if self.cache.get(queryId):
            self.logger.info("Skip query %s, HIT cache. It's already inserted into elasticsearch.", queryId)
            return None

        url = self.config['presto']['endpoint'] + '/' + queryId
        resp = self.get_resp(url)
        self.logger.info("GET %s [status: %s request: %ss]", url, resp.status_code, resp.elapsed.total_seconds())
        if resp.status_code == requests.codes.ok:
            return self.handle_output(resp.json())
        else:
            return None

    def get_queries(self):
        queries = self.get_resp(self.config['presto']['endpoint']).json()
        queries_doc = []
        for q in queries:
            if q['state'] in ['FINISHED', 'FAILED']:
                query_doc = self.get_query(q['queryId'])
                if query_doc is not None:
                    queries_doc.append(query_doc)
            else:
                self.logger.info("Skip query %s, It's in %s state. Not FINISHED/FAILED yet.", q['queryId'], q['state'])

        return queries_doc

    def save_to_es(self, id, body):
        resp = self.es.index(index=self.config['elasticsearch']['index'], id=id, body=body)
        self.logger.info("Result of es.index is %s.", resp['result'])

        self.cache.set(id, datetime.now())
        self.logger.info("Cache query %s.", id)

    def exporter(self):
        for q in self.get_queries():
            self.save_to_es(id=q['queryId'], body=q)

    def clear_cache(self):
        for q in list(self.cache.getall()):
            duration = datetime.now() - self.cache.get(q)
            duration_in_minutes = divmod(duration.total_seconds(), 60)[0]
            if duration_in_minutes > self.config['expire']:
                self.cache.rem(q)
                self.logger.info("Remove %s from cache. duration %s minutes, longer than expire time %s minutes.", q, duration_in_minutes, self.config['expire'])

    def run(self):
        schedule.every(self.config['schedule']['query_export']).minutes.do(self.exporter)
        schedule.every(self.config['schedule']['clear_cache']).minutes.do(self.clear_cache)
        while True:
            schedule.run_pending()
            time.sleep(3)

if __name__ == '__main__':
    QueryExporter().run()

