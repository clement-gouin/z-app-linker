#!/bin/python3

import os
import re
import sys
import argparse
import requests

# external librairies
import dotenv
import lzstring
import validators

dotenv.load_dotenv()

APPS = os.environ.get("APPS").strip().split("\n")
SEPARATORS = "-=+#@%$._*"
SHLINK_API_URI = os.environ.get("SHLINK_API_URI")
SHLINK_API_KEY = os.environ.get("SHLINK_API_KEY")


class Link:
    def __init__(self, app: str, link_name: str, data: str) -> None:
        self.app = app
        self.app_name = app.split("/")[-1]
        self.link_name = link_name
        self.data = data
        self.dependencies: list[Link] = []
        self.link = None
        self.resolved = False

    def link_dependencies(self, others: list["Link"]) -> None:
        for other in others:
            if other.link_name in self.data:
                self.dependencies += [other]

    def resolve_shallow(self) -> None:
        data = self.data.encode("ascii", "xmlcharrefreplace").decode("utf-8")
        self.link = shorten_url(custom_link(self.app, data))

    def resolve(self) -> None:
        data = self.data.encode("ascii", "xmlcharrefreplace").decode("utf-8")
        for dependency in self.dependencies:
            data = data.replace(
                dependency.link_name,
                dependency.link,
            )
        if self.link is None:
            self.link = shorten_url(custom_link(self.app, data), existing=True)
        else:
            update_short_url(self.link, custom_link(self.app, data))
        self.resolved = True

    def __repr__(self) -> str:
        if self.link is None:
            return f"{self.link_name} ({self.app_name}): \033[33;1mcreating...\033[0m"
        elif self.resolved:
            return f"{self.link_name} ({self.app_name}): \033[34;1m{self.link}\033[0m \033[32;1mdone\033[0m"
        else:
            return f"{self.link_name} ({self.app_name}): \033[34;1m{self.link}\033[0m \033[33;1mupdating...\033[0m"


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


def guess_app(separator: str) -> str:
    index = SEPARATORS.index(separator)
    if index > len(APPS) - 1:
        raise Exception(f"Invalid separator: {separator * 5}")
    return APPS[index]


def parse_data_file(raw_data: list[str], add_debug: bool) -> list[Link]:
    if len(raw_data) == 0:
        print(f"ERROR: Empty data file", file=sys.stderr)
        sys.exit(1)
    current_app = None
    current_link_name = None
    data_buffer = None
    apps: list[Link] = []
    for line in raw_data:
        match = re.findall(r"^([\-=+#@%$._*])\1{4}\s*(\w+)", line)
        if len(match):
            if current_link_name is not None:
                apps += [Link(current_app, current_link_name, "\n".join(data_buffer))]
            current_app = guess_app(match[0][0])
            current_link_name = match[0][1]
            data_buffer = []
        else:
            data_buffer += [line]
    if current_link_name is not None:
        apps += [Link(current_app, current_link_name, "\n".join(data_buffer))]
    if add_debug:
        apps += [
            Link(
                "https://github.com/clement-gouin/z-cross-roads",
                "DEBUG",
                "Debug\n"
                + "\n".join(
                    app.link_name + "\n" + "&#x200B;".join(c for c in app.link_name)
                    for app in apps
                ),
            )
        ]
    return apps


def print_apps(apps: list[Link], clear: bool = True) -> None:
    if clear:
        for _ in range(len(apps)):
            print("\x1b[1A\x1b[2K", end="")
    for app in apps:
        print(f"* {app}")


def link_all_apps(apps: list[Link]) -> None:
    for app in apps:
        app.link_dependencies(apps)


def resolve_all_apps(apps: list[Link], fast: bool) -> None:
    print(f"resolving links for {len(apps)} elements...")
    print_apps(apps, clear=False)
    if fast:
        while any(not app.resolved for app in apps):
            available = [
                app
                for app in apps
                if not app.resolved and all(dep.resolved for dep in app.dependencies)
            ]
            if len(available) == 0:
                print(
                    f"ERROR: Cannot resolve fast with cycling dependencies",
                    file=sys.stderr,
                )
                sys.exit(1)
            available[0].resolve()
            print_apps(apps)
    else:
        for app in apps:
            app.resolve_shallow()
            print_apps(apps)
        for app in apps:
            app.resolve()
            print_apps(apps)


def make_desc() -> str:
    return "\n".join(SEPARATORS[i] * 5 + " " + app for i, app in enumerate(APPS))


def main():
    parser = argparse.ArgumentParser(
        description="links z-app data between them.\n(see data.sample.txt for data format)\nseparators:\n"
        + make_desc(),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--with-debug",
        action="store_true",
        help="create debug Cross-Roads link with all links within",
        default=False,
    )
    parser.add_argument(
        "-f",
        "--fast",
        action="store_true",
        help="resolve links in dependency order (faster)",
        default=False,
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
    args = parser.parse_args()

    raw_data = read_data_file(args.data_path)

    apps = parse_data_file(raw_data, args.with_debug)

    link_all_apps(apps)

    resolve_all_apps(apps, args.fast)


if __name__ == "__main__":
    main()
