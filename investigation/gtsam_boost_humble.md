
## linux-64

### conda-forge gtsam (grouped by version / build number)
| version | build numbers | libboost |
|---|---|---|
| 4.1.1 | 0,1,2,3,4,5,6 | None |
| 4.2.0 | 0 | None |
| 4.2.0 | 1,2,3,6,7 | libboost >=1.82.0,<1.83.0a0 |
| 4.2.0 | 4,5,6,7,8 | libboost >=1.84.0,<1.85.0a0 |
| 4.2.0 | 9,10,11,12 | libboost >=1.86.0,<1.87.0a0 |
| 4.2.0 | 13,14 | libboost >=1.88.0,<1.89.0a0 |
| 4.2.0 | 15 | libboost >=1.90.0,<1.91.0a0 |
| 4.2.1 | 0,1 | libboost >=1.90.0,<1.91.0a0 |
| 4.2.2 | 0 | libboost >=1.90.0,<1.91.0a0 |

### robostack-humble ros2-distro-mutex
| version | build | libboost constraint |
|---|---|---|
| 0.1.0 | humble | None |
| 0.6.0 | humble_0 | libboost 1.86.* |
| 0.7.0 | humble_13 | libboost 1.86.* |
| 0.8.0 | humble_15 | libboost 1.88.* |
| 0.9.0 | humble_18 | libboost 1.88.* |

### robostack-humble ros-humble-gtsam
| version | build | gtsam dep | mutex dep | solvable with mutex libboost? |
|---|---|---|---|---|
| 4.2.0 | np126py311h2c3b307_7 | None | ros2-distro-mutex 0.6.* humble_* | True (cf gtsam boost minors [82, 84, 86, 88, 90], mutex boost 1.86) |
| 4.2.0 | py311h82375c7_13 | gtsam >=4.2.0,<4.3.0a0 | ros2-distro-mutex 0.7.* humble_* | True (cf gtsam boost minors [82, 84, 86, 88, 90], mutex boost 1.86) |
| 4.2.0 | py312hfb442f0_15 | gtsam >=4.2.0,<4.3.0a0 | ros2-distro-mutex 0.8.* humble_* | True (cf gtsam boost minors [82, 84, 86, 88, 90], mutex boost 1.88) |
| 4.2.1 | py312hdb78f74_18 | gtsam >=4.2.1,<4.3.0a0 | ros2-distro-mutex 0.9.* humble_* | False (cf gtsam boost minors [90], mutex boost 1.88) |

## osx-arm64

### conda-forge gtsam (grouped by version / build number)
| version | build numbers | libboost |
|---|---|---|
| 4.1.1 | 2,3,4,5,6 | None |
| 4.2.0 | 0 | None |
| 4.2.0 | 1,2,3,6,7 | libboost >=1.82.0,<1.83.0a0 |
| 4.2.0 | 4,5,6,7,8 | libboost >=1.84.0,<1.85.0a0 |
| 4.2.0 | 9,10,11,12 | libboost >=1.86.0,<1.87.0a0 |
| 4.2.0 | 13,14 | libboost >=1.88.0,<1.89.0a0 |
| 4.2.0 | 15 | libboost >=1.90.0,<1.91.0a0 |
| 4.2.1 | 0,1 | libboost >=1.90.0,<1.91.0a0 |
| 4.2.2 | 0 | libboost >=1.90.0,<1.91.0a0 |

### robostack-humble ros2-distro-mutex
| version | build | libboost constraint |
|---|---|---|
| 0.1.0 | humble | None |
| 0.6.0 | humble_0 | libboost 1.86.* |
| 0.7.0 | humble_13 | libboost 1.86.* |
| 0.8.0 | humble_15 | libboost 1.88.* |
| 0.9.0 | humble_18 | libboost 1.88.* |

### robostack-humble ros-humble-gtsam
| version | build | gtsam dep | mutex dep | solvable with mutex libboost? |
|---|---|---|---|---|
| 4.2.0 | np126py311h38cf310_6 | None | ros2-distro-mutex 0.6.* humble_* | True (cf gtsam boost minors [82, 84, 86, 88, 90], mutex boost 1.86) |
| 4.2.0 | py311h43e502b_13 | gtsam >=4.2.0,<4.3.0a0 | ros2-distro-mutex 0.7.* humble_* | True (cf gtsam boost minors [82, 84, 86, 88, 90], mutex boost 1.86) |
| 4.2.0 | py312h66022c0_15 | gtsam >=4.2.0,<4.3.0a0 | ros2-distro-mutex 0.8.* humble_* | True (cf gtsam boost minors [82, 84, 86, 88, 90], mutex boost 1.88) |
| 4.2.1 | py312h8546f8a_18 | gtsam >=4.2.1,<4.3.0a0 | ros2-distro-mutex 0.9.* humble_* | False (cf gtsam boost minors [90], mutex boost 1.88) |
