pipeline {
  agent any
  stages {
    stage('build') {
      steps {
        sh 'docker build -t ecloud_exporter:latest .'
      }
    }

    stage('deploy') {
      steps {
        sh 'docker run -d -p 9199:9199 -e TZ=Asia/Shanghai ecloud_exporter:latest'
      }
    }

  }
}