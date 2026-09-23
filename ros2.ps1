param(
    [string]$Command = "desktop",
    [string]$Pkg = "",
    [string]$Node = "",
    [string]$Template = ""
)

$ErrorActionPreference = "Stop"
$NovncPort = 6080
$Url = "http://localhost:$NovncPort"
$DesktopUrl = "$Url/vnc.html?autoconnect=1&resize=remote&reconnect=true"
$Service = "desktop"

function Check-Docker {
    try {
        $dockerVersion = docker --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Docker is not installed or not in PATH." -ForegroundColor Red
            Write-Host "Please install Docker Desktop from https://docs.docker.com/desktop/install/windows-install/"
            exit 1
        }
        
        docker info > $null 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Docker Desktop is installed but the Docker engine is not running." -ForegroundColor Red
            Write-Host "Please start Docker Desktop from your Start Menu and try again."
            exit 1
        }
    } catch {
        Write-Host "Docker is not installed or not in PATH." -ForegroundColor Red
        Write-Host "Please install Docker Desktop from https://docs.docker.com/desktop/install/windows-install/"
        exit 1
    }
}

function Wait-For-Desktop {
    Write-Host "Waiting for the desktop to start..."
    $maxAttempts = 30
    $attempt = 0
    while ($attempt -lt $maxAttempts) {
        try {
            $response = Invoke-WebRequest -Uri "$Url/vnc.html" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "`nDesktop is ready!"
                return
            }
        } catch {
            Write-Host -NoNewline "."
            Start-Sleep -Seconds 2
        }
        $attempt++
    }
    Write-Host "`nThe desktop did not answer after 60s. Is it running? Details: docker compose logs" -ForegroundColor Red
    exit 1
}

function Run-Up {
    Check-Docker
    Write-Host "Starting the ROS 2 workstation..."
    docker compose up -d
}

function Run-Open {
    Wait-For-Desktop
    Write-Host "Opening the browser to $DesktopUrl"
    Start-Process $DesktopUrl
    Write-Host ""
    Write-Host "Two terminals, two jobs:" -ForegroundColor Cyan
    Write-Host "  - THIS terminal, on your computer: every script command."
    Write-Host "      .\ros2.bat turtlesim   then   .\ros2.bat turtlesim-teleop"
    Write-Host "  - The terminal INSIDE the browser desktop: ROS commands"
    Write-Host "    (ros2, colcon, pkg). .\ros2.bat does not work in there."
}

function Run-Shell {
    Check-Docker
    Write-Host "Entering a ROS shell. Type exit to come back."
    docker compose run --rm shell
}

function Run-Turtlesim {
    Check-Docker
    docker compose exec -d -u ros -e DISPLAY=:1 $Service bash -lc 'nohup ros2 run turtlesim turtlesim_node >/tmp/turtlesim.log 2>&1 &'
    Write-Host "turtlesim started on the browser desktop ($Url)."
    Write-Host "Next, to drive the turtle:  .\ros2.bat turtlesim-teleop"
}

function Run-TurtlesimTeleop {
    Check-Docker
    docker compose exec -d -u ros -e DISPLAY=:1 $Service bash -lc "nohup xterm -title 'turtlesim teleop (arrow keys)' -bg white -fg black -u8 -fa 'DejaVu Sans Mono' -fs 11 -e bash -lc turtlesim-teleop >/tmp/teleop.log 2>&1 &"
    Write-Host "turtlesim teleop opened on the browser desktop."
    Write-Host "Click inside the WHITE window titled 'turtlesim teleop' to use arrow keys."
}

function Run-Package {
    if (-not $Pkg) {
        Write-Host "usage: .\ros2.bat package -Pkg name [-Template pubsub]" -ForegroundColor Red
        exit 1
    }
    $templateArg = if ($Template) { "--template $Template" } else { "" }
    docker compose exec -u ros -e DISPLAY=:1 -e PKG_VIA_MAKE=1 $Service bash -lc "pkg new $Pkg $templateArg"
}

function Run-Build {
    $pkgArg = if ($Pkg) { $Pkg } else { "" }
    docker compose exec -u ros -e DISPLAY=:1 -e PKG_VIA_MAKE=1 $Service bash -lc "pkg build $pkgArg"
}

function Run-Test {
    $pkgArg = if ($Pkg) { $Pkg } else { "" }
    docker compose exec -u ros -e DISPLAY=:1 -e PKG_VIA_MAKE=1 $Service bash -lc "pkg test $pkgArg"
}

function Run-RunNode {
    if (-not $Pkg -or -not $Node) {
        Write-Host "usage: .\ros2.bat run -Pkg name -Node executable" -ForegroundColor Red
        exit 1
    }
    docker compose exec -u ros -e DISPLAY=:1 -e PKG_VIA_MAKE=1 $Service bash -lc "pkg run $Pkg $Node"
}

function Run-Down {
    Check-Docker
    docker compose down
}

switch ($Command) {
    "desktop" { Run-Up; Run-Open }
    "up" { Run-Up }
    "open" { Run-Open }
    "shell" { Run-Shell }
    "turtlesim" { Run-Turtlesim }
    "turtlesim-teleop" { Run-TurtlesimTeleop }
    "package" { Run-Package }
    "build" { Run-Build }
    "test" { Run-Test }
    "run" { Run-RunNode }
    "down" { Run-Down }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host "Valid commands: desktop, up, open, shell, turtlesim, turtlesim-teleop, package, build, run, test, down"
    }
}
