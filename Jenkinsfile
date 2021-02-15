#!/usr/bin/env groovy
String cron_string = BRANCH_NAME == "master" ? "H H(0-4) * * *" : ""
pipeline {
    environment {
        GIT_REPO_NAME = 'automation-infra'
        GIT_CREDS = credentials('av-jenkins-reader')
        HABERTEST_HEARTBEAT_SERVER = 'https://heartbeat-server.tls.ai'
        HABERTEST_PROVISIONER = 'https://provisioner.tls.ai'
        HABERTEST_SSL_CERT='${HOME}/.habertest/habertest.crt'
        HABERTEST_SSL_KEY='${HOME}/.habertest/habertest.key'
    }
    agent {
        label 'automation'
    }
    libraries {
        lib('pipeline-library')
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
        stage('Run unit tests') {
            steps {
                echo "TODO: Not implemented yet"
            }
        }
        stage('Tests on docker') {
            steps {
                sh (
                    script: "./run/env_vars.sh automation_infra/tests/basic_tests/ --num-parallel 3"
                )
            }
        }
    } // end of stages
    post {
        success {
            cleanWs()
        }
        always {
            dir ('automation-infra') {
                script {
                    coreLib.notification()
                }
            }
        }
    }
} // end of pipeline
