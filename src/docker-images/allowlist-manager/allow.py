#!/usr/bin/env python3

import argparse

from main import RestUtil


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user",
                        "-u",
                        required=True)
    parser.add_argument("--ip",
                        "-i",
                        required=True)
    parser.add_argument("--rest",
                        "-r",
                        required=True)
    args = parser.parse_args()

    rest_util = RestUtil({"rest_url": args.rest})
    rest_util.add_allow_record(args.user, args.ip)

