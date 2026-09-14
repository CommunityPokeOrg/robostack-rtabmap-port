# Feasibility analysis — RTAB-Map on RoboStack osx-arm64 (Gate 0, issue #12)

**Decision: PENDING.** This document is the deliverable of
https://github.com/CommunityPokeOrg/robostack-rtabmap-port/issues/12 and is not yet written.
Structure to be filled (see the issue for the full research scope):

1. Findings per topic (compiler/linker, OpenMP, Qt/OpenGL/VTK, OpenCV, PCL, GTSAM/g2o, Eigen, SQLite, ROS integration, runtime paths, CI) — each with evidence links.
2. Prerequisite checklist for `rtabmap`; prerequisite checklist for `rtabmap_ros`.
3. Reusable patterns (selectors, patch snippets, CMake flags, recipe fragments) with source links.
4. Assessment: `rtabmap` → go / conditional-go / no-go; `rtabmap_ros` → go / conditional-go / no-go.
5. Unknowns that only an actual osx-arm64 build (#8) can resolve — kept separate from findings.
