cd $(dirname $0)
rm kube_config_cluster.yml cluster.rkestate

rke up
kubectl --kubeconfig kube_config_cluster.yml apply -f hello-deployment.yaml
kubectl --kubeconfig kube_config_cluster.yml rollout status deployment/hello
kubectl --kubeconfig kube_config_cluster.yml apply -f hello-svc.yaml
