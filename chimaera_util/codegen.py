"""
Generate code for chimaera
"""

import os
import sys
import yaml
from chimaera_util.util.templates import task_template, client_method_template, runtime_method_template, BASE_REPO_CMAKE
from chimaera_util.util.paths import CHIMAERA_TASK_TEMPL
from chimaera_util.util.naming import to_camel_case
import re

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
        self.namespace = namespace
        os.makedirs(MOD_REPO_DIR, exist_ok=True)
        repo_conf = {'namespace': namespace}
        self.save_repo_config(MOD_REPO_DIR, repo_conf)
        self.refresh_repo_cmake(MOD_REPO_DIR, namespace)
        print(f'Created module repository at {MOD_REPO_DIR}')

    def load_repo_config(self, MOD_REPO_DIR):
        MOD_REPO_DIR = os.path.abspath(MOD_REPO_DIR)
        with open(f'{MOD_REPO_DIR}/chimaera_repo.yaml') as fp:
            config = yaml.load(fp, Loader=yaml.FullLoader)
        self.namespace = config['namespace']
        return config

    def save_repo_config(self, MOD_REPO_DIR, repo_conf):
        with open(f'{MOD_REPO_DIR}/chimaera_repo.yaml', 'w') as fp:
            yaml.dump(repo_conf, fp)

    def make_mod(self, MOD_ROOT):
        """
        Bootstraps a task. Copies all the necessary files and replaces. This
        is an aggressive operation.
        """
        MOD_REPO_DIR = os.path.dirname(MOD_ROOT)
        self.load_repo_config(MOD_REPO_DIR)
        self.mod_name = os.path.basename(MOD_ROOT)
        if os.path.exists(f'{MOD_ROOT}/src'):
            ret = input('This task seems bootstrapped, do you really want to continue? (yes/no): ')
            if ret != 'yes':
                print('Skipping...')
                sys.exit(0)
        os.makedirs(f'{MOD_ROOT}/src', exist_ok=True)
        os.makedirs(f'{MOD_ROOT}/include/{self.mod_name}', exist_ok=True)
        self._copy_replace_iter(MOD_ROOT, CHIMAERA_TASK_TEMPL, '')

    def _copy_replace_iter(self, MOD_ROOT, CHIMAERA_TASK_TEMPL, rel_path):
        for name in os.listdir(f"{CHIMAERA_TASK_TEMPL}/{rel_path}"):
            # Copy and replace files
            if os.path.isfile(f"{CHIMAERA_TASK_TEMPL}/{rel_path}/{name}"):
                rel_file_path = os.path.join(rel_path, name)
                self._copy_replace(MOD_ROOT, CHIMAERA_TASK_TEMPL, rel_file_path)
            # Recurse
            elif os.path.isdir(f"{CHIMAERA_TASK_TEMPL}/{rel_path}/{name}"):
                self._copy_replace_iter(MOD_ROOT, CHIMAERA_TASK_TEMPL, os.path.join(rel_path, name))

    def _copy_replace(self, MOD_ROOT, CHIMAERA_TASK_TEMPL, rel_path):
        """
        Copies a file from CHIMAERA_TASK_TEMPL to MOD_ROOT and renames
        TASK_TEMPL to the value of self.mod_name
        """
        with open(f'{CHIMAERA_TASK_TEMPL}/{rel_path}') as fp:
            text = fp.read()
        text = text.replace('MOD_NAME', self.mod_name)
        text = text.replace('chimaera_MOD_NAME', f'{self.namespace}_{self.mod_name}')
        rel_path = rel_path.replace('MOD_NAME', self.mod_name)
        with open(f'{MOD_ROOT}/{rel_path}', 'w') as fp:
            fp.write(text)

    def refresh_repo(self, MOD_REPO_DIR):
        print(f'Refreshing repository at {MOD_REPO_DIR}')
        self.load_repo_config(MOD_REPO_DIR)
        self.refresh_repo_mods(MOD_REPO_DIR)
        self.refresh_repo_cmake(MOD_REPO_DIR)

    def refresh_repo_mods(self, MOD_REPO_DIR):
        MOD_REPO_DIR = os.path.abspath(MOD_REPO_DIR)
        MOD_ROOTS = [os.path.join(MOD_REPO_DIR, item)
                      for item in os.listdir(MOD_REPO_DIR)]
        # Refresh all methods
        for MOD_ROOT in MOD_ROOTS:
            try:
                self.refresh_mod_tasks(MOD_ROOT)
            except Exception as e:
                print(e)
                pass

    def refresh_repo_cmake(self, MOD_REPO_DIR):
        MOD_REPO_DIR = os.path.abspath(MOD_REPO_DIR)
        camel_ns = to_camel_case(self.namespace) 
        MOD_NAMES = [MOD_NAME for MOD_NAME in os.listdir(MOD_REPO_DIR) 
                     if os.path.isdir(f'{MOD_REPO_DIR}/{MOD_NAME}')
                     and os.path.exists(f'{MOD_REPO_DIR}/{MOD_NAME}/chimaera_mod.yaml')]
        MOD_NAMES = sorted(MOD_NAMES) 
        subdirs = '\n'.join([f'add_subdirectory({MOD_NAME})' 
                             for MOD_NAME in MOD_NAMES])
        repo_cmake = BASE_REPO_CMAKE.format(namespace=self.namespace, subdirs=subdirs, camel_ns=camel_ns)
        with open(f'{MOD_REPO_DIR}/CMakeLists.txt', 'w') as fp:
            fp.write(repo_cmake)

    def load_method_defs(self):
        with open(self.METHODS_YAML) as fp:
            method_defs = yaml.load(fp, Loader=yaml.FullLoader)
        if method_defs is None:
            method_defs = {}
        self.method_defs = method_defs

    def scan_compiled_tasks(self):
        methods = {}
        if os.path.exists(self.OLD_TASKS_H):
            with open(self.OLD_TASKS_H) as fp:
                for line in fp:
                    match = re.search(r'struct\s+(.*)Task', line)
                    if not match:
                        continue
                    task_name = match.group(1)
                    method_name = f'k{task_name}'
                    if method_name not in self.method_defs:
                        continue
                    method_off = self.method_defs[method_name]
                    methods[method_name] = {
                        'val': method_off,
                        'compiled': True
                    }
        return methods

    def mark_new_methods_uncompiled(self):
        for method_name, method_off in self.method_defs.items():
                if method_off < 0:
                    continue
                if method_off <= 2:
                    # These are required methods
                    self.methods[method_name] = {
                        'val': method_off,
                        'compiled': True
                    }
                if method_off < 10:
                    # TODO(llogan): Allow bootstrapping special methods
                    continue
                if method_name in self.methods:
                    continue
                self.methods[method_name] = {
                    'val': method_off,
                    'compiled': False
                }

    def save_method_compile_staus(self):
        lines = []
        for method in self.sorted_methods:
            method_name = method[0]
            method_info = method[1]
            if 'compiled_tmp' in method_info:
                method_info['compiled'] = method_info['compiled_tmp']
                del method_info['compiled_tmp']
            if 'inserted' in method_info:
                del method_info['inserted']
            lines.append(f'{method_name}: {method_info}')
        with open(self.COMPILED_METHODS_YAML, 'w') as fp:
            fp.write('\n'.join(lines))

    def get_method_compile_status(self):
        self.load_method_defs()
        try:
            with open(self.COMPILED_METHODS_YAML) as fp:
                self.methods = yaml.load(fp, Loader=yaml.FullLoader)
        except:
            self.methods = None
        if self.methods is None:
            self.methods = self.scan_compiled_tasks()
        self.mark_new_methods_uncompiled()

    def refresh_mod_tasks(self, MOD_ROOT):
        """
        Refreshes autogenerated code in the task.
        """
        if not os.path.exists(f'{MOD_ROOT}/include'):
            return
        self.mod_name = os.path.basename(MOD_ROOT)

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
        self.get_method_compile_status() 
        self.sorted_methods = sorted(self.methods.items(), key=lambda x: x[1]['val'])

        # Refresh the files
        self.refresh_methods_h()
        self.refresh_lib_exec_h()
        self.refresh_tasks_h()
        self.refresh_client_h()
        self.refresh_runtime_cc()

        # Save compiled methods
        self.save_method_compile_staus()

    def refresh_methods_h(self):
        lines = []
        lines += [f'#ifndef {self.METHOD_MACRO}',
                  f'#define {self.METHOD_MACRO}',
                  '',
                  '/** The set of methods in the admin task */',
                  'struct Method : public TaskMethod {']
        for method_enum_name, method_info in self.sorted_methods:
            method_off = method_info['val']
            if method_off < 10:
                continue
            lines += [f'  TASK_METHOD_T {method_enum_name} = {method_off};']
        last_method_id = self.sorted_methods[-1][1]['val']
        lines += [f'  TASK_METHOD_T kCount = {last_method_id + 1};']
        lines += ['};', '', f'#endif  // {self.METHOD_MACRO}']
        with open(self.METHODS_H, 'w') as fp:
            fp.write('\n'.join(lines))

    def refresh_lib_exec_h(self):
        # Produce the MOD_NAME_lib_exec.h file
        lines = []
        lines += [f'#ifndef {self.LIB_EXEC_MACRO}',
                  f'#define {self.LIB_EXEC_MACRO}',
                  '']
        ## Create the Run method
        lines += ['/** Execute a task */',
                  'void Run(u32 method, Task *task, RunContext &rctx) override {',
                  '  switch (method) {']
        for method_enum_name, method_info in self.sorted_methods:
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
        for method_enum_name, method_info in self.sorted_methods:
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
        for method_enum_name, method_info in self.sorted_methods:
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
        for method_enum_name, method_info in self.sorted_methods:
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
        for method_enum_name, method_info in self.sorted_methods:
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
        for method_enum_name, method_info in self.sorted_methods:
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
        for method_enum_name, method_info in self.sorted_methods:
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
        for method_enum_name, method_info in self.sorted_methods:
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
        for method_enum_name, method_info in self.sorted_methods:
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

    def refresh_tasks_h(self):
        self.correct_lib_name()
        self.refresh_method_try_modes(
            self.OLD_TASKS_H, 
            self.NEW_TASKS_H, task_template)

    def correct_lib_name(self):
        with open(self.OLD_TASKS_H) as fp:
            content = fp.read()
        # Replace lib_name_ with namespace_mod_name version
        old_text = f'lib_name_ = "{self.mod_name}"'
        new_text = f'lib_name_ = "{self.namespace}_{self.mod_name}"'
        if old_text in content:
            print(f"Fixing lib_name_ from {self.mod_name} to {self.namespace}_{self.mod_name}")
            content = content.replace(old_text, new_text)
            with open(self.OLD_TASKS_H, 'w') as fp:
                fp.write(content)

    def refresh_client_h(self):
        self.refresh_method_try_modes(
            self.OLD_CLIENT_H, 
            self.NEW_CLIENT_H, client_method_template)

    def refresh_runtime_cc(self):
        self.refresh_method_try_modes(
            self.OLD_RUNTIME_CC, 
            self.NEW_RUNTIME_CC, runtime_method_template)

    def refresh_method_try_modes(self, orig_path, new_path, tmpl_name):
        with open(orig_path) as fp:
            self.content = fp.readlines()
        self.tmpl_name = tmpl_name
        did_edits = False

        # Insert based on macros
        self.chi_ends = self.get_chi_end_map(self.content)
        self.pending_chi_ends = {}
        self.sorted_off = -1
        for method_enum_name, method_info in self.sorted_methods:
            self.sorted_off += 1
            self.method_enum_name = method_enum_name
            self.method_info = method_info
            self.method_name = method_enum_name.replace('k', '', 1)
            self.task_name = self.method_name + "Task"
            if self.refresh_insert():
                did_edits = True
                continue
            if self.refresh_append():
                did_edits = True
                continue

        # Write edited data
        if did_edits:
            self.refresh_insert_commit()
            with open(orig_path, 'w') as fp:
                fp.write(''.join(self.content))
        else:
            self.refresh_tmpfile(new_path, tmpl_name)

    def get_method_name(self, sorted_off):
        method_enum_name = self.sorted_methods[sorted_off][0]
        method_name = method_enum_name.replace('k', '', 1)
        return method_name
    
    def get_chi_end_map(self, content):
        """Find lines with CHI_END macro and map method_name to line number"""
        chi_end_pattern = r'CHI_END\((.*?)\)'
        method_map = {}
        for i, line in enumerate(content):
            match = re.search(chi_end_pattern, line)
            if match:
                method_name = match.group(1)
                method_map[method_name] = i
                continue
            match = 'CHI_AUTOGEN_METHODS' in line
            if match:
                method_map['CHI_AUTOGEN_METHODS'] = i
        return method_map

    def refresh_insert_commit(self):
        # Sort pending chi ends by insert position in descending order 
        sorted_pending = sorted(self.pending_chi_ends.values(), 
                               key=lambda x: x['insert'],
                               reverse=True)

        # Insert templates at sorted positions
        for info in sorted_pending:
            start_line = info['insert'] 
            if start_line == -100:
                break
            tmpls = info['tmpl']
            self.content = self.content[0:start_line] + tmpls + self.content[start_line:]

    def refresh_insert(self):
        """
        Inserts non-compiled methods into the runtime
        file at the ideal location
        """
        self.method_info['inserted'] = False
        method_off = self.method_info['val']
        if method_off < 0 or self.method_info['compiled']:
            return False
        tmpl = self.make_tmpl(self.tmpl_name, self.task_name, self.method_name, self.method_enum_name)
        tmpl = '\n' + tmpl
        # Find CHI_END tag to insert after
        prior_method_name = self.get_method_name(self.sorted_off - 1)
        if prior_method_name in self.chi_ends:
            self.pending_chi_ends[self.method_name] = {
                'insert': self.chi_ends[prior_method_name] + 1,
                'tmpl': [tmpl],
            }
        elif prior_method_name in self.pending_chi_ends:
            tmpls = self.pending_chi_ends[prior_method_name]['tmpl']
            tmpls.append(tmpl)
            self.pending_chi_ends[self.method_name] = {
                'insert': -100,
                'tmpl': tmpls,
            }
        else:
            return False
        self.method_info['compiled_tmp'] = True
        self.method_info['inserted'] = True
        return True
        
    def refresh_append(self):
        """
        Appends non-compiled methods to the end of the
        runtime and marks them compiled
        """
        method_off = self.method_info['val']
        if method_off < 0 or self.method_info['compiled'] or self.method_info['inserted']:
            return False
        tmpl = self.make_tmpl(self.tmpl_name, self.task_name, self.method_name, self.method_enum_name)
        # Find CHI_AUTOGEN_METHODS tag and insert before
        if 'CHI_AUTOGEN_METHODS' not in self.chi_ends:
            return False
        start_line = self.chi_ends['CHI_AUTOGEN_METHODS']
        self.content.insert(start_line, tmpl + '\n')
        self.chi_ends[self.method_name] = start_line
        self.method_info['compiled_tmp'] = True
        return True

    def refresh_tmpfile(self, new_path, tmpl_name):
        """
        Generates a temporary file with new runtime methods
        to copy-paste from.
        """
        lines = []
        for method_enum_name, method_info in self.sorted_methods:
            method_off = method_info['val']
            if method_off < 0:
                continue
            method_name = method_enum_name.replace('k', '', 1)
            task_name = method_name + "Task"
            tmpl = self.make_tmpl(tmpl_name, task_name, method_name, method_enum_name)
            lines += [tmpl]
        with open(new_path, 'w') as fp:
            fp.write(''.join(lines))

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

    def make_tmpl(self, tmpl_str, task_name, method_name, method_enum_name):
        tmpl = tmpl_str.replace('##task_name##', task_name) \
            .replace('##method_name##', method_name) \
            .replace('##method_enum_name##', method_enum_name)
        tmpl = tmpl.strip() + '\n'
        return tmpl
