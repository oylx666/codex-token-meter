"""Persistent lifecycle settings; also a local command-line interface."""
import argparse
import json
import os
from common import STATE_DIR

DEFAULTS = dict(auto_open=True, auto_close=True)


def read_settings():
    try:
        value = json.loads((STATE_DIR/'lifecycle.json').read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            return dict(DEFAULTS)
        return {key: value[key] if type(value.get(key)) is bool else default for key,default in DEFAULTS.items()}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def write_settings(**changes):
    value = read_settings()
    for key, item in changes.items():
        if key not in DEFAULTS or type(item) is not bool:
            raise ValueError('Expected auto_open/auto_close boolean')
        value[key] = item
    STATE_DIR.mkdir(parents=True,exist_ok=True)
    temp = STATE_DIR / ('lifecycle-'+str(os.getpid())+'.tmp')
    temp.write_text(json.dumps(value),encoding='utf-8')
    temp.replace(STATE_DIR/'lifecycle.json')
    return value


def main():
    parser=argparse.ArgumentParser(description='Local lifecycle settings; no model calls')
    parser.add_argument('--auto-open',choices=['on','off'])
    parser.add_argument('--auto-close',choices=['on','off'])
    args=parser.parse_args()
    changes={key: value=='on' for key,value in vars(args).items() if value is not None}
    print(json.dumps(write_settings(**changes) if changes else read_settings()))


if __name__=='__main__':
    main()
