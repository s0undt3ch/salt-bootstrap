#! /bin/sh
# $Id$
# vim:et:ft=sh:sts=2:sw=2
#
# Copyright 2008 Kate Ward. All Rights Reserved.
# Released under the LGPL (GNU Lesser General Public License)
# Author: kate.ward@forestent.com (Kate Ward)
#
# shUnit2 unit test suite runner.
#
# This script runs all the unit tests that can be found, and generates a nice
# report of the tests.


# ----- Salt Bootstrap Script ----------------------------------------------->
# This file was copied and adapted to work with salt-bootstrap
# <---- Salt Bootstrap Script ------------------------------------------------

MY_NAME=`basename $0`
MY_PATH=`dirname $0`

PREFIX='test_'
SHELLS='/bin/sh /bin/bash /bin/dash /bin/ksh /bin/pdksh /bin/zsh'
TESTS=''
for test in ${PREFIX}[a-z]*.sh; do
  TESTS="${TESTS} ${test}"
done

# Export some needed variables
export SHUNIT2_HELPERS_PATH=${MY_PATH}/ext/shunit2/src/shunit2_test_helpers
export EXT_DIR=$(dirname $0)/ext
export BS_SCRIPT=$(dirname $0)/../bootstrap-salt-minion.sh
export SH2_SCRIPT_PATH=${MY_PATH}/ext/shunit2/src/shunit2

# load common unit test functions
. ${MY_PATH}/ext/shunit2/lib/versions
. ${SHUNIT2_HELPERS_PATH}

usage()
{
  echo "usage: ${MY_NAME} [-e key=val ...] [-s shell(s)] [-t test(s)]"
}

env="SH2_SCRIPT_PATH SHUNIT2_HELPERS_PATH EXT_DIR BS_SCRIPT"

# process command line flags
while getopts 'e:hs:t:' opt; do
  case ${opt} in
    e)  # set an environment variable
      key=`expr "${OPTARG}" : '\([^=]*\)='`
      val=`expr "${OPTARG}" : '[^=]*=\(.*\)'`
      if [ -z "${key}" -o -z "${val}" ]; then
        usage
        exit 1
      fi
      eval "${key}='${val}'"
      export ${key}
      env="${env:+${env} }${key}"
      ;;
    h) usage; exit 0 ;;  # output help
    s) shells=${OPTARG} ;;  # list of shells to run
    t) tests=${OPTARG} ;;  # list of tests to run
    *) usage; exit 1 ;;
  esac
done
shift `expr ${OPTIND} - 1`

# fill shells and/or tests
shells=${shells:-${SHELLS}}
tests=${tests:-${TESTS}}

# error checking
if [ -z "${tests}" ]; then
  th_error 'no tests found to run; exiting'
  exit 1
fi

cat <<EOF
#------------------------------------------------------------------------------
# System data
#

# test run info
shells: ${shells}
tests: ${tests}
EOF
for key in ${env}; do
  eval "echo \"${key}=\$${key}\""
done
echo

# output system data
echo "# system info"
echo "$ date"
date
echo

echo "$ uname -mprsv"
uname -mprsv

#
# run tests
#

for shell in ${shells}; do
  echo

  # check for existance of shell
  if [ ! -x ${shell} ]; then
    th_warn "unable to run tests with the ${shell} shell"
    continue
  fi

  cat <<EOF

#------------------------------------------------------------------------------
# Running the test suite with ${shell}
#
EOF

  SHUNIT_SHELL=${shell}  # pass shell onto tests
  shell_name=`basename ${shell}`
  shell_version=`versions_shellVersion "${shell}"`

  echo "shell name: ${shell_name}"
  echo "shell version: ${shell_version}"

  # execute the tests
  for suite in ${tests}; do
    suiteName=`expr "${suite}" : "${PREFIX}\(.*\).sh"`
    echo
    echo "--- Executing the '${suiteName}' test suite ---"
    ( exec ${shell} ./${suite} 2>&1; )
  done
done
