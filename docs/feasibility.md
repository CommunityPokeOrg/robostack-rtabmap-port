# Feasibility analysis — RTAB-Map on RoboStack osx-arm64 (Gate 0, issue #12)

Date: 2026-09-14. Evidence base: `docs/feasibility-survey.md` (per-claim file paths / URLs),
`investigation/feasibility-raw/` (repodata query output, patch-topic greps, staged-recipes PR files),
`evidence/humble/` (linux-64 build logs and smoke test), `investigation/deps_*.md`.

**No osx-arm64 build has been executed for this project.** Everything below is derived from
(a) what RoboStack has already built and published for osx-arm64, (b) recipe/patch/CI metadata,
(c) our linux-64 builds of the same recipes. Unknowns that only a real osx-arm64 build can settle
are listed separately in §6.

## 1. Assessment

| target | verdict | conditions |
|---|---|---|
| `rtabmap` core (`ros-humble-rtabmap`) | **conditional-go** | C1 GTSAM/Boost pin resolved or accepted (mutex 0.8); C2 OpenMP decision (add `llvm-openmp` or accept `WITH_OPENMP` off on macOS); C3 one native osx-arm64 build + `rtabmap --version` smoke test (#8) |
| `rtabmap_ros` family (`ros-humble-rtabmap-*`) | **conditional-go** | C1–C3 above; C4 the Qt5/Qt6 interface-strip patch for `rtabmap_rviz_plugins` (already written and built on linux-64) must build on macOS; C5 runtime check that rviz2 (Qt5) loading the plugin does not pull Qt6 into the process; C6 `rtabmap_python` may need the Apple `-undefined dynamic_lookup` pattern |
| `libpointmatcher` ICP support | **no-go for MVP** | no `libpointmatcher`/`libnabo` on any conda channel for any platform; RTAB-Map builds without it (verified on linux-64) |
| Windows (`win-64`) | **out of scope** | `ros-humble-libg2o`, `grid-map-ros`, `realsense2-camera`, `velodyne` not published on win-64 |

Why not an unconditional **go**: the single strongest data point — RoboStack's ROS 1 Noetic RTAB-Map
suite built natively on osx-arm64 — is for a different ROS generation (catkin, ROS 1 rviz), and its GUI
runtime behaviour on macOS is unverified. Why not **no-go**: every hard prerequisite (native arm64 CI,
Qt/VTK/PCL/OpenCV/GTSAM/g2o/OctoMap/SQLite/Eigen on osx-arm64, the ROS dependency closure, a
working recipe generation path, and a precedent patch for the one known conflict) is in place.

## 2. Key findings (evidence in survey §)

### 2.1 Precedent: RTAB-Map already exists on RoboStack osx-arm64 for ROS 1
- `ros-noetic-rtabmap 0.21.13` plus `-ros`, `-rviz-plugins`, `-viz`, `-slam`, `-odom`, `-conversions`,
  `-msgs`, `-util`, `-launch` are published for **osx-arm64** on `robostack-staging` and `robostack-noetic`,
  built 2026-03-15 (build `np2py312h*_24`) by RoboStack's native `macos-15` CI job. (survey §3.3, §1.1)
- Its dependency shape is the same as ours: `pcl 1.15.1`, `vtk-base ≥9.6` (Qt6), `ros-noetic-qt-gui-cpp`
  (Qt5), `ros-noetic-gtsam`, `ros-noetic-libg2o`, `sqlite`, `libboost 1.88`. (survey §3.3)
- Noetic carries five `ros-noetic-rtabmap-*.patch` files; only two are structural and both address the
  Qt5/Qt6 split (§2.3 below). The others are a PCL 1.15 header rename and no-ops. (survey §2.1)

### 2.2 Toolchain and CI pattern
- RoboStack builds osx-arm64 **natively** on `macos-15` runners (`osx-64` on `macos-15-intel`); no
  cross-compilation for macOS. Command: `pixi run rattler-build build --recipe-dir recipes
  --target-platform osx-arm64 -m conda_build_config.yaml -c conda-forge -c robostack-staging --skip-existing`.
  (survey §1.1) → our CI (#9) should copy this; a GitHub-hosted `macos-15`/`macos-14` runner suffices.
- Compiler: conda-forge `clang 18` (Humble), `c_stdlib_version 11.0` on arm64; vinca's build templates
  pass `-DCMAKE_OSX_DEPLOYMENT_TARGET=10.15` (native) and `-DCMAKE_IGNORE_PREFIX_PATH=/opt/homebrew;...`,
  `-DCMAKE_FIND_FRAMEWORK=LAST`. Mixing Homebrew and other toolchains is a recurring theme in upstream
  macOS build reports (introlab/rtabmap #785, #897, #1177, #351 — linker/library-not-found class; not
  individually root-caused here) and is structurally prevented inside a conda build.
  (survey §1.2, §1.4, §4.1)
- No template-level rpath / `install_name_tool` handling is needed: rattler-build relinks dylibs; RoboStack
  patches only add `-undefined dynamic_lookup` for Python extension modules on Apple (`qt-gui-cpp`,
  `python-qt-binding`, noetic `rqt-gui-cpp`). (survey §1.4, §2.2)

### 2.3 Qt5 (rviz) vs Qt6 (VTK / PCL / rtabmap_gui) — the one confirmed structural conflict
- RoboStack rviz2, rviz-rendering, qt-gui-cpp depend on `qt-main` (**Qt 5.15**) on every distro
  (Humble, Jazzy, Noetic), every mutex generation, on osx-arm64 and linux-64 alike. (survey §3.1)
- conda-forge `pcl 1.15.1` and every current `vtk-base` build on osx-arm64 require **`qt6-main`**. (survey §3.2)
- Consequence: `rtabmap::gui` and `VTK::GUISupportQt` export Qt6 targets; `rtabmap_rviz_plugins`
  (a Qt5 rviz plugin) fails to configure with `INTERFACE_QT_MAJOR_VERSION ... does not agree`. We hit
  this on linux-64 and fixed it with `robostack/humble/patch/ros-humble-rtabmap-rviz-plugins.patch`
  (strip `rtabmap::gui`, `VTK::GUISupportQt`, `Qt6::*` from consumed interfaces; resulting plugin links Qt5 only).
  Noetic's `ros-noetic-rtabmap-rviz-plugins.patch` / `-viz.patch` do the equivalent (`/qt6/`, `Qt6::` filter).
  (`evidence/humble/build-rtabmap-rviz-plugins-attempt{1,2}.log`, survey §2.1)
- Reusable pattern: Qt5 pinning patches exist for `rviz2`, `rviz-default-plugins`, `nav2-rviz-plugins`,
  `octomap-rviz-plugins`, `vision-msgs-rviz-plugins` — this is routine in RoboStack. (survey §2.2, §2.3)

### 2.4 Dependency availability on osx-arm64
| dependency | status on osx-arm64 | note |
|---|---|---|
| PCL 1.15.1 (VTK 9.7, Qt6) | conda-forge | Boost 1.90 in newest builds; RoboStack mutex pins the matching generation |
| OpenCV 4.13 via `ros-humble-cv-bridge` | robostack-humble | `xfeatures2d` presence on osx-arm64 unverified (§6) |
| GTSAM | `ros-humble-gtsam` 4.2.0/4.2.1 | ≥4.2.1 needs Boost ≥1.90 → conflict with mutex 0.9 (Boost 1.88); same on linux (#2) |
| g2o | `ros-humble-libg2o` 2020.5.29 | conda-forge `g2o` absent on macOS; the ROS wrapper is present |
| Qt | `qt-main` 5.15 (via qt-gui-cpp), `qt6-main` (via VTK) | both installed side by side — as in Noetic |
| VTK | `vtk-base` 9.5–9.7 | Qt6 |
| Eigen 5.0.1, SQLite 3.53, zlib, proj, OctoMap 1.10 (`ros-humble-octomap`) | present | `liboctomap-dev` rosdep key needs the mapping we added |
| OpenMP | `llvm-openmp` present; **not a dependency** of rtabmap's `package.xml` nor of `pcl`/`ros-noetic-rtabmap` on osx-arm64 | expect `WITH_OPENMP` = NO unless we add `libomp-dev`/`llvm-openmp` (C2) |
| libpointmatcher / libnabo | **absent everywhere** | build without (`WITH_POINTMATCHER=OFF`) |
| ROS closure for `rtabmap_ros` | all published on robostack-humble osx-arm64 except `aruco-msgs`, `aruco-opencv-msgs` | both generated and built by us on linux-64 (`empy <4` fix) |
(survey §3.2, §3.3, `investigation/deps_humble.md`)

### 2.5 Second precedent: conda-forge standalone recipe
- conda-forge/staged-recipes#34714 (rtabmap 0.23.8) passes CI on `osx_64` with `RTABMAP_QT_VERSION=6`,
  `llvm-openmp` (`if: osx`), GTSAM/g2o/libpointmatcher **off**. An `osx_arm64` CI leg is not visible
  (conda-forge cross-builds arm64 from osx-64); arm64 binary status unverified. (survey §4.2)
- It confirms the Qt6 GUI path of RTAB-Map compiles with conda clang on macOS, and gives a
  reusable patch set (system lz4/sqlite, VTK-with-Qt scoping, OpenCV 5 backport for 0.23.x).

### 2.6 Our linux-64 result as a control
All 15 Humble packages build with RoboStack's stock generator; **one** source patch (Qt5/Qt6 strip) and
one recipe-level fix (`empy <4`) were needed; smoke test passes (`evidence/humble/phase2-smoke-test.log`).
This bounds the macOS delta to macOS-specific issues only.

## 3. Prerequisites checklist

### `rtabmap` core
- [x] Recipe generation path (vinca → rattler-build) works — linux-64.
- [x] `liboctomap-dev → octomap` mapping added to `robostack.yaml`.
- [x] `libpointmatcher` removed from the dependency closure.
- [x] C1 — GTSAM/Boost: **accepted mutex 0.8 / `ros-humble-gtsam` 4.2.0 / Boost 1.88 as the temporary pin** (#2).
  `investigation/check_gtsam_boost.py` → `investigation/gtsam_boost_humble.md` shows from live repodata that
  mutex 0.9 + `ros-humble-gtsam` 4.2.1 is unsatisfiable on linux-64 *and* osx-arm64 (gtsam 4.2.1 builds need
  Boost 1.90), and that the 0.8 pair solves on both. Dry-run solve of the `ros-humble-rtabmap` host env for
  osx-arm64: `evidence/humble/osx-arm64/dry-run-solve-rtabmap-host.txt` (gtsam 4.2.0 b14, boost 1.88, mutex 0.8.0).
  Exit path unchanged: a `ros-humble-gtsam` rebuilt on mutex 0.9 against Boost 1.88, or a mutex ≥0.10 on Boost 1.90.
- [x] C2 — OpenMP on macOS: `llvm-openmp` added `if osx` to host **and** run of `rtabmap` in
  `robostack/humble/patch/dependencies.yaml` (vinca depmod, same mechanism upstream uses for `ceres-solver`/`vtk`).
  Verified in the rendered osx-arm64 recipe (`evidence/humble/osx-arm64/render-rtabmap-osx-arm64.json`). Whether
  CMake actually reports `WITH_OPENMP=ON` on macOS is still to be read off the first native build log (C3).
- [ ] C3 — Native osx-arm64 build + smoke test (#8). CI scaffolding is in place
  (`.github/workflows/build-humble.yml`: `macos-15` job → vinca `--platform osx-arm64` → drift/patch/dry-run-solve,
  then `pixi run build-port` + smoke gated on the `ci:build` label / `workflow_dispatch`). **Not yet executed on a
  Mac — the development machine is linux-64.**

### `rtabmap_ros`
- [ ] C4 — `patch/ros-humble-rtabmap-rviz-plugins.patch` applies and builds on macOS (no APPLE-specific code in it; expected to carry over).
- [ ] C5 — rviz2 runtime with the plugin loaded: confirm `otool -L` of the plugin shows Qt5 only and rviz2 does not dlopen Qt6 through `librtabmap_core` → `libpcl_visualization` → `VTK::GUISupportQt`. On linux-64 `ldd` of the plugin shows no Qt6; macOS must be re-checked.
- [ ] C6 — `rtabmap_python`: check whether its extension links `Python::Python`; if so apply the RoboStack Apple `-undefined dynamic_lookup` pattern.
- [ ] `rtabmap_costmap_plugins` is not generated (vinca warning) — it is not in the Humble release list we seeded; decide whether it is needed.

## 4. Reusable patterns (with sources)
- Native macOS CI matrix and build command: `RoboStack/ros-humble/.github/workflows/testpr.yml`.
- Qt5 pinning / Qt6-strip: `robostack/humble/patch/ros-humble-rtabmap-rviz-plugins.patch` (this repo);
  `RoboStack/ros-noetic/patch/ros-noetic-rtabmap-rviz-plugins.patch`, `-viz.patch`.
- OpenMP on Apple: `ros-humble-nav2-mppi-controller.osx.patch`, `ros-humble-nav2-smac-planner.osx.patch`
  (skip `find_package(OpenMP)`, link `-fopenmp`); rosdep `libomp-dev → osx: [llvm-openmp]`.
- Python extension on Apple: `ros-humble-qt-gui-cpp.patch` (`if(NOT APPLE) ... Python::Python`).
- OpenGL/GLUT framework handling if ever needed: `ros-humble-moveit-ros-perception.osx.patch`.
- Platform selectors: `if: osx` (`llvm-openmp`, `tapi`), `if: not win` (seed), `if: linux`
  (`libgomp`, `libopengl-devel`, `libgl-devel`) — all already emitted by vinca/robostack.yaml.
- conda-forge recipe fragments for RTAB-Map 0.23.x: `investigation/feasibility-raw/staged-recipes-34714.txt`.

## 5. Recommended path (if the conditional-go is accepted)
1. ~~Add a `macos-15` (osx-arm64) job to this repo's CI (#9)~~ — done, `.github/workflows/build-humble.yml`;
   first run the `build` stage via `workflow_dispatch` (or the `ci:build` PR label) and commit the log.
2. ~~Resolve C2 in the recipe before that run~~ — done via `patch/dependencies.yaml`.
3. Run the smoke test set from `evidence/humble/phase2-smoke-test.log` on macOS, plus `otool -L` checks (C5).
4. Only after a green arm64 run, open the upstream RoboStack PR (seed + mapping + patch).

## 6. Unknowns (not resolvable without an osx-arm64 build or a Mac)
1. Whether the osx-arm64 Noetic RTAB-Map GUI actually runs (artifacts exist, runtime untested).
2. RTAB-Map Qt6 GUI rendering on macOS (upstream introlab/rtabmap#1567 "MainWindow fully black with Qt6" is open; platform unclear).
3. Whether conda-forge `libopencv` on osx-arm64 includes `xfeatures2d`/contrib (affects feature detectors, not buildability).
4. OpenMP: `llvm-openmp` is now in the host env; still confirm `WITH_OPENMP=ON` in the macOS CMake log (C2/C3).
5. Whether staged-recipes#34714 produced an osx-arm64 binary (only `osx_64` CI leg visible).
6. Runtime Qt5+Qt6 coexistence inside one rviz2 process on macOS (C5).
7. vinca template `OSX_DEPLOYMENT_TARGET=10.15` vs Humble `c_stdlib_version 10.13` mismatch — affects osx-64 only; arm64 is consistent at 11.0.
8. Build time of the PCL/VTK-heavy packages on GitHub-hosted macOS runners (RoboStack builds them, so it is feasible; duration unknown).
