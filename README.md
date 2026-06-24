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
- `watchdog_plugin`
- `imu_calibration_plugin`

### Core component
- `FSM` — monolithic core module, not a plugin

### Declared but not currently built
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

## Configure USB Power Delivery via Software
Enable the maximum USB power output by editing:

```bash
/boot/firmware/config.txt
```

and adding:

```bash
usb_max_current_enable=1
```

## External runtime dependency: MADS

Walker depends on **MADS**. This README targets **MADS v2.0.4**, which is published as the latest release on the referenced GitHub release page.

Download and install the latest MADS release from:

- `pbosetti/MADS` release `v2.0.4`

After installing MADS, make sure the `mads` executable is available in your `PATH` before installing Walker with service support.

## Additional hardware/software dependencies

### Sense HAT

The `imu_plugin` is fetched from the `sense-hat_plugin` repository. For the required Sense HAT installation and setup steps, follow the README of the [sense-hat repository](https://github.com/mmt-unitn/sense-hat_plugin).

### Phidget22

If your setup requires Phidget22, paste the following commands
```bash
curl -fsSL https://www.phidgets.com/downloads/setup_linux | sudo -E bash -
sudo apt install -y libphidget22
```
or follow the installation procedure documented in the referenced [Phidget22 repository](https://github.com/MatteoBonetto/Phidget22/tree/897d367527e2bce3e7ca2bc8521db213b275d294).

### **Remove root permission to files for serial communication**
  1. Accessing `ttyACM*` Without `Root`
      - By default, `ttyACM*` is owned by root and belongs to the dialout group. Add Your User to the dialout Group:
         ```bash
         sudo usermod -aG dialout $USER
         ```
      - To check what is your connection type:
        ```bash
        ls -l /dev/serial/by-id/
        ```
  
  3. Persistent Permission Changes: Use udev rules to ensure the device always has desired permissions:
      - Create a new udev rules file for Phidget communication:
         ```bash
        sudo nano /etc/udev/rules.d/99-libphidget22.rules
         ```

      - Add the following rule:
        ```bash
        All current and future Phidgets - Vendor = 0x06c2, Product = 0x0030 - 0x00af
        SUBSYSTEMS=="usb", ACTION=="add", ATTRS{idVendor}=="06c2", ATTRS{idProduct}=="00[3-a][0-f]", MODE="666" 
         ```
      - Create a new udev rules file for serial communication:
         ```bash
        sudo nano /etc/udev/rules.d/99-usb-serial.rules
         ```

      - Add the following rule for Drivers and Portenta:
        ```bash
        SUBSYSTEM=="tty", ATTRS{idVendor}=="20d2", ATTRS{idProduct}=="5740", SYMLINK+="drivers", MODE="0666"
        SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="025b", ATTRS{serial}=="004200473033510A34323437", SYMLINK+="portenta", MODE="0666"
         ```
      - Reboot to apply the rule 

## Build and install

### Configure

Use:

```bash
cmake -Bbuild -DCMAKE_INSTALL_PREFIX=/usr/local -DFETCHCONTENT_SHALLOW_CLONE=ON -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
```

A CMake cache variable is available to control whether `FetchContent` uses shallow or full Git clones for dependencies:

- `FETCHCONTENT_SHALLOW_CLONE=ON` → shallow clone
- `FETCHCONTENT_SHALLOW_CLONE=OFF` → full clone

The default is `ON`.

Example with full clones:

```bash
cmake -Bbuild -DCMAKE_INSTALL_PREFIX=/usr/local -DFETCHCONTENT_SHALLOW_CLONE=OFF -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
```

To disable systemd service installation, explicitly set:

```bash
cmake -Bbuild -DCMAKE_INSTALL_PREFIX=/usr/local -DFETCHCONTENT_SHALLOW_CLONE=ON -DINSTALL_MADS_SERVICE=OFF -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++
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
cmake -Bbuild -DCMAKE_INSTALL_PREFIX=/usr/local -DFETCHCONTENT_SHALLOW_CLONE=ON -DINSTALL_MADS_SERVICE=OFF
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

## Python Scripts

### `compute_walker_inertia.py`

A utility script for identifying Walker's rotational inertia and viscous damping parameters through experimental estimation.

**Purpose:**
- Temporarily stops the FSM service
- Applies a series of variable torques to the wheels while measuring angular velocity from the IMU
- Uses LMS (Least Mean Squares) regression to estimate the rotational inertia (`I`) and viscous damping coefficient (`C`)
- Optionally allows fixing the damping coefficient to a known value and recalculating inertia

**Output:**
Prints estimated parameters according to the model: `torque = I * alpha + C * omega`

**Requirements:**
- MADS agent running with broker access
- Proper security configuration (`/home/miro/security` directory expected)
- Access to IMU data via the FSM
- `sudo` privileges to control systemd services

### `compute_walker_dumping.py`

(Similar utility for computing Walker's damping characteristics)

# Test Scripts

## Common requirements for all tests

All Python test scripts must be executed inside a dedicated Python virtual environment.

Create and activate a virtual environment:

```bash
cd Python
python3 -m venv .venv
source .venv/bin/activate
```

Install the required Python dependencies:

```bash
pip install pyserial
```

Additional dependencies may be required depending on the specific test being executed.

The virtual environment should be activated before running any of the test scripts.

---

## `test_driver_communication.py`

This test verifies the system's ability to detect and properly handle a loss of communication with the motor driver.

### Purpose

- Starts the Walker software stack using the test-specific configuration.
- Monitors communication between the Driver, FSM, and Portenta components through MADS.
- Waits until normal driver communication is established.
- Simulates a driver communication failure by closing the serial connection to the driver board.
- Measures the time required for the FSM to detect the failure and trigger the corresponding emergency command.
- Evaluates whether the failure handling latency remains below the configured threshold.

### Measured parameter

- Time elapsed between failure detection by the FSM and the generation of the emergency command.

### Pass criterion

- The emergency response must be generated within the configured maximum allowed time (`max_elapsed_time_ms`).

### Requirements

- MADS broker running and reachable.
- Walker software stack available.
- Access to the driver serial interface (`/dev/drivers`).
- Python virtual environment with `pyserial` installed.
- Appropriate permissions to access serial devices.

## `test_pose_check.py`

This test verifies the repeatability and drift of the Walker ego-state pose estimation.

### Purpose

- Starts the Walker software stack using the test-specific configuration.
- Runs the stack without the FSM, using `process-compose-without-fsm.yml`.
- Waits for manual user confirmation before each pose evaluation.
- Reads pose messages from the `ego_state` topic.
- Records the estimated planar position and orientation over multiple evaluations.
- Checks whether the measured pose uncertainty remains within the configured limits.
- After a fixed waiting time, evaluates pose drift.

### Measured parameters

- Position magnitude:

```text
sqrt(x^2 + y^2)
```

- Orientation angle:

```text
theta
```

- Position uncertainty, computed as two standard deviations over repeated measurements.
- Orientation uncertainty, computed as two standard deviations over repeated measurements.
- Position drift after the configured waiting time.
- Orientation drift after the configured waiting time.

### Pass criteria

For **Test 1.1**:

- The position uncertainty must be below `max_2std_position`.
- The position drift must remain below `max_dist_drift`.

For **Test 1.2**:

- The orientation uncertainty must be below `max_2std_theta`.
- The orientation drift must remain below `max_theta_drift`.

### Configuration

The main thresholds are defined in `TEST_CONFIG`:

```text
n_evaluations = 3
max_2std_position = 0.05 m
max_2std_theta = 5 deg
max_dist_drift = 0.5 m
max_theta_drift = 15 deg
delay_drift_s = 30 s
```

### Requirements

- MADS broker running and reachable.
- Walker software stack available.
- `ego_state` component publishing pose estimates.
- Test-specific `.ini` configuration file available in `config_files`.
- Python virtual environment with the required dependencies installed.
- `numpy` installed in the virtual environment.
- `tmux` and `process-compose` session utilities available.

## `test_speed_check.py`

This test verifies the speed estimation repeatability and the enforcement of the Walker speed limit.

### Purpose

- Starts the Walker software stack using the test-specific configuration.
- Runs the stack without the FSM, using `process-compose-without-fsm.yml`.
- Commands wheel speeds higher than the configured speed limit.
- Alternates the commanded direction at each evaluation.
- Reads the measured speed from the `ego_state` topic.
- Verifies that the speed limiter prevents the Walker from exceeding the configured maximum speed.
- Evaluates the repeatability of the measured speed by computing its uncertainty over repeated samples.

### Measured parameters

- Linear speed:

```text
ego_state.speed
```

- Mean measured speed during each evaluation interval.
- Speed uncertainty, computed as two standard deviations of the recorded speed samples.

### Pass criteria

For **Test 3**:

- The speed measurement uncertainty must remain below `max_2std`.

For **Test 8.3**:

- The absolute measured speed must remain below `speed_limit`, even when a higher speed is commanded.

### Test procedure

For each evaluation:

1. A speed command greater than the configured speed limit is sent.
2. The Walker is allowed to move for the evaluation period.
3. Speed measurements are collected from the `ego_state` topic.
4. The average speed and uncertainty are computed.
5. The speed limit and uncertainty requirements are verified.
6. The Walker is stopped before the next evaluation.

The procedure is repeated for the configured number of evaluations while alternating the direction of motion.

### Configuration

The main thresholds are defined in `TEST_CONFIG`:

```text
n_evaluations = 10
speed_set = 1.0 m/s
speed_limit = 0.25 m/s
max_2std = 1.0 m/s
time_evaluation = 1.0 s
time_between_evaluations = 3.0 s
wheel_radius = 0.084 m
```

### Requirements

- MADS broker running and reachable.
- Walker software stack available.
- `ego_state` component publishing speed estimates.
- Driver and motion-control components operational.
- Test-specific `.ini` configuration file available in `config_files`.
- Python virtual environment with the required dependencies installed.
- `numpy` installed in the virtual environment.
- `tmux` and `process-compose` session utilities available.
- Sufficient free space for safe Walker motion during the test.

## `test_path_following_clothoid.py`

This test verifies the Walker path-following performance on a clothoid trajectory and evaluates the effect of torsional stiffness on path-tracking accuracy.

### Purpose

- Starts the Walker software stack using the test-specific configuration.
- Generates a clothoid (Euler spiral) path from `(0,0)` to `(4,1)` with zero heading at both ends.
- Commands the FSM to enter `path_following_mode` through the `GUI` topic.
- Executes two path-following runs:
  - Baseline torsional stiffness (`K_w = 10 Nm/rad`)
  - High torsional stiffness (`K_w = 100 Nm/rad`)
- Records walker pose feedback from the `FSM/path_planning` topic.
- Computes the minimum-distance offset between the measured trajectory and the commanded clothoid path.
- Verifies that the walker actually traverses the path and reaches the target region.
- Compares tracking performance between the two stiffness configurations.

### Measured parameters

- Walker position:

```text
walker_pose = [x, y, theta]
```

- Lateral offset from the commanded clothoid path.
- Maximum path-tracking error.
- Mean path-tracking error.
- Final distance to the goal position.
- Progress ratio along the path arc length.
- Completion status of the path-following task.

### Acceptance criteria

The test passes only if all of the following conditions are satisfied:

1. The maximum offset from the commanded path remains below:

```text
MAX_ALLOWED_OFFSET_M = 1.0 m
```

2. The walker successfully follows the path:

   - Final distance to goal ≤ 0.5 m
   - Progress ratio ≥ 0.8

3. The path-following task completes normally:

   - FSM mode transition detected, or
   - Path-following activity becomes inactive after successful execution.

4. Increasing torsional stiffness improves tracking performance by at least:

```text
HIGH_STIFFNESS_MARGIN_M = 0.05 m
```

where:

```text
improvement = max_offset_baseline - max_offset_high_stiffness
```

### Test procedure

#### Baseline run

- Set FSM to idle.
- Send a clothoid path-following command.
- Apply impedance-control parameters with:

```text
K_w = 10 Nm/rad
```

- Record the resulting trajectory.

#### High-stiffness run

- Repeat the same procedure with:

```text
K_w = 100 Nm/rad
```

- Record the resulting trajectory.

#### Comparison

- Compute trajectory offsets for both runs.
- Compare maximum path-tracking errors.
- Verify that the higher stiffness configuration improves tracking accuracy.

### Impedance parameters

The following impedance parameters are used:

```text
M_v = 5.0
M_w = 2.0
K_v = 0.0
C_v = 40.0
C_w = 35.0
```

The torsional stiffness parameter `K_w` is varied between the two runs.

### Virtual command

The test applies a constant virtual force:

```text
virtual_force = 10 N
virtual_torque = 0 Nm
```

### Configuration

Important test parameters:

```text
samples = 300
timeout = 60 s

baseline K_w = 10 Nm/rad
high stiffness K_w = 100 Nm/rad

max allowed offset = 1.0 m
minimum final distance = 0.5 m
minimum progress ratio = 0.8

required improvement = 0.05 m
```

### Generated outputs

The script reports:

- Maximum trajectory offset.
- Mean trajectory offset.
- Final distance from the goal.
- Final heading.
- Path coverage ratio.
- Completion status.
- Tracking improvement obtained with increased torsional stiffness.

If the optional `plotext` package is installed, the script also displays:

- Commanded clothoid path and measured trajectories.
- Offset-versus-sample plots for both stiffness configurations.

### Requirements

- MADS broker running and reachable.
- Walker software stack available.
- FSM capable of entering `path_following_mode`.
- `FSM/path_planning` feedback topic available.
- `FSM/mode` feedback topic available.
- `ego_state` feedback available.
- Driver communication operational.
- Test-specific `.ini` configuration file available in `config_files`.
- Python virtual environment with the required dependencies installed.
- Optional: `plotext` for terminal plots.
- Sufficient free space for safe path-following execution.


## `test_impedance_validation.py`

This test verifies that the Walker behaves as a configured mass-spring-damper system when operating in impedance-control mode.

### Purpose

- Starts the Walker software stack using the test-specific configuration.
- Switches the FSM to `impedance_control_mode`.
- Configures a target impedance model defined by mass (`M`), damping (`C`), and stiffness (`K`).
- Applies a constant virtual force to excite the system.
- Records position, velocity, and acceleration measurements from the `ego_state` topic.
- Estimates the effective dynamic parameters of the Walker through regression and model fitting.
- Verifies that the measured behavior matches the configured impedance model within the specified tolerance.

### Supported profiles

#### Legacy profile

- M = 50 kg
- C = 65 Ns/m
- K = 85 N/m

#### Requirement 12.1 profile

- M = 20 kg
- C = 10 Ns/m
- K = 10 N/m

### Test procedure

1. Configure the Walker impedance parameters.
2. Switch the FSM to `impedance_control_mode`.
3. Allow the system to settle.
4. Apply a virtual force of 120 N.
5. Record position, velocity, and acceleration.
6. Build the dynamic model:

   F = M·a + C·v + K·x

7. Estimate the parameters using:
   - Ordinary Least Squares regression
   - Transient-response analysis
   - Output-error trajectory fitting

8. Compare the estimated parameters with the configured values.

### Measured parameters

From `ego_state`:

- acceleration
- speed
- space_linear

Estimated:

- Mass (M)
- Damping (C)
- Stiffness (K)

### Acceptance criteria

Each estimated parameter must remain within ±45% of the configured target value.

The test passes only if:

- Mass estimate passes.
- Damping estimate passes.
- Stiffness estimate passes.

### Configuration

Important settings:

- period = 0.05 s (20 Hz)
- excitation force = 120 N
- excitation duration = 3.5 s
- startup delay = 3 s
- settle delay = 3 s
- minimum regression samples = 30
- tolerance = ±45%

### Generated outputs

The script reports:

- Estimated Mass
- Estimated Damping
- Estimated Stiffness
- Position RMSE
- Velocity RMSE
- Regression diagnostics
- Residual statistics
- Expected versus measured acceleration

### Terminal plots

If `plotext` is installed, the script displays:

- Force residual histograms
- Position residual histograms
- Velocity residual histograms
- Mass candidate distributions
- Damping candidate distributions
- Stiffness candidate distributions

### Requirements

- MADS broker running and reachable.
- Walker software stack available.
- FSM capable of entering `impedance_control_mode`.
- `ego_state` topic available.
- Test-specific `.ini` configuration file available.
- Python virtual environment with required dependencies installed.
- `numpy` installed.
- Optional: `plotext` for terminal visualization.

## Contact

MADS Consortium  
paolo.bosetti@unitn.it
