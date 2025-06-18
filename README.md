# Robotic Walker - New Codebase

## Project steps

1. Define MADS-compliant [architecture](ARCHITECTURE.md): 
   1. identify the necessary and optional agents
   2. identify the list of devices
   3. create an **issue** on this project for each of the above
2. Implement code for embebbed systems (Arduino)
3. Implement **source** agents (or plugins)
4. Implement **filter** agents
5. Implement controller agent as an RT-timed state machine
6. Implement/adapt GUI (as a **sink** agent)

This action order ensures that each agent can be tested, debugged and timed before integrating into the next higher level agent.

## Repo layout

Each agent has its own repo. All repos are added to this main repo as **git sumbodules**, so that:

* each submodule has its own repo that is independent (i.e. can be developed, built and tested independently)
* cloning this repo also clones all the necessary submodules
* submodules versions are *synchronized*, i.e. their commit hashes are recorded in the main repo, and each tag version in the main repo keeps the list of proper submodules versions

This repo shall only contain documentation and links to submodules. Each submodule shall be self-contained and self-sufficient. The purpose of this repo is thus to collect all the necessary codebase in a single container, also providing a single access point to GitHub issues.

## GitHub stuff

Each module shall have a maintainer person. The module repo shall be under the maintainer GitHub account.

The [current organization](https://github.com/mmt-unitn) keeps **forks** of all modules. This main repo adds submodules via the forks URLs.

## Code etiquette

### Project management

Project management shall be performed with CMake tools.

### Third party libraries

* Unless absolutely necessary, try to avoid the use of large/huge general purpose frameworks (as QT or boost).
* When available, prefer header-only libraries to compiled ones (e.g. use `eigen` rather than `armadillo`). This tipically means easier integration and porting.
* Unless for very common libraries (e.g. `libgzip`, `libcurl`, `libopenssl`), prefer a locally built library with standard version. Use CMake's `FetchContent` or, as a second choice, `ExternalProject`. In this way, any build uses exactly the same version of any external tool, and that version is tracked in the git repo.
* If possible, prefer static linking of libraries, so that the resulting code can be installed more easily.

### Coding

* Use 2 spaces for tabs.
* Use `TitleCase` for classes, namespaces, and global variables; use `snake_case` for variable and methods/functions; prepend an underscore to any `_private_attribute` (but not to `public_attributes`!); use `ALL_CAPS` for preprocessor macros.
* Install `clang-format` and regularly reformat the code with the default `clang-format` style (there is a VSCode extension for that).
* Mark each file with a comment header reporting purpose, author, creation date.