# Changelog

Tutte le modifiche rilevanti a questo progetto saranno documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/1.0.0/)
e questo progetto segue il versionamento semantico.

## [Unreleased]

### Added
### Changed
### Fixed

---

## [v1.4.1] - 07/05/2026 
### Fixed
 - Driver bouncing of leds
 - state machine

## [v1.4.0] - 12/06/2026 
### Added
 - Python script test files for test speed limitation and speed computing
 - Python script test files for path following
 - Python script test files for driver communication
 - Python script test files for pose accuracy
 - Python script test files for applying impedance parameter behaviour 
 - Launch files 
 - Load Cell plugin scaling from ini for each load cell

### Fixed
 - Service file for installation
 - Driver parsing
 - Force calibration plugin saving

---

## [v1.3.0] - 28/05/2026 
### Added
- Python script test files for check impedance control mode 
- Python script test files for check path following mode
- imu_calibration plugin added
- FSM publish a reason in case of uncommon change of modality

### Changed
- ego_state integrates into sensor fusion also absolute pose data when available

### Fixed
- improved the unhook detection 


---

## [v1.2.0] - 07/05/2026 

### Added
- Watchdog plugin added
- A variable is added to CMakeList for configuring fetchContent SHALLOW
- Agents with Cryptography
- Python script files for finding the Inertia and Dumping parameters of the walker 

---

## [v1.1.0] - 15/04/2026

### Added
- Plugin supported: loadcells, driver, portenta, imu, forces_calibration, ego_state, harness_detachment, FSM
- Dependency required on the README
- Service automatically installed

---

## [v1.0.1] - 15/04/2026

### Added
- Plugin supported: loadcells, driver

### Fixed
- Variable of Tag set correctly 

---

## [v1.0.0] - 15/04/2026

### Added
- First stable verion
- Plugin supported: loadcells