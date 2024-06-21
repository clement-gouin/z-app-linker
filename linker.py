#!/bin/python3

import os
import re
import sys
import argparse
import requests
import html

# external librairies
import dotenv
import lzstring
import validators

dotenv.load_dotenv()

TREASURE_FINDER_URI = os.environ.get("TREASURE_FINDER_URI")
ON_THE_QUIZZ_URI = os.environ.get("ON_THE_QUIZZ_URI")
CROSS_ROADS_URI = os.environ.get("CROSS_ROADS_URI")
SHLINK_API_URI = os.environ.get("SHLINK_API_URI")
SHLINK_API_KEY = os.environ.get("SHLINK_API_KEY")


class Link:
    def __init__(self, link_name: str, data: str) -> None:
        self.link_name = link_name
        self.data = data
        self.dependencies: list[Link] = []
        self.link = None
        self.resolved = False

    def get_uri(self) -> str:
        lines = self.data.splitlines()
        if len(lines) > 0 and is_float(lines[0]):
            return TREASURE_FINDER_URI
        elif len(lines) >= 3 and (
            validators.url(lines[1])
            or any(lines[1] == dependency.link_name for dependency in self.dependencies)
        ):
            return CROSS_ROADS_URI
        else:
            return ON_THE_QUIZZ_URI

    def link_dependencies(self, others: list["Link"]) -> None:
        for other in others:
            if other.link_name in self.data:
                self.dependencies += [other]

    def resolve_shallow(self) -> None:
        data = self.data.encode("ascii", "xmlcharrefreplace").decode("utf-8")
        self.link = shorten_url(custom_link(self.get_uri(), data))

    def resolve(self) -> None:
        data = self.data.encode("ascii", "xmlcharrefreplace").decode("utf-8")
        for dependency in self.dependencies:
            data = data.replace(
                dependency.link_name,
                dependency.link,
            )
        if self.link is None:
            self.link = shorten_url(custom_link(self.get_uri(), data), existing=True)
        else:
            update_short_url(self.link, custom_link(self.get_uri(), data))
        self.resolved = True

    def __repr__(self) -> str:
        if self.link is None:
            return f"{self.link_name}: \033[33;1mcreating...\033[0m"
        elif self.resolved:
            return (
                f"{self.link_name}: \033[34;1m{self.link}\033[0m \033[32;1mdone\033[0m"
            )
        else:
            return f"{self.link_name}: \033[34;1m{self.link}\033[0m \033[33;1mupdating...\033[0m"


def is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def shorten_url(url: str, existing: bool = False) -> str:
    resp = requests.post(
        f"{SHLINK_API_URI}/short-urls",
        data={"longUrl": url, "findIfExists": existing},
        headers={"X-Api-Key": SHLINK_API_KEY},
    )

    if resp.status_code != 200:
        print(f"ERROR: Could not shorten URL: {resp.status_code} {resp.reason}")
        sys.exit(1)

    return resp.json()["shortUrl"]


def update_short_url(short_url: str, new_url: str) -> None:
    shortCode = short_url.split("/")[-1]
    resp = requests.patch(
        f"{SHLINK_API_URI}/short-urls/{shortCode}",
        data={"longUrl": new_url},
        headers={"X-Api-Key": SHLINK_API_KEY},
    )

    if resp.status_code != 200:
        print(
            f"ERROR: Could not update short URL {short_url}: {resp.status_code} {resp.reason}"
        )
        sys.exit(1)


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
        with open(data_path, encoding="utf-8") as data_file:
            return data_file.read().strip().splitlines()
    except Exception as exception:
        print(f"ERROR: Cannot read {data_path}: {exception}", file=sys.stderr)
        sys.exit(1)


def parse_data_file(raw_data: list[str], add_debug: bool) -> list[Link]:
    if len(raw_data) == 0:
        print(f"ERROR: Empty data file", file=sys.stderr)
        sys.exit(1)
    current_link_name = None
    data_buffer = None
    riddles: list[Link] = []
    for line in raw_data:
        match = re.findall(r"^---\s*(\w+)", line)
        if len(match):
            if current_link_name is not None:
                riddles += [Link(current_link_name, "\n".join(data_buffer))]
            current_link_name = match[0]
            data_buffer = []
        else:
            data_buffer += [line]
    if current_link_name is not None:
        riddles += [Link(current_link_name, "\n".join(data_buffer))]
    if add_debug:
        riddles += [
            Link(
                "DEBUG",
                "Debug\n"
                + "\n".join(
                    riddle.link_name
                    + "\n"
                    + "&#x200B;".join(c for c in riddle.link_name)
                    for i, riddle in enumerate(riddles)
                ),
            )
        ]
    return riddles


def print_riddles(riddles: list[Link], clear: bool = True) -> None:
    if clear:
        for _ in range(len(riddles)):
            print("\x1b[1A\x1b[2K", end="")
    for riddle in riddles:
        print(f"* {riddle}")


def link_all_riddles(riddles: list[Link]) -> None:
    for riddle in riddles:
        riddle.link_dependencies(riddles)


def resolve_all_riddles(riddles: list[Link], fast: bool) -> None:
    print(f"resolving links for {len(riddles)} elements...")
    print_riddles(riddles, clear=False)
    if fast:
        while any(not riddle.resolved for riddle in riddles):
            available = [
                riddle
                for riddle in riddles
                if not riddle.resolved
                and all(dep.resolved for dep in riddle.dependencies)
            ]
            if len(available) == 0:
                print(
                    f"ERROR: Cannot resolve fast with cycling dependencies",
                    file=sys.stderr,
                )
                sys.exit(1)
            available[0].resolve()
            print_riddles(riddles)
    else:
        for riddle in riddles:
            riddle.resolve_shallow()
            print_riddles(riddles)
        for riddle in riddles:
            riddle.resolve()
            print_riddles(riddles)


def main():
    parser = argparse.ArgumentParser(
        description="links [Treasure Finder/On The Quizz/Cross-Roads] data between them.\n(see data.sample.txt for data format)\n\ndocumentations:\n* Treasure Finder -> https://github.com/clement-gouin/treasure-finder\n* On The Quizz -> https://github.com/clement-gouin/on-the-quizz\n* Cross-Roads -> https://github.com/clement-gouin/cross-roads",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-d",
        "--data",
        nargs="?",
        help="data file path (default: data.txt)",
        default="data.txt",
        required=False,
        metavar="data.txt",
        dest="data_path",
    )
    parser.add_argument(
        "--with-debug",
        action=argparse.BooleanOptionalAction,
        help="create debug Cross-Roads link with all links within",
        default=False,
    )
    parser.add_argument(
        "--fast",
        action=argparse.BooleanOptionalAction,
        help="resolve links in dependency order (faster)",
        default=False,
    )
    args = parser.parse_args()

    raw_data = read_data_file(args.data_path)

    riddles = parse_data_file(raw_data, args.with_debug)

    link_all_riddles(riddles)

    resolve_all_riddles(riddles, args.fast)


if __name__ == "__main__":
    main()
