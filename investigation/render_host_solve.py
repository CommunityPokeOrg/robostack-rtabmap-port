#!/usr/bin/env python3
"""Solve (or smoke-test) the ros-humble-rtabmap dependency set for a target platform.

Two modes, both built on ``pixi`` so they work on a linux-64 dev box *and* on the
macos-15 CI runner without any extra solver install:

  --dry-run   render the recipe's ``requirements.host`` for --platform (evaluating the
              ``${{ 'pkg' if osx }}`` / ``if: linux`` selectors vinca emits), write a
              throw-away pixi project pinned to that platform and run ``pixi lock``.
              A successful lock proves the mutex 0.8 / gtsam 4.2.0 / boost 1.88 set plus
              llvm-openmp (osx) is satisfiable on that platform (#2, #12 condition C1/C2).
              Works cross-platform: solving for osx-arm64 from linux is fine.

  --smoke DIR install ros-humble-rtabmap + every ros-humble-rtabmap-* package found in
              DIR/<platform> into a fresh env (DIR first in the channel list) and run
              ``rtabmap --version``, ``ros2 pkg list`` and ``otool -L``/``ldd`` on
              librtabmap. Must run natively on the target platform.

Usage:
  python investigation/render_host_solve.py --recipe recipes/ros-humble-rtabmap/recipe.yaml \
      --platform osx-arm64 --dry-run
  python investigation/render_host_solve.py --platform osx-arm64 --smoke ./output
"""
import argparse
import glob
import os
import re
import subprocess
import sys
import tempfile

import yaml

CHANNELS = ["robostack-humble", "conda-forge"]
SEL_RE = re.compile(r"^\$\{\{\s*'([^']+)'\s+if\s+(\w+)\s*\}\}$")


def selector_true(name, platform):
    os_name = platform.split("-")[0]
    return {
        "osx": os_name == "osx",
        "linux": os_name == "linux",
        "win": os_name == "win",
        "unix": os_name in ("osx", "linux"),
        "wasm32": platform == "emscripten-wasm32",
    }.get(name, False)


def render(items, platform):
    """Flatten a vinca requirements list for one platform.

    Handles ``${{ 'pkg' if osx }}`` strings and ``{if: <cond>, then: [...]}`` maps.
    ``build_platform == target_platform`` is taken as true (native build)."""
    out = []
    for it in items:
        if isinstance(it, str):
            m = SEL_RE.match(it)
            if m:
                if selector_true(m.group(2), platform):
                    out.append(m.group(1))
                continue
            if "${{" in it:  # compiler()/stdlib() jinja, not a host dep
                continue
            out.append(it)
        elif isinstance(it, dict) and "if" in it:
            cond = str(it["if"]).strip()
            if cond == "build_platform == target_platform":
                ok = True
            elif cond == "build_platform != target_platform":
                ok = False
            else:
                ok = selector_true(cond, platform)
            branch = it.get("then" if ok else "else", []) or []
            out.extend(render(branch if isinstance(branch, list) else [branch], platform))
    return out


def to_pixi_dep(spec):
    parts = spec.split(None, 1)
    name = parts[0]
    ver = parts[1] if len(parts) > 1 else "*"
    # "0.8.* humble_*" -> version + build glob
    if " " in ver:
        v, b = ver.split(None, 1)
        return f'{name} = {{ version = "{v}", build = "{b}" }}'
    return f'{name} = "{ver}"'


def write_project(dirname, platform, deps, channels):
    lines = [
        "[workspace]",
        'name = "rtabmap-solve"',
        f"channels = {channels!r}".replace("'", '"'),
        f'platforms = ["{platform}"]',
        "",
        "[dependencies]",
    ]
    lines += [to_pixi_dep(d) for d in deps]
    with open(os.path.join(dirname, "pixi.toml"), "w") as f:
        f.write("\n".join(lines) + "\n")


def run(cmd, cwd):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd, check=True)


def dry_run(recipe, platform):
    with open(recipe) as f:
        rec = yaml.safe_load(f)
    host = list(dict.fromkeys(render(rec["requirements"]["host"], platform)))
    print(f"# rendered host requirements for {platform} ({len(host)}):")
    for d in host:
        print("  ", d)
    with tempfile.TemporaryDirectory() as td:
        write_project(td, platform, host, CHANNELS)
        run(["pixi", "lock"], td)
        with open(os.path.join(td, "pixi.lock")) as f:
            lock = f.read()
    for key in ("libboost-", "gtsam-", "ros2-distro-mutex-", "llvm-openmp-"):
        hits = sorted(set(re.findall(rf"/{re.escape(key)}[^/\s]+\.conda", lock)))
        print(f"# {key}: {hits}")
    print(f"OK: ros-humble-rtabmap host env solves on {platform}")


def smoke(output_dir, platform):
    pkg_dir = os.path.join(output_dir, platform)
    files = glob.glob(os.path.join(pkg_dir, "ros-humble-rtabmap*.conda"))
    if not files:
        sys.exit(f"no ros-humble-rtabmap*.conda in {pkg_dir}")
    names = sorted({re.match(r"(ros-humble-[a-z0-9-]+?)-\d", os.path.basename(f)).group(1) for f in files})
    print("# smoke-testing:", names)
    with tempfile.TemporaryDirectory() as td:
        write_project(td, platform, names + ["ros-humble-ros-base"],
                      [os.path.abspath(output_dir)] + CHANNELS)
        run(["pixi", "install"], td)
        sh = (
            "set -ex; "
            "rtabmap --version; "
            "ros2 pkg list | grep rtabmap; "
            "ros2 pkg executables rtabmap_slam; "
            "lib=$(ls $CONDA_PREFIX/lib/librtabmap_core*.dylib $CONDA_PREFIX/lib/librtabmap_core*.so 2>/dev/null | head -1); "
            "if command -v otool >/dev/null; then otool -L \"$lib\"; else ldd \"$lib\"; fi; "
            "if command -v otool >/dev/null; then otool -L \"$lib\" | grep -i omp || echo 'WARNING: no libomp linked'; fi"
        )
        run(["pixi", "run", "bash", "-c", sh], td)
    print(f"OK: smoke test passed on {platform}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--platform", required=True)
    ap.add_argument("--recipe", default="recipes/ros-humble-rtabmap/recipe.yaml")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--smoke", metavar="OUTPUT_DIR")
    a = ap.parse_args()
    if a.dry_run:
        dry_run(a.recipe, a.platform)
    else:
        smoke(a.smoke, a.platform)


if __name__ == "__main__":
    main()
