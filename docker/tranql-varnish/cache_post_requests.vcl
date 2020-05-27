vcl 4.0;
import std;
import bodyaccess;

/**
*  More on this logic can be found at https://info.varnish-software.com/blog/caching-post-requests-with-varnish
*
**/

sub vcl_recv {
    unset req.http.x-body-len;
    if (req.method == "POST") {
        set req.http.x-method = req.method;
        // Request body more than 500KB will not be cached.
        std.cache_req_body(500KB);
        set req.http.x-body-len = bodyaccess.len_req_body();
        return (hash);
    }
}

sub vcl_hash {
    if (req.method == "POST" && req.http.x-body-len) {
        // Adding body to hash data via bodyaccess mod.
        // Default hashing hashes url and path. This causes
        // undesired effect on post caching. We need to hash body aswell.
        bodyaccess.hash_req_body();
    } else {
        hash_data("");
    }
}

sub vcl_backend_fetch {
    // Varnish converts method to GET when fetching from backend by default
    // This is to preserve the initial method coming from Client / Browser
    if (bereq.http.x-method) {
        set bereq.method = bereq.http.x-method;
    }
}

