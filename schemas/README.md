# Esquemas oficiales SUNAT

Descarga manualmente el paquete **Archivo XSD - 2.1**, actualizado al **28/02/2022**, desde la sección **Archivos XSL - XSD** del portal oficial. [Guías y manuales SUNAT](https://cpe.sunat.gob.pe/guias-y-manuales)

Extrae el paquete completo en esta carpeta. Conserva los nombres y directorios relativos originales para que funcionen las importaciones. Usa el esquema principal de factura `UBL-Invoice-2.1.xsd` y las dependencias incluidas en el mismo paquete. Registra la fecha de descarga y la huella SHA-256 del ZIP con `Get-FileHash -Algorithm SHA256`.

Con el paquete incorporado en `Archivos XSD/2.1/`, el esquema principal y sus dependencias se compilaron con lxml y la factura de ejemplo superó la validación estructural.

Desde una copia descargada del proyecto, el archivo debe quedar en `schemas/Archivos XSD/2.1/maindoc/UBL-Invoice-2.1.xsd`. Comprueba que el directorio `common` quede junto a `maindoc`. El validador sigue 13 dependencias transitivas locales del esquema de factura.

La entrega pública enlaza la descarga oficial. El paquete contiene avisos de OASIS y componentes de terceros. Las condiciones de [OASIS UBL 2.1, sección Notices](https://docs.oasis-open.org/ubl/UBL-2.1.html#S-NOTICES) contemplan la copia del estándar con sus avisos. La revisión del portal y del ZIP no confirmó condiciones expresas para redistribuir el paquete de SUNAT en su conjunto. Conserva los archivos y avisos originales al extraerlos.
