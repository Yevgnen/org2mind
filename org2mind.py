#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import copy
import dataclasses
import json
import os
import random
import re
import uuid
from typing import List, Optional


@dataclasses.dataclass
class Node:
    topic: str
    level: int = 0
    id: Optional[str] = dataclasses.field(
        default_factory=lambda: uuid.uuid4().hex)
    isroot: Optional[bool] = False
    expended: Optional[bool] = True
    direction: Optional[str] = 'right'
    children: Optional[List[str]] = dataclasses.field(default_factory=list)
    background_color: Optional[str] = None
    foreground_color: Optional[str] = None

    def add_child(self, node: 'Node'):
        self.children += [node]


def asdict(obj, dict_factory):
    if dataclasses._is_dataclass_instance(obj):
        result = []
        for f in dataclasses.fields(obj):
            value = asdict(getattr(obj, f.name), dict_factory)
            result.append((f.name.replace('_', '-'), value))
        return dict_factory(result)

    if isinstance(obj, tuple) and hasattr(obj, '_fields'):
        return type(obj)(*[asdict(v, dict_factory) for v in obj])

    if isinstance(obj, (list, tuple)):
        return type(obj)(asdict(v, dict_factory) for v in obj)

    if isinstance(obj, dict):
        return type(obj)((asdict(k, dict_factory), asdict(v, dict_factory))
                         for k, v in obj.items())

    return copy.deepcopy(obj)


def get_jsmind():
    return """
<link type="text/css" rel="stylesheet" href="{jsmind}/style/jsmind.css" />
<script type="text/javascript" src="{jsmind}/js/jsmind.js"></script>
<div id="jsmind_container"></div>
<script type="text/javascript">
    var mind = {mind};
    var options = {{
         container: 'jsmind_container',
         theme: '{theme}',
         editable: false
     }};
     var jm = new jsMind(options);
     jm.show(mind);
</script>
"""


def get_majax():
    return """
<script type="text/x-mathjax-config">
    MathJax.Hub.Config({
        displayAlign: "center",
        displayIndent: "0em",
        "HTML-CSS": {
            scale: 100,
            linebreaks: { automatic: "false" },
            webFont: "TeX"
        },
        SVG: {
            scale: 100,
            linebreaks: { automatic: "false" },
            font: "TeX"
        },
        NativeMML: {scale: 100},
        TeX: {
            equationNumbers: {autoNumber: "AMS"},
            MultLineWidth: "85%",
            TagSide: "right",
            TagIndent: ".8em"
        }
    });
</script>
<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.0/MathJax.js?config=TeX-AMS_HTML"></script>
"""


def random_color():
    colors = [
        '#5EBD3E',
        '#FFB900',
        '#F78200',
        '#E23838',
        '#973999',
        '#009CDF',
    ]

    while True:
        color = random.choice(colors)
        if (not hasattr(random_color, 'last_color')
                or color != random_color.last_color):
            break

    random_color.last_color = color

    return color


def org2mind(file_, theme='success', jsmind='jsmind/', text=''):
    re_meta = r'^#\+(.+?):\s+(.+?)$'
    re_heading = r'^(\*+)\s+(.+?)$'
    meta = {'version': 0.2}
    foreground_color = '#ffffff'
    background_color = None
    directions = ['right', 'left']
    direction = 0
    level = -1

    root = Node('root',
                background_color=random_color(),
                foreground_color=foreground_color)
    stack = [root]
    with open(file_) as fd:
        for line in fd:
            line = line.strip()
            if not line:
                continue

            # Parse meta
            match = re.match(re_meta, line)
            if match:
                meta_key, meta_value = match.groups()
                meta[meta_key] = meta_value

                if meta_key.lower() == 'title':
                    root.topic = meta_value

            # Parse headings
            match = re.match(re_heading, line)
            if match:
                stars, heading = match.groups()
                current_level = len(stars)
                node = Node(heading,
                            level=current_level,
                            background_color=background_color,
                            foreground_color=foreground_color)

                if current_level == 1:
                    node.direction = directions[direction]
                    direction = 1 - direction
                    background_color = random_color()
                    node.background_color = background_color

                if current_level <= level:
                    stack = [x for x in stack if x.level < current_level]

                stack[-1].add_child(node)
                stack += [node]

                level = current_level

    mind = {
        'meta': meta,
        'format': 'node_tree',
        'data': asdict(root, dict),
    }

    jsmind = get_jsmind().format(mind=json.dumps(mind),
                                 theme=theme,
                                 jsmind=jsmind)
    html = """
<html>
    <head>
    {mathjax}
    </head>
<body>
    <div hidden>{text}</div>
    {jsmind}
</body>
</html>""".format(jsmind=jsmind, mathjax=get_majax(), text=text)

    return html


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i',
                        '--input',
                        type=str,
                        required=True,
                        help='Input file')
    parser.add_argument('-o',
                        '--output',
                        type=str,
                        default=None,
                        help='Output file')
    parser.add_argument('-H',
                        '--theme',
                        type=str,
                        default='success',
                        help='Theme (default: \'success\')')
    parser.add_argument(
        '-t',
        '--text',
        nargs='+',
        type=str,
        default=[],
        help='Extra text, mainly for mathjax custom commands (default: \'\')')
    parser.add_argument('-m',
                        '--jsmind',
                        type=str,
                        default='jsmind/',
                        help='Directory to jsmind (default: \'jsmind/\')')
    parser.add_argument('--seed',
                        type=int,
                        default=0,
                        help='Seed (default: 0)')

    args = parser.parse_args()  # pylint: disable=redefined-outer-name

    if not args.output:
        args.output = os.path.join(os.path.splitext(args.input)[0] + '.html')

    args.text = '\n'.join(args.text)

    return args


if __name__ == '__main__':
    args = parse_args()

    random.seed(args.seed)
    with open(args.output, mode='w') as fd:
        fd.write(
            org2mind(args.input,
                     theme=args.theme,
                     jsmind=args.jsmind,
                     text=args.text))
