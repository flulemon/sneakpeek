##################
Deployment options
##################

There are multiple options how you can deploy your scrapers depending on your requirements:

=============================
One replica that does it all
=============================

This is a good option if:

* you can tolerate some downtime
* you don't need to host thousands of scrapers that can be dynamically changed by users
* you don't care if you lose the information about the scraper jobs

In this case all you need to do is to:

* define a list of scrapers in the code (just like in the :doc:`tutorial </quick_start>`)
* use in-memory storage

======================
Using external storage
======================

If you use some external storage (e.g. redis or RDBMS) for jobs queue and lease storage you'll be able:

* to scale workers horizontally until queue, storage or scheduler becomes a bottleneck
* to have a secondary replicas for the scheduler, so when primary dies for some reason there are fallback options

If you also use the external storage as a scrapers storage you'll be able to dynamically 
add, delete and update scrapers via UI or JsonRPC API.

Note that each **Sneakpeek** server by default runs worker, scheduler and API services, but
it's possible to run only one role at the time, therefore you'll be able to scale
services independently.

