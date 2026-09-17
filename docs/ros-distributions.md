# ROS 2 distribution choice

## Current choice: Jazzy

This project uses ROS 2 Jazzy Jalisco. It is an LTS release supported through
May 2029, is newer than Humble, and is the ROS distribution packaged by the
pinned SystoleOS Guix source. For turtlesim, Jazzy provides the familiar ROS 2
tutorial workflow while keeping every source and toolchain input under Guix.

## Why not Lyrical yet?

ROS 2 Lyrical Luth is the latest ROS 2 release as of September 2026 and is an
LTS supported through May 2031. The pinned SystoleOS checkout does not package
Lyrical, however. A name change in `manifest.scm` cannot supply it: the ROS
packages, dependency versions, patches, source commits, hashes, and build
results must first be ported and tested in Guix.

Moving this project to Lyrical should therefore be a deliberate packaging
upgrade:

1. Add a Lyrical distribution definition and package set to SystoleOS.
2. Port the minimal turtlesim and `ros2 run` dependency closure.
3. Build it with the pinned Guix channels and run the headless smoke test.
4. Test two graphical containers for DDS discovery and keyboard control.
5. Update the SystoleOS submodule pin and this manifest in one reviewable
   dependency-upgrade commit.

Until that work exists upstream or is completed locally, Jazzy is the newest
native Guix option available here. The `podman` branch can remain a fallback
for testing a newer official Ubuntu-based ROS image without weakening the
versioned native environment on `main`.
