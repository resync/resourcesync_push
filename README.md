# ResourceSync PuSH
![alt text](https://github.com/hariharshankar/resourcesync_push/blob/master/resourcesync_logo.jpg?raw=true ResourceSync)

**A ResourceSync PubSubHubbub Implementation.**

ResourceSync Push is a Hub, Publisher, Source implementation of ResourceSync written in Python and uses the [uWSGI](http://projects.unbit.it/uwsgi/) server.

The [ResourceSync specification](http://www.openarchives.org/rs/0.9.1/resourcesync) describes a synchronization framework for the web consisting of various capabilities that allow third party systems to remain synchronized with a server's evolving resources. This library is an implementation of the ResourceSync [Change Notification](http://www.openarchives.org/rs/notification/0.9/notification#ChangeNoti) and uses the [PubSubHubbub](https://pubsubhubbub.googlecode.com/git/pubsubhubbub-core-0.4.html) protocol.

## Features
* Scalable, fast and easily installable Publisher, Hub and Subscriber.
* Fully compliant implementation of the ResourceSync Change Notification spec.
* The Hub is also compliant with the PubSubHubbub spec and can be used as a simple pubsub hub.
* ResourceSync Push can be easily deployed into any existing system and is programming language independent.
  * Sends and receives data using REST APIs.


## Getting Started

Read the [documentation](https://github.com/hariharshankar/resourcesync_push/wiki) to get started.
