# FACTURACION_SUNAT

Generador local para una factura académica UBL 2.1 de venta interna, en soles, al contado y gravada con IGV del 18 %. El ejemplo usa datos ficticios y se genera mediante un árbol XML de la biblioteca estándar `xml.etree.ElementTree`. La dependencia `lxml` se usa al validar contra el XSD y en las pruebas de análisis estricto de namespaces.

## Windows con PowerShell

### Abrir el validador gráfico

Haz doble clic en `Iniciar validador.cmd` en la carpeta del proyecto.

- **Generar factura.** Completa los datos del emisor, del adquirente y del comprobante. Usa la fecha `AAAA-MM-DD` y escribe el importe en letras como lo solicita el modelo. Agrega, modifica o quita productos en la tabla. Puedes escribir decimales con punto o coma, sin separador de miles. La base, el IGV y el total se actualizan al guardar o quitar un producto. Pulsa **Generar XML**, elige dónde guardarlo y consulta el resultado que se abre en **Validar XML**. La aplicación pide confirmación para reemplazar un archivo y protege los XML de ejemplo y respaldo del proyecto.
- **Validar XML.** Pulsa **Seleccionar XML…**, elige una factura y pulsa **Validar factura**. El panel muestra el resultado del XSD, el del perfil académico y el primer diagnóstico. La aplicación solo lee el archivo seleccionado.

En una instalación nueva, instala Python 3.11 o superior para Windows con el componente Tcl/Tk. Conserva el árbol del paquete XSD oficial descrito en [schemas/README.md](schemas/README.md). Desde PowerShell, prepara el entorno y abre la aplicación:

```powershell
Set-Location 'RUTA_DE_LA_CARPETA_DESCARGADA'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B -m facturacion_sunat.interfaz
```

La interfaz usa Tkinter/ttk incluido con Python para Windows. Si los scripts Tcl/Tk vienen en ZIP en la instalación base, la aplicación los extrae en `.venv\tcltk` y configura las rutas solo durante su ejecución. El esquema oficial se carga desde `schemas/Archivos XSD/2.1/maindoc/UBL-Invoice-2.1.xsd`. El resultado local no equivale a la aceptación de SUNAT ni de un OSE.

### Generar y probar desde la terminal

Desde la raíz del proyecto, con Python 3.11 o superior:

```powershell
Set-Location 'RUTA_DE_LA_CARPETA_DESCARGADA'
.\.venv\Scripts\python.exe -m facturacion_sunat generar
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

El comando escribe `output/20999999001-01-F001-1.xml`. El ejemplo contiene dos productos con bases de S/ 110,00 y S/ 90,00. El IGV total es S/ 36,00 y el importe a pagar es S/ 236,00.

Para validar después de incorporar el paquete oficial, localiza su esquema de factura y pasa su ruta al comando. Sigue las instrucciones de [schemas/README.md](schemas/README.md).

```powershell
$esquemasFactura = @(Get-ChildItem .\schemas -Recurse -File -Filter 'UBL-Invoice-2.1.xsd')
if ($esquemasFactura.Count -ne 1) { throw 'Debe existir un único XSD oficial de Invoice en schemas.' }
.\.venv\Scripts\python.exe -m facturacion_sunat validar-xsd .\output\20999999001-01-F001-1.xml --xsd $esquemasFactura[0].FullName
```

El validador usa códigos de salida 0 para validación estructural exitosa, 1 para error de lectura o validación y 2 para XSD ausente o inutilizable. La factura de ejemplo superó la validación con el paquete oficial incorporado manualmente.

Para verificar también el perfil académico sobre el XML guardado, ejecuta:

```powershell
.\.venv\Scripts\python.exe -m facturacion_sunat verificar-perfil .\output\20999999001-01-F001-1.xml --xsd $esquemasFactura[0].FullName
```

El comando valida primero el XSD y después comprueba los códigos y la conciliación de importes del perfil. Devuelve 1 si falla un control e identifica el primer campo afectado. Consulta la [cobertura y las fuentes](referencias/cobertura-perfil.md).

## Cobertura y límites

### Preparar una futura entrega en GitHub

La entrega pública incluye el paquete Python, las pruebas, `requirements.txt`, el lanzador y la documentación. El paquete SUNAT y las matrices se incorporan localmente desde sus enlaces oficiales. Consulta las instrucciones de [esquemas](schemas/README.md) y [referencias](referencias/README.md). El ejemplo ficticio es reproducible mediante la CLI.

`.gitignore` excluye las salidas de `output/`, entornos, cachés, temporales, el ZIP redundante de esquemas y extensiones comunes de claves y certificados privados. Guarda datos reales y credenciales fuera de la carpeta del proyecto. Antes de publicar, revisa el contenido de todos los archivos que se vayan a incluir, especialmente XML, configuraciones y adjuntos.

Los controles locales comprueban formato de serie, correlativo y fecha, formato y dígito de control del RUC, establecimiento, textos XML válidos y presencia de líneas. El perfil fija factura `01`, venta interna `0101`, moneda `PEN`, unidad `NIU`, documento `6`, contado, precio tipo `01` y afectación `10` con tributo `1000 / IGV / VAT`. Las pruebas comprueban esos datos y la conciliación de importes serializados del ejemplo.

El cálculo aplica redondeo decimal al céntimo a la base y al IGV de cada línea. El IGV global se calcula sobre la suma de las bases declaradas y se redondea al céntimo. El perfil admite cantidades positivas de hasta tres decimales y valores unitarios de hasta diez. La leyenda en letras se proporciona como dato, con comprobación de longitud y caracteres. Su equivalencia con el total se verificó para el ejemplo.

El verificador implementa 17 reglas de la matriz oficial para el perfil descrito. El [informe de cobertura](referencias/cobertura-perfil.md) identifica las reglas y los límites. La verificación local de RUC cubre estructura y dígito de control. El estado registral, el vínculo del establecimiento con el RUC, la habilitación del emisor y los plazos de envío requieren comprobaciones adicionales.

**Un XML sin firma puede superar el XSD y las reglas locales cubiertas. Ese resultado no garantiza su aceptación para emisión tributaria ni por un OSE.** La firma digital, la emisión, las credenciales y los envíos a SUNAT o NubeFact quedan fuera de esta fase. El XML generado es exclusivamente para uso local de prueba.

Consulta [referencias/README.md](referencias/README.md) para las fuentes oficiales y su incorporación manual.
