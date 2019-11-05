FROM greentranslator/tranql-base

WORKDIR /
RUN apk add nodejs npm git
WORKDIR /tranql/web
RUN npm install
RUN node --max-old-space-size=4000 ./node_modules/react-scripts/scripts/build.js
RUN ln -s /tranql/web/build/static/ /tranql/tranql/static
RUN apk del nodejs npm git
WORKDIR /

#ENTRYPOINT /usr/local/bin/gunicorn --workers=$WORKERS --bind=0.0.0.0:$PORT --name=$APP_NAME --log-level=debug $APP_MODULE
