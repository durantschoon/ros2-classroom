# Running on Linux, macOS, and Windows

The workstation renders its own desktop inside the container and serves it over
HTTP. There is no XQuartz on macOS, no VcXsrv on Windows, and no X11 or Wayland
socket forwarding on Linux. The same three commands work everywhere:

```sh
docker compose build
docker compose up -d
# open http://localhost:6080/vnc.html?autoconnect=1&resize=remote&reconnect=true
```

`make image`, `make up`, and `make open` are the same commands with less typing.

## Requirements

| Host | Requirement |
|---|---|
| Linux | Docker Engine 24+ with the Compose plugin, or rootless Podman 4.4+ |
| macOS | Docker Desktop 4.30+ (Apple Silicon or Intel), or Podman Desktop |
| Windows | Docker Desktop 4.30+ with the WSL 2 backend, or Podman on WSL 2 |

Give Docker at least 4 GB of RAM and ~15 GB of disk. RViz and `rqt` are the
memory-hungry parts; turtlesim alone is happy with less.

## Docker or Podman

The Make targets and the smoke tests detect the engine at runtime, preferring
Docker when both are installed:

```sh
make engine       # prints what was detected, or why nothing was
make doctor       # full host check with the fix for anything missing
```

Podman older than 4.4 has no built-in `compose`, so it needs `podman-compose`
from [requirements-host.txt](../requirements-host.txt). Full details in
[host-requirements.md](host-requirements.md).

The search order is `docker compose`, `podman compose`, `podman-compose`,
`docker-compose`. Force a specific one when you need to:

```sh
make up COMPOSE='podman-compose'
```

Nothing in the image or `compose.yaml` is Docker-specific: no host networking,
no bind mounts that need SELinux relabelling, and no privileged flags. Under
rootless Podman the desktop service's `user: root` is root *inside* the user
namespace, which is your own unprivileged host user.

Two caveats for the Podman path:

- `podman-compose` flag coverage varies by version. `podman compose` (Podman
  4.4+, which delegates to a real compose implementation) is the smoother
  option when it is available.
- CI validates the Docker path end to end; Podman is tested by hand. If a
  target fails only under Podman, run it with `COMPOSE=...` set explicitly and
  check whether the flag exists in your `podman-compose` version.

If `make` reports no engine, `make engine` explains which of the two it found
and what is missing — the most common case on Windows is Docker Desktop being
installed but WSL integration switched off for the distro you are in.

## Windows notes

Run the commands from PowerShell or from a WSL 2 shell — both work, because
nothing depends on the host filesystem layout. Make is often absent on Windows,
so every target has a plain equivalent:

| Make target | Plain command |
|---|---|
| `make image` | `docker compose build` |
| `make up` | `docker compose up -d` |
| `make shell` | `docker compose run --rm shell` |
| `make turtlesim` | `docker compose exec -d -u ros -e DISPLAY=:1 desktop bash -lc "ros2 run turtlesim turtlesim_node"` |
| `make down` | `docker compose down` |
| `make reset` | `docker compose down --volumes` |

If you clone into a Windows path and run from WSL, keep the repository inside
the WSL filesystem (`~/...`, not `/mnt/c/...`). Build context reads across the
9p mount are slow enough to be noticeable.

**Opening the desktop from WSL.** `make open` detects WSL and hands the URL to
Windows via `wslview`, then `powershell.exe Start-Process`, then
`explorer.exe`. It deliberately does not use `xdg-open` there: WSL distros
usually have a mime database that names a browser which is not installed, and
`xdg-open` then falls through to a *text editor*, so the noVNC page appears as
HTML source instead of a desktop. The URL is always printed first, so you can
paste it into a Windows browser regardless — `localhost:6080` reaches the
container through WSL 2's port forwarding.

## macOS notes

Everything runs in Docker Desktop's Linux VM, so the image must match the VM's
architecture. On Apple Silicon this builds `linux/arm64` natively; ROS publishes
arm64 packages for the supported distributions, so no emulation is involved.
Avoid forcing `--platform linux/amd64`: it works through Rosetta but the
software-rendered desktop becomes noticeably slow.

## Using the desktop

Open `http://localhost:6080/vnc.html?autoconnect=1&resize=remote&reconnect=true`.

- A terminal opens automatically at startup, already sourced for ROS. It is
  *inside* the workstation: use it for `ros2`, `colcon`, and `pkg`. Every
  `make` command belongs in the terminal on your own computer instead. Typing a
  workstation target like `make turtlesim` in here prints where to run it,
  rather than make's confusing "No rule to make target".
- Right-click the desktop background for a menu with turtlesim_node,
  turtle_teleop_key, `rqt`, and RViz.
- For the classic tutorial, run `ros2 run turtlesim turtlesim_node` in one
  terminal, then open a second terminal from the menu and run
  `ros2 run turtlesim turtle_teleop_key`. Keyboard focus must be on the teleop
  window for the arrow keys to move the turtle.

`resize=remote` makes the container's virtual screen follow the browser window.
Set `SCREEN_GEOMETRY` in `.env` to change the startup resolution.

**The page can disconnect, and that is fine.** After laptop sleep, a network
blip, or a closed tab, the page shows "Disconnected". Nothing inside the desktop
stops — turtlesim, your terminals, and running nodes carry on — and
`reconnect=true` in the URL makes it reconnect by itself within a few seconds.
Reloading the page, or running `make open` again, works too.

**The side panel.** A small tab on the left edge of the page opens noVNC's
control panel:

| Button | Use it for |
|---|---|
| Clipboard | Pasting text *into* the desktop. The browser's own paste does not reach it, so this is how a command printed in your host terminal gets into the desktop terminal. Text copied inside the desktop appears here too. |
| Extra keys | Ctrl, Alt, Tab, Esc, and Ctrl+Alt+Del — keys your browser or OS would otherwise intercept. |
| Fullscreen | More room for RViz and rqt. |
| Settings | Scaling and quality, if the desktop looks blurry or cramped. |
| Disconnect | Leaves everything running; reconnect any time. |

## Security model

noVNC is published to `127.0.0.1` only and runs without a password by default,
because on a single-user machine loopback is already the trust boundary. x11vnc
itself listens only on the container's loopback interface, so websockify is the
only route in.

Before changing the port binding to anything reachable from another machine:

1. Set `VNC_PASSWORD` in `.env`, or
2. leave the binding on loopback and reach it through an SSH tunnel:
   `ssh -L 6080:127.0.0.1:6080 user@host`.

The container user has passwordless `sudo`. This is a development environment,
not an isolation boundary — do not treat the container as a sandbox for
untrusted code.

## ROS networking

`ROS_DOMAIN_ID` defaults to 42 so this workstation does not join unrelated ROS
sessions on the same machine or LAN. Change it in `.env` if 42 collides with
something else you run.

Beginner tutorials run both nodes inside the one desktop container, which avoids
cross-container discovery entirely. For tutorials that specifically teach
distributed nodes, use separate compose services on the shared `ros` network:

```sh
docker compose --profile demo up talker listener
```

`ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET` lets nodes discover each other across
services on that network. (It replaces the deprecated `ROS_LOCALHOST_ONLY`.)
If your host or VPN blocks multicast and discovery fails, configure a unicast
discovery server instead:

```sh
docker compose exec -d desktop fastdds discovery --server-id 0
# then in each service: export ROS_DISCOVERY_SERVER=desktop:11811
```

`network_mode: host` is deliberately not used: it behaves differently on native
Linux and inside Docker Desktop's VM, which is exactly the portability problem
this branch exists to remove.

## Troubleshooting

**`make open` opened an editor, or nothing.** That was a bug in WSL handling,
fixed by `scripts/open-url`. The URL is printed on the first line of the
output; paste it into a Windows browser if the automatic route fails.

**A `WARN ... Error validating CNI config file ... plugin firewall does not
support config version` line appears.** The Make targets filter this now. If
you see it from a raw `podman-compose` command, it is a Podman 3.x false alarm:
one optional plugin is skipped while the plugins that carry traffic load
normally. [host-requirements.md](host-requirements.md) explains it, and
`VERBOSE=1 make up` shows the unfiltered output.

**The page says "Disconnected".** Expected after sleep or a network blip; it
reconnects on its own, and nothing in the desktop was lost. If it does not come
back within half a minute, check the desktop is still up with `make ps`.

**Pasting into the desktop does nothing.** Use the Clipboard button in the
side panel (the tab on the page's left edge): paste your text there, then paste
inside the desktop as usual.

**The browser shows "failed to connect".** The desktop takes a few seconds to
start. Check `docker compose ps` for the health status and `make logs` for
supervisor output.

**The turtle does not move.** Keyboard focus follows the mouse into the teleop
xterm; click that window inside the noVNC view first.

**`make turtlesim` says the container is not running.** Run `make up` first;
`make turtlesim` and `make turtlesim-teleop` attach to a running desktop.

**Rebuilding is slow.** The apt layer is a single large layer by design. Only a
change to the package list or the base digest invalidates it.

**Everything is gone after `make reset`.** That is what `reset` does: it deletes
the named volumes. Use `make down` to stop containers and keep the workspace.
