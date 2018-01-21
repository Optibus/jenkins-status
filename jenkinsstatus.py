import click
import sys
from termcolor import colored
from tabulate import tabulate
from datetime import datetime
import json
import requests

LOCAL_JENKINS_PORT = 8080
PROTOCOL_SUFFIX = "api/json?pretty=true"
DEBUG = False
NO_COLOR = False

TEST_SUITES = ["integration", "euclid", "e2e"]


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


def all_project_builds(project_name, stderr_on_missing):
    try:
        return getjson("/job/" + project_name)["builds"]
    except:
        if stderr_on_missing:
            sys.stderr.write("No such job in Jenkins\n")

        return []


def get_build(name, number):
    return getjson("/job/%s/%d" % (name, number))


def get_build_envars(name, number):
    return getjson("/job/%s/%d/injectedEnvVars" % (name, number))['envMap']


def tests_by_tag(test_suite, branch, limit):
    project = "%s-test-%s" % (branch, test_suite)
    builds = all_project_builds(project, stderr_on_missing=False)
    r = {}
    builds.sort(key=lambda b: int(b["number"]))
    for b in builds[-limit:]:
        n = b["number"]
        try:
            envars = get_build_envars(project, n)
            status = get_build(project, n)
            if 'TAG' not in envars:
                continue

            tag = envars['TAG']
            r[tag] = {
                "env": envars,
                "status": status
            }
        except Exception, e:
            dbg("Error processing build %d: " % n + str(e))
            continue
    return r


def status_rep(status):
    global NO_COLOR
    if status['building']:
        return "..."
    if status['result'] == 'SUCCESS':
        return "V" if NO_COLOR else colored("V", "green")
    return "X" if NO_COLOR else colored("X", "red")


@cli.command()
@click.argument("branch")
@click.option("--limit", type=click.types.INT, default=20)
@click.option("--debug", is_flag=True, default=False)
@click.option("--no-color", is_flag=True, default=False)
def armada(branch, debug, limit, no_color):
    armada_builds(branch, debug, limit, no_color)


def armada_builds(branch, debug=False, limit=20, no_color=False, no_print=False, stderr_on_missing=True):
    global DEBUG
    DEBUG = debug
    global NO_COLOR
    NO_COLOR = no_color if not no_print else True
    build_project = "%s-build-docker" % branch

    builds = all_project_builds(build_project, stderr_on_missing=stderr_on_missing)
    if not builds:
        return []

    results = {}
    tests = {suite: tests_by_tag(suite, branch, limit) for suite in TEST_SUITES}

    tags_seen = set()
    for b in builds:
        n = b["number"]
        dbg("Processing build %d" % n)
        try:
            build_result = get_build(build_project, n)
            envars = get_build_envars(build_project, n)

            r = {
                'details': build_result,
                'number': n,
                'tag': envars['TAG'],
                'deployable': False,
                'build': '',
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
                if tag in tests[suite]:
                    r["%s-test" % suite] = status_rep(tests[suite][tag]['status'])

        results[n] = r
    headers = ["#", "time", "tag", "build"]
    for suite in TEST_SUITES:
        headers.append("%s-test" % suite[:6])
    rows = []

    build_numbers = list(reversed(sorted(results.keys())))
    if limit:
        build_numbers = build_numbers[:limit]

    if no_print:
        return [results[x] for x in build_numbers]

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
