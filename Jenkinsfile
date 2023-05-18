pipeline {
  agent any
  stages {
    stage('build') {
      steps {
        sh 'docker build -t ecloud_exporter:latest .'
      }
    }

  }
}