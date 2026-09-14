#!/usr/bin/env python3
"""Check which ROS package deps of the rtabmap_ros stack exist in robostack channels.

Usage: [ROBOSTACK_HOST=https://repo.prefix.dev] check_ros_deps.py <distro> <platform...>
Downloads robostack-<distro> repodata.json (default host conda.anaconda.org) and prints a table.
RoboStack publishes humble/jazzy/kilted to conda.anaconda.org and rolling/kilted to repo.prefix.dev.
"""
import json
import os
import sys
import urllib.request

HOST = os.environ.get("ROBOSTACK_HOST", "https://conda.anaconda.org")

DEPS = [
    # rtabmap core deps (ROS keys)
    "cv-bridge", "libg2o", "gtsam", "octomap", "qt-gui-cpp", "libpointmatcher", "libnabo",
    # rtabmap_ros stack deps
    "ament-cmake", "ament-cmake-ros", "rclcpp", "rclcpp-components", "pluginlib",
    "geometry-msgs", "sensor-msgs", "std-msgs", "std-srvs", "nav-msgs", "stereo-msgs",
    "visualization-msgs", "builtin-interfaces", "rosidl-default-generators",
    "image-geometry", "laser-geometry", "pcl-conversions", "pcl-ros", "image-transport",
    "message-filters", "tf2", "tf2-ros", "tf2-eigen", "tf2-geometry-msgs",
    "diagnostic-updater", "octomap-msgs", "grid-map-ros",
    "rviz-common", "rviz-rendering", "rviz-default-plugins",
    "apriltag-msgs", "aruco-msgs", "aruco-opencv-msgs", "nav2-msgs", "nav2-bringup",
    "nav2-costmap-2d", "imu-filter-madgwick", "realsense2-camera", "velodyne",
    "ament-copyright", "ament-flake8", "ament-pep257",
]


def load(channel, platform):
    url = f"{HOST}/{channel}/{platform}/repodata.json"
    with urllib.request.urlopen(url, timeout=300) as r:
        data = json.load(r)
    names = {}
    for rec in list(data.get("packages", {}).values()) + list(data.get("packages.conda", {}).values()):
        names.setdefault(rec["name"], set()).add(rec["version"])
    return names


def main():
    distro = sys.argv[1]
    platforms = sys.argv[2:] or ["linux-64", "osx-arm64", "osx-64", "win-64", "linux-aarch64"]
    channel = f"robostack-{distro}"
    tables = {p: load(channel, p) for p in platforms}
    print(f"channel: {HOST}/{channel}")
    print("| package | " + " | ".join(platforms) + " |")
    print("|---|" + "---|" * len(platforms))
    for dep in DEPS:
        name = f"ros-{distro}-{dep}"
        row = []
        for p in platforms:
            vers = tables[p].get(name)
            row.append(",".join(sorted(vers)) if vers else "MISSING")
        print(f"| {name} | " + " | ".join(row) + " |")


if __name__ == "__main__":
    main()
