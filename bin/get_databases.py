import json
import sys
import os

GRAPH_DB_TYPE = os.environ["GRAPH_DB_TYPE"]

data = json.load(sys.stdin)

if GRAPH_DB_TYPE.lower() == "stardog":
    for db in data["databases"]:
        print(db)
elif GRAPH_DB_TYPE.lower() == "jena":
    for db in data["datasets"]:
        print(db["ds.name"].replace("/", ""))
else:
    raise Exception("Unknown graph DB")
