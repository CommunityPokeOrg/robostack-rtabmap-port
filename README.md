# robostack-rtabmap-port

RoboStack / conda-forge packaging of [RTAB-Map](https://github.com/introlab/rtabmap) and
[rtabmap_ros](https://github.com/introlab/rtabmap_ros) for ROS 2, with a focus on
**macOS Apple Silicon (osx-arm64)** and other non-Ubuntu platforms.

Requested by Hermano (@dotio). Maintained under CommunityPokeOrg.

> **This project is currently a feasibility pass, not a committed port.** Gate 0 is
> [#12 — feasibility analysis](https://github.com/CommunityPokeOrg/robostack-rtabmap-port/issues/12):
> research how comparable C++/ROS packages reach osx-arm64 via RoboStack/conda-forge, document
> macOS toolchain/linking/runtime quirks, and record an explicit **go / conditional-go / no-go**
> for `rtabmap` and for `rtabmap_ros`, with unknowns listed separately from findings
> (`docs/feasibility.md`, TODO). Milestones #1–#11 are gated by that decision; the linux-64
> builds below are evidence *for* the feasibility pass, not a commitment.
>
> **Feasibility decision: PENDING** (no osx-arm64 build has been attempted yet).

> Status legend: **BUILT** = a `.conda` artifact was produced and the log is committed under `evidence/`;
> **FAILED** = attempted, log committed; **TODO** = not attempted. Nothing here is claimed
> without a log.

## Scope

0. **Feasibility first (#12):** inspect representative conda-forge recipes, RoboStack patches,
   bot-generated PRs and build metadata (RoboStack/ros-humble, robostack-staging) for complex
   C++/Qt/PCL/OpenCV/GTSAM packages on osx-arm64; document compiler/linking quirks, platform
   selectors, patching strategy, CMake/toolchain behaviour, runtime library paths and CI
   requirements; derive prerequisites and reusable patterns for RTAB-Map; decide go/no-go.
1. Package the RTAB-Map core library (`rtabmap`: `librtabmap_core`, `librtabmap_gui`,
   `librtabmap_utilite`, `rtabmap` GUI binary) as a RoboStack ROS package
   (`ros-<distro>-rtabmap`), reusing RoboStack's `vinca` generator and `rattler-build`.
2. Package the `rtabmap_ros` family (`rtabmap_msgs`, `rtabmap_conversions`, `rtabmap_sync`,
   `rtabmap_util`, `rtabmap_odom`, `rtabmap_slam`, `rtabmap_viz`, `rtabmap_rviz_plugins`,
   `rtabmap_launch`, `rtabmap_python`, `rtabmap_demos`, `rtabmap_examples`, `rtabmap_ros`).
3. Audit every native dependency (PCL, OpenCV, GTSAM, g2o, libpointmatcher, Qt, VTK, Eigen,
   sqlite3, OpenMP, OctoMap, Ceres) for availability on conda-forge / RoboStack per platform,
   with osx-arm64 first.
4. Upstream the result to `RoboStack/ros-humble` (then `ros-jazzy`) and document what is
   implemented vs. deferred.

Out of scope for the MVP: Windows (`win-64`) — see [Current status](#current-status).

## Package targets

| target | ROS distro | RTAB-Map version | notes |
|---|---|---|---|
| `ros-humble-rtabmap` | Humble | 0.22.1 | MVP; **BUILT on linux-64** |
| `ros-humble-rtabmap-*` / `ros-humble-rtabmap-ros` | Humble | 0.22.1 | **BUILT on linux-64** (15 pkgs, 1 patch) |
| `ros-jazzy-rtabmap`, `ros-jazzy-rtabmap-*` | Jazzy | 0.23.7 | TODO (#10) |
| `ros-kilted-rtabmap`, `ros-rolling-rtabmap` | Kilted / Rolling | 0.22.1 | core only; `rtabmap_ros` is **not released** to Rolling upstream (#10) |
| standalone `rtabmap` on conda-forge | — | 0.23.8 | **not duplicated here**: open PR [conda-forge/staged-recipes#34714](https://github.com/conda-forge/staged-recipes/pull/34714) |

## Humble vs Rolling

- **Humble** is the primary target: it is the only distro where both `rtabmap` and
  `rtabmap_ros` are bloom-released *and* RoboStack publishes the whole ROS dependency
  closure for linux-64, osx-arm64, osx-64 and linux-aarch64 (only `aruco_msgs`,
  `aruco_opencv_msgs`, `libpointmatcher` are unpublished — the first two build fine here).
- **Rolling** has `rtabmap` 0.22.1 in the RoboStack snapshot but **no `rtabmap_ros`
  release at all**, so only the core library can be built for Rolling. RoboStack Rolling
  packages are hosted on `https://repo.prefix.dev/robostack-rolling` (the
  `conda.anaconda.org/robostack-rolling` channel is empty); keep that in mind when
  querying availability.
- **Jazzy** carries RTAB-Map 0.23.7 (newer API, OpenCV 5 readiness upstream) and is the
  natural second target. Kilted is on 0.22.1 and lacks `ros-kilted-libg2o`.
- Version/hosting details and the decision table live in issue #10 and will be frozen in
  `docs/humble-vs-rolling.md`.

## osx-arm64 focus

The development machine for this repo is Linux x86_64; **no osx-arm64 build has been run
yet** (#8). What is known from repodata queries (`investigation/`):

- Available on conda-forge osx-arm64: `pcl`, `gtsam`, `octomap`, `ceres-solver`,
  `libopencv`, `qt6-main`, `vtk`, `eigen`, `sqlite`, `yaml-cpp`, `zlib`, `llvm-openmp`.
- Missing on conda-forge osx-arm64: `g2o` (RoboStack's `ros-humble-libg2o` covers it),
  `libpointmatcher`, `libnabo` (build without ICP: `WITH_POINTMATCHER=OFF`, #4).
- The upstream conda-forge recipe (staged-recipes#34714) shows RTAB-Map 0.23.8 + Qt6 + VTK
  building on osx-arm64 CI with GTSAM/g2o/libpointmatcher off — useful precedent.
- macOS-specific flags to watch: `llvm-openmp` for OpenMP, `-undefined dynamic_lookup`
  for Python modules, Qt discovery in `rtabmap_rviz_plugins`.

## Current status (2026-09-14, linux-64, RoboStack Humble, mutex 0.8 — see below)

**All 15 Humble packages BUILT on linux-64** and smoke-tested in a fresh env
(`evidence/humble/phase2-smoke-test.log`: `ros2 pkg list`, `ros2 pkg executables`, `rtabmap --version`,
`ldd librtabmap_core.so` has no "not found"). Per-package results: `evidence/humble/phase2-results.txt`.

| package | status | attempts / notes | log |
|---|---|---|---|
| `ros-humble-rtabmap` 0.22.1 | **BUILT** | 2 (attempt 1: mutex-0.9 GTSAM/Boost solve failure, #2); no source patch | `evidence/humble/build-ros-humble-rtabmap-attempt{1,2}.log` |
| `ros-humble-aruco-msgs` 5.0.5 | **BUILT** | 2 (attempt 1: `empy` 4 breaks `rosidl_adapter`; fix `empy <4` in host reqs) | `evidence/humble/build-aruco-msgs-attempt{1,2}.log` |
| `ros-humble-aruco-opencv-msgs` 2.4.2 | **BUILT** | 1 | `evidence/humble/build-aruco-opencv-msgs-attempt1.log` |
| `ros-humble-rtabmap-msgs` | **BUILT** | 1 | `evidence/humble/build-rtabmap-msgs-attempt1.log` |
| `ros-humble-rtabmap-conversions` | **BUILT** | 1 | `evidence/humble/build-rtabmap-conversions-attempt1.log` |
| `ros-humble-rtabmap-sync` | **BUILT** | 1 | `evidence/humble/build-rtabmap-sync-attempt1.log` |
| `ros-humble-rtabmap-util` | **BUILT** | 1 | `evidence/humble/build-rtabmap-util-attempt1.log` |
| `ros-humble-rtabmap-odom` | **BUILT** | 1 | `evidence/humble/build-rtabmap-odom-attempt1.log` |
| `ros-humble-rtabmap-slam` | **BUILT** | 1 | `evidence/humble/build-rtabmap-slam-attempt1.log` |
| `ros-humble-rtabmap-viz` | **BUILT** | 1 (Qt6 standalone GUI) | `evidence/humble/build-rtabmap-viz-attempt1.log` |
| `ros-humble-rtabmap-rviz-plugins` | **BUILT** | 2 — **needs source patch** `robostack/humble/patch/ros-humble-rtabmap-rviz-plugins.patch` (Qt5 rviz vs Qt6 VTK, see below) | `evidence/humble/build-rtabmap-rviz-plugins-attempt{1,2}.log` |
| `ros-humble-rtabmap-launch` | **BUILT** | 1 | `evidence/humble/build-rtabmap-launch-attempt1.log` |
| `ros-humble-rtabmap-python` | **BUILT** | 1 | `evidence/humble/build-rtabmap-python-attempt1.log` |
| `ros-humble-rtabmap-demos` | **BUILT** | 1 | `evidence/humble/build-rtabmap-demos-attempt1.log` |
| `ros-humble-rtabmap-examples` | **BUILT** | 1 | `evidence/humble/build-rtabmap-examples-attempt1.log` |
| `ros-humble-rtabmap-ros` (umbrella) | **BUILT** | 1 | `evidence/humble/build-rtabmap-ros-attempt1.log` |
| any package on osx-arm64 / osx-64 / linux-aarch64 | TODO (#12 → #8, #9) | — | — |

Feature summary of the built `ros-humble-rtabmap` (from the configure log): OpenCV 4.13 **on**,
Qt 6.10 **on**, VTK 9.5 **on**, external SQLite3 **on**, OpenMP **on**, g2o **on**, GTSAM 4.2.0 **on**,
OctoMap 1.10 **on**, libpointmatcher **off** (not found), Ceres **off**, Python **off**.

### Known constraints / workarounds

- **GTSAM / Boost / mutex 0.9 (#2):** RoboStack Humble's current `ros2-distro-mutex 0.9`
  pins `libboost 1.88.*`, but `ros-humble-gtsam 4.2.1` (the only version on mutex 0.9)
  requires conda-forge `gtsam` builds that need Boost >= 1.90 → unsolvable. This repo
  temporarily sets `mutex_package.version: 0.8.0` in `robostack/humble/vinca.yaml` and
  builds against `ros-humble-gtsam 4.2.0`. This is a workaround, not the target state.
- **libpointmatcher (#4):** no conda-forge package; `ros-humble-libpointmatcher` is not
  published. Removed from the dependency closure (`packages_remove_from_deps`) — RTAB-Map
  builds without it.
- **`liboctomap-dev` (#5):** ROS key was not mapped in RoboStack's `robostack.yaml`; this
  repo adds `liboctomap-dev: robostack: [octomap]`.
- **Windows:** `ros-humble-libg2o`, `grid-map-ros`, `realsense2-camera`, `velodyne` are
  not published on win-64 → the seed is `if: not win`.
- **Qt5 (rviz) vs Qt6 (VTK/rtabmap_gui) split (#5, #12):** RoboStack Humble rviz is Qt5, but
  conda-forge VTK ≥ 9 is Qt6-only, so `rtabmap::gui` exports Qt6 targets. `rtabmap_rviz_plugins`
  hits `INTERFACE_QT_MAJOR_VERSION ... does not agree` at configure time. The committed patch
  strips `rtabmap::gui` / `VTK::GUISupportQt` / `Qt6::*` from the consumed link interfaces
  (the plugins only use core/conversions symbols); the built plugin links Qt5 only. This is the
  first RTAB-Map-specific patch of the port and a key feasibility input for macOS (#12).
- **`empy` 4 vs `rosidl_adapter` 3.1.8:** interface packages need `empy <4` in host requirements
  (recipe-level fix in `robostack/humble/recipes-generated/*-msgs`).
- **The stale upstream patch** `RoboStack/ros-humble/patch/ros-humble-rtabmap.patch` (2022)
  does not apply to 0.22.1 and is not needed; kept for reference as
  `evidence/humble/stale-upstream-ros-humble-rtabmap.patch`.

## Repository layout (implemented vs TODO)

```
robostack/humble/            IMPLEMENTED — RoboStack/ros-humble overlay (base commit in UPSTREAM_BASE.txt)
  vinca.yaml                 seeds rtabmap_ros (if: not win) — replaces the upstream seed list for a scoped build; an upstream PR would only add the seed, drops libpointmatcher, mutex 0.8 workaround
  robostack.yaml             + liboctomap-dev mapping
  conda_build_config.yaml, pkg_additional_info.yaml, rosdistro_snapshot.yaml, pixi.toml  (upstream copies)
  recipes-generated/         the 16 vinca-generated rattler-build recipes that produced the linux-64 artifacts
  patch/ros-humble-rtabmap-rviz-plugins.patch   the only source patch so far (Qt5/Qt6 interface strip)
evidence/humble/             IMPLEMENTED — full build logs, generated recipe, diffs vs upstream
investigation/               IMPLEMENTED — repodata query script + per-distro dependency availability tables
docs/                        TODO — feasibility.md (#12, first deliverable), dependency-matrix.md (#1, #5), humble-vs-rolling.md (#10), how-to-build.md, limitations.md (#11)
conda-forge/                 TODO — only if a non-ROS variant is needed; otherwise defer to staged-recipes#34714
.github/workflows/           TODO — linux-64 + macos-14 (arm64) matrix (#9)
```

### Reproducing the linux-64 build

```bash
# tools: rattler-build 0.76, RoboStack vinca (pinned in robostack/humble/pixi.toml)
cd robostack/humble
vinca -m --platform linux-64                      # regenerates recipes/ from vinca.yaml + rosdistro_snapshot.yaml
rattler-build build --recipe recipes/ros-humble-rtabmap/recipe.yaml \
  -m conda_build_config.yaml \
  -c ./output -c robostack-humble -c conda-forge --output-dir output
```

Dependent `rtabmap_ros` packages are built the same way, serially, with `./output` first
in the channel list so already-built local packages are picked up.

## Milestones and issue tracking

Work is tracked as GitHub issues, one per milestone, all labelled `milestone`. **#12 is the
entry gate**; #2 and #10 feed it, everything else waits for its decision. Extra labels:
`dependency`, `recipe`, `ci`, `documentation`, `blocked`, `humble`, `rolling`,
`platform:osx-arm64`. Each issue has acceptance criteria and lists its dependencies; an
issue is only closed with a link to committed evidence.

| # | milestone | depends on |
|---|---|---|
| [#12](https://github.com/CommunityPokeOrg/robostack-rtabmap-port/issues/12) | **Gate 0 — feasibility analysis**: RoboStack osx-arm64 patterns, macOS quirks, go/no-go for `rtabmap` and `rtabmap_ros` | — (inputs: #2, #10) |
| [#1](https://github.com/CommunityPokeOrg/robostack-rtabmap-port/issues/1) | osx-arm64 dependency matrix audit | #12, #2 #3 #4 #5 |
| [#2](https://github.com/CommunityPokeOrg/robostack-rtabmap-port/issues/2) | GTSAM feedstock/package status (mutex 0.9 / Boost 1.90 blocker) | — |
| [#3](https://github.com/CommunityPokeOrg/robostack-rtabmap-port/issues/3) | PCL feedstock/package status | #12 |
| [#4](https://github.com/CommunityPokeOrg/robostack-rtabmap-port/issues/4) | libpointmatcher feedstock/package status | #12 |
| [#5](https://github.com/CommunityPokeOrg/robostack-rtabmap-port/issues/5) | OpenCV and remaining native dependency audit | #12 |
| [#6](https://github.com/CommunityPokeOrg/robostack-rtabmap-port/issues/6) | conda recipe for `rtabmap` (`ros-humble-rtabmap`) | #12, #2 |
| [#7](https://github.com/CommunityPokeOrg/robostack-rtabmap-port/issues/7) | conda recipes for the `rtabmap_ros` family | #12, #6 |
| [#8](https://github.com/CommunityPokeOrg/robostack-rtabmap-port/issues/8) | local macOS Apple Silicon (osx-arm64) build verification | #12, #1 #2 #5 #6 |
| [#9](https://github.com/CommunityPokeOrg/robostack-rtabmap-port/issues/9) | packaging and CI integration (+ upstream PRs to RoboStack) | #12, #6 #7 |
| [#10](https://github.com/CommunityPokeOrg/robostack-rtabmap-port/issues/10) | Humble vs Rolling package/version strategy and documentation | — |
| [#11](https://github.com/CommunityPokeOrg/robostack-rtabmap-port/issues/11) | final validation, documentation, and handoff | #12, #6–#10 |

Full list: https://github.com/CommunityPokeOrg/robostack-rtabmap-port/issues?q=label%3Amilestone

## References

- RoboStack: https://github.com/RoboStack/ros-humble, https://github.com/RoboStack/ros-jazzy, https://github.com/RoboStack/ros-rolling
- RTAB-Map release repos: https://github.com/ros2-gbp/rtabmap-release, https://github.com/introlab/rtabmap_ros-release
- conda-forge standalone recipe PR: https://github.com/conda-forge/staged-recipes/pull/34714
- ROS 1 (Noetic) precedent with patches: https://github.com/RoboStack/ros-noetic/tree/main/patch (`ros-noetic-rtabmap-*.patch`)
