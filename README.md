# ResourceSync PuSH
![alt text](https://github.com/hariharshankar/resourcesync_push/blob/master/resourcesync_logo.jpg?raw=true ResourceSync)

**A ResourceSync PubSubHubbub (PuSH) Implementation.**

ResourceSync PuSH is a PubsubHubbub implementation that supports two modes: the ResourceSync notification mode and the traditional PubsubHubbub mode. In the ResourceSync notification mode change notifications are being pushed directly to the Hub whereas in the feed mode just the URI of the feed is pushed to the Hub.
This software provides Publisher, Hub, and Subscriber modules with a RESTful API for easy integration into existing systems. ResourceSync PuSH is written in Python and uses the [uWSGI](http://projects.unbit.it/uwsgi/) server. Please refer to the [ResouceSync Notification specification](http://www.openarchives.org/rs/notification/0.9/notification) for motivating examples and a complete overview of the framework's architecture. 

The core [ResourceSync specification](http://www.openarchives.org/rs/0.9.1/resourcesync) describes a synchronization framework for the web consisting of various capabilities that allow third party systems to remain synchronized with a server's evolving resources. This library is an implementation of the [ResourceSync Notification specification ](http://www.openarchives.org/rs/notification/0.9/notification#ChangeNoti) and uses the [PubSubHubbub](https://pubsubhubbub.googlecode.com/git/pubsubhubbub-core-0.4.html) protocol.

## Features
* Scalable, fast and easy to install Publisher, Hub and Subscriber modules.
* Fully compliant implementation of the ResourceSync Change Notification spec.
* The Hub module is also fully compliant with the [PubSubHubbub specification](https://pubsubhubbub.googlecode.com/git/pubsubhubbub-core-0.4.html).
* ResourceSync PuSH is RESTful and can be easily deployed into any existing system without any programming language barriers.
* The individual modules are fully customizable and can be extended to suit any needs.


## Getting Started

Read the [documentation](https://github.com/hariharshankar/resourcesync_push/wiki) to get started.
