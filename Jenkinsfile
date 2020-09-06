#!/usr/bin/env groovy
def remote = [:]

def SpinUpVM(remote, base_image) {
    VM_INFO = sshCommand (
        remote: remote,
        command: String.format('/home/user/automation-infra/hypervisor_cli.py --allocator=localhost:8080 create --image=%s --cpu=10 --ram=20 --size=150 --gpus=1 --networks bridge', base_image)
    )
    return VM_INFO
}

def SetConnection(ips, ids) {
    cmd = String.format("make -f Makefile-env set-jenkins-connection-file HOST_IP=%s RESOURCE_MANAGER_EP=${KVM_MACHINE_IP}:8080 VM_ID=%s CONN_FILE_PATH=${WORKSPACE}/hardware.yaml", ips.join(','), ids.join(','))
    echo cmd
    sh cmd
    sh "cat ${WORKSPACE}/hardware.yaml"
}

def DeleteVM(remote, name) {
    echo "Deleting VM: ${name}"
    sshCommand (
        remote: remote,
        command: "/home/user/automation-infra/hypervisor_cli.py --allocator=localhost:8080 delete --name ${name}"
    )
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
    triggers {
        issueCommentTrigger('^\\/rebuild')
    }
    stages {
        stage ('Build automation proxy container') {
           steps {
                sh(script: "make push-automation-proxy")
	   }
        }
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
        stage('Tests on docker') {
            stages {
                stage('Spin up VM') {
                    steps {
                        script {
                            try {
                                env.docker_vminfo = SpinUpVM(remote, "ubuntu-compose_v2")
                            } catch (Exception e) {
                                echo " ------ FAILED TO CREATE VM -------"
                                echo e.getMessage()
                                echo " ------ journalctl SYSLOG_IDENTIFIER=HYPERVISOR -n 300 -------"
                                sshCommand (
                                    remote: remote,
                                    command: 'journalctl SYSLOG_IDENTIFIER=HYPERVISOR -n 300'
                                )
                                echo " ------ end journalctl -------"
                                error(e.getMessage())
                            }
                        }
                    }
                }
                stage('Create the hardware.yaml') {
                    steps {
                        script {
                            env.vm_ip = sh (
                                script: "echo '${env.docker_vminfo}' | jq  .info.net_ifaces[0].ip",
                                returnStdout: true
                            ).trim()
                            env.vm_id = sh (
                                script: "echo '${env.docker_vminfo}' | jq  .info.name",
                                returnStdout: true
                            ).trim()
                            SetConnection([env.vm_ip], [env.vm_id])
                        }
                    }
                }
                stage('Run integration tests') {
                    steps {
                        sh (
                            script: "./containerize.sh python3 -m pytest -p pytest_automation_infra -o log_cli=true -o log_cli_level=DEBUG ./automation_infra/tests/basic_tests --hardware ${WORKSPACE}/hardware.yaml"
                        )
                    }
                }
            }
            post {
                always {
                    script {
                        vmname = sh (
                            script: "echo '${env.docker_vminfo}' | jq .info.name",
                            returnStdout: true
                        ).trim()
                        DeleteVM(remote, vmname)
                        sh "rm -f ${WORKSPACE}/hardware.yaml"

                    }
                }
            }
        }
        stage('Tests on k8s') {
            stages {
                stage('Spin up VM') {
                    steps {
                        script {
                            try {
                                env.k8s_vminfo = SpinUpVM(remote, "ubuntu-k8s-1804")
                            } catch (Exception e) {
                                echo " ------ FAILED TO CREATE VM -------"
                                echo e.getMessage()
                                echo " ------ journalctl SYSLOG_IDENTIFIER=HYPERVISOR -n 300 -------"
                                sshCommand (
                                    remote: remote,
                                    command: 'journalctl SYSLOG_IDENTIFIER=HYPERVISOR -n 300'
                                )
                                echo " ------ end journalctl -------"
                                error(e.getMessage())
                            }
                        }
                    }
                }
                stage('Create the hardware.yaml') {
                    steps {
                        script {
                            env.vm_ip = sh (
                                script: "echo '${env.k8s_vminfo}' | jq  .info.net_ifaces[0].ip",
                                returnStdout: true
                            ).trim()
                            env.vm_id = sh (
                                script: "echo '${env.k8s_vminfo}' | jq  .info.name",
                                returnStdout: true
                            ).trim()
                            SetConnection([env.vm_ip], [env.vm_id])
                        }
                    }
                }
                stage('Run integration tests') {
                    steps {
                        sh (
                            script: "./containerize.sh python3 -m pytest -p pytest_automation_infra -o log_cli=true -o log_cli_level=DEBUG ./automation_infra/tests/basic_tests --hardware ${WORKSPACE}/hardware.yaml"
                        )
                    }
                }
            }
            post {
                always {
                    script {
                        vmname = sh (
                            script: "echo '${env.k8s_vminfo}' | jq .info.name",
                            returnStdout: true
                        ).trim()
                        DeleteVM(remote, vmname)
                        sh "rm -f ${WORKSPACE}/hardware.yaml"
                    }
                }
            }
        }
    } // end of stages
    post {
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
        always{
            archiveArtifacts artifacts: '**/logs/**/*', fingerprint: true
        }
        success {
            cleanWs()
        }

    }
} // end of pipeline
