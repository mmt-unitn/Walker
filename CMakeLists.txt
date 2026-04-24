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

# Control whether FetchContent clones are shallow or full.
# ON  -> shallow clone
# OFF -> full clone
set(FETCHCONTENT_SHALLOW_CLONE
    ON
    CACHE BOOL "Use shallow clones for FetchContent dependencies")

message(STATUS "FETCHCONTENT_SHALLOW_CLONE: ${FETCHCONTENT_SHALLOW_CLONE}")

# Version from git tags
execute_process(
  COMMAND git rev-parse --is-inside-work-tree
  WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}
  OUTPUT_VARIABLE IS_GIT_REPO
  OUTPUT_STRIP_TRAILING_WHITESPACE
  ERROR_QUIET
)

if(IS_GIT_REPO STREQUAL "true")
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

set(
  NOVAWALK_VERSION
  "${CPACK_PACKAGE_VERSION_MAJOR}.${CPACK_PACKAGE_VERSION_MINOR}.${CPACK_PACKAGE_VERSION_PATCH}"
)

set(
  INSTALL_MADS_SERVICE
  ON
)

find_package(Eigen3 QUIET NO_MODULE)
if(NOT Eigen3_FOUND)
  message(FATAL_ERROR "
Eigen3 not found!

Install it with:
  sudo apt install libeigen3-dev
")
endif()

include(FetchContent)

FetchContent_Declare(
  load_cells_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/load_cells_plugin.git
  GIT_TAG 7651405
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  driver_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/driver_plugin.git
  GIT_TAG 1824b0ab568a4e0ff761ac855eb2d5640633f1bb
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  portenta_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/portenta_plugin.git
  GIT_TAG 971d8d8e78d540558ffb7d375e331df75f971428
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  imu_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/sense-hat_plugin.git
  GIT_TAG fb6d27b1970be76e240d77be7a2c2c2e59d01f4d
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  forces_calibration_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/forces_calibration_plugin.git
  GIT_TAG 0262fc96eb755fa46e98377b753c9c522acfaede
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  ego_state_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/ego_state_plugin.git
  GIT_TAG 89ad65de02e4794bc783ee3cc5315084c77bafba
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  FSM
  GIT_REPOSITORY https://github.com/mmt-unitn/FSM.git
  GIT_TAG 8855c74c686278e7c5247e8585d9ce0193d992d6
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  harness_detachment_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/Harness_detachment_plugin.git
  GIT_TAG a843664
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(
  watchdog_plugin
  GIT_REPOSITORY https://github.com/mmt-unitn/watchdog_plugin.git
  GIT_TAG 1b852de
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
  GIT_TAG 0.0.7
  GIT_SHALLOW ${FETCHCONTENT_SHALLOW_CLONE}
)

FetchContent_Declare(plugin_tester
  GIT_REPOSITORY https://github.com/mmt-unitn/plugin_tester.git
  GIT_TAG        main
  GIT_SHALLOW    TRUE
)

FetchContent_MakeAvailable(
  load_cells_plugin
  driver_plugin
  portenta_plugin
  imu_plugin
  forces_calibration_plugin
  ego_state_plugin
  harness_detachment_plugin
  FSM
  watchdog_plugin
  plugin_tester

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