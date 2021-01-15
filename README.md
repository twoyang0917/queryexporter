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
    "number_of_replicas" : 0,
    "index": {
        "lifecycle": {
            "name": "presto_queries_policy",
            "rollover_alias": "presto_queries"
        }
    }
  }
}

# create index and alias
PUT /presto_queries-000001
PUT /presto_queries-000001/_alias/presto_queries
```

### Config
```bash
# create config file from template config.json.example
{
    # API endpoint url of presto
    "presto": {
        "endpoint": "http://127.0.0.1:8080/v1/query"
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

### Run in docker
```bash
docker-compose build
docker-compose up -d
```
