#!/usr/bin/env groovy
pipeline {
    environment {
        GIT_REPO_NAME = 'automation-infra'
        GIT_CREDS = credentials('av-jenkins-reader')
        TEST_TARGET_BRANCH = 'master'
        EMAIL_TO = 'orielh@anyvision.co'
        KVM_MACHINE_CREDS = credentials("office-il-servers")
        HABERTEST_HEARTBEAT_SERVER = '192.168.70.7:7080'
        HABERTEST_PROVISIONER = '192.168.70.7:8080'
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
        stage('pull git repos'){
            steps {
                cleanWs() // clean workspace
                    sh("""
                        git clone https://${GIT_CREDS_USR}:${GIT_CREDS_PSW}@github.com/AnyVisionltd/automation-infra.git -b hab/resource_manager_hb_TMTNNFR-279
                    """)
            } // end of steps
        } // end of stage
        stage('Run unit tests') {
            steps {
                script {
                    sh "echo 'Not yet implemented!'"
                }
            }
        }
        stage('Tests on docker') {
            stages {
                stage('Run integration tests') {
                    steps {
                        dir ('automation-infra') {
                            sh (
                                script: "./containerize.sh python -m pytest -p pytest_automation_infra --provisioner ${env.HABERTEST_PROVISIONER} automation_infra/tests/basic_tests/ --ignore=lab --ignore=hwprovisioner --log-cli-level info --fixture-scope session"
                            )
                        }
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
