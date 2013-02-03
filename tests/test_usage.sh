#!/bin/sh - 
#===============================================================================
# vim: softtabstop=4 shiftwidth=4 expandtab fenc=utf-8 spell spelllang=en
#===============================================================================
set -o nounset                              # Treat unset variables as an error

# ----- Source helpers ------------------------------------------------------>
. ${SHUNIT2_HELPERS_PATH}
# <---- Source helpers -------------------------------------------------------


# ----- Test Cases ---------------------------------------------------------->
test_at_least_one_daemon_installs() {
    (${BS_SCRIPT} -N >"${stdoutF}" 2>"${stderrF}")
    Tc=$?
    assertEquals "Passing '-N'(no minion) without passing '-M'(install master) or '-S'(install syndic) fails" \
                 " * ERROR: Nothing to install" \
                 "$([ -f ${stdoutF} ] && cat ${stdoutF} || '')"
    assertEquals "STDERR should be empty." "" "$([ -f ${stderrF} ] && cat ${stderrF} || '')"
    assertEquals "Wrong exit code." 1 $Tc
}

test_unknown_installation_type() {
    (${BS_SCRIPT} foobar >"${stdoutF}" 2>"${stderrF}")
    Tc=$?
    assertEquals "Using an unknown installation type fails" \
                 " ERROR: Installation type \"foobar\" is not known..." \
                 "$([ -f ${stdoutF} ] && cat ${stdoutF} || '')"
    assertEquals "STDERR should be empty." "" "$([ -f ${stderrF} ] && cat ${stderrF} || '')"
    assertEquals "Wrong exit code." 1 $Tc
}

test_install_using_bash() {
    [ -f /bin/bash1 ] && startSkipping
    (/bin/bash ${BS_SCRIPT} && salt-minion --versions-report >"${stdoutF}" 2>"${stderrF}")
    Tc=$?
    assertEquals "Wrong exit code." 0 $Tc
    [ -f /bin/bash1 ] && endSkipping
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
