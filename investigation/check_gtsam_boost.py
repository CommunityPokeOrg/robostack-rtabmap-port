#!/usr/bin/env python3
"""Cross-check the GTSAM / Boost / ros2-distro-mutex pin interaction (issue #2).

Usage: check_gtsam_boost.py [platform...]   (default: linux-64 osx-arm64)

For each platform prints:
  * every conda-forge `gtsam` build with its libboost run requirement,
  * every robostack-humble `ros-humble-gtsam` build with its `gtsam` and `ros2-distro-mutex` requirements,
  * every robostack-humble `ros2-distro-mutex` build with its libboost constraint,
and then which (ros-humble-gtsam, mutex) pairs are jointly solvable w.r.t. Boost.
Output is meant to be committed under investigation/ as evidence.
"""
import json
import re
import sys
import urllib.request

CF = "https://conda.anaconda.org/conda-forge"
RS = "https://conda.anaconda.org/robostack-humble"


def load(channel, platform):
    url = f"{channel}/{platform}/repodata.json"
    with urllib.request.urlopen(url, timeout=600) as r:
        data = json.load(r)
    recs = list(data.get("packages", {}).values()) + list(data.get("packages.conda", {}).values())
    return recs


def dep(rec, name):
    for d in rec.get("depends", []) + rec.get("constrains", []):
        if d.split(" ")[0] == name:
            return d
    return None


def boost_minor(spec):
    m = re.search(r"1\.(\d+)", spec or "")
    return int(m.group(1)) if m else None


def main():
    platforms = sys.argv[1:] or ["linux-64", "osx-arm64"]
    for p in platforms:
        print(f"\n## {p}")
        cf = load(CF, p)
        rs = load(RS, p)

        gtsam = sorted((r for r in cf if r["name"] == "gtsam"), key=lambda r: (r["version"], r["build_number"]))
        print("\n### conda-forge gtsam (grouped by version / build number)")
        print("| version | build numbers | libboost |")
        print("|---|---|---|")
        cf_boost = {}
        groups = {}
        for r in gtsam:
            b = dep(r, "libboost")
            cf_boost.setdefault(r["version"], set()).add(boost_minor(b))
            groups.setdefault((r["version"], b), set()).add(r["build_number"])
        for (v, b), nums in sorted(groups.items(), key=lambda kv: (kv[0][0], min(kv[1]))):
            print(f"| {v} | {','.join(str(n) for n in sorted(nums))} | {b} |")

        mutex = sorted((r for r in rs if r["name"] == "ros2-distro-mutex"), key=lambda r: r["version"])
        print("\n### robostack-humble ros2-distro-mutex")
        print("| version | build | libboost constraint |")
        print("|---|---|---|")
        mutex_boost = {}
        for r in mutex:
            b = dep(r, "libboost")
            mutex_boost[r["version"]] = boost_minor(b)
            print(f"| {r['version']} | {r['build']} | {b} |")

        rsg = sorted((r for r in rs if r["name"] == "ros-humble-gtsam"), key=lambda r: (r["version"], r["build_number"]))
        print("\n### robostack-humble ros-humble-gtsam")
        print("| version | build | gtsam dep | mutex dep | solvable with mutex libboost? |")
        print("|---|---|---|---|---|")
        for r in rsg:
            g = dep(r, "gtsam")
            m = dep(r, "ros2-distro-mutex")
            mv = re.search(r"ros2-distro-mutex ([\d.]+)", m or "")
            mutex_ver = mv.group(1) if mv else None
            # gtsam spec like "gtsam >=4.2.1,<4.3.0a0" -> candidate cf versions
            gmin = re.search(r">=([\d.]+)", g or "")
            cands = [v for v in cf_boost if not gmin or tuple(map(int, v.split("."))) >= tuple(map(int, gmin.group(1).split(".")))]
            cand_boost = set().union(*(cf_boost[v] for v in cands)) if cands else set()
            mb = mutex_boost.get(mutex_ver) if mutex_ver else None
            for k, v in mutex_boost.items():
                if mutex_ver and k.startswith(mutex_ver.rsplit(".", 1)[0]):
                    mb = v
            ok = (mb in cand_boost) if mb is not None else "n/a"
            print(f"| {r['version']} | {r['build']} | {g} | {m} | {ok} (cf gtsam boost minors {sorted(x for x in cand_boost if x)}, mutex boost 1.{mb}) |")


if __name__ == "__main__":
    main()
