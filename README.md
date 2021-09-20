# An util to export query history of presto to elasticsearch.
It's an implementation of the QueryTracker decribe in the link https://github.com/prestodb/presto/issues/12185


## Attention
```bash
# Only test on elasticsearch 7.x. You may need to change some code if you want to adopt the other version.
# Elasticsearch 7.x
elasticsearch

# Elasticsearch 6.x
elasticsearch>=6.0.0,<7.0.0

# Elasticsearch 5.x
elasticsearch>=5.0.0,<6.0.0

# Elasticsearch 2.x
elasticsearch2
```

## Usage

### Initial elasticsearch
```bash
# create ilm policy
PUT _ilm/policy/presto_queries_policy
{
  "policy": {
    "phases": {
      "hot" : {
        "min_age" : "0ms",
        "actions" : {
          "rollover" : {
            "max_size" : "10gb",
            "max_age" : "30d"
          }
        }
      }
    }
  }
}

# create index template
PUT _template/presto_queries_template
{
  "index_patterns": ["presto_queries-*"],
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas" : 2,
    "index": {
        "lifecycle": {
            "name": "presto_queries_policy",
            "rollover_alias": "presto_queries"
        }
    }
  },
  "mappings": {
    "properties": {
      "query": {
          "type": "text"
      },
      "queryStats.elapsedTime": {
          "type": "double"
      },
      "queryStats.queuedTime": {
          "type": "double"
      },
      "queryStats.resourceWaitingTime": {
          "type": "double"
      },
      "queryStats.executionTime": {
          "type": "double"
      },
      "queryStats.analysisTime": {
          "type": "double"
      },
      "queryStats.totalPlanningTime": {
          "type": "double"
      },
      "queryStats.finishingTime": {
          "type": "double"
      },
      "queryStats.totalScheduledTime": {
          "type": "double"
      },
      "queryStats.totalCpuTime": {
          "type": "double"
      },
      "queryStats.totalBlockedTime": {
          "type": "double"
      },
      "queryStats.userMemoryReservation": {
          "type": "long"
      },
      "queryStats.totalMemoryReservation": {
          "type": "long"
      },
      "queryStats.peakUserMemoryReservation": {
          "type": "long"
      },
      "queryStats.peakTotalMemoryReservation": {
          "type": "long"
      },
      "queryStats.peakTaskUserMemory": {
          "type": "long"
      },
      "queryStats.peakTaskTotalMemory": {
          "type": "long"
      },
      "queryStats.rawInputDataSize": {
          "type": "long"
      },
      "queryStats.processedInputDataSize": {
          "type": "long"
      },
      "queryStats.outputDataSize": {
          "type": "long"
      },
      "queryStats.physicalWrittenDataSize": {
          "type": "long"
      },
      "queryStats.logicalWrittenDataSize": {
          "type": "long"
      },
      "queryStats.spilledDataSize": {
          "type": "long"
      }
    }
  }
}

# create index and alias
PUT /<presto_queries-{now{yyyy.MM.dd}}>
PUT /<presto_queries-{now{yyyy.MM.dd}}>/_alias/presto_queries
GET /<presto_queries-{now{yyyy.MM.dd}}>/_alias

# delete index and template, then recreate. when test
DELETE /<presto_queries-{now{yyyy.MM.dd}}>
DELETE /_template/presto_queries_template
```

### Config
```bash
# create config file from template config.json.example
{
    # API endpoint url of presto
    "presto": {
        "endpoint": "http://127.0.0.1:8080/v1/query",
        "auth": {
            "username": "test",
            "password": "test"
        }
    },
    # Elasticsearch connection
    "elasticsearch": {
        "hosts": ["127.0.0.1"],
        "port": 9200,
        "scheme": "http",
        "username": "",
        "password": "",
        "index": "presto_queries"
    },
    "log": {
        "level": "info"
    },
    "cache_file": "queries.cache", # Just give a name here.
    "schedule": {
        "query_export": 1, # Interval to schedule to run task query_export. Unit is minutes.
        "clear_cache": 1 # Interval to schedule to run task clear_cache. Unit is minutes.
    },
    "expire": 1440 # cache expire time. Unit is minutes.
}
```

### Build docker image on Mac M1
```bash
docker buildx create --use --name mbuilder
docker buildx inspect --bootstrap
docker buildx build --platform linux/amd64 --load -t queryexporter .
```

### Run in docker
```bash
cd docker
docker-compose build
docker-compose up -d
```

### Run in K8S
```bash
cd k8s; kubectl apply -k .
# or deploy via helm
cd helm; helm install --values values.yaml olap queryexporter/
```
