#!/usr/bin/env python3
"""Render one stack's config-<env>/<config> into inputs for the
aws-actions/aws-cloudformation-github-deploy step, and decide whether that
stack needs deploying this run.

Writes GITHUB_OUTPUT-style `key=value` lines to stdout:
  deploy     - "true"/"false"
  name       - CloudFormation stack name
  template   - path to the template file
  overrides  - comma-joined Key=Value parameter-overrides string
  tags       - comma-joined Key=Value tags string

Static parameters come from the config file; dynamic (cross-stack) ones are
supplied by the workflow via repeated --set KEY=VALUE, reading another
stack's already-resolved outputs (see the "Resolve <stack> outputs" step in
deploy.yml).

Deploy decision:
  --event workflow_dispatch: deploy if --only is empty or equals --stack
  --event push:              deploy if this stack's config or template file
                              is among --changed-files (newline-separated)
"""
import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", default="dev")
    parser.add_argument("--stack", required=True, help="stack key, used as the last segment of the stack name")
    parser.add_argument("--config", required=True, help="filename within config-<env>/")
    parser.add_argument("--event", required=True, choices=["push", "workflow_dispatch"])
    parser.add_argument("--only", default="", help="workflow_dispatch 'only' input; empty means deploy everything")
    parser.add_argument("--changed-files", default="", help="newline-separated changed file list (push event)")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", dest="overrides_in")
    args = parser.parse_args()

    config_path = REPO_ROOT / f"config-{args.env}" / args.config
    with config_path.open() as f:
        config = yaml.safe_load(f)

    params = dict(config["parameters"])
    for item in args.overrides_in:
        key, _, value = item.partition("=")
        params[key] = value

    if args.event == "workflow_dispatch":
        deploy = args.only == "" or args.only == args.stack
    else:
        changed = {line.strip() for line in args.changed_files.splitlines() if line.strip()}
        relevant = {f"config-{args.env}/{args.config}", config["template-file-path"]}
        deploy = bool(changed & relevant)

    name = f"{params['ProjectName']}-{params['Environment']}-{args.stack}"
    # aws-cloudformation-github-deploy splits parameter-overrides on top-level commas;
    # a value that itself contains commas (e.g. PublicSubnets/PrivateSubnets, which are
    # comma-joined subnet ID lists) must be double-quoted per its documented format:
    # <ParameterName>="<ParameterValue>,<ParameterValue>"
    overrides = ",".join(
        f'{k}="{v}"' if "," in str(v) else f"{k}={v}"
        for k, v in params.items()
    )
    tags = ",".join(f"{k}={v}" for k, v in (config.get("tags") or {}).items())

    print(f"deploy={'true' if deploy else 'false'}")
    print(f"name={name}")
    print(f"template={config['template-file-path']}")
    print(f"overrides={overrides}")
    print(f"tags={tags}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
