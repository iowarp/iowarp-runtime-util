# IOWarp Runtime Utilities

[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![IoWarp](https://img.shields.io/badge/IoWarp-GitHub-blue.svg)](http://github.com/iowarp)
[![GRC](https://img.shields.io/badge/GRC-Website-blue.svg)](https://grc.iit.edu/)
[![Python](https://img.shields.io/badge/Python-3.7+-yellow.svg)](https://www.python.org/)
[![IOWarp-Runtime](https://img.shields.io/badge/IOWarp-Runtime-purple.svg)](https://github.com/iowarp/iowarp-runtime)

A Python library for automating code generation and module management for the IOWarp Runtime (Chimaera).

## Purpose

IOWarp Runtime Utilities provides a comprehensive set of tools to help developers automate code generation, module creation, and repository management for the Chimaera runtime. This library simplifies the development workflow for creating high-performance I/O modules, compression, encryption, and other runtime functionalities.

## Installation

We recommend using a local installation. The scripts assume they are called from the git clone directory.
```bash
pip install -e .
```

## Concepts

### Module Repository
A **module repository** is a directory that contains a set of modules and a `chimaera_repo.yaml` file. It serves as a container for organizing related modules that can be managed and built together.

### Module
A **module** represents a specific functionality to be executed in the runtime, such as an I/O system, compression, or encryption. Each module resides within a module repository and contains a `chimaera_mod.yaml` file.

## Usage

The following utility commands are available after installation:

### 1. `chi_clear_temp`
- **Usage:** `./chi_clear_temp [MOD_REPO_DIR]`
- **Description:** Clears auto-generated temporary files in the specified module repository directory using the Chimaera codegen utility.

### 2. `chi_make_config`
- **Usage:** `chi_make_config [CHI_ROOT (optional)]`
- **Description:** Generates default configuration header files for client and server (`config_client_default.h`, `config_server_default.h`) in the `${CHI}/src/` directory. If `CHI_ROOT` is not provided, uses the current working directory.

### 3. `chi_make_macro`
- **Usage:** `./chi_make_macro [PATH]`
- **Description:** Generates macro files at the specified path using the Chimaera codegen utility.

### 4. `chi_make_mod`
- **Usage:** `./chi_make_mod [MODULE_ROOT]`
- **Description:** Creates a new module within a module repository at the specified root path.

### 5. `chi_make_repo`
- **Usage:** `./chi_make_repo [MOD_REPO_DIR] [MOD_NAMESPACE]`
- **Description:** Initializes a new module repository at the given directory with the specified namespace, which is used for CMake project naming and install namespace.

### 6. `chi_refresh_repo`
- **Usage:** `./chi_refresh_mods [MOD_REPO_DIR]`
- **Description:** Refreshes the module repository, updating or regenerating necessary files.

### 7. `chi_repo_reformat`
- **Usage:** `chi_repo_reformat <repo_path>`
- **Description:** Reformats a module repository:
  - Renames source/header files to follow new naming conventions.
  - Updates references in source and include files.
  - Modifies CMake files to use updated function names and namespaces.
  - Creates backups and new client source files as needed.

## Project Structure

- `bin/` - Utility scripts
- `chimaera_util/` - Core Python library
- `setup.py` - Package configuration

## License

IOWarp Runtime Util is licensed under the BSD 3-Clause License. You can find the full license text in the source files.

## Support

For issues, questions, or contributions, please:
- Open an issue on the [GitHub repository](https://github.com/iowarp/iowarp-runtime-util)
- Refer to the [IOWarp Runtime documentation](https://github.com/iowarp/iowarp-runtime) for runtime-specific questions
- Contact the Gnosis Research Center at Illinois Institute of Technology
