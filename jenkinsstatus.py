import click
import json
import requests

LOCAL_JENKINS_PORT=8080
PROTOCOL_SUFFIX="api/json?pretty=true"

def endpoint():
    return "http://localhost:%d" % LOCAL_JENKINS_PORT

def get(url):
    return requests.get(endpoint() + url)

def getjson(path):
    return json.loads(get(path + "/" + PROTOCOL_SUFFIX).text)
    

@click.group()
def cli():
    pass


@cli.command()
@click.argument("branch")
def armada(branch):
    build_job = "%s-build-docker" % branch

    print getjson("/job/" + build_job)


if __name__ == "__main__":
    cli()
