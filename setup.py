try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(name='resourcesync_push',
      version='0.5.0',
      author='Harihar Shankar, Martin Klein, Herbert Van de Sompel',
      author_email="hariharshankar@gmail.com",
      url="http://www.openarchives.org/rs/0.9.1/resourcesync",
      download_url=
      "https://github.com/hariharshankar/resourcesync_push/releases",
      description="A ResourceSync PubSubHubhub implementation.",
      long_description="ResourceSync PuSH is a PubsubHubbub implementation\
      that also supports the ResourceSync change notification framework. \
      This software provides Publisher, Hub and Subscriber modules with a \
      RESTful API for easy integration in to existing systems.",
      packages=[
          'resourcesync_push',
          'resourcesync_push.hub',
          'resourcesync_push.publisher',
          'resourcesync_push.subscriber'
      ],
      keywords="resourcesync pubsubhubbub uwsgi python",
      license='http://mementoweb.github.io/SiteStory/license.html',
      install_requires=[
          "uWSGI>=2.0.3",
          "requests>=2.2.1",
          "requests_futures>=0.9.4"
      ],
      tests_require=[
          'WebTest>=2.0.14'
      ],
      test_suite='test',
      scripts=['bin/resourcesync_hub',
               'bin/resourcesync_sub',
               'bin/resourcesync_pub'],
      include_package_data=True,
      zip_safe=False,
      data_files=[('/etc/resourcesync_push', ['conf/resourcesync_push.ini',
                                              'conf/resourcesync_hub.ini',
                                              'conf/resourcesync_pub.ini',
                                              'conf/resourcesync_sub.ini']),
                  ('db', ['db/subscriptions.pk']),
                  ('resourcesync_push/hub/templates',
                   ['resourcesync_push/hub/templates/register.html',
                    'resourcesync_push/hub/templates/register_success.html']),
                  ]
      )
