FROM greentranslator/green-tranql-base

WORKDIR /
RUN apk add nodejs npm git
WORKDIR /tranql/web
RUN npm install
RUN npm run build
RUN apk del nodejs npm git
WORKDIR /

#ENTRYPOINT /usr/local/bin/gunicorn --workers=$WORKERS --bind=0.0.0.0:$PORT --name=$APP_NAME $APP_MODULE
