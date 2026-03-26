cmake_minimum_required(VERSION 3.20)

project(
  mads_plugins
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

# Python3 virtual environment
find_package(
  Python3
  COMPONENTS Interpreter
  REQUIRED)

set(VENV_DIR "${CMAKE_SOURCE_DIR}/.venv")

if(WIN32)
  set(VENV_PYTHON "${VENV_DIR}/Scripts/python.exe")
else()
  set(VENV_PYTHON "${VENV_DIR}/bin/python")
endif()

if(DEFINED ENV{VIRTUAL_ENV})
  message(
    STATUS "Python virtual environment is already activated: $ENV{VIRTUAL_ENV}")
else()
  if(NOT EXISTS "${VENV_DIR}")
    execute_process(
      COMMAND ${Python3_EXECUTABLE} -m venv "${VENV_DIR}"
      RESULT_VARIABLE venv_creation_result
      OUTPUT_VARIABLE venv_creation_output
      ERROR_VARIABLE venv_creation_error
      OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_STRIP_TRAILING_WHITESPACE)
    if(NOT venv_creation_result EQUAL 0)
      message(
        FATAL_ERROR
          "Failed to create virtual environment: ${venv_creation_error}")
    endif()

    add_custom_target(
      setup_venv
      COMMAND ${VENV_PYTHON} -m pip install --upgrade pip
      COMMAND ${VENV_PYTHON} -m pip install numpy rerun-sdk
      COMMENT
        "Setting up Python virtual environment and installing dependencies"
      VERBATIM)
  else()
    message(
      FATAL_ERROR
        "Python virtual environment already exists at ${VENV_DIR}, remember to activate it!"
    )
  endif()
endif()

# Plugins to build
include(FetchContent)
FetchContent_Declare(
  replay_plugin
  GIT_REPOSITORY https://github.com/mads-net/replay_plugin.git
  GIT_TAG HEAD
  GIT_SHALLOW TRUE)

FetchContent_Declare(
  rerunner_plugin
  GIT_REPOSITORY https://github.com/mads-net/rerunner_plugin.git
  GIT_TAG HEAD
  GIT_SHALLOW TRUE)

FetchContent_Declare(
  tui_plugin
  GIT_REPOSITORY https://github.com/mads-net/tui_plugin.git
  GIT_TAG HEAD
  GIT_SHALLOW TRUE)

FetchContent_Declare(
  hdf5_plugin
  GIT_REPOSITORY https://github.com/mads-net/hdf5_plugin.git
  GIT_TAG HEAD
  GIT_SHALLOW TRUE)

FetchContent_Declare(
  python_agent
  GIT_REPOSITORY https://github.com/MADS-NET/python_agent.git
  GIT_TAG HEAD
  GIT_SHALLOW TRUE)

if(UNIX AND NOT APPLE)
  FetchContent_Declare(
    rpio_plugin
    GIT_REPOSITORY https://github.com/MADS-NET/rpio.plugin.git
    GIT_TAG HEAD
    GIT_SHALLOW TRUE)
  FetchContent_MakeAvailable(rpio_plugin)
endif()

FetchContent_MakeAvailable(
  replay_plugin rerunner_plugin tui_plugin hdf5_plugin
  python_agent
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
set(CMAKE_PROJECT_HOMEPAGE_URL "https://github.com/MADS-NET")
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
