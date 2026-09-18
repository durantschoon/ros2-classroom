# Hardware, GPU, and other optional extensions

The base workflow promises one thing: a portable ROS tutorial environment with a
browser desktop. Hardware access is *not* portable, so it lives here as
documented opt-ins rather than hidden defaults.

Each section below is an override file you apply explicitly:

```sh
docker compose -f compose.yaml -f compose.gpu.yaml up -d
```

## GPU acceleration (Linux + NVIDIA only)

The default desktop renders in software (llvmpipe). That is fine for turtlesim
and usable for `rqt`; RViz with a large point cloud will feel slow.

On Linux with the NVIDIA Container Toolkit installed, create `compose.gpu.yaml`:

```yaml
services:
  desktop:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      NVIDIA_DRIVER_CAPABILITIES: all
```

This does not work through Docker Desktop on macOS, and on Windows it requires
WSL 2 with an NVIDIA driver that supports GPU passthrough. Software rendering
remains the portable default so the documented commands keep working everywhere.

## USB and serial devices (Linux)

On native Linux, pass the device through:

```yaml
services:
  desktop:
    devices:
      - "/dev/ttyUSB0:/dev/ttyUSB0"
    group_add:
      - dialout
```

On macOS and Windows, Docker Desktop runs containers inside a Linux VM that has
no direct access to host USB. Reaching a device there needs USB/IP
(`usbipd-win` on Windows) or platform-specific tooling, and is out of scope for
the tutorial workflow.

## Cameras

Linux: `devices: ["/dev/video0:/dev/video0"]`. macOS and Windows: not supported
through Docker Desktop; use a recorded bag file instead, which is also more
reproducible for tutorials.

## Real-time and multicast

The container inherits the host kernel's scheduling. Real-time tutorials that
require `SCHED_FIFO` need `cap_add: [SYS_NICE]` and a suitable host, and will not
behave identically inside Docker Desktop's VM.

Multicast DDS discovery works on the compose bridge network but can be blocked by
VPN clients and some corporate networks. See the discovery-server note in
[cross-platform.md](cross-platform.md).

## Host source bind mounts (editor integration)

The default keeps source in a named volume, which avoids UID mismatches and slow
cross-VM filesystem access. If you want to edit `/workspace/src` with a host
editor, create `compose.bind.yaml`:

```yaml
services:
  desktop:
    volumes:
      - ./workspace-src:/workspace/src
```

On Linux, files will be owned by UID 1000 inside the container; if your host UID
differs, rebuild with `--build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g)`.
On macOS and Windows, expect slower builds than the named volume.

## VS Code dev container

[`.devcontainer/devcontainer.json`](../.devcontainer/devcontainer.json) points
VS Code at the same `desktop` service rather than defining a second
environment: same image, same `/workspace` volume, same `ros` user. Open the
repository in VS Code and use **Reopen in Container**; it reuses `compose.yaml`
as-is, so anything already running via `make up` keeps running.

## Heavier simulation stacks

Gazebo, Nav2, and MoveIt are deliberately not in the base image: they would
several-x the download for users who came to run turtlesim. Add them either as
`EXTRA_ROS_PACKAGES` for your own builds, or as a separate compose profile with
its own image target.
