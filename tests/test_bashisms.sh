#!/bin/sh - 
#===============================================================================
# vim: softtabstop=4 shiftwidth=4 expandtab fenc=utf-8 spell spelllang=en
#===============================================================================
set -o nounset                              # Treat unset variables as an error

# ----- Source helpers ------------------------------------------------------>
. ${SHUNIT2_HELPERS_PATH}
# <---- Source helpers -------------------------------------------------------


# ----- Test Cases ---------------------------------------------------------->
test_checkbashisms() {
    (${EXT_DIR}/checkbashisms -pxfn ${BS_SCRIPT} >"${stdoutF}" 2>"${stderrF}")
    Tc=$?
    assertEquals "STDOUT shoud be empty." "" "$(cat ${stdoutF} || '')"
    assertEquals "STDERR shoud be empty." "" "$(cat ${stderrF} || '')"
    assertEquals "Wrong exit code." 0 $Tc
}
# <---- Test Cases -----------------------------------------------------------


# ----- Suite Setup Functions ----------------------------------------------->
oneTimeSetUp() {
    tmpDir="${__shunit_tmpDir}/output"
    mkdir "${tmpDir}"
    stdoutF="${tmpDir}/stdout"
    stderrF="${tmpDir}/stderr"
}

oneTimeTearDown() {
    rm -rf "${tmpDir}"
}
# <---- Suite Setup Functions ------------------------------------------------

# ----- Load and run shunit2 ------------------------------------------------>
. ${SH2_SCRIPT_PATH}
# <---- Load and run shunit2 -------------------------------------------------
