FROM greentranslator/tranql-base

WORKDIR /
RUN apk add nodejs npm git
WORKDIR /tranql/web
RUN npm install
#RUN npm run build
RUN node --max-old-space-size=4000 ./node_modules/react-scripts/scripts/build.js
RUN apk del nodejs npm git
WORKDIR /

#ENTRYPOINT /usr/local/bin/gunicorn --workers=$WORKERS --bind=0.0.0.0:$PORT --name=$APP_NAME $APP_MODULE
