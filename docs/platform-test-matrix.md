# Platform test checklist

CI covers amd64 end to end and arm64 as a build plus headless checks. What CI
*cannot* check is the part students actually see: whether the desktop renders in
a browser, whether keystrokes reach the turtle, and how each platform's
container runtime behaves. That needs a human on each machine.

This doubles as data collection. Record results in the decision-point vocabulary
from [roadmap.md](roadmap.md#stage-4--failure-capture-and-the-improvement-loop),
so your own three machines seed the recipe corpus rather than living in your
head.

## Before you start

Per machine, budget **30-45 minutes**, nearly all of it the first image build.

| Need | Value |
|---|---|
| Disk free | 15 GB minimum, 25 GB comfortable |
| RAM for the engine | 4 GB minimum, 8 GB comfortable |
| Network | The build pulls ~3 GB |

Run `make doctor` first on every machine — it reports engine, version, rootless
status, disk and RAM, and names the fix for anything missing.

---

## A. macOS (Apple Silicon)

**Engine:** Docker Desktop, or `brew install podman && podman machine init && podman machine start`.

- [ ] `make doctor` reports an engine and passes resources
- [ ] `make image` completes — **watch:** it must build `linux/arm64` natively
- [ ] Confirm the arch: `docker image inspect ros2-tutorials:lyrical --format '{{.Architecture}}'` → `arm64`
- [ ] `make up` then `make open` — browser opens the desktop
- [ ] Desktop renders: Openbox background, a terminal already open
- [ ] Right-click → turtlesim_node — window appears
- [ ] Right-click → turtle_teleop_key, click it, **arrow keys move the turtle**
- [ ] **Reconnect**: close and reopen the tab (or sleep the machine) — the page
      reconnects by itself and turtlesim is still running
- [ ] **Clipboard**: paste a command into the desktop terminal via the side
      panel's Clipboard button, and run it
- [ ] `install-ros-packages demo-nodes-cpp` succeeds in the desktop terminal
- [ ] `tutorial clone https://github.com/ros/ros_tutorials.git && tutorial deps && tutorial build`
- [ ] `make down && make up` — `/workspace/src` still has the clone
- [ ] `make selftest` — record the pass/fail counts
- [ ] `make down` stops within the grace period

**Watch for:** if the build falls back to `linux/amd64` it will run under Rosetta
and the software-rendered desktop will be noticeably slow — that is a bug to
report, not something to work around with `--platform`.

---

## B. Windows 11 + WSL 2

Test **both** entry points, because the README advertises both.

**Engine:** Docker Desktop with WSL integration enabled for your distro, or
Podman inside WSL.

### B1. From a WSL shell

- [ ] Repo is cloned inside the WSL filesystem (`~/...`, **not** `/mnt/c/...`)
- [ ] `make doctor` reports an engine
- [ ] `make image` completes
- [ ] `make up` then `make open` — **watch:** this must open a Windows browser,
      not a text editor. That failure mode was real; see `scripts/open-url`
- [ ] Desktop renders in the Windows browser at `localhost:6080`
- [ ] turtlesim window appears
- [ ] **Arrow keys move the turtle**
- [ ] **Reconnect**: close and reopen the tab (or sleep the machine) — the page
      reconnects by itself and turtlesim is still running
- [ ] **Clipboard**: paste a command into the desktop terminal via the side
      panel's Clipboard button, and run it
- [ ] `install-ros-packages demo-nodes-cpp` succeeds
- [ ] `tutorial clone ... && tutorial deps && tutorial build`
- [ ] Persistence across `make down && make up`
- [ ] `make selftest` — record counts
- [ ] `make down` clean

### B2. From PowerShell

Make is usually absent; use the documented plain commands.

- [ ] `docker compose build`
- [ ] `docker compose up -d`
- [ ] Browse to `http://localhost:6080/vnc.html?autoconnect=1&resize=remote&reconnect=true`
- [ ] Desktop renders; turtlesim and turtle_teleop_key work from the right-click menu
- [ ] `docker compose down`

**Watch for:** a repo on `/mnt/c` makes the build crawl; Docker Desktop must
have WSL integration on for the distro you are in, or `docker` resolves to the
Windows shim and fails.

---

## C. Pure Linux

**Engine:** Docker Engine + Compose plugin, or rootless Podman 4.4+.

- [ ] `make doctor` — note whether it reports docker or podman
- [ ] `make image`
- [ ] `make up` then `make open` — `xdg-open` path, needs a real browser installed
- [ ] Desktop renders
- [ ] turtlesim appears; **arrow keys move the turtle**
- [ ] **Reconnect**: close and reopen the tab (or sleep the machine) — the page
      reconnects by itself and turtlesim is still running
- [ ] **Clipboard**: paste a command into the desktop terminal via the side
      panel's Clipboard button, and run it
- [ ] `install-ros-packages demo-nodes-cpp`
- [ ] `tutorial clone ... && tutorial deps && tutorial build`
- [ ] Persistence across `make down && make up`
- [ ] `make selftest` — record counts
- [ ] `make down` clean
- [ ] If Podman: confirm no CNI warnings leak through the Make targets, and that
      `VERBOSE=1 make up` shows them again

**Watch for:** on Fedora/RHEL, SELinux affects bind mounts — this project uses
named volumes so it should not bite, but note it if it does. If the machine has
an NVIDIA GPU, the software-rendered default must still work *without* the
NVIDIA toolkit.

---

## Recording a run

For each machine, fill in the decision points. Closed values only — this is the
same vocabulary the failure reports will use.

```
os:             ubuntu-24.04 | fedora-41 | macos-15 | windows-11 | ...
arch:           amd64 | arm64
environment:    native | wsl2 | vm | ssh-only
package_manager: apt | dnf | brew | conda | none
engine:         docker | podman-3 | podman-4 | none
display:        x11 | wayland | wslg | headless
gpu:            nvidia | amd | intel | none
network:        direct | proxy | restricted
ros_distro:     lyrical
```

## Results

| Machine | Decision points | Date | `make selftest` | Manual steps | Notes |
|---|---|---|---|---|---|
| WSL 2 Ubuntu 22.04 | `windows-11 / amd64 / wsl2 / apt / podman-3 / wslg / — / direct / lyrical` | 2026-09-17 | 20/20 | desktop ☑ turtlesim ☑ arrow keys ☐ | podman-compose 1.6.0; image 3.1 GB |
| macOS | | | | ☐ | |
| Windows 11 (WSL shell) | | | | ☐ | |
| Windows 11 (PowerShell) | | | | ☐ | |
| Pure Linux | | | | ☐ | |

A row counts as complete only when a human has done the browser steps. An
automated `make selftest` pass cannot tell you the desktop rendered or that the
arrow keys worked.

## If something fails

Note which checklist line failed, the decision points above, and the error text.
That is exactly the payload Stage 4 will formalise — capturing it by hand now
tells us whether those nine fields are actually sufficient to explain a failure,
which is worth knowing before any reporting tooling gets built.
