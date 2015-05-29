import click
import sys
from termcolor import colored
from tabulate import tabulate
from datetime import datetime
import json
import requests

LOCAL_JENKINS_PORT=8080
PROTOCOL_SUFFIX="api/json?pretty=true"
DEBUG=False
TEST_SUITES = ["integration", "euclid"]

def endpoint():
    return "http://localhost:%d" % LOCAL_JENKINS_PORT

def dbg(msg):
    if DEBUG:
        print msg

def get(url):
    return requests.get(endpoint() + url)

def getjson(path):
    j = get(path + "/" + PROTOCOL_SUFFIX).text
    dbg(j)
    return json.loads(j)
    

@click.group()
def cli():
    pass

def all_project_builds(project_name):
    try:
        return getjson("/job/" + project_name)["builds"]
    except:
        sys.stderr.write("No such job in Jenkins\n")
        sys.exit(1)


def get_build(name, number):
    return getjson("/job/%s/%d" % (name, number))


def get_build_envars(name, number):
    return getjson("/job/%s/%d/injectedEnvVars" % (name, number))['envMap']


def tests_by_tag(test_suite, branch):
    project = "%s-test-%s" % (branch, test_suite)
    builds = all_project_builds(project)
    r = {}

    for b in builds:
        n = b["number"]
        envars = get_build_envars(project, n)
        status = get_build(project, n)
        if not 'TAG' in envars:
            continue

        tag = envars['TAG']
        if tag in r:
            continue
        r[tag] = {
            "env" : envars,
            "status" : status
        }
    return r

def status_rep(status):
    if status['building']:
        return "..."
    if status['result'] == 'SUCCESS':
        return colored("V", "green")
    return colored("X", "red")

@cli.command()
@click.argument("branch")
@click.option("--limit", type=click.types.INT, default=20)
@click.option("--debug", is_flag=True, default=False)
def armada(branch, debug, limit):
    global DEBUG
    DEBUG = debug
    build_project = "%s-build-docker" % branch

    builds = all_project_builds(build_project)

    results = {}
    tests = { suite : tests_by_tag(suite, branch) for suite in TEST_SUITES }
    
    tags_seen = set()
    for b in builds:
        n = b["number"]
        dbg("Processing build %d" % n)
        build_result = get_build(build_project, n)
        envars = get_build_envars(build_project, n)
        try:
            r = {
                'details' : build_result,
                'number' : n,
                'tag' : envars['TAG'],
                'deployable': False,
                'build' : '',
            }
            for suite in TEST_SUITES:
                r["%s-test" % suite] = ''
        except Exception, e:
            dbg("Error processing build %d: " % n + str(e))
            continue

        ts = build_result['timestamp']
        
        r['time'] = datetime.fromtimestamp(ts / 1000)

        if r['tag'] in tags_seen:
            continue
        tags_seen.add(r['tag'])

        r['build'] = status_rep(build_result)

        if build_result['result'] == "SUCCESS":
            for suite in TEST_SUITES:
                tag = r['tag']
                r["%s-test" % suite] = status_rep(tests[suite][tag]['status'])

        results[n] = r
    headers = ["#", "time", "tag", "build"]
    for suite in TEST_SUITES:
        headers.append("%s-test" % suite[:6])
    rows = []

    build_numbers = list(reversed(sorted(results.keys())))
    if limit:
        build_numbers = build_numbers[:limit]
    for n in build_numbers:
        r = results[n]
        row = [n, r["time"], r["tag"], r["build"]]
        for suite in TEST_SUITES:
            dbg(r)
            row.append(r["%s-test" % suite])
        rows.append(row)

    print tabulate(rows, headers=headers)
    


if __name__ == "__main__":
    cli()
