# Chimaera Codegen 

A Python Library for Chimaera Code Generation

This repository is used to help automate code generation for the IOWarp Runtime: Chimaera.

## Concepts

### Module Repository
A **module repository** is a directory that contains a set of modules and a `chimaera_repo.yaml` file. It serves as a container for organizing related modules that can be managed and built together.

### Module
A **module** represents a specific functionality to be executed in the runtime, such as an I/O system, compression, or encryption. Each module resides within a module repository and contains a `chimaera_mod.yaml` file (which is currently empty).

## Installation

We recommend using a local installation. The scripts
assume they are called from the git clone directory.
```
pip install -e .
```

## Usage

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
