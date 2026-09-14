# Feasibility survey — RTAB-Map port to RoboStack (issue #12, CommunityPokeOrg/robostack-rtabmap-port)

Research only; no conclusions. Sources: `RoboStack/{ros-humble,ros-jazzy,ros-noetic}` (git clones; ros-noetic deepened to depth≥200 for patch history), installed vinca at the installed RoboStack vinca package (RoboStack vinca @ b5e03d1f), repodata snapshots saved under `investigation/feasibility-raw/repodata-<channel>-<platform>.json` and consolidated query output in `investigation/feasibility-raw/repodata-queries.txt`, staged-recipes PR files copied verbatim to `investigation/feasibility-raw/staged-recipes-34714.txt`.

---

## 1. macOS CI / build metadata

### 1.1 CI workflows (identical layout in ros-humble, ros-jazzy, ros-noetic)

| Fact | Evidence |
|---|---|
| `testpr.yml` builds osx natively: `os: macos-15-intel → platform: osx-64`, `os: macos-15 → platform: osx-arm64` (no cross-compilation for osx; linux-aarch64 also runs on `ubuntu-24.04-arm`) | `RoboStack/ros-humble/.github/workflows/testpr.yml:24-29`; identical block `RoboStack/ros-jazzy/.github/workflows/testpr.yml:24-29` and `RoboStack/ros-noetic/.github/workflows/testpr.yml:24-29` |
| Per-platform build cache: `folder_cache: output/osx-64` / `output/osx-arm64` via actions/cache restore+save | testpr.yml lines ~24-29 + cache steps in same file |
| Build command: `pixi run rattler-build build --recipe-dir recipes --target-platform ${{ matrix.platform }} -m ./conda_build_config.yaml -c conda-forge -c robostack-staging --skip-existing` | `RoboStack/ros-humble/.github/workflows/testpr.yml` (build step) |
| `main.yml` regenerates recipes per platform: `pixi run -v vinca --multiple --platform osx-64` / `osx-arm64` then `vinca-gha` pipelines pushed to `buildbranch_*` branches | `RoboStack/ros-humble/.github/workflows/main.yml:44-52` (osx section); same pattern in ros-noetic `main.yml:44-52` |

### 1.2 conda_build_config.yaml — osx entries

| key | ros-humble | ros-jazzy | location |
|---|---|---|---|
| `c_compiler` | `clang # [osx]` | `clang # [osx]` | `conda_build_config.yaml` in each repo root |
| `c_compiler_version` | `18 # [osx]` | `19 # [osx]` | same |
| `cxx_compiler` / version | `clangxx` / `18 # [osx]` | `clangxx` / `19 # [osx]` | same |
| `c_stdlib` | `macosx_deployment_target # [osx]` | same | same |
| `c_stdlib_version` | `10.13 # [osx and x86_64]`; `11.0 # [osx and arm64]` | `12.0` for both | same |

Note the vinca templates hardcode `OSX_DEPLOYMENT_TARGET` to 10.15/11.0 (see 1.4) — this disagrees with the humble config's 10.13 for osx-64. The effective value passed is the template's, not conda_build_config's. UNVERIFIED which one wins at `-DCMAKE_OSX_DEPLOYMENT_TARGET` (template passes it explicitly, so the template value is what CMake sees).

### 1.3 osx conditions in vinca.yaml / pkg_additional_info.yaml

- `pkg_additional_info.yaml`: **zero** `osx` occurrences in ros-humble, ros-jazzy, ros-noetic.
- `vinca.yaml` (ros-humble): single `osx` mention — a comment at line ~441. ros-jazzy/ros-noetic vinca.yaml: zero `osx` grep hits. (All platform conditioning in vinca.yaml is via `if: unix/not win/win` — grep `osx` returns nothing else.)

### 1.4 vinca build templates — macOS-relevant lines

Files: `vinca/templates/build_ament_cmake.sh.in` and `build_catkin.sh.in` (identical copies in `RoboStack/vinca/vinca/templates/`).

| template:line | content |
|---|---|
| build_ament_cmake.sh.in:20-24 | `if [[ "$CONDA_BUILD_CROSS_COMPILATION" != "1" ]]; then … OSX_DEPLOYMENT_TARGET="10.15" else … OSX_DEPLOYMENT_TARGET="11.0"` |
| build_ament_cmake.sh.in:134 | `-DCMAKE_OSX_DEPLOYMENT_TARGET=$OSX_DEPLOYMENT_TARGET` |
| build_ament_cmake.sh.in:~133 | `-DCMAKE_IGNORE_PREFIX_PATH="/opt/homebrew;/usr/local/homebrew"` (keeps Homebrew out of the search path) |
| build_ament_cmake.sh.in:~110 | `-DCMAKE_FIND_FRAMEWORK=LAST` (in build_catkin.sh.in:98) |
| build_catkin.sh.in:25-29 | same OSX_DEPLOYMENT_TARGET 10.15/11.0 split |
| build_catkin.sh.in:112 | `-DCMAKE_OSX_DEPLOYMENT_TARGET=$OSX_DEPLOYMENT_TARGET` |

No `-undefined dynamic_lookup`, no explicit rpath/`@rpath`/`CMAKE_INSTALL_NAME_DIR` lines in either template — dynamic_lookup appears only as a documented fix pattern in `AGENTS.md` ("Avoid linking to `Python::Python` on Apple … `-undefined dynamic_lookup`", `RoboStack/ros-humble/AGENTS.md`, "Common fix patterns"). Both templates use `${CMAKE_ARGS}`/`Ninja`, `QT_HOST_PATH` export for cross builds, and linux-only `gcc`/`g++` symlinks (`if [[ $target_platform =~ linux.* ]]`).

---

## 2. Patch survey (macOS-relevant topics)

Method: grep over `patch/*.patch` in each repo for `APPLE|Darwin|osx|macOS|dynamic_lookup|rpath|OpenMP|Qt|OpenGL|glew|VTK|PCL|OpenCV|GTSAM|Eigen|sqlite`. Full list of matching files with matched topics is in `raw/` derivations; below are the entries most relevant to rtabmap's dependency surface. Format: file :: topics :: one-line description.

### 2.1 ros-noetic rtabmap* patches (full detail — these are the direct precedent)

| file | changes | macOS-relevant? |
|---|---|---|
| `patch/ros-noetic-rtabmap.patch` (192 lines) | (a) deletes the `gcc -dumpversion` "GCC 4 required" FATAL_ERROR block; (b) `IF(MOBILE_BUILD)→IF(FALSE)` so `WITH_QT` defaults ON, `WITH_PYTHON` OFF→ON; (c) forces `CMAKE_AUTOMOC/AUTORCC/AUTOUIC ON` under `WITH_QT`; (d) adds `DISABLE_VTK` definition when `WITH_QT` off; (e) adds `Python3_INCLUDE_DIRS`/`Python3_NumPy_INCLUDE_DIRS` in corelib; (f) `UThreadC.h`: `virtual ~UThreadC<void>() {}` → `virtual ~UThreadC() {}` plus whitespace | Not APPLE-gated; generic toolchain/Qt fixes. (b)+(c) matter because conda VTK is Qt6 → rtabmap picks Qt6 GUI. |
| `patch/ros-noetic-rtabmap-rviz-plugins.patch` (62 lines) | bumps cmake_minimum to 3.20; replaces `FIND_PACKAGE(Qt5 …)`/`QT5_USE_MODULES` with `find_package(QT NAMES Qt5 QUIET …)` + `find_package(Qt${QT_VERSION_MAJOR} …)`; **filters `catkin_INCLUDE_DIRS` and `catkin_LIBRARIES` to strip anything matching `/qt6/` or `Qt6::`**; explicitly links `Qt5::Core/Widgets/Gui` | Directly macOS/conda-relevant: the same Qt6-leak-into-Qt5-rviz problem solved for humble in `robostack/humble/patch/ros-humble-rtabmap-rviz-plugins.patch`. Not APPLE-gated — applied on all platforms. |
| `patch/ros-noetic-rtabmap-viz.patch` (57 lines) | same pattern: cmake_minimum 3.20, Qt5-preferred discovery, strips `/qt6/`+`Qt6::` from catkin vars, links Qt5 explicitly | same as above |
| `patch/ros-noetic-rtabmap-conversions.patch` (18 lines) | only adds commented-out find_package lines (jsoncpp/libxml2/NetCDF/HDF5/LibPROJ) — effectively a no-op | no |
| `patch/ros-noetic-rtabmap-slam.patch` (11 lines) | `CoreWrapper.cpp`: `#include <pcl/io/io.h>` → `<pcl/io/file_io.h>` (PCL 1.15 header rename) | no (PCL-related, platform-independent) |
| `patch/ros-noetic-rtabmap-demos.patch` (40 lines) | catkin_install_python tweaks; find_object_2d conditional | no |

### 2.2 humble patches touching the surveyed topics (selected, per lead's list)

| file | topics | what it does |
|---|---|---|
| `ros-humble-qt-gui-cpp.patch` | apple darwin opengl | `cmake_minimum_required(VERSION 3.12...3.20)`; sip subdir: uses `Python` (not `Python3`), adds `find_package(OpenGL REQUIRED)` + `OpenGL::GL`, and `if(NOT APPLE) … Python::Python` — i.e. **does not link libpython into the sip module on Apple** (dynamic_lookup pattern) |
| `ros-humble-rviz2.patch` | qt5 | CMakeLists: rviz2 links `Qt5::Widgets` etc. explicitly (Qt5 pinning) |
| `ros-humble-rviz-default-plugins.patch` | qt5 | adds Qt5 link to rviz_default_plugins |
| `ros-humble-rviz-ogre-vendor.patch` | apple macos osx | vendored mega-patch: `0001` pkg-config for Windows; `0002-osx-no-framework.patch` (OgreDynLib framework→dylib); `0003-clang11-fix`; `0004-fix-arm64.patch` — on `APPLE AND NOT APPLE_IOS`: always run `xcodebuild -version -sdk macosx Path` for CMAKE_OSX_SYSROOT, adds `-D_LIBCPP_ENABLE_CXX17_REMOVED_UNARY_BINARY_FUNCTION`, disables GLES2; also `unicode_char` → `char32_t` in OgreUTFString.h |
| `ros-humble-nav2-rviz-plugins.patch`, `ros-humble-vision-msgs-rviz-plugins.patch` | qt5 | Qt5 link pins |
| `ros-humble-rqt-gui-cpp.linux.patch` | qt5 | adds Qt5 discovery on linux |
| `ros-humble-python-qt-binding.patch` | apple qt5 | sip build plumbing; `pyproject.toml.in` added; sip_helper changes |
| `ros-humble-libg2o.patch` | opengl openmp | g2o CMakeLists OpenMP/OpenGL section edited |
| `ros-humble-cartographer-ros.patch` | pcl | misc C++ fixes (glog basename, includes) |
| `ros-humble-moveit-ros-perception.osx.patch` | apple eigen glew opencv opengl | on APPLE: `find_package(GLUT)` + framework path instead of FreeGLUT; `#include <OpenGL/gl.h>`/`<GLUT/glut.h>`; `glutMainLoopEvent()` → `glutCheckLoop()` under `__APPLE__`; adds OpenCV to semantic_world deps |
| `ros-humble-moveit-planners-ompl.patch` | apple macos openmp | OpenMP link adjustments on APPLE |
| `ros-humble-nav2-mppi-controller.osx.patch` / `ros-humble-nav2-smac-planner.osx.patch` | openmp apple | APPLE: skip `find_package(OpenMP)`, link `-fopenmp` raw instead of `OpenMP::OpenMP_CXX` |
| `ros-humble-plotjuggler.osx.patch` | qt5 | qwt links `Qt5::Xml` (missing link) |
| `ros-humble-grid-map-pcl.osx.patch` | apple pcl | helpers.hpp Apple fix |
| `ros-humble-moveit-ros-move-group.patch` | apple macos rpath | rpath fix |
| `ros-humble-rtabmap.patch` | opencv pcl sqlite | **the stale 2022 patch** (kept as `evidence/humble/stale-upstream-ros-humble-rtabmap.patch`); old Qt5-era edits |
| also matching grep but lower relevance | — | `ros-humble-cyclonedds`, `-fastrtps` (APPLE), `-rcutils` (APPLE), `-ros-workspace` (APPLE), `-rosidl-generator-py` (APPLE), `-osrf-testing-tools-cpp` (APPLE darwin), `-apriltag-ros` (APPLE), `-mimick-vendor.osx`, `-mavlink.osx`, `-menge-vendor`, `-realsense2-camera`, `-realtime-tools.osx`, `-rplidar-ros`, `-ublox-dgnss-node`, `-gripper-controllers`, `-mrpt2` |

### 2.3 jazzy patches (selected)

| file | topics | what it does |
|---|---|---|
| `ros-jazzy-rviz2.osx.patch`, `ros-jazzy-rviz-common.osx.patch` | apple macos | osx-specific rviz fixes |
| `ros-jazzy-rviz-ogre-vendor.patch` | apple macos opengl osx | same vendored-OGRE osx/arm64 treatment as humble |
| `ros-jazzy-qt-gui-cpp.patch` | apple darwin macos opengl osx | bigger version of the humble qt-gui-cpp patch (sip + OpenGL + no libpython on APPLE) |
| `ros-jazzy-python-qt-binding.patch` | apple darwin macos osx qt5 | sip/qt binding fixes incl. darwin paths |
| `ros-jazzy-octomap-rviz-plugins.patch` | qt5 | Qt5 link pin — precedent that octomap-rviz-plugins needed the same Qt5 treatment |
| `ros-jazzy-nav2-rviz-plugins.patch`, `ros-jazzy-moveit-setup-framework.patch` | qt5 | Qt5 pins |
| `ros-jazzy-moveit-ros-perception.osx.patch` | apple eigen glew opencv opengl | same GLUT/OpenGL framework treatment as humble |
| `ros-jazzy-moveit-planners-ompl.patch`, `ros-jazzy-nav2-mppi-controller.osx.patch` | apple openmp | OpenMP-on-APPLE handling |
| `ros-jazzy-plotjuggler.osx.patch` / `.win.patch` | qt5 apple opengl | qwt Qt5 link / win fixes |
| `ros-jazzy-rosidl-generator-py.osx.patch` | apple | osx generator fix |
| `ros-jazzy-warehouse-ros-sqlite.patch` | sqlite | sqlite-related |
| `ros-jazzy-libg2o.patch`, `ros-jazzy-slam-toolbox.patch`, `ros-jazzy-grid-map-core.patch`, `ros-jazzy-grid-map-pcl.osx.patch`, `ros-jazzy-cartographer-ros.patch`, `ros-jazzy-pcl-ros.win.patch`, `ros-jazzy-spatio-temporal-voxel-layer.patch`, `ros-jazzy-bonxai-ros.patch` | eigen/pcl/openmp | assorted header/dep fixes |

### 2.4 Topic index (files per repo matching the survey keywords)

- Full enumerated lists were produced by the grep in `raw/` (command reproduced in survey notes): ros-humble 62 files, ros-jazzy 47, ros-noetic ~85 matching ≥1 keyword. See section-2 tables above for the rtabmap-relevant subset; every other hit is a routine Eigen/PCL/OpenCV include fix or win64-only patch.
- Notable: no humble/jazzy patch mentions `dynamic_lookup` (the pattern lives only in AGENTS.md); several noetic patches do (`ros-noetic-rqt-gui-cpp`, `-jsk-recognition-utils`, `-moveit-ros-planning-interface`).

---

## 3. Repodata evidence — osx-arm64 (raw: `raw/repodata-queries.txt`, `raw/repodata-*.json`)

### 3.1 Which Qt does RoboStack rviz use on osx-arm64?

**Qt5 (`qt-main`) everywhere, on every distro and every mutex generation.**

| package / channel / platform | versions present | Qt dep (latest mutex gen) |
|---|---|---|
| robostack-humble osx-arm64 `ros-humble-rviz2` | 11.2.2–11.2.26 | `qt-main >=5.15.15,<5.16.0a0` (mutex 0.9 gen) |
| robostack-humble osx-arm64 `ros-humble-rviz-rendering` | same | `qt-main` + `qt-main >=5.15.15,<5.16.0a0` |
| robostack-humble osx-arm64 `ros-humble-qt-gui-cpp` | 2.2.1–2.2.5 | `qt-main >=5.15.15,<5.16.0a0` |
| robostack-humble linux-64 `ros-humble-rviz2` | same versions | `qt-main >=5.15.15,<5.16.0a0` (Qt5 identical to osx) |
| robostack-jazzy osx-arm64 `ros-jazzy-rviz2` | 14.1.6–14.1.23 | `qt-main >=5.15.15,<5.16.0a0` |
| robostack-jazzy osx-arm64 `ros-jazzy-qt-gui-cpp` | 2.7.5, 2.7.6 | `qt-main >=5.15.15,<5.16.0a0` through mutex 0.16 |
| robostack-humble osx-arm64 `ros-humble-libg2o`, `-slam-toolbox`, `-plotjuggler`, `-octomap-rviz-plugins` | present | all pin `qt-main >=5.15.15,<5.16.0a0` |
| robostack-staging osx-arm64 `ros-noetic-rviz`, `-qt-gui-cpp` | 1.14.x, 0.4.x | `qt-main >=5.15.x,<5.16.0a0` |

→ The Qt5-vs-Qt6 mismatch found on linux-64 (our `rtabmap-rviz-plugins` patch, `robostack/humble/patch/ros-humble-rtabmap-rviz-plugins.patch`) exists identically on osx-arm64: RoboStack rviz is Qt5 while conda-forge VTK/PCL are Qt6.

### 3.2 conda-forge osx-arm64 dependency surfaces

| package | evidence (raw/repodata-conda-forge-osx-arm64.json) |
|---|---|
| `pcl` 1.15.1 | ALL 16 builds require `qt6-main >=6.9.1,<7.0a0` + `vtk` + `vtk-base` + `libboost` (1.88 or 1.90). Old pcl ≤1.14.1 builds used `qt-main` (Qt5) with vtk ≤9.2.6 — the Qt5→Qt6 switch happened at vtk-base 9.3.x |
| `vtk-base` | mixed: 466 records; old records (qt5-era, `qt-main >=5.15.8`) and 376 records with `qt6-main`. **All py312 builds of vtk-base 9.5.2/9.6.x/9.7.0 require `qt6-main`** (e.g. `vtk-base-9.6.0-py312h287a223_1.conda → qt6-main >=6.10.2`). No current Qt5 vtk-base |
| `vtk` | 516 records, no qt in deps (the `* qt*` build-string variant exists; GUISupportQt lives in vtk-base per pcl dep edges — detail UNVERIFIED beyond dep lists) |
| `libopencv` 4.13.0 / 5.0.0 | `headless_py312*` and `qt6_py312*` build variants; 175 records dep on qt6. Whether xfeatures2d/opencv_contrib modules ship on osx-arm64: UNVERIFIED from repodata alone (our linux-64 build at 4.13.0 found xfeatures2d YES — `evidence/humble/build-ros-humble-rtabmap-attempt2.log`) |
| `gtsam` | latest 4.2.2; osx-arm64 gtsam ≥4.2.1 builds all require `libboost >=1.90` (same conflict as linux-64 with mutex-0.9's `libboost 1.88` pin — see attempt1 log) |
| `llvm-openmp` | present, 97 records, latest 23.1.1 (osx equivalent of libgomp) |
| `octomap` | present, latest 1.9.8 on conda-forge osx-arm64 (1.10.0 lives in robostack-humble as `ros-humble-octomap`) |
| `eigen` 5.0.1, `sqlite` 3.53.4, `ceres-solver` 2.2.0, `qt-main` 5.15.8, `qt6-main` 6.9.3 | all present on osx-arm64 |
| `libnabo`, `libpointmatcher` | **ABSENT on osx-arm64 AND osx-64** (and every platform — no channel has them) |
| `g2o` (conda-forge) | absent on osx-arm64/osx-64/aarch64 (linux-64/win-64 only) — but `ros-humble-libg2o` 2020.5.29 exists on osx-arm64 in robostack-humble (mutex 0.7/0.8/0.9) |

### 3.3 Do osx-arm64 Noetic rtabmap artifacts exist?

**Yes — the full suite, current generation, built 2026-03-15** (raw/repodata-robostack-staging-osx-arm64.json and -robostack-noetic-osx-arm64.json):

| artifact (both robostack-staging and robostack-noetic, osx-arm64) | version/build/timestamp |
|---|---|
| `ros-noetic-rtabmap-0.21.13-np2py312hbc6d90e_24.conda` | 2026-03-15; deps: `ros-noetic-qt-gui-cpp`, `pcl >=1.15.1,<1.15.2`, `vtk-base >=9.6.0,<9.6.1`, `libboost >=1.88`, mutex `ros-distro-mutex 0.7.* noetic_*` |
| `ros-noetic-rtabmap-ros / -rviz-plugins / -viz / -slam / -odom / -conversions / -msgs / -util / -launch` | all 0.21.13, `np2py312h*_24`, 2026-03-15 |

Note the dep shape: `ros-noetic-rtabmap` on osx-arm64 depends on **both** `ros-noetic-qt-gui-cpp` (→ qt-main/Qt5) **and** `vtk-base ≥9.6.0` (whose py312 builds → qt6-main) — i.e. the noetic package already ships with Qt5+Qt6 co-installed, and `ros-noetic-rtabmap-rviz-plugins` itself depends only on pcl-conversions (Qt libs come transitively). Whether the osx-arm64 GUI actually works at runtime is UNVERIFIED (no runtime test possible here).

`ros-humble-moveit-ros-perception`: ABSENT on osx-arm64 (has `.osx.patch` though). `ros-humble-libnabo`: ABSENT everywhere.

---

## 4. rtabmap macOS precedents (GitHub)

### 4.1 introlab/rtabmap issues/PRs (gh api search)

| URL | state | gist |
|---|---|---|
| https://github.com/introlab/rtabmap/issues/1224 | open | "Error launching v0.21.4 on M1 Mac Ventura" |
| https://github.com/introlab/rtabmap/issues/1177 | open | "mac build error" |
| https://github.com/introlab/rtabmap/issues/1593 | closed | "macOS PCL not built with OpenNI!" (kinect v1) |
| https://github.com/introlab/rtabmap/issues/897 | closed | "Building with XCode 14 not working anymore" |
| https://github.com/introlab/rtabmap/issues/785 | closed | "Can't build library on macOS" |
| https://github.com/introlab/rtabmap/issues/351 | open | `ld: library not found for -lflann` linker error |
| https://github.com/introlab/rtabmap/issues/1567 | open | "Qt MainWindow appears fully black with Qt6" — Qt6 GUI rendering issue |
| https://github.com/introlab/rtabmap/issues/1566 | open | "Cloud viewer crash" |
| https://github.com/introlab/rtabmap/pull/968 | closed/merged | "Qt6 compatibility" PR |
| https://github.com/introlab/rtabmap/pull/1135 | closed | switch to AUTOUIC/AUTOMOC/AUTORCC |
| https://github.com/introlab/rtabmap/pull/1732 | merged | OpenCV 5 compatibility (backported in conda-forge PR below) |
| https://github.com/introlab/rtabmap/issues/1730 | open | opencv 5.0.0 support tracking |
| iOS-adjacent (tangential) | — | #1642, #1491, #1051, #836, #1429, #1278 |

introlab/rtabmap_ros searches for "macos"/"arm64": no relevant macOS-specific build issues surfaced (top hits are Jetson/ARM-Linux and generic topics). UNVERIFIED exhaustiveness — GitHub search indexing; suggest also trying `is:issue label:macOS` if needed.

### 4.2 conda-forge/staged-recipes PR #34714 "Add RTAB-Map 0.23.8" (open, not merged)

- URL: https://github.com/conda-forge/staged-recipes/pull/34714 (files copied to `raw/staged-recipes-34714.txt`; branch `jeongseok-meta/staged-recipes:add-rtabmap`).
- CI: **10/10 checks passed** incl. `build osx osx_64` and `build linux_64`/`win_64` (git_pr_checks 2026-09). Note: the check list shows `osx osx_64` only — an `osx_arm64` leg is NOT visible; conda-forge cross-builds osx-arm64 on osx-64 runners, so arm64 binary build status in CI: UNVERIFIED (PR body claims dep-solve checks passed for macOS arm64).
- `build.sh` flags (verbatim in raw file): `-DRTABMAP_QT_VERSION=6 -DWITH_QT=ON -DWITH_OPENMP=ON -DWITH_OCTOMAP=ON -DWITH_APRILTAG=ON -DWITH_CERES=ON -DWITH_PDAL=ON -DWITH_REALSENSE2=ON`, and notably `WITH_G2O=OFF, WITH_GTSAM=OFF, WITH_POINTMATCHER=OFF, WITH_TORO=OFF, WITH_VERTIGO=OFF, WITH_MADGWICK=OFF, WITH_ORB_OCTREE=OFF, WITH_PYTHON=OFF`.
- `recipe.yaml` host: `qt6-main`, `vtk`, `pcl >=1.7`, `octomap`, `ceres-solver`, `libopencv`, `sqlite`, `lz4-c`, `libdc1394` (not win), `llvm-openmp` (**`if: osx`**), `libgomp`+`libopengl-devel` (if linux); `qt6-main` in build when cross-compiling.
- Patches shipped: 0001 system lz4/sqlite; 0002 exclude disabled ORB-Octree code; 0003 scope vtk/pthreads discovery ("VTK is required when using Qt"); 0004 winsock2; 0005 PDAL writer export; 0006 OpenCV 5 backport (upstream PR 1732).
- Key delta vs our RoboStack recipe: conda-forge ships with Qt6 GUI and drops g2o/gtsam/toro/vertigo entirely; our linux-64 build kept g2o+GTSAM+OctoMap ON.

### 4.3 ros-noetic git history for rtabmap patches

(Clone was shallow; deepened to ~200 commits. All patch changes land in bulk "rebuild" commits — no per-patch rationale messages.)

- `patch/ros-noetic-rtabmap.patch`: touched by `4a31cb8` (2023-01-25 "Update vinca_linux_aarch64.yaml"), `c93c9cc` (2024-01-29 "Full Rebuild January 2024 with updated conda-forge pinnings" #418), `33d3128` (2025-01-09 "January 2025 rebuild using rattler-build" #501).
- `patch/ros-noetic-rtabmap-rviz-plugins.patch`: introduced/modified by `33d3128` (2025-01-09, rattler-build rebuild) and `0a1df5a` (2026-03-15 "Full Rebuild (Sync) March 2026: bump ros-distro-mutex to 0.7.0 and build_number to 24" #557) — the same commit date as the osx-arm64 0.21.13 artifacts in 3.3.
- `patch/ros-noetic-rtabmap-viz.patch`: `0a1df5a` (2026-03-15).

---

## 5. robostack.yaml (ros-humble) osx-relevant rosdep mappings — verbatim

File: `RoboStack/ros-humble/robostack.yaml` (line numbers).

```yaml
libpcl-all-dev:                       # L441
  robostack:
    linux: [pcl, libboost-devel, vtk-base, libopengl-devel, libgl-devel]
    osx:   [pcl, libboost-devel, vtk-base]          # no opengl/gl devel pkgs on osx
libopencv-dev:                        # L421
  robostack:
    linux: [py-opencv, libopencv, libopengl-devel, libgl-devel]
    osx:   [py-opencv, libopencv]
libqt5-* / qtbase5-dev / qt5-qmake / qt5-image-formats-plugins:   # L472-516, 1060-1074
  robostack:
    linux: [qt-main, libopengl-devel, libgl-devel]
    osx:   [qt-main]                                # all Qt5 keys → qt-main (Qt 5.15), NOT qt6
libsqlite3-dev: robostack: [sqlite 3.*]             # L527
eigen:          robostack: [eigen, eigen-abi-devel] # L83
libvtk / libvtk-qt: robostack: [vtk]                # L570-573
libglu-dev:     {linux: [libglu], osx: [], win64: []}              # L344
libomp-dev:     {linux: [libgomp], osx: [llvm-openmp], win64: []}  # L409
libx11{,-dev}:  {linux: [xorg-libx11, xorg-xorgproto, libopengl-devel, libgl-devel],
                 osx: [xorg-libx11, xorg-xorgproto]}               # L579-588
libglew-dev:    robostack: [glew]                   # L340
libglfw3-dev:   robostack: [glfw 3.*]               # L342
libvulkan-dev:  {linux: [libvulkan-headers, libvulkan-loader], osx: [], win64: […]}  # L574
```

**Not present** (grep returns nothing): `liboctomap-dev` (added in our worktree at `robostack/humble/robostack.yaml`), `qtbase5-private-dev` (hence vinca warning "Unsatisfied dependencies: {…, qtbase5-private-dev}" during phase-2 generation), `libgl-dev`, `libopengl-dev` bare keys, any `qt6*` rosdep keys.

---

## Notable UNVERIFIED items (consolidated)

1. Whether the hardcoded `OSX_DEPLOYMENT_TARGET=10.15` in vinca templates vs `c_stdlib_version: 10.13` in humble's conda_build_config causes any osx-64 issue (osx-arm64 unaffected: 11.0 == 11.0).
2. Whether osx-arm64 ros-noetic-rtabmap GUI actually runs (artifacts exist; no runtime test done).
3. Whether conda-forge `libopencv` osx-arm64 ships xfeatures2d/contrib modules.
4. staged-recipes #34714: whether CI produced an osx-arm64 binary (only `osx_64` job visible; PR body claims arm64 solve-passed).
5. Whether `vtk-base` vs `vtk` is the package owning `VTK::GUISupportQt` CMake target (dep-graph inference only).
6. ros-noetic patch commit intent — bulk rebuild commits, no per-patch messages.
7. GitHub search exhaustiveness for rtabmap_ros macOS issues.
