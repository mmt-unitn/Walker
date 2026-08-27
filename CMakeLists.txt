cmake_minimum_required(VERSION 3.20)

project(
  walker
  VERSION 1.4.0
  LANGUAGES CXX
)

# ------------------------------------------------------------------------------
# Build configuration
# ------------------------------------------------------------------------------

if(CMAKE_BUILD_TYPE STREQUAL "")
  set(
    CMAKE_BUILD_TYPE
    "Release"
    CACHE STRING "Choose the type of build."
    FORCE
  )
endif()

if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
  set(
    CMAKE_INSTALL_PREFIX
    "${CMAKE_CURRENT_LIST_DIR}/usr/local"
    CACHE PATH "Install path prefix, prepended onto install directories."
    FORCE
  )
endif()

option(
  MADS_UP
  "Use mads_up-Novawalk.service instead of mads-Novawalk.service"
  ON
)

option(
  INSTALL_MADS_SERVICE
  "Install and enable the selected MADS systemd service"
  ON
)

option(
  FETCHCONTENT_SHALLOW_CLONE
  "Use shallow clones for FetchContent dependencies"
  ON
)

message(STATUS "CMAKE_BUILD_TYPE: ${CMAKE_BUILD_TYPE}")
message(STATUS "CMAKE_INSTALL_PREFIX: ${CMAKE_INSTALL_PREFIX}")
message(STATUS "FETCHCONTENT_SHALLOW_CLONE: ${FETCHCONTENT_SHALLOW_CLONE}")
message(STATUS "INSTALL_MADS_SERVICE: ${INSTALL_MADS_SERVICE}")
message(STATUS "MADS_UP: ${MADS_UP}")

# ------------------------------------------------------------------------------
# Version from Git tag
# ------------------------------------------------------------------------------

execute_process(
  COMMAND git rev-parse --is-inside-work-tree
  WORKING_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}"
  OUTPUT_VARIABLE IS_GIT_REPO
  OUTPUT_STRIP_TRAILING_WHITESPACE
  ERROR_QUIET
)

if(IS_GIT_REPO STREQUAL "true")
  execute_process(
    COMMAND git describe --tags --dirty
    WORKING_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}"
    OUTPUT_VARIABLE GIT_TAG
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
  )

  if(GIT_TAG MATCHES "^v([0-9]+)\\.([0-9]+)\\.([0-9]+)(.*)?$")
    string(
      REGEX REPLACE
      "^v([0-9]+)\\.([0-9]+)\\.([0-9]+)(.*)?$"
      "\\1"
      CPACK_PACKAGE_VERSION_MAJOR
      "${GIT_TAG}"
    )

    string(
      REGEX REPLACE
      "^v([0-9]+)\\.([0-9]+)\\.([0-9]+)(.*)?$"
      "\\2"
      CPACK_PACKAGE_VERSION_MINOR
      "${GIT_TAG}"
    )

    string(
      REGEX REPLACE
      "^v([0-9]+)\\.([0-9]+)\\.([0-9]+)(.*)?$"
      "\\3"
      CPACK_PACKAGE_VERSION_PATCH
      "${GIT_TAG}"
    )

    message(
      STATUS
      "Project root is a Git repository. "
      "Using version from latest tag: "
      "${CPACK_PACKAGE_VERSION_MAJOR}."
      "${CPACK_PACKAGE_VERSION_MINOR}."
      "${CPACK_PACKAGE_VERSION_PATCH}"
    )
  else()
    message(
      WARNING
      "Latest Git tag does not match vMAJOR.MINOR.PATCH format. "
      "Using default version 0.0.1."
    )

    set(CPACK_PACKAGE_VERSION_MAJOR 0)
    set(CPACK_PACKAGE_VERSION_MINOR 0)
    set(CPACK_PACKAGE_VERSION_PATCH 1)
  endif()
else()
  message(
    WARNING
    "Project root is not a Git repository. Using default version 0.0.1."
  )

  set(CPACK_PACKAGE_VERSION_MAJOR 0)
  set(CPACK_PACKAGE_VERSION_MINOR 0)
  set(CPACK_PACKAGE_VERSION_PATCH 1)
  set(GIT_TAG "vUNKNOWN_GIT_VERSION")
endif()

set(
  NOVAWALK_VERSION
  "${CPACK_PACKAGE_VERSION_MAJOR}.${CPACK_PACKAGE_VERSION_MINOR}.${CPACK_PACKAGE_VERSION_PATCH}"
)

message(STATUS "NOVAWALK_VERSION: ${NOVAWALK_VERSION}")
message(STATUS "GIT_TAG: ${GIT_TAG}")

# ------------------------------------------------------------------------------
# Dependencies
# ------------------------------------------------------------------------------

find_package(Eigen3 QUIET NO_MODULE)

if(NOT Eigen3_FOUND)
  message(
    FATAL_ERROR
    "
Eigen3 not found!

Install it with:

  sudo apt install libeigen3-dev
"
  )
endif()

include(FetchContent)

FetchContent_Declare(
  load_cells_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/load_cells_plugin.git
  GIT_TAG 5b97f40
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  driver_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/driver_plugin.git
  GIT_TAG 0e85e3b
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  portenta_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/portenta_plugin.git
  GIT_TAG 9296810
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  imu_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/sense-hat_plugin.git
  GIT_TAG 1737080
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  forces_calibration_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/forces_calibration_plugin.git
  GIT_TAG c4e7450
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  ego_state_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/ego_state_plugin.git
  GIT_TAG 55ddd33
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  FSM
  GIT_REPOSITORY https://github.com/mmt-unitn/FSM.git
  GIT_TAG 2aacb45
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  unhook_detector_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/UnhookDetector.git
  GIT_TAG e22013d
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  watchdog_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/watchdog_plugin.git
  GIT_TAG b731a55
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  forces_autocalibration_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/forces_autocalibration_plugin.git
  GIT_TAG HEAD
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  common_walker
  GIT_REPOSITORY https://github.com/mmt-unitn/common_walker.git
  GIT_TAG bf6a546
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  imu_calibration_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/imu_calibration_plugin.git
  GIT_TAG 5b9ae3d
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  plugin_tester
  GIT_REPOSITORY https://github.com/mmt-unitn/plugin_tester.git
  GIT_TAG main
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  overload_detector_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/overload_detector_plugin.git
  GIT_TAG 8377e10
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_MakeAvailable(
  load_cells_plugin
  driver_plugin
  portenta_plugin
  imu_plugin
  imu_calibration_plugin
  forces_calibration_plugin
  ego_state_plugin
  unhook_detector_plugin
  FSM
  watchdog_plugin
  plugin_tester
  overload_detector_plugin
)

# ------------------------------------------------------------------------------
# MADS systemd service
# ------------------------------------------------------------------------------

if(INSTALL_MADS_SERVICE)
  set(HOME_DIR "$ENV{HOME}")
  set(MADS_KEYS_DIR "${HOME_DIR}/security")
  set(CURRENT_CMAKE_DIR "${CMAKE_CURRENT_LIST_DIR}")

  if(MADS_UP)
    set(MADS_SERVICE_NAME "mads_up-Novawalk.service")
  else()
    set(MADS_SERVICE_NAME "mads-Novawalk.service")
  endif()

  set(
    MADS_SERVICE_TEMPLATE
    "${CMAKE_CURRENT_LIST_DIR}/services/${MADS_SERVICE_NAME}.in"
  )

  set(
    MADS_SERVICE_OUTPUT
    "${CMAKE_CURRENT_BINARY_DIR}/services/${MADS_SERVICE_NAME}"
  )

  if(NOT EXISTS "${MADS_SERVICE_TEMPLATE}")
    message(
      FATAL_ERROR
      "Service template not found: ${MADS_SERVICE_TEMPLATE}"
    )
  endif()

  file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/services")

  configure_file(
    "${MADS_SERVICE_TEMPLATE}"
    "${MADS_SERVICE_OUTPUT}"
    @ONLY
  )

  message(STATUS "Selected systemd service: ${MADS_SERVICE_NAME}")
  message(STATUS "Service template: ${MADS_SERVICE_TEMPLATE}")
  message(STATUS "Generated service: ${MADS_SERVICE_OUTPUT}")
  message(STATUS "Current CMake directory: ${CURRENT_CMAKE_DIR}")
  message(STATUS "MADS keys directory: ${MADS_KEYS_DIR}")

  install(
    FILES "${MADS_SERVICE_OUTPUT}"
    DESTINATION "/etc/systemd/system"
  )

  install(CODE "
    message(STATUS \"Reloading systemd configuration...\")

    execute_process(
      COMMAND systemctl daemon-reload
      RESULT_VARIABLE SYSTEMD_RELOAD_RESULT
    )

    if(NOT SYSTEMD_RELOAD_RESULT EQUAL 0)
      message(
        FATAL_ERROR
        \"systemctl daemon-reload failed with code: \${SYSTEMD_RELOAD_RESULT}\"
      )
    endif()

    message(STATUS \"Enabling ${MADS_SERVICE_NAME}...\")

    execute_process(
      COMMAND systemctl enable \"${MADS_SERVICE_NAME}\"
      RESULT_VARIABLE SYSTEMD_ENABLE_RESULT
    )

    if(NOT SYSTEMD_ENABLE_RESULT EQUAL 0)
      message(
        FATAL_ERROR
        \"Could not enable ${MADS_SERVICE_NAME}. Error code: \${SYSTEMD_ENABLE_RESULT}\"
      )
    endif()
  ")
endif()

# ------------------------------------------------------------------------------
# CPack configuration
# ------------------------------------------------------------------------------

set(CPACK_PACKAGE_NAME "MADS-plugins")

set(
  CPACK_PACKAGE_FILE_NAME
  "${CPACK_PACKAGE_NAME}-${CMAKE_SYSTEM_NAME}-${CMAKE_SYSTEM_PROCESSOR}"
)

set(CPACK_PACKAGE_VENDOR "MADS Consortium")
set(CPACK_PACKAGE_DIRECTORY "${CMAKE_SOURCE_DIR}/packages")
set(CPACK_STRIP_FILES TRUE)
set(CPACK_PACKAGING_INSTALL_PREFIX "/usr/local")
set(CPACK_PACKAGE_CONTACT "paolo.bosetti@unitn.it")
set(CMAKE_PROJECT_HOMEPAGE_URL "https://github.com/mmt-unitn/Walker.git")
set(CPACK_PACKAGE_DESCRIPTION "MADS installer: Multi-Agent Distributed System")

if(APPLE)
  set(CPACK_GENERATOR "STGZ;ZIP")

  if(CMAKE_OSX_ARCHITECTURES MATCHES ";")
    set(
      CPACK_PACKAGE_FILE_NAME
      "${CPACK_PACKAGE_NAME}-${GIT_TAG}-${CMAKE_SYSTEM_NAME}-universal"
    )
  endif()
elseif(UNIX)
  set(CPACK_PACKAGING_INSTALL_PREFIX "/usr/local")
  set(CPACK_DEBIAN_PACKAGE_DEPENDS "libzstd1, libssl3, openssl")
  set(CPACK_DEBIAN_PACKAGE_NAME "mads-plugins")
  set(CPACK_GENERATOR "DEB")
else()
  message(FATAL_ERROR "Unsupported platform")
endif()

include(CPack)
