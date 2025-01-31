---
title: Site implementations
layout: home
nav_order: 4
---

## Site implementations

In order to import images and metadata to your application, an image and metadata importer is needed. Additionally services for authentication and login needs to be provided.

### MetadataImporter

A [`MetadataImporter`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/importer/metadata_importer.py) is responsible for importing metadata from an outsde source, such as a LIMS, and organize it into the used schema.

### ImageImporter

An [`ImageImporter`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/importer/image_importer.py) is responsible for importing images from an outsde source, such as a PACS, and making it avaiable for further use.

### Authentication and login

An [`AuthService`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/services/auth/auth_service.py) that authenticates users and a [`LoginService`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/services/login/login_service.py) that logins users, and a [`LoginController`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/web/controller/login/login_controller.py) that the front-end can use to login users.
