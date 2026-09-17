# ROS 2 distribution choice

The two branches use different ROS releases, for reasons that come down to how
each one obtains ROS.

## This branch (default): Lyrical

The container image installs ROS from the official `packages.ros.org` apt
repository, where ROS 2 Lyrical Luth is published for Ubuntu 26.04 (Resolute)
on both amd64 and arm64. Nothing has to be ported, so the default tracks the
current LTS.

## The `guix` branch: Jazzy

That branch uses ROS 2 Jazzy Jalisco. It is an LTS release supported through
May 2029, is newer than Humble, and is the ROS distribution packaged by the
pinned SystoleOS Guix source. For turtlesim, Jazzy provides the familiar ROS 2
tutorial workflow while keeping every source and toolchain input under Guix.

### Why that branch cannot simply move to Lyrical

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
native Guix option available there. This branch can be used to try a newer
official Ubuntu-based ROS image without weakening the versioned native
environment on `guix`.

## Why the two disagree

They answer different questions. The `guix` branch asks "what can be built
reproducibly from source under Guix?" This branch asks "what can a learner run
on any laptop today?"

The base image here is pinned by digest rather than by source hash. That is a
weaker reproducibility guarantee than Guix provides — the same digest yields the
same base layers, but the apt layer resolves against a moving repository. It is
the right trade for a tutorial environment, and the reason the `guix` branch
keeps the stronger guarantee for the native build.
