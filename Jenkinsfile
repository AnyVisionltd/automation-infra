#!/usr/bin/env groovy
def remote = [:]

def SpinUpVM(remote) {
    VM_INFO = sshCommand (
        remote: remote,
        command: '/home/user/automation-infra/hypervisor_cli.py --allocator=localhost:8080 create --image=ubuntu-compose_v2 --cpu=10 --ram=20 --size=150 --gpus=1 --networks bridge'
    )
    return VM_INFO
}

def SetConnection(ip) {
    sh "make -f Makefile-env set-connection-file HOST_IP=${ip} USERNAME=root PASS=root CONN_FILE_PATH=${WORKSPACE}/hardware.yaml"
    sh "cat ${WORKSPACE}/hardware.yaml"
}

def DeleteVM(remote, name) {
    echo "Deleting VM: ${name}"
    sshCommand (
        remote: remote,
        command: "/home/user/automation-infra/hypervisor_cli.py --allocator=localhost:8080 delete --name ${name}"
    )
    sh "rm -f ${WORKSPACE}/hardware.yaml"
}

pipeline {
    environment {
        GIT_REPO_NAME = 'automation-infra'
        GIT_CREDS = credentials('av-jenkins-reader')
        TEST_TARGET_BRANCH = 'master'
        EMAIL_TO = 'peterm@anyvision.co'
        KVM_MACHINE_IP = '192.168.70.35'
        KVM_MACHINE_CREDS = credentials("office-il-servers")
    }
    agent {
        label 'iloffice'
    }
    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 4, unit: 'HOURS')
        ansiColor('xterm')
        buildDiscarder(logRotator(numToKeepStr:'50'))
    }
    stages {
        stage ('Set Remote connection to KVM machine') {
            steps {
                script {
                    remote.name = "kvm-machine"
                    remote.host = "${env.KVM_MACHINE_IP}"
                    remote.allowAnyHosts = true
                    remote.user = "${env.KVM_MACHINE_CREDS_USR}"
                    remote.password = "${env.KVM_MACHINE_CREDS_PSW}"
                }
            }
        }
        stage('Run unit tests') {
            steps {
                script {
                    sh "echo 'Not yet implemented!'"
                }
            }
        }
        stage('Create VM for executing tests upon') {
            stages {
                stage('Spin up VM') {
                    steps {
                        script {
                            env.vminfo = SpinUpVM(remote)
                            env.vmip = sh (
                                script: "echo '${env.vminfo}' | jq  .info.net_ifaces[0].ip",
                                returnStdout: true
                            ).trim()
                        }
                    }
                }
                stage('Create the hardware.yaml') {
                    steps {
                        script {
                            SetConnection(env.vmip)
                        }
                    }
                }
                stage('Run integration tests') {
                    steps {
                        sh (
                            script: "./containerize.sh python3 -m pytest -p pytest_automation_infra -o log_cli=true -o log_cli_level=DEBUG ./automation_infra/tests/test_ssh.py --hardware ${WORKSPACE}/hardware.yaml"
                        )
                    }
                }
            }
        }
    } // end of stages
    post {
        always {
            script {
                vmname = sh (
                    script: "echo '${env.vminfo}' | jq .info.name",
                    returnStdout: true
                ).trim()
                DeleteVM(remote, vmname)
            }
        }
        failure {
            echo "${currentBuild.result}, exiting now..."

            mail to: "${EMAIL_TO}",
                 bcc: '',
                 cc: '',
                 charset: 'UTF-8',
                 from: '',
                 mimeType: 'text/html',
                 replyTo: '',
                 subject: "${currentBuild.result}: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                 body: "<b>Jenkins Job status:</b><br><br>" +
                        "Project: ${env.JOB_NAME}<br>" +
                        "Build Number: # ${env.BUILD_NUMBER}<br>" +
                        "Build Duration: ${currentBuild.durationString}<br>" +
                        "build url: ${env.BUILD_URL}<br>" +
                        "Build Log:<br>${currentBuild.rawBuild.getLog(50).join("<br>")}<br><br>" +
                        "<img class='cartoon' src='https://jenkins.io/images/226px-Jenkins_logo.svg.png' width='42' height='42' align='middle'/><br>"
        }
        success {
            cleanWs()
        }
    }
} // end of pipeline
