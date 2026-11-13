# Cobertura de la verificación XML

Caso cubierto: factura académica UBL 2.1, venta interna al contado, en soles y con IGV general del 18 %. La verificación comienza tras la aprobación del XSD y lee los datos serializados. Los números de campo y catálogo que se citan identifican las fuentes de cada control. Los códigos de rechazo y las severidades de la matriz oficial están pendientes.

| Comprobación | Identificador y fuente oficial | Alcance |
|---|---|---|
| Versiones `2.1` y `2.0`, documento `01`, operación `0101` | Anexo IV de la R.S. 123-2022/SUNAT, Anexo 9-A, campos 1, 2, 6 y 58, catálogos 01 y 51. Actualización del catálogo 51 en la R.S. 000048-2026/SUNAT, Anexo IX. | El código 0101 corresponde al supuesto de venta interna contemplado. |
| Emisor y adquirente | R.S. 123-2022/SUNAT, Anexo IV, Anexo 9-A, datos del emisor y campos 16–18. Catálogo 06, RUC `6`. | Se comprueban el tipo de identidad, el RUC y la presencia y longitud de las razones sociales. El código de establecimiento debe tener cuatro dígitos. El prefijo y dígito verificador se revisan con el control local existente. |
| Moneda `PEN` | R.S. 123-2022/SUNAT, Anexo IV, Anexo 9-A, catálogo 02. Guía de Factura UBL 2.1, apartado sobre moneda del documento. | Comprueba la moneda del documento y de los importes evaluados. |
| Unidad `NIU` y tipo de precio `01` | R.S. 123-2022/SUNAT, Anexo IV, Anexo 9-A, campos 25, 26, 32 y 33, catálogos 03 y 16. La guía incluye ejemplos con `NIU`. | `NIU` es la unidad del perfil del ejemplo. La comprobación no abarca las demás unidades del catálogo. |
| Pago al contado | R.S. 193-2020/SUNAT, Anexo IV, campo 170. Matriz CPE 2026, filas citadas abajo. | El verificador exige `FormaPago` y `Contado` en el perfil y diagnostica errores de estructura, valores y combinaciones de pago. |
| Afectación `10`, tributo `1000 / IGV / VAT` y tasa `18` | R.S. 123-2022/SUNAT, Anexo IV, Anexo 9-A, campos 35–36 y 46–47, catálogos 05 y 07. Tasa general 2026 según Orientación SUNAT. | Se comprueba la afectación y tasa por ítem y el esquema tributario por ítem y global. |
| Importes y sumatorias | R.S. 123-2022/SUNAT, Anexo IV, Anexo 9-A, campos 32–36, 46–47 y 53–55. Guía de Factura UBL 2.1 y TUO de la Ley del IGV, arts. 12–14. | Compara cantidades, valor y precio unitarios, base, IGV, sumatorias y total a pagar. Controla la precisión de importes, precios y cantidades según el campo. |

## Reglas oficiales de ítem implementadas

Fuente: `Reglas de validación - actualizado al 26.08.2026.xlsx`, hoja `Factura2_0`. Las cinco filas tienen severidad `ERROR` en la columna K. Sus condiciones en J carecen de tolerancias y excepciones por operación, moneda o forma de pago. El verificador se ejecuta tras el XSD e informa el primer fallo con código SUNAT y ruta UBL indexada.

| Código | Fila y elemento | Condición comprobada |
|---|---|---|
| 2023 | 145, `InvoiceLine/cbc:ID` | Número de uno a tres dígitos distinto de cero. El formato admite ceros iniciales dentro del límite. |
| 2752 | 146, `InvoiceLine/cbc:ID` | Otra línea contiene el mismo valor de ID. La comparación usa el texto del identificador. La fila no indica normalización de ceros iniciales. |
| 2024 | 151, `InvoiceLine/cbc:InvoicedQuantity` | El elemento falta o su valor decimal es cero. La regla 2025 de la fila 152 es independiente. |
| 2026 | 175, `InvoiceLine/cac:Item/cbc:Description` | El elemento falta o su texto está vacío. |
| 2027 | 176, `InvoiceLine/cac:Item/cbc:Description` | El texto presente debe tener de 1 a 500 caracteres. Se cuentan y permiten espacios, tabulaciones y saltos de línea admitidos por XML. |

La hoja `Control de Cambios`, fila 81, registra una aclaración histórica del 2752 con fecha 24/06/2019. La fila 352 registra el cambio de 2023 a un máximo de 999 líneas. Las cinco filas operativas citadas carecen de fecha de vigencia individual.

## Reglas oficiales de forma de pago implementadas

Fuente: `Reglas de validación - actualizado al 26.08.2026.xlsx`, hoja `Factura2_0`, columnas H (ruta), J (condición), K (severidad), L (código) y M (mensaje). Todas las reglas de esta tabla figuran como `ERROR`. Las filas 855–859 y 876 indican expresamente esa severidad desde el **01/01/2022**. La fila 863 carece de fecha en la condición. `Control de Cambios`, fila 475, registra la vigencia de 3461 desde el **21/11/2022** para factura UBL 2.1.

| Código | Fila | Condición que genera el diagnóstico |
|---|---:|---|
| 3244 | 855 | Falta un `PaymentTerms` con `cbc:ID` igual a `FormaPago`. |
| 3245 | 856 | Un bloque `FormaPago` carece del elemento `cbc:PaymentMeansID`. |
| 3246 | 857 | El elemento presente en `FormaPago` contiene un valor distinto de `Contado`, `Credito` o `Cuota[0-9]{3}`. Incluye el texto vacío. |
| 3247 | 858 | Aparecen `Contado` y `Credito` en bloques `FormaPago` del mismo documento. |
| 3248 | 859 | El mismo valor de `cbc:PaymentMeansID` aparece en dos bloques `FormaPago`. Distintos valores de cuota pueden coexistir con `Credito` sin activar este código. |
| 3461 | 863 | Hay más de un `cbc:PaymentMeansID` dentro de un mismo `PaymentTerms`. La condición de esta fila no añade un filtro por indicador. |
| 3252 | 876 | Un bloque `FormaPago` identifica una cuota con el formato de tres dígitos y falta un bloque `FormaPago` con `Credito`. |

Se diagnostican incoherencias de crédito y cuotas antes de aplicar el límite local de un único bloque `FormaPago/Contado`. Un XML con crédito o con otros bloques de pago puede quedar fuera del perfil sin código SUNAT de esta fase. Los controles sobre montos pendientes, suma de cuotas, vencimientos y demás condiciones de crédito quedan fuera del alcance. La comparación usa el texto exacto de los indicadores y valores.

## Redondeos y límites de la comprobación

La fase 2 usa los campos declarados del XML y `Decimal`. Fuente: `Reglas de validación - actualizado al 26.08.2026.xlsx`, hoja `Factura2_0`, columnas J (condición), K (severidad), L (código) y M (mensaje). Todas las reglas de esta tabla tienen severidad `ERROR`.

| Código y fila | Referencia en el perfil | Comparación |
|---|---|---|
| 3270, fila 183 | (Valor de venta de la línea + monto total de sus tributos) / cantidad. La comparación multiplica ambos lados por la cantidad positiva para evitar el redondeo de una división periódica. | ±1 en el precio unitario |
| 3272, fila 206 | Base del subtotal IGV igual al valor de venta declarado en la línea. Se aplica la rama sin ISC con base positiva. | Exacta |
| 3271, fila 280 | Valor unitario sin IGV por cantidad. Se aplica la rama sin gratuidad con base positiva. | ±1 |
| 3291, fila 351 | IGV global del tributo 1000 igual a la suma de bases de línea por la tasa del perfil, comprobada en cada línea. | ±1 |
| 3279, fila 420 | Subtotal con impuestos igual al valor de venta global declarado más el IGV calculado sobre las bases acumuladas. Se aplica la rama sin IVAP con base positiva. | ±1 |

El perfil se limita a factura 01, operación 0101, PEN, al contado e IGV del 18 % con afectación 10. Rechaza fuera de alcance los cargos, descuentos, anticipos, ajuste explícito de redondeo, moneda tributaria distinta y otros tributos. Por ello, las fórmulas usan ajustes nulos y las ramas con gratuidad, ISC e IVAP de las filas 279, 205 y 421 quedan fuera de esta fase.

Siguen vigentes los controles locales exactos para IGV redondeado de línea, consistencia entre total y subtotal de tributos, sumas globales de base y venta e igualdad entre subtotal con impuestos y total a pagar. Esos controles pueden rechazar documentos que superan las cinco reglas nuevas. Las demás fórmulas y tolerancias oficiales de la matriz quedan pendientes.

El generador calcula el IGV global aplicando el 18 % a la suma de las bases de línea que se escriben en el XML. Redondea el resultado una vez a dos decimales con `ROUND_HALF_UP` como política de generación. La fila 350 especifica la escala de hasta dos decimales para el importe declarado. La fila 351 fija la fórmula y tolerancia ±1. El verificador conserva la referencia sin redondeo previo. El subtotal y el total a pagar se derivan de la base acumulada más el IGV global, según el perfil sin ajustes de las filas 420 y 412.

El IGV de cada ítem se calcula y se redondea de manera independiente. El total tributario de cada línea coincide con su único subtotal IGV, en consonancia con la fila 201 (3292). El total tributario global coincide con el subtotal IGV global, en consonancia con la fila 299 (3294). Ambas filas tienen tolerancia ±1 y comparan subtotales de su propio nivel. El 3294 no suma los impuestos redondeados de las líneas. La fila 213 (3103) compara el tributo de línea con base por tasa, también con ±1. Las filas 200, 208 y 212 contienen controles independientes de formato y de importe cero. Esta corrección conserva la lógica de línea y no amplía la cobertura de esas reglas.

| Caso | IGV de cada línea | IGV global anterior → corregido | Total anterior → corregido |
|---|---:|---:|---:|
| Dos líneas de S/ 0,08 | S/ 0,01 | S/ 0,02 → S/ 0,03 | S/ 0,18 → S/ 0,19 |
| Dos líneas de S/ 0,09 | S/ 0,02 | S/ 0,04 → S/ 0,03 | S/ 0,22 → S/ 0,21 |
| 300 líneas de S/ 0,08 | S/ 0,01 | S/ 3,00 → S/ 4,32 | S/ 27,00 → S/ 28,32 |
| Factura original | S/ 19,80 y S/ 16,20 | S/ 36,00 → S/ 36,00 | S/ 236,00 → S/ 236,00 |

El archivo de laboratorio `output/20999999001-01-F001-2.xml` contiene las 300 líneas. El resultado anterior se conserva como caso negativo en memoria para 3291 y 3279.

El [diagnóstico de la matriz CPE del 26/08/2026](analisis-reglas-sunat-2026.md) registra los demás códigos, vigencias y tolerancias identificados. Quedan pendientes las reglas de esa matriz ajenas a esta fase, la habilitación del emisor, el estado registral, la asociación del establecimiento con el RUC, las condiciones de emisión y la firma. Los datos del ejemplo son ficticios.

## Metadatos del firmante

El borrador incluye el bloque UBL `cac:Signature` antes de `cac:AccountingSupplierParty`. Contiene el identificador del bloque y el RUC y la razón social del emisor como firmante previsto. La guía de factura UBL 2.1, apartado 1, describe esos metadatos y la referencia al objeto criptográfico. El XSD permite omitir el adjunto en este borrador. La referencia y la extensión criptográfica quedan pendientes de la etapa de firma. La comprobación local de estructura y metadatos se realiza con el XSD y las pruebas automatizadas. La compatibilidad con el firmador de OSE-DEMO sigue sin confirmar.

## Referencias oficiales

### Diagnóstico de OSE-DEMO 2083

La variante `output/factura_prueba_namespace_ext.xml` contiene los metadatos del firmante y la declaración `xmlns:ext`. En el borrador, el bloque `cac:Signature` carece de adjunto criptográfico. La guía UBL 2.1, apartado 1, sitúa la referencia en `cac:Signature/cac:DigitalSignatureAttachment/cac:ExternalReference/cbc:URI`. En la factura firmada, su valor debe apuntar al `Id` de `ds:Signature` mediante un fragmento interno. El identificador UBL `cac:Signature/cbc:ID` identifica el bloque de metadatos.

La respuesta 2083 indica una URI ausente o vacía en la etapa que reportó el error. Para preparar una variante con la referencia hace falta que NubeFact confirme si su opción Firmar toma el identificador de la URI de entrada, asigna un `Id` fijo o crea también el enlace UBL. El XML exacto que genera el firmador permitiría comprobar el `Id` y el enlace resultantes. La preparación del enlace debe coordinarse con el firmador antes del cálculo de la firma. Agregarlo a un documento ya firmado puede invalidar el resumen criptográfico. [Herramienta pública de prueba](https://probar-xml.nubefact.com/) · [XML Signature 1.1](https://www.w3.org/TR/xmldsig-core1/)

- [R.S. 123-2022/SUNAT, anexos con el mapeo UBL 2.1 de factura](https://www.sunat.gob.pe/legislacion/superin/2022/anexo-123-2022.pdf)
- [R.S. 193-2020/SUNAT, Anexo IV, forma de pago](https://www.sunat.gob.pe/legislacion/superin/2020/anexo4-193-2020.pdf)
- [R.S. 000048-2026/SUNAT, Anexo IX, catálogo 51](https://www.sunat.gob.pe/legislacion/superin/2026/anexo-000048-2026.pdf)
- [Guía de elaboración de factura UBL 2.1](https://cpe.sunat.gob.pe/sites/default/files/inline-files/guia%2Bxml%2Bfactura%2Bversion%202-1%2B1%2B0%20%282%29_0%20%282%29.pdf)
- [SUNAT, cálculo y tasa general del IGV en 2026](https://orientacion.sunat.gob.pe/3109-05-calculo-del-impuesto)
- [TUO de la Ley del IGV, impuesto bruto y base imponible](https://www.sunat.gob.pe/legislacion/igv/ley/capitul5.htm)
- [Portal oficial de guías y reglas de validación CPE](https://cpe.sunat.gob.pe/guias-y-manuales)
