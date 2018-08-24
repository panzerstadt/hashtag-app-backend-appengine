## build (do only this if you want to update your app)
#### before
delete the app of the same name in `kubernetes engine > workloads`
#### then
docker build -t hashtag-app-backend .
docker tag hashtag-app-backend gcr.io/dan-tokyo-server/hashtag-app-backend:latest
gcloud docker -- push gcr.io/dan-tokyo-server/hashtag-app-backend:latest
kubectl run hashtag-app-backend --image=gcr.io/dan-tokyo-server/hashtag-app-backend:latest --port=5000

## test run
docker run -p 5000:5000 hashtag-app-backend
(don't run detached since you can't see the errors)
## stop test run
docker ps
(copy docker id)
docker stop <docker-id>

## deploy
kubectl expose deployment hashtag-app-backend --type=LoadBalancer --target-port=5000 --port 80

## one time
gcloud auth login
gcloud config set project dan-tokyo-server
gcloud container clusters create hashtag-app-cluster --num-nodes=2 --zone=asia-northeast1-a
gcloud container clusters get-credentials hashtag-app-cluster
kubectl get nodes

docker run -d -p 5000:5000 nginx-flask