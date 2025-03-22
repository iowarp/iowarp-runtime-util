"""
Generate code for chimaera
"""

import os
import sys
import yaml
from chimaera_util.util.templates import task_template, client_method_template, runtime_method_template
from chimaera_util.util.paths import CHIMAERA_TASK_TEMPL
from chimaera_util.util.naming import to_camel_case
import re

BASE_REPO_CMAKE = """
cmake_minimum_required(VERSION 3.25)
project({namespace})
set(MOD_NAMESPACE {namespace})

# FIND CHIMAERA
if (NOT CHIMAERA_IS_MAIN_PROJECT)
  find_package(Chimaera CONFIG REQUIRED)
endif()

# SET INSTALL VARIABLES
if(NOT CHIMAERA_INSTALL_BIN_DIR)
  set(CHIMAERA_INSTALL_BIN_DIR ${{CMAKE_INSTALL_PREFIX}}/bin)
endif()

if(NOT CHIMAERA_INSTALL_LIB_DIR)
  set(CHIMAERA_INSTALL_LIB_DIR ${{CMAKE_INSTALL_PREFIX}}/lib)
endif()

if(NOT CHIMAERA_INSTALL_INCLUDE_DIR)
  set(CHIMAERA_INSTALL_INCLUDE_DIR ${{CMAKE_INSTALL_PREFIX}}/include)
endif()

if(NOT CHIMAERA_INSTALL_DATA_DIR)
  set(CHIMAERA_INSTALL_DATA_DIR ${{CMAKE_INSTALL_PREFIX}}/share)
endif()

if (NOT CHIMAERA_EXPORTED_TARGETS)
  set(CHIMAERA_EXPORTED_TARGETS {camel_ns})
endif()

# ADD SUBDIRECTORIES
{subdirs}

# INSTALL TARGETS
if (NOT CHIMAERA_IS_MAIN_PROJECT)
  install(EXPORT ${{CHIMAERA_EXPORTED_TARGETS}}
          FILE ${{CHIMAERA_EXPORTED_TARGETS}}Config.cmake
          NAMESPACE {namespace}::
          DESTINATION cmake
   )
endif()
"""


class ChimaeraCodegen:
    def make_macro(self, PATH):
        """
        Converts the file at PATH into a C macro. The name of the
        file is used as the name of the macro. The macro name will
        be made all caps. You can use any extension on the file.
        """
        MACRO_NAME = os.path.basename(PATH).upper().split('.')[0]
        self.print_macro(PATH, MACRO_NAME)

    def print_macro(self, path, macro_name):
        """
        Prints the C macro conversion
        """
        with open(path) as fp:
            lines = fp.read().splitlines()
        macro_def = f'#define {macro_name} \\\n'
        macro_body = ' \\\n'.join(lines)
        print(f'{macro_def}{macro_body}')

    def make_configs(self, CHI_ROOT):
        """
        Creates the default chimaera client and server configurations
        """
        self._create_config(
            path=f"{CHI_ROOT}/config/chimaera_client_default.yaml",
            var_name="kChiDefaultClientConfigStr",
            config_path=f"{CHI_ROOT}/include/chimaera/config/config_client_default.h",
            macro_name="CHI_CLIENT"
        )
        self._create_config(
            path=f"{CHI_ROOT}/config/chimaera_server_default.yaml",
            var_name="kChiServerDefaultConfigStr",
            config_path=f"{CHI_ROOT}/include/chimaera/config/config_server_default.h",
            macro_name="CHI_SERVER"
        )

    def _create_config(self, path, var_name, config_path, macro_name):
        """
        Creates a chimaera configuration file. Either the server or the client.
        """
        with open(path) as fp:
            yaml_config_lines = fp.read().splitlines()

        # Create the hermes config string
        string_lines = []
        string_lines.append(f"const inline char* {var_name} = ")
        for line in yaml_config_lines:
            line = line.replace('\"', '\\\"')
            line = line.replace('\'', '\\\'')
            string_lines.append(f"\"{line}\\n\"")
        string_lines[-1] = string_lines[-1] + ';'

        # Create the configuration
        config_lines = []
        config_lines.append(f"#ifndef CHI_SRC_CONFIG_{macro_name}_DEFAULT_H_")
        config_lines.append(f"#define CHI_SRC_CONFIG_{macro_name}_DEFAULT_H_")
        config_lines += string_lines
        config_lines.append(f"#endif  // CHI_SRC_CONFIG_{macro_name}_DEFAULT_H_")

        # Persist
        config = "\n".join(config_lines)
        with open(config_path, 'w') as fp:
            fp.write(config)

    def make_repo(self, MOD_REPO_DIR, namespace):
        """
        Creates a chimaera module repository.
        """
        MOD_REPO_DIR = os.path.abspath(MOD_REPO_DIR)
        os.makedirs(MOD_REPO_DIR, exist_ok=True)
        repo_conf = {'namespace': namespace}
        self.save_repo_config(MOD_REPO_DIR, repo_conf)
        self.refresh_repo_cmake(MOD_REPO_DIR, namespace)
        print(f'Created module repository at {MOD_REPO_DIR}')

    def load_repo_config(self, MOD_REPO_DIR):
        MOD_REPO_DIR = os.path.abspath(MOD_REPO_DIR)
        with open(f'{MOD_REPO_DIR}/chimaera_repo.yaml') as fp:
            config = yaml.load(fp, Loader=yaml.FullLoader)
        return config

    def save_repo_config(self, MOD_REPO_DIR, repo_conf):
        with open(f'{MOD_REPO_DIR}/chimaera_repo.yaml', 'w') as fp:
            yaml.dump(repo_conf, fp)

    def make_mod(self, MOD_ROOT):
        """
        Bootstraps a task. Copies all the necessary files and replaces. This
        is an aggressive operation.
        """
        TASK_NAME = os.path.basename(MOD_ROOT)
        if os.path.exists(f'{MOD_ROOT}/src'):
            ret = input('This task seems bootstrapped, do you really want to continue? (yes/no): ')
            if ret != 'yes':
                print('Skipping...')
                sys.exit(0)
        os.makedirs(f'{MOD_ROOT}/src', exist_ok=True)
        os.makedirs(f'{MOD_ROOT}/include/{TASK_NAME}', exist_ok=True)
        self._copy_replace_iter(MOD_ROOT, CHIMAERA_TASK_TEMPL, TASK_NAME, '')

    def _copy_replace_iter(self, MOD_ROOT, CHIMAERA_TASK_TEMPL, TASK_NAME, rel_path):
        for name in os.listdir(f"{CHIMAERA_TASK_TEMPL}/{rel_path}"):
            # Copy and replace files
            if os.path.isfile(f"{CHIMAERA_TASK_TEMPL}/{rel_path}/{name}"):
                rel_file_path = os.path.join(rel_path, name)
                self._copy_replace(MOD_ROOT, CHIMAERA_TASK_TEMPL, rel_file_path, TASK_NAME)
            # Recurse
            elif os.path.isdir(f"{CHIMAERA_TASK_TEMPL}/{rel_path}/{name}"):
                self._copy_replace_iter(MOD_ROOT, CHIMAERA_TASK_TEMPL, TASK_NAME, os.path.join(rel_path, name))

    def _copy_replace(self, MOD_ROOT, CHIMAERA_TASK_TEMPL, rel_path, TASK_NAME):
        """
        Copies a file from CHIMAERA_TASK_TEMPL to MOD_ROOT and renames
        TASK_TEMPL to the value of TASK_NAME
        """
        with open(f'{CHIMAERA_TASK_TEMPL}/{rel_path}') as fp:
            text = fp.read()
        text = text.replace('TASK_NAME', TASK_NAME)
        rel_path = rel_path.replace('TASK_NAME', TASK_NAME)
        with open(f'{MOD_ROOT}/{rel_path}', 'w') as fp:
            fp.write(text)

    def refresh_repo(self, MOD_REPO_DIR):
        print(f'Refreshing repository at {MOD_REPO_DIR}')
        self.refresh_repo_methods(MOD_REPO_DIR)
        self.refresh_repo_cmake(MOD_REPO_DIR)

    def refresh_repo_methods(self, MOD_REPO_DIR):
        MOD_REPO_DIR = os.path.abspath(MOD_REPO_DIR)
        MOD_ROOTS = [os.path.join(MOD_REPO_DIR, item)
                      for item in os.listdir(MOD_REPO_DIR)]
        # Refresh all methods
        for MOD_ROOT in MOD_ROOTS:
            try:
                self.refresh_methods(MOD_ROOT)
            except Exception as e:
                print(e)
                pass

    def refresh_repo_cmake(self, MOD_REPO_DIR, namespace=None):
        MOD_REPO_DIR = os.path.abspath(MOD_REPO_DIR)
        if namespace is None:
            repo_conf = self.load_repo_config(MOD_REPO_DIR)
            namespace = repo_conf['namespace']
        camel_ns = to_camel_case(namespace) 
        MOD_NAMES = [MOD_NAME for MOD_NAME in os.listdir(MOD_REPO_DIR) 
                     if os.path.isdir(f'{MOD_REPO_DIR}/{MOD_NAME}')
                     and os.path.exists(f'{MOD_REPO_DIR}/{MOD_NAME}/chimaera_mod.yaml')]
        MOD_NAMES = sorted(MOD_NAMES) 
        subdirs = '\n'.join([f'add_subdirectory({MOD_NAME})' 
                             for MOD_NAME in MOD_NAMES])
        repo_cmake = BASE_REPO_CMAKE.format(namespace=namespace, subdirs=subdirs, camel_ns=camel_ns)
        with open(f'{MOD_REPO_DIR}/CMakeLists.txt', 'w') as fp:
            fp.write(repo_cmake)

    def load_method_defs(self):
        with open(self.METHODS_YAML) as fp:
            method_defs = yaml.load(fp, Loader=yaml.FullLoader)
        if method_defs is None:
            method_defs = {}
        return method_defs

    def scan_compiled_tasks(self, method_defs):
        methods = {}
        if os.path.exists(self.OLD_TASKS_H):
            with open(self.OLD_TASKS_H) as fp:
                for line in fp:
                    match = re.search(r'struct\s+(.*)Task', line)
                    if not match:
                        continue
                    task_name = match.group(1)
                    if task_name not in method_defs:
                        continue
                    method_id = f'k{task_name}'
                    method_off = method_defs[task_name]
                    methods[method_id] = {
                        'val': method_off,
                        'compiled': True
                    }
        return methods

    def mark_new_methods_uncompiled(self, method_defs, methods):
        for method_name, method_off in method_defs.items():
                if method_off < 0:
                    continue
                if method_off <= 2:
                    # These are required methods
                    methods[method_name] = True
                if method_off < 10:
                    # TODO(llogan): Allow bootstrapping special methods
                    continue
                if method_name in methods:
                    continue
                methods[method_name] = {
                    'val': method_off,
                    'compiled': False
                }

    def save_method_compile_staus(self, methods):
        with open(self.COMPILED_METHODS_YAML, 'w') as fp:
            yaml.dump(methods, fp)

    def get_method_compile_status(self):
        method_defs = self.load_method_defs()
        with open(self.COMPILED_METHODS_YAML) as fp:
            methods = yaml.load(fp, Loader=yaml.FullLoader)
        if methods is None:
            methods = self.scan_compiled_tasks(method_defs)
        self.mark_new_methods_uncompiled(method_defs, methods)
        return methods

    def refresh_methods(self, MOD_ROOT):
        """
        Refreshes autogenerated code in the task.
        """
        if not os.path.exists(f'{MOD_ROOT}/include'):
            return
        #Create paths
        MOD_NAME = os.path.basename(MOD_ROOT)
        self.METHODS_YAML = f'{MOD_ROOT}/include/{MOD_NAME}/{MOD_NAME}_methods.yaml'
        self.COMPILED_METHODS_YAML = f'{MOD_ROOT}/include/{MOD_NAME}/{MOD_NAME}_methods.compiled.yaml'
        self.METHODS_H = f'{MOD_ROOT}/include/{MOD_NAME}/{MOD_NAME}_methods.h'
        self.METHOD_MACRO = f'CHI_{MOD_NAME.upper()}_METHODS_H_'
        self.LIB_EXEC_H = f'{MOD_ROOT}/include/{MOD_NAME}/{MOD_NAME}_lib_exec.h'
        self.LIB_EXEC_MACRO = f'CHI_{MOD_NAME.upper()}_LIB_EXEC_H_'
        self.OLD_TASKS_H = f'{MOD_ROOT}/include/{MOD_NAME}/{MOD_NAME}_tasks.h'
        self.NEW_TASKS_H = f'{MOD_ROOT}/include/{MOD_NAME}/{MOD_NAME}_tasks.temp_h'
        self.OLD_CLIENT_H = f'{MOD_ROOT}/include/{MOD_NAME}/{MOD_NAME}_client.h'
        self.NEW_CLIENT_H = f'{MOD_ROOT}/include/{MOD_NAME}/{MOD_NAME}_client.temp_h'
        self.OLD_RUNTIME_CC = f'{MOD_ROOT}/src/{MOD_NAME}_runtime.cc'
        self.NEW_RUNTIME_CC = f'{MOD_ROOT}/src/{MOD_NAME}_runtime.temp_cc'

        # Load methods and their compiled status
        methods = self.get_method_compile_status() 
        methods = sorted(methods.items(), key=lambda x: x[1]['val'])

        # Refresh the files
        self.refresh_methods_h(methods)
        self.refresh_lib_exec_h(methods)
        self.refresh_tasks_h(methods)
        self.refresh_client_h(methods)
        self.refresh_runtime_cc(methods)

        # Save compiled methods
        self.save_method_compile_staus(methods)

    def refresh_methods_h(self, methods):
        lines = []
        lines += [f'#ifndef {self.METHOD_MACRO}',
                  f'#define {self.METHOD_MACRO}',
                  '',
                  '/** The set of methods in the admin task */',
                  'struct Method : public TaskMethod {']
        for method_enum_name, method_info in methods:
            method_off = method_info['val']
            if method_off < 10:
                continue
            lines += [f'  TASK_METHOD_T {method_enum_name} = {method_off};']
        lines += [f'  TASK_METHOD_T kCount = {methods[-1][1] + 1};']
        lines += ['};', '', f'#endif  // {self.METHOD_MACRO}']
        with open(self.METHODS_H, 'w') as fp:
            fp.write('\n'.join(lines))

    def refresh_lib_exec_h(self, methods):
        # Produce the MOD_NAME_lib_exec.h file
        lines = []
        lines += [f'#ifndef {self.LIB_EXEC_MACRO}',
                  f'#define {self.LIB_EXEC_MACRO}',
                  '']
        ## Create the Run method
        lines += ['/** Execute a task */',
                  'void Run(u32 method, Task *task, RunContext &rctx) override {',
                  '  switch (method) {']
        for method_enum_name, method_info in methods:
            method_off = method_info['val']
            if method_off < 0:
                continue
            method_name = method_enum_name.replace('k', '', 1)
            task_name = method_name + "Task"
            lines += [f'    case Method::{method_enum_name}: {{',
                      f'      {method_name}(reinterpret_cast<{task_name} *>(task), rctx);',
                      f'      break;',
                      f'    }}']
        lines += ['  }']
        lines += ['}']

        ## Create the Monitor method
        lines += ['/** Execute a task */',
                  'void Monitor(MonitorModeId mode, MethodId method, Task *task, RunContext &rctx) override {',
                  '  switch (method) {']
        for method_enum_name, method_info in methods:
            method_off = method_info['val']
            if method_off < 0:
                continue
            method_name = method_enum_name.replace('k', '', 1)
            task_name = method_name + "Task"
            lines += [f'    case Method::{method_enum_name}: {{',
                      f'      Monitor{method_name}(mode, reinterpret_cast<{task_name} *>(task), rctx);',
                      f'      break;',
                      f'    }}']
        lines += ['  }']
        lines += ['}']

        ## Create the Del method
        lines += ['/** Delete a task */',
                  'void Del(const hipc::MemContext &mctx, u32 method, Task *task) override {',
                  '  switch (method) {']
        for method_enum_name, method_info in methods:
            method_off = method_info['val']
            if method_off < 0:
                continue
            method_name = method_enum_name.replace('k', '', 1)
            task_name = method_name + "Task"
            lines += [f'    case Method::{method_enum_name}: {{',
                      f'      CHI_CLIENT->DelTask<{task_name}>(mctx, reinterpret_cast<{task_name} *>(task));',
                      f'      break;',
                      f'    }}']
        lines += ['  }']
        lines += ['}']

        ## Create the CopyStart method
        lines += ['/** Duplicate a task */',
                  'void CopyStart(u32 method, const Task *orig_task, Task *dup_task, bool deep) override {',
                  '  switch (method) {']
        for method_enum_name, method_info in methods:
            method_off = method_info['val']
            if method_off < 0:
                continue
            method_name = method_enum_name.replace('k', '', 1)
            task_name = method_name + "Task"
            lines += [f'    case Method::{method_enum_name}: {{',
                      f'      chi::CALL_COPY_START(',
                      f'        reinterpret_cast<const {task_name}*>(orig_task), ',
                      f'        reinterpret_cast<{task_name}*>(dup_task), deep);',
                      f'      break;',
                      f'    }}']
        lines += ['  }']
        lines += ['}']

        ## Create the CopyStart method
        lines += ['/** Duplicate a task */',
                  'void NewCopyStart(u32 method, const Task *orig_task, FullPtr<Task> &dup_task, bool deep) override {',
                  '  switch (method) {']
        for method_enum_name, method_info in methods:
            method_off = method_info['val']
            if method_off < 0:
                continue
            method_name = method_enum_name.replace('k', '', 1)
            task_name = method_name + "Task"
            lines += [f'    case Method::{method_enum_name}: {{',
                      f'      chi::CALL_NEW_COPY_START(reinterpret_cast<const {task_name}*>(orig_task), dup_task, deep);',
                      f'      break;',
                      f'    }}']
        lines += ['  }']
        lines += ['}']

        ## Create the SaveStart Method
        lines += ['/** Serialize a task when initially pushing into remote */',
                  'void SaveStart(',
                  # '    const hipc::CtxAllocator<CHI_ALLOC_T> &alloc, ',
                  '    u32 method, BinaryOutputArchive<true> &ar,',
                  '    Task *task) override {',
                  '  switch (method) {']
        for method_enum_name, method_info in methods:
            method_off = method_info['val']
            if method_off < 0:
                continue
            method_name = method_enum_name.replace('k', '', 1)
            task_name = method_name + "Task"
            lines += [f'    case Method::{method_enum_name}: {{',
                      f'      ar << *reinterpret_cast<{task_name}*>(task);',
                      f'      break;',
                      f'    }}']
        lines += ['  }']
        lines += ['}']

        ## Create the LoadStart Method
        lines += ['/** Deserialize a task when popping from remote queue */',
                  'TaskPointer LoadStart('
                  # '    const hipc::CtxAllocator<CHI_ALLOC_T> &alloc, ',
                  '    u32 method, BinaryInputArchive<true> &ar) override {',
                  '  TaskPointer task_ptr;',
                  '  switch (method) {']
        for method_enum_name, method_info in methods:
            method_off = method_info['val']
            if method_off < 0:
                continue
            method_name = method_enum_name.replace('k', '', 1)
            task_name = method_name + "Task"
            lines += [f'    case Method::{method_enum_name}: {{',
                      f'      task_ptr.ptr_ = CHI_CLIENT->NewEmptyTask<{task_name}>(',
                      f'             HSHM_DEFAULT_MEM_CTX, task_ptr.shm_);',
                      f'      ar >> *reinterpret_cast<{task_name}*>(task_ptr.ptr_);',
                      f'      break;',
                      f'    }}']
        lines += ['  }']
        lines += ['  return task_ptr;']
        lines += ['}']

        ## Create the SaveEnd Method
        lines += ['/** Serialize a task when returning from remote queue */',
                  'void SaveEnd(u32 method, BinaryOutputArchive<false> &ar, Task *task) override {',
                  '  switch (method) {']
        for method_enum_name, method_info in methods:
            method_off = method_info['val']
            if method_off < 0:
                continue
            method_name = method_enum_name.replace('k', '', 1)
            task_name = method_name + "Task"
            lines += [f'    case Method::{method_enum_name}: {{',
                      f'      ar << *reinterpret_cast<{task_name}*>(task);',
                      f'      break;',
                      f'    }}']
        lines += ['  }']
        lines += ['}']

        ## Create the LoadEnd Method
        lines += ['/** Deserialize a task when popping from remote queue */',
                  'void LoadEnd(u32 method, BinaryInputArchive<false> &ar, Task *task) override {',
                  '  switch (method) {']
        for method_enum_name, method_info in methods:
            method_off = method_info['val']
            if method_off < 0:
                continue
            method_name = method_enum_name.replace('k', '', 1)
            task_name = method_name + "Task"
            lines += [f'    case Method::{method_enum_name}: {{',
                      f'      ar >> *reinterpret_cast<{task_name}*>(task);',
                      f'      break;',
                      f'    }}']
        lines += ['  }']
        lines += ['}']

        ## Finish the file
        lines += ['', f'#endif  // {self.LIB_EXEC_MACRO}']

        ## Write MOD_NAME_lib_exec.h
        with open(self.LIB_EXEC_H, 'w') as fp:
            fp.write('\n'.join(lines))

    def refresh_tasks_h(self, methods):
        self.refresh_method_try_modes(
            methods, self.OLD_TASKS_H, 
            self.NEW_TASKS_H, task_template)

    def refresh_client_h(self, methods):
        self.refresh_method_try_modes(
            methods, self.OLD_CLIENT_H, 
            self.NEW_CLIENT_H, client_method_template)

    def refresh_runtime_cc(self, methods):
        self.refresh_method_try_modes(
            methods, self.OLD_RUNTIME_CC, 
            self.NEW_RUNTIME_CC, runtime_method_template)

    def refresh_method_try_modes(self, methods, orig_path, new_path, tmpl_name):
        self.refresh_insert(methods, orig_path, tmpl_name)
        ret = self.refresh_append(methods, orig_path, tmpl_name)
        if not ret:
            self.refresh_tmpfile(methods, new_path, tmpl_name)

    def refresh_insert(self, methods, orig_path, tmpl_name):
        """
        Inserts non-compiled methods into the runtime
        file at the ideal location
        """
        with open(self.OLD_RUNTIME_CC) as fp:
            content = fp.read()
        for method_enum_name, method_info in methods:
            method_off = method_info['val']
            if method_off < 0 or method_info['compiled']:
                continue
            method_name = method_enum_name.replace('k', '', 1)
            task_name = method_name + "Task"
            tmpl = self.tmpl(tmpl_name, task_name, method_name, method_enum_name)
            method_info['compiled'] = True
            # Find CHI_END tag to insert before
            start_idx = content.find(f'CHI_END({method_name})')
            if start_idx == -1:
                continue
            # Insert 2 newlines after the template
            content = content[:start_idx] + tmpl + '\n\n' + content[start_idx:]
        with open(orig_path) as fp:
            content = fp.read()
            with open(self.OLD_RUNTIME_CC, 'w') as fp:
                fp.write(content)
        
    def refresh_append(self, methods, orig_path, tmpl_name):
        """
        Appends non-compiled methods to the end of the
        runtime and marks them compiled
        """
        # Open the file and read its contents
        with open(self.OLD_RUNTIME_CC) as fp:
            content = fp.read()
        
        # Find the autogen methods section
        start_idx = content.find('CHI_AUTOGEN_METHODS')
        if start_idx == -1:
            return False
        lines = []
        for method_enum_name, method_info in methods:
            method_off = method_info['val']
            if method_off < 0 or method_info['compiled']:
                continue
            method_name = method_enum_name.replace('k', '', 1)
            task_name = method_name + "Task"
            tmpl = self.tmpl(tmpl_name, task_name, method_name, method_enum_name)
            lines += [tmpl]
            method_info['compiled'] = True
        
        # Add newlines before autogen methods tag
        content = content[:start_idx] + '\n'.join(lines) + '\n\n' + content[start_idx:]
        with open(orig_path, 'w') as fp:
            fp.write(content)
        return True

    def refresh_tmpfile(self, methods, new_path, tmpl_name):
        """
        Generates a temporary file with new runtime methods
        to copy-paste from.
        """
        lines = []
        for method_enum_name, method_info in methods:
            method_off = method_info['val']
            if method_off < 0:
                continue
            method_name = method_enum_name.replace('k', '', 1)
            task_name = method_name + "Task"
            tmpl = self.tmpl(tmpl_name, task_name, method_name, method_enum_name)
            lines += [tmpl]
        with open(new_path, 'w') as fp:
            fp.write('\n'.join(lines))

    def clear_autogen_temp(self, MOD_REPO_DIR):
        MOD_ROOTS = [os.path.join(MOD_REPO_DIR, item)
                      for item in os.listdir(MOD_REPO_DIR)]
        for MOD_ROOT in MOD_ROOTS:
            self._clear_autogen_temp(MOD_ROOT)

    def _clear_autogen_temp(self, MOD_ROOT):
        """
        Removes autogenerated temporary files from the task.
        """
        if not os.path.exists(f'{MOD_ROOT}/include'):
            return
        MOD_NAME = os.path.basename(MOD_ROOT)
        for file_path in [
            f'{MOD_ROOT}/include/{MOD_NAME}/{MOD_NAME}_tasks.temp_h',
            f'{MOD_ROOT}/include/{MOD_NAME}/{MOD_NAME}_client.temp_h',
            f'{MOD_ROOT}/include/{MOD_NAME}/{MOD_NAME}.temp_h',
            f'{MOD_ROOT}/src/{MOD_NAME}_runtime.temp_cc',
            f'{MOD_ROOT}/src/{MOD_NAME}.temp_cc',
            f'{MOD_ROOT}/src/CMakeLists.txt.backup',
        ]:
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass

    def tmpl(self, tmpl_str, task_name, method_name, method_enum_name):
        return tmpl_str.replace('##task_name##', task_name) \
            .replace('##method_name##', method_name) \
            .replace('##method_enum_name##', method_enum_name)
