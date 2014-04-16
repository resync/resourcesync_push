# ResourceSync PuSH
![alt text](https://github.com/hariharshankar/resourcesync_push/blob/master/doc/resourcesync_logo.jpg?raw=true ResourceSync)

**A ResourceSync PubSubHubbub Implementation.**

ResourceSync Push is a Hub, Publisher, Source implementation of ResourceSync written in Python and uses the [uWSGI](http://projects.unbit.it/uwsgi/) server.

The [ResourceSync specification](http://www.openarchives.org/rs/0.9.1/resourcesync) describes a synchronization framework for the web consisting of various capabilities that allow third party systems to remain synchronized with a server's evolving resources. This library is an implementation of the ResourceSync [Change Notification](http://www.openarchives.org/rs/notification/0.9/notification#ChangeNoti) and uses the [PubSubHubbub](https://pubsubhubbub.googlecode.com/git/pubsubhubbub-core-0.4.html) protocol.

## Features
* Scalable, fast and easily installable Publisher, Hub and Subscriber with minimal configuration required.
* Fully compliant implementation of the ResourceSync Change Notification specification.
* The Hub fully supports regular PubSubHubbub requests.
* Publisher has REST API support.
- Existing sources can easily publish change notification to the hub by sending a POST request to the publisher.

TBD...
