#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
#############################################################
#                                                           #
#      Copyright @ 2013 - 2017 Dashingsoft corp.            #
#      All rights reserved.                                 #
#                                                           #
#      pyarmor                                              #
#                                                           #
#      Version: 1.7.0 - 3.2.0                               #
#                                                           #
#############################################################
#
#
#  @File: benchmark.py
#
#  @Author: Jondy Zhao(jondy.zhao@gmail.com)
#
#  @Create Date: 2017/11/21
#
#  @Description:
#
#   Check performance of pyarmor.
#
import logging
import os
import shutil
import sys
import subprocess
import tempfile
import time

from ctypes import cdll, c_int, c_void_p, py_object, pythonapi, PYFUNCTYPE
from ctypes.util import find_library

def metricmethod(func):
    def wrap(*args, **kwargs):
        t1 = time.clock()
        result = func(*args, **kwargs)
        t2 = time.clock()
        logging.info('%s: %s ms', func.__name__, (t2 - t1) * 1000)
        return result
    return wrap

def make_test_script(filename):
    lines = [
        'def empty():',
        '  return 0',
        '',
        'def one_thousand():',
        '  if False:',
        '    i = 0',
    ]
    lines.extend(['    i += 1'] * 100)
    lines.append('\n  return 1000\n')
    lines.extend(['def ten_thousand():',
                  '  if False:',
                  '    i = 0'])
    lines.extend(['    i += 1'] * 1000)
    lines.append('\n  return 10000\n')

    with open(filename, 'w') as f:
        f.write('\n'.join(lines))

@metricmethod
def verify_license(pytransform):
    try:
        prototype = PYFUNCTYPE(py_object)
        dlfunc = prototype(('get_registration_code', pytransform))
        code = dlfunc()
    except Exception:
        logging.warning('Verify license failed')
        code = ''
    return code

@metricmethod
def init_pytransform(pytransform):
    major, minor = sys.version_info[0:2]
    # Python2.5 no sys.maxsize but sys.maxint
    # bitness = 64 if sys.maxsize > 2**32 else 32
    prototype = PYFUNCTYPE(c_int, c_int, c_int, c_void_p)
    init_module = prototype(('init_module', pytransform))
    init_module(major, minor, pythonapi._handle)

    prototype = PYFUNCTYPE(c_int, c_int, c_int, c_int)
    init_runtime = prototype(('init_runtime', pytransform))
    init_runtime(0, 0, 0, 0)

@metricmethod
def load_pytransform():
    try:
        if sys.platform.startswith('linux'):
            m = cdll.LoadLibrary(os.path.abspath('_pytransform.so'))
            m.set_option('libc'.encode(), find_library('c').encode())
        elif sys.platform.startswith('darwin'):
            m = cdll.LoadLibrary('_pytransform.dylib')
        else:
            m = cdll.LoadLibrary('_pytransform.dll')
    except Exception:
        raise RuntimeError('Could not load library _pytransform.')
    return m

@metricmethod
def run_empty_obfuscated_code_object(foo):
    return foo.empty()

@metricmethod
def run_one_thousand_obfuscated_bytecode(foo):
    return foo.one_thousand()

@metricmethod
def run_ten_thousand_obfuscated_bytecode(foo):
    return foo.ten_thousand()

@metricmethod
def run_empty_no_obfuscated_code_object(foo):
    return foo.empty()

@metricmethod
def run_one_thousand_no_obfuscated_bytecode(foo):
    return foo.one_thousand()

@metricmethod
def run_ten_thousand_no_obfuscated_bytecode(foo):
    return foo.ten_thousand()

def check_output(output):
    if not os.path.exists(output):
        logging.info('Create output path: %s', output)
        os.makedirs(output)
    else:
        logging.info('Output path: %s', output)

def obffuscate_python_scripts(output, filename):
    p = subprocess.Popen([sys.executable, 'pyarmor.py',
                          'encrypt', '-O', output, '-i', filename])
    p.wait()

def main():
    time.clock()
    pytransform = load_pytransform()
    init_pytransform(pytransform)
    verify_license(pytransform)

    logging.info('')

    output = 'test-bench'
    name = 'bfoo'
    filename = os.path.join(output, name + '.py')

    obname = 'obfoo'
    obfilename = os.path.join(output, obname + '.pyc')

    if os.path.exists(os.path.basename(filename)):
        logging.info('Test script: %s', os.path.basename(filename))
    else:
        check_output(output)
        logging.info('Generate test script %s ...', filename)
        make_test_script(filename)
        logging.info('Test script %s has been generated.', filename)

    if os.path.exists(os.path.basename(obfilename)):
        logging.info('Obffuscated script: %s', os.path.basename(obfilename))
    else:
        check_output(output)
        logging.info('Obffuscate test script ...')
        obffuscate_python_scripts(output, filename)
        if not os.path.exists(filename + 'c'):
            logging.info('Something is wrong to obsfucate %s.', filename)
            return
        shutil.move(filename + 'c', obfilename)
        logging.info('Generate obffuscated script %s', obfilename)

        logging.info('Copy benchmark.py to %s', output)
        shutil.copy('benchmark.py', output)

        logging.info('')
        logging.info('Now change to "%s"', output)
        logging.info('Run "%s benchmark.py" again.', sys.executable)
        return

    foo = __import__(name)
    obfoo = __import__(obname)

    logging.info('')
    run_empty_no_obfuscated_code_object(foo)
    run_empty_obfuscated_code_object(obfoo)

    logging.info('')
    run_one_thousand_no_obfuscated_bytecode(foo)
    run_one_thousand_obfuscated_bytecode(obfoo)

    logging.info('')
    run_ten_thousand_no_obfuscated_bytecode(foo)
    run_ten_thousand_obfuscated_bytecode(obfoo)

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
    )
    main()