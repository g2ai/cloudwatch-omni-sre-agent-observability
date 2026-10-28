<# Build the sre-agent Lambda package: Linux wheels, no OpenTelemetry (the ADOT layer provides it). #>
$ErrorActionPreference = "Stop"
$root  = Split-Path -Parent $PSScriptRoot
$build = Join-Path $root "deploy\terraform\build\sre_agent"
$req   = Join-Path $root "src\sre_agent\requirements.txt"

if (Test-Path $build) { Remove-Item $build -Recurse -Force }
New-Item -ItemType Directory -Path $build | Out-Null

uv pip install --target $build --python-platform x86_64-manylinux2014 --python-version 3.13 --only-binary :all: --no-installer-metadata --no-compile-bytecode -r $req
if ($LASTEXITCODE -ne 0) { throw "uv pip install failed" }

# ADOT layer :29 ships OpenTelemetry 1.44.0 / 0.65b0. Keep one copy only: the layer's.
# ADOT layer :29 ships OpenTelemetry 1.44.0 / 0.65b0 and its own wrapt. Keep one copy only: the layer's.
Get-ChildItem $build -Directory | Where-Object { $_.Name -like "opentelemetry*" -or $_.Name -like "wrapt*" } | Remove-Item -Recurse -Force

Copy-Item (Join-Path $root "src\sre_agent\*.py") $build

$size = (Get-ChildItem $build -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
"Package: {0:N1} MB in {1}" -f $size, $build