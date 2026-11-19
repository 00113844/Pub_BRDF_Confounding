project(
  'pyprosail',
  'c', 'fortran',
  version: '1.0.2+brdf.1',
  meson_version: '>= 1.1.0',
  default_options: ['buildtype=release', 'b_ndebug=if-release'],
)

py = import('python').find_installation(pure: false)
py_dep = py.dependency()

incdir_numpy = run_command(py,
  ['-c', 'import numpy; print(numpy.get_include())'],
  check: true,
).stdout().strip()
incdir_f2py = run_command(py,
  ['-c', 'import numpy.f2py; print(numpy.f2py.get_include())'],
  check: true,
).stdout().strip()
inc_np = include_directories(incdir_numpy, incdir_f2py)

# The signature file is hand-written, so f2py emits exactly one C file.
prosail_module_c = custom_target('_prosail_modelmodule.c',
  input: 'src/fortran/_prosail_model.pyf',
  output: '_prosail_modelmodule.c',
  command: [py, '-m', 'numpy.f2py', '@INPUT@', '--build-dir', '@OUTDIR@'],
)

# Order matters: modules first so .mod files exist for the routines using them.
fortran_sources = files(
  'src/fortran/MODULE_PRO4SAIL.f90',
  'src/fortran/dataSpec_P5B.f90',
  'src/fortran/LIDF.f90',
  'src/fortran/dladgen.f',
  'src/fortran/PRO4SAIL.f90',
  'src/fortran/prospect_5B.f90',
  'src/fortran/tav_abs.f90',
  'src/fortran/volscatt.f90',
  'src/fortran/PyPROSAIL.f90',
)

# Link the gfortran runtime statically on Windows so the extension does not
# depend on MinGW DLLs being on PATH at import time.
link_args = []
if host_machine.system() == 'windows'
  link_args += ['-static', '-static-libgcc', '-static-libgfortran']
endif

py.extension_module('_prosail_model',
  [prosail_module_c, incdir_f2py / 'fortranobject.c', fortran_sources],
  include_directories: inc_np,
  dependencies: py_dep,
  link_args: link_args,
  link_language: 'fortran',
  subdir: 'pyprosail',
  install: true,
)

py.install_sources('pyprosail/__init__.py', subdir: 'pyprosail')
