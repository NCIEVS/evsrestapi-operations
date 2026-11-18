#!/usr/bin/env python3
"""Run on the graph server after Jena starts to verify SERVICE is denied."""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class Canary(BaseHTTPRequestHandler):
    hits = 0

    def do_GET(self):
        type(self).hits += 1
        self.send_response(200)
        self.end_headers()

    do_POST = do_GET

    def log_message(self, *_args):
        pass


def query(endpoint, sparql, escaped=False):
    body = urlencode({"query": sparql})
    if escaped:
        body = body.replace("SERVICE", "%53ERVICE")
    request = Request(
        endpoint,
        data=body.encode("ascii"),
        headers={"Accept": "application/sparql-results+json",
                 "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


def verify(base_url):
    Canary.hits = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), Canary)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    target = "http://127.0.0.1:{}/canary".format(server.server_port)
    forms = {
        "direct": "SELECT * WHERE {{ SERVICE <{0}> {{ ?s ?p ?o }} }}",
        "nested": "SELECT * WHERE {{ {{ SELECT * WHERE {{ SERVICE <{0}> {{ ?s ?p ?o }} }} }} }}",
        "SILENT": "SELECT * WHERE {{ SERVICE SILENT <{0}> {{ ?s ?p ?o }} }}",
        "variable": "SELECT * WHERE {{ VALUES ?service {{ <{0}> }} SERVICE ?service {{ ?s ?p ?o }} }}",
        "escaped": "SELECT * WHERE {{ SERVICE <{0}> {{ ?s ?p ?o }} }}",
    }
    failures = []
    try:
        for dataset in ("NCIT2", "CTRP"):
            endpoint = "{}/{}/query".format(base_url.rstrip("/"), dataset)
            status, body = query(endpoint, "SELECT * WHERE { } LIMIT 1")
            if status != 200:
                failures.append("{} read: HTTP {}".format(dataset, status))
            for name, template in forms.items():
                status, body = query(endpoint, template.format(target), name == "escaped")
                # SPARQL SILENT masks the execution error and returns HTTP 200.
                # The canary must still see no request.
                if name == "SILENT" and status != 200:
                    failures.append("{} SILENT: HTTP {}, expected masked denial".format(dataset, status))
                elif name != "SILENT" and (status < 400 or "SERVICE execution disabled" not in body):
                    failures.append("{} {}: HTTP {}, expected SERVICE denial".format(dataset, name, status))
                if Canary.hits:
                    failures.append("{} {}: canary received outbound HTTP".format(dataset, name))
        if failures:
            raise RuntimeError("; ".join(failures))
        print("NCIT2 and CTRP: reads pass; SERVICE disabled; SILENT masked; no canary HTTP hits")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:3030", help="Fuseki base URL")
    arguments = parser.parse_args()
    verify(arguments.url)
