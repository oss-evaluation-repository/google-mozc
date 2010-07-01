# -*- coding: utf-8 -*-
# Copyright 2010, Google Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#     * Neither the name of Google Inc. nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Script building Mozc.

Typical usage:

  % python build_mozc.py gyp
  % python build_mozc.py build_tools -c Release
  % python build_mozc.py build base/base.gyp:base
"""

__author__ = "komatsu"

import glob
import logging
import optparse
import os
import re
import shutil
import subprocess
import sys

from build_tools import mozc_version


SRC_DIR = '.'
EXTRA_SRC_DIR = '..'

sys.path.append(SRC_DIR)


def IsWindows():
  """Returns true if the platform is Windows."""
  return os.name == 'nt'


def IsMac():
  """Returns true if the platform is Mac."""
  return os.name == 'posix' and os.uname()[0] == 'Darwin'


def IsLinux():
  """Returns true if the platform is Linux."""
  return os.name == 'posix' and os.uname()[0] == 'Linux'


# TODO(yukawa): Move this function to util.py (b/2715400)
def GetNumberOfProcessors():
  """Returns the number of processors available.

  Returns:
    An integer corresponding to the number of processors available in
    Windows, Mac, and Linux.  In other platforms, returns 1.
  """
  if IsWindows():
    return int(os.environ['NUMBER_OF_PROCESSORS'])
  elif IsMac():
    commands = ['sysctl', '-n', 'hw.ncpu']
    process = subprocess.Popen(commands, stdout=subprocess.PIPE)
    return int(process.communicate()[0])
  elif IsLinux():
    # Count the number of 'vendor_id' in /proc/cpuinfo, assuming that
    # each line corresponds to one logical CPU.
    file = open('/proc/cpuinfo', 'r')
    count = len([line for line in file if line.find('vendor_id') != -1])
    file.close()
    return count
  else:
    return 1


def GetGeneratorName():
  """Gets the generator name based on the platform."""
  generator = 'make'
  if IsWindows():
    generator = 'msvs'
  elif IsMac():
    generator = 'xcode'
  return generator


def GenerateVersionFile(version_template_path, version_path):
  """Reads the version template file and stores it into version_path.

  This doesn't update the "version_path" if nothing will be changed to
  reduce unnecessary build caused by file timestamp.

  Args:
    version_template_path: a file name which contains the template of version.
    version_path: a file name to be stored the official version.
  """
  version = mozc_version.MozcVersion(version_template_path, expand_daily=True)
  version_definition = version.GetVersionInFormat(
      'MAJOR=@MAJOR@\nMINOR=@MINOR@\nBUILD=@BUILD@\nREVISION=@REVISION@\n')
  old_content = ''
  if os.path.exists(version_path):
    # if the target file already exists, need to check the necessity of update.
    old_content = open(version_path).read()

  if version_definition != old_content:
    open(version_path, 'w').write(version_definition)


def GetVersionFileNames(options):
  """Gets the (template of version file, version file) pair."""
  template_path = '%s/%s' % (SRC_DIR, options.version_file)
  version_path = '%s/mozc_version.txt' % SRC_DIR
  return (template_path, version_path)


def GetGypFileNames():
  """Gets the list of gyp file names."""
  gyp_file_names = []
  mozc_top_level_names = glob.glob('%s/*' % SRC_DIR)
  # Exclude the gyp directory where we have special gyp files like
  # breakpad.gyp that we should exclude.
  mozc_top_level_names = [x for x in mozc_top_level_names if
                          os.path.basename(x) != 'gyp']
  for name in mozc_top_level_names:
    gyp_file_names.extend(glob.glob(name + '/*.gyp'))
  gyp_file_names.extend(glob.glob('%s/build_tools/*/*.gyp' % SRC_DIR))
  # Include subdirectory of dictionary
  gyp_file_names.append(
      '%s/dictionary/file/dictionary_file.gyp' % SRC_DIR)
  gyp_file_names.append(
      '%s/dictionary/system/system_dictionary.gyp' % SRC_DIR)
  # Include subdirectory of win32 and breakpad for Windows
  if IsWindows():
    gyp_file_names.extend(glob.glob('%s/win32/*/*.gyp' % SRC_DIR))
    gyp_file_names.extend(glob.glob('third_party/breakpad/*.gyp'))
    gyp_file_names.append('third_party/mozc/sandbox/sandbox.gyp')
  elif IsLinux():
    gyp_file_names.extend(glob.glob('%s/unix/*/*.gyp' % SRC_DIR))
    # Add ibus.gyp if ibus is installed.
    # Ubuntu 8.04 (Hardy) does not contain ibus package.
    try:
      RunOrDie(['pkg-config', '--exists', 'ibus-1.0'])
    except RunOrDieError:
      gyp_file_names.remove('%s/unix/ibus/ibus.gyp' % SRC_DIR)
    # Add gui.gyp if Qt libraries are installed.
    try:
      RunOrDie(['pkg-config', '--exists', 'QtCore', 'QtGui'])
    except RunOrDieError:
      gyp_file_names.remove('%s/gui/gui.gyp' % SRC_DIR)
    # Add scim.gyp if SCIM is installed.
    try:
      RunOrDie(['pkg-config', '--exists', 'scim'])
    except RunOrDieError:
      gyp_file_names.remove('%s/unix/scim/scim.gyp' % SRC_DIR)
  gyp_file_names.extend(glob.glob('third_party/rx/*.gyp'))
  gyp_file_names.sort()
  return gyp_file_names


def RemoveFile(file_name):
  """Removes the specified file."""
  if not os.path.isfile(file_name):
    return  # Do nothing if not exist.
  if IsWindows():
    # Read-only files cannot be deleted on Windows.
    os.chmod(file_name, 0700)
  print 'Removing file: %s' % file_name
  os.unlink(file_name)


def CopyFile(source, destination):
  """Copies a file to the destination. Remove an old version if needed."""
  if os.path.isfile(destination):  # Remove the old one if exists.
    RemoveFile(destination)
  print 'Copying file to: %s' % destination
  shutil.copy(source, destination)


def RecursiveRemoveDirectory(directory):
  """Removes the specified directory recursively."""
  if os.path.isdir(directory):
    print 'Removing directory: %s' % directory
    if IsWindows():
      # Use RD because shutil.rmtree fails when the directory is readonly.
      RunOrDie(['CMD.exe', '/C', 'RD', '/S', '/Q',
                os.path.normpath(directory)])
    else:
      shutil.rmtree(directory, ignore_errors=True)


def CleanBuildFilesAndDirectories():
  """Cleans build files and directories."""
  # File and directory names to be removed.
  file_names = []
  directory_names = []

  # Collect stuff in the gyp directories.
  gyp_directory_names = [os.path.dirname(f) for f in GetGypFileNames()]
  for gyp_directory_name in gyp_directory_names:
    if IsWindows():
      for pattern in ['*.rules', '*.sln', '*.vcproj']:
        file_names.extend(glob.glob(os.path.join(gyp_directory_name,
                                                 pattern)))
      for build_type in ['Debug', 'Optimize', 'Release']:
        directory_names.append(os.path.join(gyp_directory_name,
                                            build_type))
    elif IsMac():
      directory_names.extend(glob.glob(os.path.join(gyp_directory_name,
                                                    '*.xcodeproj')))
    elif IsLinux():
      file_names.extend(glob.glob(os.path.join(gyp_directory_name,
                                               '*.target.mk')))
  file_names.append('%s/mozc_version.txt' % SRC_DIR)
  file_names.append('third_party/rx/rx.gyp')
  # Collect stuff in the top-level directory.
  directory_names.append('mozc_build_tools')
  if IsMac():
    directory_names.append('out_mac')
  elif IsLinux():
    file_names.append('Makefile')
    directory_names.append('out_linux')
  elif IsWindows():
    file_names.append('third_party/breakpad/breakpad.gyp')
    directory_names.append('out_win')
  # Remove files.
  for file_name in file_names:
    RemoveFile(file_name)
  # Remove directories.
  for directory_name in directory_names:
    RecursiveRemoveDirectory(directory_name)


def GetTopLevelSourceDirectoryName():
  """Gets the top level source directory name."""
  if SRC_DIR == '.':
    return SRC_DIR
  script_file_directory_name = os.path.dirname(sys.argv[0])
  num_components = len(SRC_DIR.split('/'))
  dots = ['..'] * num_components
  return os.path.join(script_file_directory_name, '/'.join(dots))


def MoveToTopLevelSourceDirectory():
  """Moves to the build top level directory."""
  os.chdir(GetTopLevelSourceDirectoryName())


def GetGypSvnUrl(deps_file_name):
  """Get the GYP SVN URL from DEPS file."""
  contents = file(deps_file_name).read()
  match = re.search(r'"(http://gyp\.googlecode\.com.*?)@', contents)
  if match:
    base_url = match.group(1)
    match = re.search(r'"gyp_revision":\s+"(\d+)"', contents)
    if match:
      revision = match.group(1)
      return '%s@%s' % (base_url, revision)
  else:
    PrintErrorAndExit('GYP URL not found in %s:' % deps_file_name)


def GypMain(deps_file_name):
  """The main function for the 'gyp' command."""
  options = ParseGypOptions()
  # Copy rx.gyp to the third party directory.
  CopyFile('%s/gyp/rx.gyp' % SRC_DIR,
           'third_party/rx/rx.gyp')
  # Copy breakpad.gyp to the third party directory, if necessary.
  if IsWindows():
    CopyFile('%s/gyp/breakpad.gyp' % SRC_DIR,
             'third_party/breakpad/breakpad.gyp')

  # Determine the generator name.
  generator = GetGeneratorName()
  os.environ['GYP_GENERATORS'] = generator
  print 'Build tool: %s' % generator

  # Get and show the list of .gyp file names.
  gyp_file_names = GetGypFileNames()
  print 'GYP files:'
  for file_name in gyp_file_names:
    print '- %s' % file_name
  # We use the one in third_party/gyp
  gyp_script = '%s/gyp' % options.gypdir
  # If we don't have a copy of gyp, download it.
  if not os.path.isfile(gyp_script):
    # SVN creates mozc_build_tools directory if it's not present.
    gyp_svn_url = GetGypSvnUrl(deps_file_name)
    RunOrDie(['svn', 'checkout', gyp_svn_url, options.gypdir])
  # Run GYP.
  print 'Running GYP...'
  command_line = [sys.executable, gyp_script,
                  '--no-circular-check',
                  '--depth=.',
                  '--include=%s/gyp/common.gypi' % SRC_DIR]
  if options.onepass:
    command_line.extend(['-D', 'two_pass_build=0'])
  command_line.extend(gyp_file_names)

  if options.branding:
    command_line.extend(['-D', 'branding=%s' % options.branding])
  if options.noqt:
    command_line.extend(['-D', 'use_qt=NO'])
  if options.coverage:
    command_line.extend(['-D', 'coverage=1'])

  # Check the version and determine if the building version is
  # dev-channel or not.
  (template_path, unused_version_path) = GetVersionFileNames(options)
  version = mozc_version.MozcVersion(template_path, expand_daily=False)
  if options.channel_dev or version.IsDevChannel():
    command_line.extend(['-D', 'channel_dev=1'])


  RunOrDie(command_line)


  # Done!
  print 'Done'


def ListAllTests():
  """List all existing tests in the gyp files.

  Returns:
    a list of dict which contains 'target' and 'size'
  """
  all_tests = []
  # Here we directly load the .gyp files.
  # TODO(mukai): use GYP as a library to load gyp files correctly with
  # variable expansions.
  gyp_file_names = GetGypFileNames()
  for file_name in gyp_file_names:
    if not os.path.exists(file_name):
      logging.warning('gyp file %s is not found', file_name)
      continue
    gyp_file = open(file_name)
    gyp_map = eval(open(file_name).read())
    if not isinstance(gyp_map, dict):
      logging.warning('Not a valid gyp file: %s', file_name)
      continue
    if (not gyp_map.has_key('targets') or
        not isinstance(gyp_map['targets'], list)):
      logging.warning('gyp does not have a valid targets: %s', file_name)
      continue
    for target in gyp_map['targets']:
      if not target.has_key('target_name'):
        logging.warning('not a valid target in %s', file_name)
        continue
      if not target['target_name'].endswith('_test'):
        # Not a test target
        continue
      if (not target.has_key('variables') or
          not target['variables'].has_key('test_size')):
        logging.warning('test target does not have test_size: %s:%s',
                        file_name,target['target_name'])
        continue
      all_tests.append(
          {'target': '%s:%s' % (file_name, target['target_name']),
           'size': target['variables']['test_size']})
  return all_tests


def RunTests(targets, configuration, calculate_coverage):
  """Run built tests actually.

  Args:
    targets: a list of 'gyp_file:test_target'
    configuration: build configuration ('Release' or 'Debug')
    calculate_coverage: True if runtests calculates the test coverage.
  """
  # Currently we don't check calculate at all -- just run tests.
  if IsMac():
    base_path = os.path.join('out_mac', configuration)
  elif IsLinux():
    base_path = os.path.join('out_linux', configuration)
  elif IsWindows():
    base_path = os.path.join('out_win', configuration)
  else:
    logging.error('Unsupported platform: %s', os.name)
    return

  failed_tests = []
  for target in targets:
    logging.info('running %s...', target)

    index = target.find(':')
    if index == -1:
      print "Invalid target name:", target
      failed_tests.append(target)
      continue
    gyp_file = target[0:index]
    binary_name = target[(index+1):]

    try:
      RunOrDie([os.path.join(base_path, binary_name)])
    except RunOrDieError, e:
      print e
      failed_tests.append(target)
  if len(failed_tests) > 0:
    raise RunOrDieError('\n'.join(['following tests failed'] + failed_tests))


def RuntestsMain(original_directory_name):
  """The main function for 'runtests' command."""
  (options, args) = ParseRuntestsOptions()

  # extracting test targets and build flags.  To avoid parsing build
  # options from ParseRuntestsOptions(), user has to specify the test
  # targets at first, and then add '--' and build flags.  Although
  # optparse removes the '--' argument itself, the first element of
  # build options has to start with '-' character because they are
  # flags.
  # ex: runtests foo.gyp:foo_test bar.gyp:bar_test -- -c Release
  #   => ['foo.gyp:foo_test', 'bar.gyp:bar_test', '-c', 'Release']
  # here 'foo.gyp:foo_test' and 'bar.gyp:bar_test' are test targets
  # and '-c' and 'Release' are build options.
  targets = []
  build_options = []
  for i in xrange(len(args)):
    if args[i].startswith('-'):
      # starting with build options
      build_options = args[i:]
      break
    targets.append(args[i])

  # configuration flag is shared among runtests options and build
  # options.
  if options.configuration:
    build_options.extend(['-c', options.configuration])

  alltests = ListAllTests()
  # filter out target which is not a test actually
  all_test_targets = [test['target'] for test in alltests]
  test_targets = []
  for target in targets:
    if not target in all_test_targets:
      logging.warning('specified target %s is not a test target', target)
      continue
    test_targets.append(target)

  # the test targets not specified.  Find all tests which matches the
  # specified size.
  if not test_targets:
    test_targets = [test['target'] for test in alltests
                    if test['size'] == options.test_size]

  # Build the test targets
  sys.argv = [sys.argv[0]] + build_options + test_targets
  BuildMain(original_directory_name)

  # Run tests actually
  RunTests(test_targets, options.configuration, options.calculate_coverage)


def CleanMain():
  """The main function for the 'clean' command."""
  CleanBuildFilesAndDirectories()


class RunOrDieError(StandardError):
  """The exception class for RunOrDie."""

  def __init__(self, message):
    StandardError.__init__(self, message)


def RunOrDie(argv):
  """Run the command, or die if it failed."""

  # Rest are the target program name and the parameters, but we special
  # case if the target program name ends with '.py'
  if argv[0].endswith('.py'):
    argv.insert(0, sys.executable)  # Inject the python interpreter path.
  # We don't capture stdout and stderr from Popen. The output will just
  # be emitted to a terminal or console.
  print 'Running: ' + ' '.join(argv)
  process = subprocess.Popen(argv)

  if process.wait() != 0:
    raise RunOrDieError('\n'.join(['',
                                   '==========',
                                   ' ERROR: %s' % ' '.join(argv),
                                   '==========']))


def PrintErrorAndExit(error_message):
  """Prints the error message and exists."""
  print error_message
  sys.exit(1)


def ParseGypOptions():
  """Parse command line options for the gyp command."""
  parser = optparse.OptionParser(usage='Usage: %prog gyp [options]')
  parser.add_option('--onepass', '-1', dest='onepass', action='store_true',
                    default=False, help='build mozc in one pass. '
                    'Not recommended for Debug build.')
  parser.add_option('--branding', dest='branding', default='Mozc')
  parser.add_option('--gypdir', dest='gypdir', default='third_party/gyp')
  parser.add_option('--noqt', action='store_true', dest='noqt', default=False)
  parser.add_option('--coverage', action='store_true', dest='coverage',
                    help='use code coverage analysis build options',
                    default=False)
  parser.add_option('--channel_dev', action='store_true', dest='channel_dev',
                    help='Specify this to build dev channel explicitly',
                    default=False)
  parser.add_option('--version_file', dest='version_file',
                    help='use the specified version template file',
                    default='mozc_version_template.txt')
  (options, unused_args) = parser.parse_args()
  return options


def ParseBuildOptions():
  """Parse command line options for the build command."""
  parser = optparse.OptionParser(usage='Usage: %prog build [options]')
  parser.add_option('--jobs', '-j', dest='jobs', default='4', metavar='N',
                    help='run jobs in parallel')
  parser.add_option('--configuration', '-c', dest='configuration',
                    default='Debug', help='specify the build configuration.')
  parser.add_option('--build_base', dest='build_base',
                    help='specify the base directory of the built binaries.')
  parser.add_option('--noqt', action='store_true', dest='noqt', default=False)
  parser.add_option('--version_file', dest='version_file',
                    help='use the specified version template file',
                    default='mozc_version_template.txt')
  if IsWindows():
    parser.add_option('--platform', '-p', dest='platform',
                      default='Win32',
                      help='specify the target plaform: [Win32|x64]')
  # default Qt dir to support the current build procedure for Debian.
  default_qtdir = '/usr/local/Trolltech/Qt-4.5.2'
  if IsWindows():
    default_qtdir = None
  parser.add_option('--qtdir', dest='qtdir',
                    default=os.getenv('QTDIR', default_qtdir),
                    help='Qt base directory to be used.')

  (options, args) = parser.parse_args()

  targets = args
  if not targets:
    PrintErrorAndExit('No build target is specified.')

  return (options, args)


def ParseRuntestsOptions():
  """Parse command line options for the runtests command."""
  parser = optparse.OptionParser(
      usage='Usage: %prog runtests [options] [test_targets] [-- build options]')
  parser.add_option('--test_size', dest='test_size', default='small')
  parser.add_option('--calculate_coverage', dest='calculate_coverage',
                    default=False, action='store_true',
                    help='specify if you want to calculate test coverage.')
  parser.add_option('--configuration', '-c', dest='configuration',
                    default='Debug', help='specify the build configuration.')

  (options, args) = parser.parse_args()

  return (options, args)


def ParseTarget(target):
  """Parses the target string."""
  if not ':' in target:
    PrintErrorAndExit('Invalid target: ' + target)
  (gyp_file_name, target_name) = target.split(':')
  return (gyp_file_name, target_name)


def BuildOnLinux(options, targets):
  """Build the targets on Linux."""
  target_names = []
  for target in targets:
    (unused_gyp_file_name, target_name) = ParseTarget(target)
    target_names.append(target_name)

  make_command = os.getenv('BUILD_COMMAND', 'make')
  # flags for building in Chrome OS chroot environment
  envvars = [
      'CFLAGS',
      'CXXFLAGS',
      'CXX',
      'CC',
      'AR',
      'AS',
      'RANLIB',
      'LD',
  ]
  for envvar in envvars:
    if envvar in os.environ:
      os.environ[envvar] = os.getenv(envvar)

  # set output directory
  os.environ['builddir_name'] = 'out_linux'

  build_args = ['-j%s' % options.jobs, 'BUILDTYPE=%s' % options.configuration]
  if options.build_base:
    build_args.append('builddir_name=%s' % options.build_base)

  RunOrDie([make_command] + build_args + target_names)


def CheckFileOrDie(file_name):
  """Check the file exists or dies if not."""
  if not os.path.isfile(file_name):
    PrintErrorAndExit('No such file: ' + file_name)


def GetRelpath(path, start):
  """Return a relative path to |path| from |start|."""
  # NOTE: Python 2.6 provides os.path.relpath, which has almost the same
  # functionality as this function. Since Python 2.6 is not the internal
  # official version, we reimplement it.
  path_list = os.path.abspath(os.path.normpath(path)).split(os.sep)
  start_list = os.path.abspath(os.path.normpath(start)).split(os.sep)

  common_prefix_count = 0
  for i in range(0, min(len(path_list), len(start_list))):
    if path_list[i] != start_list[i]:
      break
    common_prefix_count += 1

  return os.sep.join(['..'] * (len(start_list) - common_prefix_count) +
                     path_list[common_prefix_count:])


def BuildOnMac(options, targets, original_directory_name):
  """Build the targets on Mac."""
  # For some reason, xcodebuild does not accept absolute path names for
  # the -project parameter. Convert the original_directory_name to a
  # relative path from the build top level directory.
  original_directory_relpath = GetRelpath(original_directory_name, os.getcwd())
  if options.build_base:
    sym_root = options.build_base
  else:
    sym_root = os.path.join(os.getcwd(), 'out_mac')
  for target in targets:
    (gyp_file_name, target_name) = ParseTarget(target)
    gyp_file_name = os.path.join(original_directory_relpath, gyp_file_name)
    CheckFileOrDie(gyp_file_name)
    (xcode_base_name, _) = os.path.splitext(gyp_file_name)
    RunOrDie(['xcodebuild',
              '-project', '%s.xcodeproj' % xcode_base_name,
              '-configuration', options.configuration,
              '-target', target_name,
              '-parallelizeTargets',
              'SYMROOT=%s' % sym_root,
              'BUILD_WITH_GYP=1'])


def LocateVCBuildDir():
  """Locate the directory where vcbuild.exe exists.

  Returns:
    A string of absolute directory path where vcbuild.exe exists.
  """
  if not IsWindows():
    PrintErrorAndExit('vcbuild.exe is not supported on this platform')

  # TODO(yukawa): Implement this.
  PrintErrorAndExit('Failed to locate vcbuild.exe')


def BuildOnWindows(options, targets, original_directory_name):
  """Build the target on Windows."""
  # TODO(yukawa): make a python module to set up environment for vcbuild.
  abs_vcbuild_dir = LocateVCBuildDir()

  CheckFileOrDie(os.path.join(abs_vcbuild_dir, 'vcbuild.exe'))

  if os.getenv('PATH'):
    os.environ['PATH'] = os.pathsep.join([abs_vcbuild_dir, os.getenv('PATH')])
  else:
    os.environ['PATH'] = abs_vcbuild_dir


  os.environ['INCLUDE'] = ''
  os.environ['LIB'] = ''
  os.environ['LIBPATH'] = ''

  for target in targets:
    # TODO(yukawa): target name is currently ignored.
    (gyp_file_name, _) = ParseTarget(target)
    gyp_file_name = os.path.join(original_directory_name, gyp_file_name)
    CheckFileOrDie(gyp_file_name)
    (sln_base_name, _) = os.path.splitext(gyp_file_name)
    sln_file_path = os.path.abspath('%s.sln' % sln_base_name)
    build_concurrency = GetNumberOfProcessors() * 2
    # To use different toolsets for vcbuild, we set %PATH%, %INCLUDE%, %LIB%,
    # %LIBPATH% and specify /useenv option here.  See the following article
    # for details.
    # http://blogs.msdn.com/vcblog/archive/2007/12/30/using-different-toolsets-
    #   for-vc-build.aspx
    RunOrDie(['vcbuild',
              '/useenv',  # Use %PATH%, %INCLUDE%, %LIB%, %LIBPATH%
              '/M%d' % build_concurrency,  # Use concurrent build
              '/time',    # Show build time
              '/platform:%s' % options.platform,
              sln_file_path,
              '%s|%s' % (options.configuration, options.platform)])


def BuildMain(original_directory_name):
  """The main function for the 'build' command."""
  (options, targets) = ParseBuildOptions()

  # Generate a version definition file.
  print 'Generating version definition file...'
  (template_path, version_path) = GetVersionFileNames(options)
  GenerateVersionFile(template_path, version_path)

  if not options.noqt:
    # Set $QTDIR for mozc_tool
    if options.qtdir:
      if not options.qtdir.startswith('/'):
        options.qtdir = os.path.join(os.getcwd(), options.qtdir)
      print 'export $QTDIR = %s' % options.qtdir
      os.environ['QTDIR'] = options.qtdir

  if IsMac():
    BuildOnMac(options, targets, original_directory_name)
  elif IsLinux():
    BuildOnLinux(options, targets)
  elif IsWindows():
    BuildOnWindows(options, targets, original_directory_name)
  else:
    print 'Unsupported platform: ', os.name


def BuildToolsMain(original_directory_name):
  """The main function for 'build_tools' command."""
  build_tools_dir = os.path.join(GetRelpath(os.getcwd(),
                                            original_directory_name),
                                 '%s/build_tools' % SRC_DIR)
  # build targets in this order
  gyp_files = [
      os.path.join(build_tools_dir, 'primitive_tools', 'primitive_tools.gyp'),
      os.path.join(build_tools_dir, 'build_tools.gyp')
      ]

  for gyp_file in gyp_files:
    (target, _) = os.path.splitext(os.path.basename(gyp_file))
    sys.argv.append('%s:%s' % (gyp_file, target))
    BuildMain(original_directory_name)
    sys.argv.pop()


def ShowHelpAndExit():
  """Shows the help message."""
  print 'Usage: build_mozc.py COMMAND [ARGS]'
  print 'Commands: '
  print '  gyp          Generate project files.'
  print '  build        Build the specified target.'
  print '  build_tools  Build tools used by the build command.'
  print '  runtests     Build all tests and run them.'
  print '  clean        Clean all the build files and directories.'
  print ''
  print 'See also the comment in the script for typical usage.'
  sys.exit(1)


def main():
  if len(sys.argv) < 2:
    ShowHelpAndExit()

  # DEPS files should exist in the same directory of the script.
  deps_file_name = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),
                                                'DEPS'))
  # Remember the original current directory name.
  original_directory_name = os.getcwd()
  # Move to the top level source directory only once since os.chdir
  # affects functions in os.path and that causes troublesome errors.
  MoveToTopLevelSourceDirectory()

  command = sys.argv[1]
  del(sys.argv[1])  # Delete the command.
  if command == 'build':
    BuildMain(original_directory_name)
  elif command == 'build_tools':
    BuildToolsMain(original_directory_name)
  elif command == 'clean':
    CleanMain()
  elif command == 'gyp':
    GypMain(deps_file_name)
  elif command == 'runtests':
    RuntestsMain(original_directory_name)
  else:
    print 'Unknown command: ' + command
    ShowHelpAndExit()

if __name__ == '__main__':
  main()
