# Host requirements

The container holds ROS, the desktop, and the build toolchain. Only three
things have to exist on the host.

## Which engine should I use?

**Docker unless you have a reason to prefer Podman.** It is one installer on
Linux, macOS, and Windows, its Compose implementation is the reference one, and
it is the path CI validates end to end. If Docker is installed, everything here
detects and uses it automatically — nothing in this file applies to you.

Choose Podman when you want rootless containers with no daemon, or when Docker
Desktop's licensing does not suit your organization. It is a supported fallback,
not a second-class one, but two things are worth knowing before you commit:

- **Use Podman 4.4 or newer.** It has `podman compose` built in. Older versions
  need `podman-compose` from `requirements-host.txt`, and its flag coverage
  varies by version — Podman 3.4 (Ubuntu 22.04's version) rejects some flags
  that `podman-compose` passes through.
- **CI tests Podman non-blocking.** A Podman-only regression is reported rather
  than gating the branch, so it may be fixed a release later than a Docker one.

Both engines run the same image and the same `compose.yaml`; the difference is
entirely in the host tooling.

## 1. A container engine

Either one works; `make engine` reports which was detected.

| Engine | Minimum | Notes |
|---|---|---|
| Docker Engine / Docker Desktop | 24+ with the Compose plugin | The documented default; what CI tests |
| Podman | 4.4+ | `podman compose` is built in |
| Podman | 3.4–4.3 | Also needs `podman-compose` from [requirements-host.txt](../requirements-host.txt) |

Install commands:

```sh
# Debian/Ubuntu
sudo apt install podman
# Fedora
sudo dnf install podman
# macOS
brew install podman && podman machine init && podman machine start
# Windows: Docker Desktop with WSL 2, or Podman Desktop
```

## 2. A compose implementation

Docker's Compose plugin ships with Docker. Podman 4.4+ has `podman compose`
built in. Older Podman needs `podman-compose`:

```sh
pip install --user -r requirements-host.txt
```

Make sure `~/.local/bin` is on your `PATH` afterwards, or `make` will not find
it.

## 3. Resources

| Resource | Minimum | Comfortable |
|---|---|---|
| RAM available to the engine | 4 GB | 8 GB |
| Disk | 15 GB | 25 GB |

The image is large because RViz and `rqt` are large. turtlesim alone would fit
in a fraction of it; see [hardware-and-gpu.md](hardware-and-gpu.md) for
splitting heavier tools into separate targets.

## Checking

```sh
make doctor
```

reports each requirement with the exact command to fix it. It changes nothing.

## Podman-specific notes

**Short image names.** Podman refuses unqualified names unless the host defines
`unqualified-search-registries`. The Dockerfile spells out
`docker.io/library/ros`, so no host configuration is needed. If you point
`ROS_REGISTRY` at a mirror, use its fully qualified form too.

**Rootless by default.** The desktop service runs as `root` inside a user
namespace, which is your own unprivileged host account. No `sudo` is required
to build or run anything here.

**The "/ is not a shared mount" warning.** Harmless for this project — it
concerns mount propagation for bind mounts, and everything here uses named
volumes. Silence it with `sudo mount --make-rshared /` if it bothers you.

**Ubuntu 22.04 ships Podman 3.4.4**, which predates `podman compose`. That is
exactly the case `requirements-host.txt` exists for.

### Known quirks with podman-compose on Podman 3.x

All of these are host-tooling limitations, not image problems. The full smoke
suite passes on this combination; these are the places where the *commands
around* it differ from Docker.

| Quirk | Effect | Work around it |
|---|---|---|
| `logs` passes `--color`, which Podman 3.x rejects | `make logs` fails | `podman logs -f <container>`; `make logs` prints the exact command |
| `ps` takes no service argument | `podman-compose ps desktop` errors | `podman-compose ps` and read the list |
| Profile services need `--profile` on *every* subcommand | `exec talker` reports "missing services" | `podman-compose --profile demo exec talker ...` |
| `run` prints a container id, not the command's output | Scripted `run` output is unusable | Use `exec` against a running service |
| `build --pull` becomes `--pull=newer` | Build fails | Already removed; the base is digest-pinned |

A CNI warning — `plugin firewall does not support config version "1.0.0"` — is
printed on every network operation with Podman 3.4. It is noise: the bridge
network works, and cross-service DDS discovery was verified over it.
