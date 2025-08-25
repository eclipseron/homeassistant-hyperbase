## Hyperbase

Hyperbase is an open source Backend-as-a-Service (BaaS) that strives to be performant and reliable. It provides a way for developers to handle common backend functionalities without having to build and maintain them from scratch. This can save time and resources, allowing developers to focus on the core features of their application.

It works with [ScyllaDB](https://www.scylladb.com) for high volume IoT data transaction. It also works with various SQL database, PostgreSQL, MySQL, and SQLite. Communication is provided by REST API, MQTT, and Websockets. Kindly check the official documentation of [Hyperbase](https://hyperbase-book.hilmy.dev/01_introduction/01_chapter) for further information

## Hyperbase for Home Assistant

This is a custom component which provides integration for Home Assistant and Hyperbase. The integration supports data collecting mechanism from commercial IoT products into Hyperbase. You can easily manage your Iot data collection without complex database configuration. Data collecting configuration can be accessed from Home Assistant integration UI. But, it is recommended for you to have extensive understanding of Home Assistant environment.