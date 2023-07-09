#################
  Middleware
#################

**Sneakpeek** allows you to run arbitrary code before the request and after the response has been recieved.
This can be helpful if you have some common logic you want to use in your scrapers. 

There are some plugins that are already implemented:

.. toctree::
   :maxdepth: 2


   rate_limiter_middleware
   robots_txt_middleware
   user_agent_injecter_middleware
   proxy_middleware
   requests_logging_middleware
   new_middleware
