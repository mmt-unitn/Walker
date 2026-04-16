cmake_minimum_required(VERSION 3.20)

project(
  walker
  VERSION 1.4.0
  LANGUAGES CXX)
if(CMAKE_BUILD_TYPE STREQUAL "")
  set(CMAKE_BUILD_TYPE
      "Release"
      CACHE STRING "Choose the type of build." FORCE)
endif()
if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
  set(CMAKE_INSTALL_PREFIX
      "${CMAKE_CURRENT_LIST_DIR}/usr/local/"
      CACHE PATH "Install path prefix, prepended onto install directories."
            FORCE)
endif()
message(STATUS "CMAKE_BUILD_TYPE: ${CMAKE_BUILD_TYPE}")
message(STATUS "CMAKE_INSTALL_PREFIX: ${CMAKE_INSTALL_PREFIX}")

# Version from git tags
# Check if project root is a git repository
execute_process(
  COMMAND git rev-parse --is-inside-work-tree
  WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}
  OUTPUT_VARIABLE IS_GIT_REPO
  OUTPUT_STRIP_TRAILING_WHITESPACE
  ERROR_QUIET
)
if(IS_GIT_REPO STREQUAL "true")
  # Get the latest tag
  execute_process(
    COMMAND git describe --tags --dirty
    WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}
    OUTPUT_VARIABLE GIT_TAG
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
  )
  if(GIT_TAG MATCHES "^v([0-9]+)\\.([0-9]+)\\.([0-9]+)(.*)?$")
    string(REGEX REPLACE "^v([0-9]+)\\.([0-9]+)\\.([0-9]+)(.*)?$" "\\1" CPACK_PACKAGE_VERSION_MAJOR "${GIT_TAG}")
    string(REGEX REPLACE "^v([0-9]+)\\.([0-9]+)\\.([0-9]+)(.*)?$" "\\2" CPACK_PACKAGE_VERSION_MINOR "${GIT_TAG}")
    string(REGEX REPLACE "^v([0-9]+)\\.([0-9]+)\\.([0-9]+)(.*)?$" "\\3" CPACK_PACKAGE_VERSION_PATCH "${GIT_TAG}")
    message(STATUS "Project root is a git repository, using version from latest tag: ${CPACK_PACKAGE_VERSION_MAJOR}.${CPACK_PACKAGE_VERSION_MINOR}.${CPACK_PACKAGE_VERSION_PATCH}")
  else()
    message(WARNING "Latest git tag does not match vMAJOR.MINOR.PATCH format, using default version")
    set(CPACK_PACKAGE_VERSION_MAJOR 0)
    set(CPACK_PACKAGE_VERSION_MINOR 0)
    set(CPACK_PACKAGE_VERSION_PATCH 1)
  endif()
else()
  message(WARNING "Project root is NOT a git repository, using default version")
  set(CPACK_PACKAGE_VERSION_MAJOR 0)
  set(CPACK_PACKAGE_VERSION_MINOR 0)
  set(CPACK_PACKAGE_VERSION_PATCH 1)
  set(GIT_TAG "vUNKNOWN_GIT_VERSION")
endif()

# Set variables for project
set(
  NOVAWALK_VERSION
  "${CPACK_PACKAGE_VERSION_MAJOR}.${CPACK_PACKAGE_VERSION_MINOR}.${CPACK_PACKAGE_VERSION_PATCH}"
)
set(
  INSTALL_MADS_SERVICE
  ON
)

# Plugins to build
include(FetchContent)
FetchContent_Declare(
  load_cells_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/load_cells_plugin.git
  GIT_TAG e6d2122
  GIT_SHALLOW TRUE)


FetchContent_Declare(
  driver_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/driver_plugin.git
  GIT_TAG f55966b
  GIT_SHALLOW TRUE)

FetchContent_Declare(
  portenta_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/portenta_plugin.git
  GIT_TAG 4057ba4
  GIT_SHALLOW TRUE)

FetchContent_Declare(
  imu_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/sense-hat_plugin.git
  GIT_TAG fb6d27b
  GIT_SHALLOW TRUE)

FetchContent_Declare(
  forces_calibration_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/forces_calibration_plugin.git
  GIT_TAG afe1cd0
  GIT_SHALLOW TRUE)

FetchContent_Declare(
  ego_state_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/ego_state_plugin.git
  GIT_TAG 27e3920
  GIT_SHALLOW TRUE)

FetchContent_Declare(
  FSM
  GIT_REPOSITORY https://github.com/mmt-unitn/FSM.git
  GIT_TAG 6b6edd3
  GIT_SHALLOW TRUE)

FetchContent_Declare(
  harness_detachment_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/Harness_detachment_plugin.git
  GIT_TAG 6aa18ea
  GIT_SHALLOW TRUE)

FetchContent_Declare(
  mqtt_plugin
  GIT_REPOSITORY https://github.com/MADS-NET/mqtt_plugin.git
  GIT_TAG HEAD
  GIT_SHALLOW TRUE)

FetchContent_Declare(
  forces_autocalibration_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/forces_autocalibration_plugin.git
  GIT_TAG HEAD
  GIT_SHALLOW TRUE)

FetchContent_Declare(common_walker 
  GIT_REPOSITORY https://github.com/mmt-unitn/common_walker.git
  GIT_TAG        0.0.7
  GIT_SHALLOW    TRUE)

#FetchContent_MakeAvailable(
#  FSM load_cells_plugin driver_plugin portenta_plugin ego_state_plugin forces_autocalibration_plugin forces_calibration_plugin imu_plugin Harness_detachment_plugin mqtt_plugin
#)
FetchContent_MakeAvailable(
  load_cells_plugin
  driver_plugin
  portenta_plugin
  imu_plugin
  forces_calibration_plugin
  ego_state_plugin
  harness_detachment_plugin
  FSM
)

set(CPACK_PACKAGE_NAME "MADS plugins")
set(CPACK_PACKAGE_FILE_NAME
    "${CPACK_PACKAGE_NAME}-${CMAKE_SYSTEM_NAME}-${CMAKE_SYSTEM_PROCESSOR}"
)
set(CPACK_PACKAGE_VENDOR "MADS Consortium")
set(CPACK_PACKAGE_DIRECTORY ${CMAKE_SOURCE_DIR}/packages)
set(CPACK_STRIP_FILES TRUE)
set(CPACK_PACKAGING_INSTALL_PREFIX "/usr/local")
set(CPACK_PACKAGE_CONTACT "paolo.bosetti@unitn.it")
set(CMAKE_PROJECT_HOMEPAGE_URL "https://github.com/mmt-unitn/Walker.git")
set(CPACK_PACKAGE_DESCRIPTION "MADS installer: Multi-Agent Distributed System")
if(APPLE)
  set(CPACK_GENERATOR "STGZ;ZIP")
  if(CMAKE_OSX_ARCHITECTURES MATCHES ";")
    set(CPACK_PACKAGE_FILE_NAME
        "${CPACK_PACKAGE_NAME}-${GIT_TAG}-${CMAKE_SYSTEM_NAME}-universal")
  endif()
elseif(UNIX)
  set(CPACK_PACKAGING_INSTALL_PREFIX "/usr/local")
  set(CPACK_DEBIAN_PACKAGE_DEPENDS "libzstd1, libssl3, openssl")
  set(CPACK_DEBIAN_PACKAGE_NAME MADS-plugins)
  set(CPACK_GENERATOR "DEB")
else()
  message(FATAL_ERROR "Unsupported platform")
endif()
include(CPack)


if(INSTALL_MADS_SERVICE)

  install(
    FILES ${CMAKE_SOURCE_DIR}/services/mads-Novawalk.service
    DESTINATION /etc/systemd/system
  )

  install(CODE "
    message(STATUS \"Reloading systemd...\")
    execute_process(COMMAND systemctl daemon-reload)

    message(STATUS \"Enabling mads-Novawalk.service...\")
    execute_process(COMMAND systemctl enable mads-Novawalk.service)
  ")

endif()