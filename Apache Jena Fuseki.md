# Apache Jena Fuseki

Open-source [[SPARQL]] server from the [Apache Jena](https://jena.apache.org/documentation/fuseki2/) project, providing HTTP endpoints for an [[RDF]] triplestore/[[quadstore]].

## In Flexo MMS

Fuseki is the reference quadstore backend for Flexo. It binds locally on port 3030 and exposes three endpoints ([flexo-mms-layer1-service](https://github.com/Open-MBEE/flexo-mms-layer1-service)):

| Endpoint | Fuseki path | Purpose |
|----------|-------------|---------|
| SPARQL Query | `/ds/sparql` | Read queries |
| SPARQL Update | `/ds/update` | Write operations |
| [[Graph Store Protocol]] | `/ds/data` | Named graph CRUD |

### Cluster initialization

Before the Layer 1 service can run, the quadstore must be bootstrapped ([Layer 1 docs](https://flexo-mms-deployment-guide.readthedocs.io/en/latest/flexo-mms-layer1-service/index.html)):

1. Generate a `.trig` file: `npx ts-node src/main.ts $APP_URL > cluster.trig`
2. Insert it into the empty Fuseki instance via the GSP endpoint

### Production considerations

Read and write operations can be separated to distinct Fuseki nodes. Flexo env vars `FLEXO_MMS_QUERY_URL` and `FLEXO_MMS_UPDATE_URL` point to different endpoints, with `FLEXO_MMS_MASTER_QUERY_URL` available for strict-consistency reads ([Layer 1 docs](https://flexo-mms-deployment-guide.readthedocs.io/en/latest/flexo-mms-layer1-service/index.html)).

For a complete walkthrough of standing up a local Fuseki-backed Flexo instance, see [[Local Deployment Setup]].

---
← [[Quadstore]] · [[SPARQL]] · [[Flexo Organization Level]]
