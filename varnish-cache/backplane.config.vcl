// Add include to post request caching
include "cache_post_requests.vcl";

backend default {
    .host = "backplane";
    .port = "8099";
    .probe = {
        .url = "/apidocs/";
        .timeout = 60s;
        .interval = 5s;
        .window = 5;
        .threshold = 3;
    }
}

