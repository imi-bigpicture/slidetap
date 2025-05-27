---
title: Site implementations
layout: home
nav_order: 4
---

## Site implementations

In order to import images and metadata to your application, an image and metadata importer is needed. Additionally services for authentication and login needs to be provided.

### MetadataImportInterface

A [`MetadataImportInterface`](https://github.com/imi-bigpicture/slidetap/tree/v0.2.0/slidetap-app/slidetap/external_interfaces/metadata_import.py) is responsible for importing metadata from an outsde source, such as a LIMS, and organize it into the used schema.

### ImageImportInterface

An [`ImageImportInterface`](https://github.com/imi-bigpicture/slidetap/tree/v0.2.0/slidetap-app/slidetap/external_interfaces/image_import.py) is responsible for importing images from an outsde source, such as a PACS, and making it avaiable for further use.

### Authentication and login

An [`AuthService`](https://github.com/imi-bigpicture/slidetap/tree/v0.2.0/slidetap-app/slidetap/web/services/auth/auth_service.py) that authenticates users and a [`LoginService`](https://github.com/imi-bigpicture/slidetap/tree/v0.2.0/slidetap-app/slidetap/web/services/login/login_service.py) that logins users, and a [`LoginController`](https://github.com/imi-bigpicture/slidetap/tree/v0.2.0/slidetap-app/slidetap/web/controller/login/login_controller.py) that the front-end can use to login users.
