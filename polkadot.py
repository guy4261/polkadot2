#!/usr/bin/env python
"""The polkadot system.

Usage: $ ./polkadot.py design.gv design.styled.gv
"""
import argparse
import base64
import json
import os
import shutil
import sys
from ast import literal_eval
from subprocess import getstatusoutput
from typing import Dict, List, Optional
from urllib.parse import urlparse

import pydot

DEBUG = None
GH = shutil.which("gh")
REPOS_KEYWORD = "repos"

CONFIG_FILE = "~/.polkadot2.json"
CONFIG_FILE = os.path.expanduser(CONFIG_FILE)
print(CONFIG_FILE)
REPOS = None
if os.path.exists(CONFIG_FILE):
    config = json.load(open(CONFIG_FILE))
    REPOS = config.get("repos", dict())
else:
    REPOS = dict()


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("INPUT_PATH", type=str, help="design.gv")
    parser.add_argument("OUTPUT_PATH", type=str, help="design.styled.gv", default=None)
    return parser


def dotfile_read(dot_file_path: str) -> pydot.core.Graph:
    graph = pydot.graph_from_dot_file(dot_file_path)
    assert isinstance(graph, list) and len(graph) == 1
    graph = graph[0]
    return graph


def get_nodes(graph: pydot.core.Graph) -> List[pydot.core.Node]:
    todo = [graph]
    rv = []
    while len(todo):
        current = todo.pop()
        rv.extend(current.get_nodes())
        todo.extend(current.get_subgraphs())
    return rv


def clean(s: Optional[str]) -> Optional[str]:
    try:
        return literal_eval(s)
    except:
        return s


def get_url(node: pydot.core.Node) -> str:
    return clean(node.get_attributes().get("URL"))


def get_fingerprint(node: pydot.core.Node) -> str:
    return clean(node.get_attributes().get("fingerprint"))


def get_github_public_url(url: str) -> str:
    """
    https://github.com/guy4261/polkadot/blob/main/README.md
    https://github.com/guy4261/polkadot/blob/interim.turkey/README.md

    https://raw.githubusercontent.com/guy4261/polkadot/main/README.md
    https://raw.githubusercontent.com/guy4261/polkadot/interim.turkey/README.md

    https://github.com/guy4261/polkadot/tree/main
    https://github.com/guy4261/polkadot/tree/interim.turkey

    $ gh api repos/guy4261/polkadot/contents/README.md
    """
    pass


def get_url_contents(url: str, local_first: bool = True, /, cache={}) -> str:
    """

    >>> urlparse("https://github.com/guy4261/polkadot2/blob/main/polkadot.py")
    ParseResult(scheme='https', netloc='github.com', path='/guy4261/polkadot2/blob/main/polkadot.py', params='', query='', fragment='')

    $ gh api repos/guy4261/polkadot/contents/README.md --jq '.content' | base64 --decode
    """
    if url in cache:
        return cache[url]
    """
    {
        "repos": {
            "https://github.com/guy4261/polkadot2": "/Users/guyr/Documents/polkadot2"
        }
    }
    """
    if local_first:
        p = urlparse(url)
        # >>> urlparse("https://github.com/guy4261/polkadot2/blob/main/polkadot.py")
        # ParseResult(scheme='https', netloc='github.com', path='/guy4261/polkadot2/blob/main/polkadot.py', params='', query='', fragment='')
        user, reponame, blob, branch, path = p.path.strip(os.path.sep).split(
            os.path.sep, 4
        )
        repo = f"{p.scheme}://{p.netloc}/{user}/{reponame}"
        print("repo => ", repo)
        print(REPOS)
        local = REPOS.get(repo)
        if local is not None:
            return open(os.path.join(local, path)).read()

    cmd = f"{GH} api {os.path.join(REPOS_KEYWORD, urlparse(url).path.strip(os.path.sep))} --jq '.content'"
    cmd = cmd.replace("blob/main", "contents", 1)
    status, output = getstatusoutput(cmd)
    print(cmd, "=>", status)
    assert status == 0, output
    contents = base64.b64decode(output)
    contents = contents.decode("utf-8")
    cache[url] = contents
    return contents


def normalize(s: str) -> List[str]:
    return "\n".join([line.strip() for line in s.splitlines() if len(line.strip()) > 0])


def contains(fingerprint: str, content: str) -> bool:
    assert isinstance(fingerprint, str) and len(fingerprint) > 0
    assert isinstance(content, str) and len(content) > 0

    if fingerprint[0] == fingerprint[-1] and fingerprint[0] in {'"', "'"}:
        try:
            fingerprint = literal_eval(fingerprint)
        except:
            pass  # so maybe not
    elif (fingerprint[0], fingerprint[-1]) == ("<", ">"):
        fingerprint = fingerprint[1:-1]

    return normalize(fingerprint) in normalize(content)


def apply_style(graph: pydot.core.Graph, results: Dict[str, bool]):
    nodes = get_nodes(graph)
    for a_node in nodes:
        key = clean(a_node.get_name())
        value = results.get(key, None)
        if value in {True, False}:
            a_node.set_style("filled")
            if value is True:
                a_node.set_color("lightgreen")
            else:
                a_node.set_color("red")
    return graph


def polkadot(dot_file_path: str, output_file_path: str):
    assert GH is not None
    graph_object = dotfile_read(dot_file_path)

    node_list = get_nodes(graph_object)

    results = {}
    for a_node in node_list:
        url = get_url(a_node)
        fingerprint = get_fingerprint(a_node)
        if url is not None and fingerprint is not None:
            contents = get_url_contents(url)
            a_result = contains(fingerprint, contents)
        else:
            a_result = None
        name = clean(a_node.get_name())
        results[name] = a_result

    styled_graph = apply_style(graph_object, results)

    def dotfile_write(graph: pydot.core.Graph, path: str):
        open(path, "w").write(str(graph).strip() + "\n")

    dotfile_write(styled_graph, output_file_path)
    os.system(f"dotsvg {output_file_path}")
    global DEBUG
    DEBUG = locals()
    return styled_graph


def main():
    parser = get_parser()
    args = parser.parse_args()
    dot_file_path = args.INPUT_PATH
    output_file_path = args.OUTPUT_PATH
    if output_file_path is None:
        head, tail = dot_file_path.rsplit(".", 1)
        output_file_path = f"{head}.styled.{tail}"
        verb = "Overwriting" if os.path.exists(output_file_path) else "Using"
        print(f"{verb} {output_file_path} as the output path")
    polkadot(dot_file_path, output_file_path)


if __name__ == "__main__":
    main()


# sys.exit(1)
