#!/usr/bin/env groovy

pipeline {
  agent {
    label "slave-anyvision-2"
  }
  options {
    timeout(time: 15, unit: "MINUTES")
  }
  environment {
    AUTO_APPROVE = "True"
    DOCKERIZE_FORCE_BUILD = "1"
    NO_CACHE = "0"
    V = "1"
  }
  stages {
    stage("clean workspace") {
      steps {
        cleanWs()
        checkout scm
      }
    }
    stage("test") {
      parallel {
        stage("./run_tests.sh") {
          steps {
            sh "./run_tests.sh || true"
          }
        }
      }
    }
    stage("deploy") {
      when {
        branch 'master'
      }
      parallel {
        stage("publish to artifactory") {
          steps {
            withCredentials([usernamePassword(credentialsId: 'jenkins-artifactory-pypi', usernameVariable: 'UNAME', passwordVariable: 'PASS')]) {
              sh "./containerize.sh 'python setup.py sdist bdist_wheel && twine upload --verbose --repository-url https://anyvision.jfrog.io/anyvision/api/pypi/pypi -u ${UNAME} -p ${PASS} dist/*'"
            }
          }
        }
      }
    }
  }
}
