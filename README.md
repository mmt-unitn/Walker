# Multiple plugin builder/installer

Customize this repo for compiling and installing multiple plugins in one command.

To create an installer for a selection of plugins:

```sh
cmake -Bbuild -DCMAKE_INSTALL_PREFIX=./usr/local
# if needed, activate the .venv:
source .venv/bin/activate
cmake --build build -j6
cmake --build build -t package
```


**NOTE**: some of the plugins depend on a Python virtual environment. If one `venv` is already loaded, then the CMake scripts uses it. Iv a **local** `.venv` directory des not exist, the CMake script creates it during configuration and installs `numpy` and `rerun-sdk`, then you have to manually activate it **before** the build phase. Finally, if a local `.venv` exists but it is not activate, CMake stops with an error.