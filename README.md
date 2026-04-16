# Walker

This project builds the Walker software stack with CMake and `FetchContent`, pulling the required repositories at configure time and building them as a single workspace.

The build includes a set of Walker plugins plus the **FSM** core component, which is **not a plugin** but a monolithic module used by the system.

## Components

### Plugins
- `load_cells_plugin`
- `driver_plugin`
- `portenta_plugin`
- `imu_plugin` (fetched from `sense-hat_plugin`)
- `forces_calibration_plugin`
- `ego_state_plugin`
- `harness_detachment_plugin`

### Core component
- `FSM` — monolithic core module, not a plugin

### Declared but not currently built
- `mqtt_plugin`
- `forces_autocalibration_plugin`
- `common_walker`

## Requirements

Recommended platform:
- **Ubuntu 24.04**

Build dependencies:
- `build-essential`
- `cmake`
- `git`
- `clang`
- `libeigen3-dev`

Install them with:

```bash
sudo apt update
sudo apt install build-essential cmake git clang libeigen3-dev
```

Eigen3 is required at configure time. If it is missing, CMake stops with an explicit error and suggests installing `libeigen3-dev`.

## External runtime dependency: MADS

Walker depends on **MADS**. This README targets **MADS v2.0.4**, which is published as the latest release on the referenced GitHub release page.

Download and install the latest MADS release from:

- `pbosetti/MADS` release `v2.0.4`

After installing MADS, make sure the `mads` executable is available in your `PATH` before installing Walker with service support.

## Additional hardware/software dependencies

### Sense HAT

The `imu_plugin` is fetched from the `sense-hat_plugin` repository. For the required Sense HAT installation and setup steps, follow the README of:

- `mmt-unitn/sense-hat_plugin`

This project README does not duplicate those instructions to avoid drifting from the plugin-specific documentation.

### Phidget22

If your setup requires Phidget22, follow the installation procedure documented in the referenced Phidget22 repository. The README at the pinned revision describes a local install flow based on `configure` and `make install`:

```bash
cd build/install
../../configure --prefix=$(pwd)/..
make install -j$(nproc)
```

This installs the library and headers inside the local `build/install` tree.

## Build and install

### Configure

Use:

```bash
cmake -Bbuild -DCMAKE_INSTALL_PREFIX=./usr/local
```

To disable systemd service installation, explicitly set:

```bash
cmake -Bbuild -DCMAKE_INSTALL_PREFIX=./usr/local -DINSTALL_MADS_SERVICE=OFF
```

### Build

```bash
cmake --build build -j
```

### Install

```bash
sudo cmake --install build
```

By default, the project installs under:

```text
./usr/local
```

## Systemd service

The project can also install and enable:

```text
mads-Novawalk.service
```

Current default behavior in `CMakeLists.txt`:
- `INSTALL_MADS_SERVICE` is set to **ON**
- the service file is copied to `/etc/systemd/system`
- `systemctl daemon-reload` is executed
- `systemctl enable mads-Novawalk.service` is executed

If you do **not** want service installation, configure with:

```bash
cmake -Bbuild -DCMAKE_INSTALL_PREFIX=./usr/local -DINSTALL_MADS_SERVICE=OFF
```

Because the service is installed into the systemd system directory, the install step must be run with `sudo`.

## Versioning

The Walker version is derived from Git tags in the format:

```text
vMAJOR.MINOR.PATCH
```

If no matching tag is found, a fallback version is used.

## Packaging

The project includes `CPack` configuration for Debian package generation on Unix systems. Package output location depends on the configured CPack settings in the source tree and build environment.

## Troubleshooting

### Eigen3 not found

Install Eigen3:

```bash
sudo apt install libeigen3-dev
```

### `mads` command not found

Make sure MADS is installed and that the `mads` executable is available in your shell `PATH`.

### systemd service issues

Check the service status:

```bash
systemctl status mads-Novawalk.service
```

Check logs:

```bash
journalctl -u mads-Novawalk.service
```

## Contact

MADS Consortium  
paolo.bosetti@unitn.it
