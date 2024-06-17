#!/bin/python3

import os
import re
import sys
import argparse
import requests

# external librairies
import dotenv
import lzstring

dotenv.load_dotenv()

TREASURE_FINDER_URI = os.environ.get("TREASURE_FINDER_URI")
ON_THE_QUIZZ_URI = os.environ.get("ON_THE_QUIZZ_URI")
SHLINK_API_URI = os.environ.get("SHLINK_API_URI")
SHLINK_API_KEY = os.environ.get("SHLINK_API_KEY")


class Riddle:
    def __init__(self, link_name: str, data: str) -> None:
        self.link_name = link_name
        self.data = data
        self.dependencies: list[Riddle] = []
        self.link = None

    @property
    def resolved(self) -> bool:
        return self.link is not None

    @property
    def resolvable(self) -> bool:
        return not self.resolved and (
            len(self.dependencies) == 0
            or all(dependency.resolved for dependency in self.dependencies)
        )

    def get_uri(self) -> str:
        if is_float(self.data.splitlines()[0]):
            return TREASURE_FINDER_URI
        else:
            return ON_THE_QUIZZ_URI

    def link_dependencies(self, others: list["Riddle"]) -> None:
        for other in others:
            if other.link_name in self.data:
                self.dependencies += [other]

    def resolve(self) -> None:
        data = self.data
        for dependency in self.dependencies:
            data = data.replace(
                dependency.link_name,
                dependency.link,
            )
        self.link = shorten_url(custom_link(self.get_uri(), data))

    def __repr__(self) -> str:
        if self.resolved:
            return f"{self.link_name}: \033[34;1m{self.link}\033[0m"
        elif self.resolvable:
            return f"{self.link_name}: \033[32;1mready\033[0m"
        else:
            return f"{self.link_name}: \033[33;1mwaiting\033[0m"


def is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def shorten_url(url: str) -> str:
    resp = requests.post(
        f"{SHLINK_API_URI}/short-urls",
        data={"longUrl": url, "findIfExists": True},
        headers={"X-Api-Key": SHLINK_API_KEY},
    )

    if resp.status_code != 200:
        return url

    return resp.json()["shortUrl"]


def custom_link(uri: str, data: str) -> str:
    data = "".join(
        lzstring.LZString()
        .compressToBase64(data)
        .replace("+", "-")
        .replace("/", "_")
        .replace("=", "")[::-1]
    )
    return uri + "?z=" + data


def read_data_file(data_path: str) -> list[str]:
    try:
        with open(data_path) as data_file:
            return data_file.read().strip().splitlines()
    except Exception as exception:
        print(f"ERROR: Cannot read {data_path}: {exception}", file=sys.stderr)
        sys.exit(1)


def parse_data_file(raw_data: list[str]) -> list[Riddle]:
    if len(raw_data) == 0:
        print(f"ERROR: Empty data file", file=sys.stderr)
        sys.exit(1)
    current_link_name = None
    data_buffer = None
    riddles: list[Riddle] = []
    for line in raw_data:
        match = re.findall(r"^---\s*(\w+)", line)
        if len(match):
            if current_link_name is not None:
                riddles += [Riddle(current_link_name, "\n".join(data_buffer))]
            current_link_name = match[0]
            data_buffer = []
        else:
            data_buffer += [line]
    if current_link_name is not None:
        riddles += [Riddle(current_link_name, "\n".join(data_buffer))]
    return riddles


def print_riddles(riddles: list[Riddle], clear: bool = True) -> None:
    if clear:
        for _ in range(len(riddles)):
            print("\x1b[1A\x1b[2K", end="")
    for riddle in riddles:
        print(f"* {riddle}")


def link_all_riddles(riddles: list[Riddle]) -> None:
    for riddle in riddles:
        riddle.link_dependencies(riddles)


def resolve_all_riddles(riddles: list[Riddle]) -> None:
    print(f"resolving links for {len(riddles)} riddles...")
    print_riddles(riddles, clear=False)
    while any(not riddle.resolved for riddle in riddles):
        print_riddles(riddles)
        available = [riddle for riddle in riddles if riddle.resolvable]
        if len(available) == 0:
            print("ERROR: cycling dependency", file=sys.stderr)
            sys.exit(1)
        available[0].resolve()
    print_riddles(riddles)


def main():
    parser = argparse.ArgumentParser(
        description="links [Treasure Finder] & [On The Quizz] data between them.\n\ndocumentations:\n* Treasure Finder -> https://github.com/clement-gouin/treasure-finder\n* On The Quizz -> https://github.com/clement-gouin/on-the-quizz",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-d",
        "--data",
        nargs="?",
        help="source file path (default: data.txt)",
        default="data.txt",
        required=False,
        metavar="PATH",
        dest="data_path",
    )
    args = parser.parse_args()

    raw_data = read_data_file(args.data_path)

    riddles = parse_data_file(raw_data)

    link_all_riddles(riddles)

    resolve_all_riddles(riddles)


if __name__ == "__main__":
    main()
