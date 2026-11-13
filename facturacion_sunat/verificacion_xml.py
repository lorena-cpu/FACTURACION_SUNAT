"""Verifica el perfil académico sobre un Invoice que ya pasó el XSD."""

from decimal import Context, Decimal, localcontext
import re

from .modelos import IGV, redondear
from .reglas_sunat import validar_ruc
from .serializador import MONEDA, NS


PREFIJOS = {prefijo: uri for prefijo, uri in NS.items() if prefijo is not None}
TOLERANCIA_MONETARIA = Decimal("1")


class FueraDelPerfil(ValueError):
    """El documento requiere reglas que el perfil académico no cubre."""


def _campo(padre, ruta):
    nodos = padre.findall(ruta, PREFIJOS)
    if len(nodos) != 1:
        raise ValueError(f"{ruta}: se requiere un elemento en el perfil académico.")
    return nodos[0]


def _texto(nodo):
    return (nodo.text or "").strip()


def _iguales(actual, esperado, campo):
    if actual != esperado:
        raise ValueError(f"{campo}: se esperaba {esperado}, se obtuvo {actual!r}.")


def _decimal(nodo, escala, campo):
    # n(12, escala) del Anexo IV. Se admite signo positivo y se comprueba
    # la precisión por valor para aceptar ceros decimales redundantes.
    texto = _texto(nodo)
    if not re.fullmatch(r"\+?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", texto):
        raise ValueError(f"{campo}: se requiere un decimal no negativo.")
    entero, _, fraccion = texto.lstrip("+").partition(".")
    if len(entero.lstrip("0")) > 12 or len(fraccion.rstrip("0")) > escala:
        raise ValueError(f"{campo}: se requiere precisión n(12,{escala}).")
    return Decimal(texto)


def _importe(padre, ruta, escala=2):
    nodo = _campo(padre, ruta)
    _iguales(nodo.get("currencyID"), MONEDA, f"{ruta}/@currencyID (catálogo 02)")
    return _decimal(nodo, escala, ruta)


def _tributo_del_perfil(padre, *, linea=False):
    total = _campo(padre, "cac:TaxTotal")
    subtotal = _campo(total, "cac:TaxSubtotal")
    categoria = _campo(subtotal, "cac:TaxCategory")
    esquema = _campo(categoria, "cac:TaxScheme")
    for ruta, valor in (("cbc:ID", "1000"), ("cbc:Name", "IGV"), ("cbc:TaxTypeCode", "VAT")):
        _iguales(_texto(_campo(esquema, ruta)), valor, f"TaxScheme/{ruta} (catálogo 05)")
    if linea:
        motivo = _campo(categoria, "cbc:TaxExemptionReasonCode")
        _iguales(_texto(motivo), "10", "TaxExemptionReasonCode (catálogo 07)")
        tasa = _campo(categoria, "cbc:Percent")
        _iguales(_decimal(tasa, 5, "Percent"), IGV, "Percent (tasa general 2026)")

    return total, subtotal


def _comparar_sunat(codigo, campo, declarado, referencia, *, tolerancia):
    if abs(declarado - referencia) > tolerancia:
        raise ValueError(
            f"SUNAT {codigo} | {campo}: declarado {declarado}, "
            f"referencia {referencia}, tolerancia {tolerancia}."
        )


def _comprobar_linea(linea, total, subtotal):
    cantidad = _campo(linea, "cbc:InvoicedQuantity")
    _iguales(cantidad.get("unitCode"), "NIU", "InvoicedQuantity/@unitCode (catálogo 03)")
    unidades = _decimal(cantidad, 10, "InvoicedQuantity")
    valor = _importe(linea, "cac:Price/cbc:PriceAmount", 10)
    alternativa = _campo(linea, "cac:PricingReference/cac:AlternativeConditionPrice")
    tipo_precio = _campo(alternativa, "cbc:PriceTypeCode")
    _iguales(_texto(tipo_precio), "01", "PriceTypeCode (catálogo 16)")

    precio = _importe(alternativa, "cbc:PriceAmount", 10)
    venta = _importe(linea, "cbc:LineExtensionAmount")
    base = _importe(subtotal, "cbc:TaxableAmount")
    tributo = _importe(subtotal, "cbc:TaxAmount")
    impuesto_total = _importe(total, "cbc:TaxAmount")

    # Factura2_0, fila 183. Para cantidad positiva, se puede comparar
    # en escala de línea y evitar redondear una división periódica.
    referencia_precio = venta + impuesto_total
    if abs(precio * unidades - referencia_precio) > TOLERANCIA_MONETARIA * unidades:
        raise ValueError(
            "SUNAT 3270 | cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceAmount: "
            f"precio unitario declarado {precio}, referencia {referencia_precio / unidades}, "
            f"tolerancia {TOLERANCIA_MONETARIA}."
        )
    # Factura2_0, filas 206 y 280. El perfil excluye ISC y ajustes.
    _comparar_sunat(
        "3272", "cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount", base, venta,
        tolerancia=Decimal("0"),
    )
    _comparar_sunat(
        "3271", "cbc:LineExtensionAmount", venta, valor * unidades,
        tolerancia=TOLERANCIA_MONETARIA,
    )
    _iguales(tributo, redondear(base * IGV / 100), "TaxSubtotal/TaxAmount (control local)")
    _iguales(impuesto_total, tributo, "TaxTotal/TaxAmount (control local)")
    return base, venta


def _verificar_campos_item(lineas):
    # Matriz CPE del 26/08/2026, Factura2_0, filas 145–146, 151 y 175–176.
    identificadores = set()
    for numero, linea in enumerate(lineas, 1):
        ruta = f"cac:InvoiceLine[{numero}]"
        identificador = linea.findtext("cbc:ID", default="", namespaces=PREFIJOS)
        if not re.fullmatch(r"[0-9]{1,3}", identificador) or int(identificador) == 0:
            raise ValueError(f"SUNAT 2023 | {ruta}/cbc:ID: indique de uno a tres dígitos y un valor distinto de cero.")
        if identificador in identificadores:
            raise ValueError(f"SUNAT 2752 | {ruta}/cbc:ID: el identificador {identificador!r} ya aparece en otra línea.")
        identificadores.add(identificador)

        cantidad = linea.find("cbc:InvoicedQuantity", PREFIJOS)
        if cantidad is None or re.fullmatch(r"[+-]?(?:0+(?:\.0*)?|\.0+)", _texto(cantidad)):
            raise ValueError(f"SUNAT 2024 | {ruta}/cbc:InvoicedQuantity: la cantidad está ausente o es cero.")

        descripciones = linea.findall("cac:Item/cbc:Description", PREFIJOS)
        ruta_descripcion = f"{ruta}/cac:Item/cbc:Description"
        if not descripciones or any(nodo.text in (None, "") for nodo in descripciones):
            raise ValueError(f"SUNAT 2026 | {ruta_descripcion}: falta la descripción o está vacía.")
        if any(len(nodo.text) > 500 for nodo in descripciones):
            raise ValueError(f"SUNAT 2027 | {ruta_descripcion}: la descripción admite de 1 a 500 caracteres.")


def _verificar_forma_pago(raiz):
    # Matriz CPE del 26/08/2026, Factura2_0, filas 855–859, 863 y 876.
    bloques = raiz.findall("cac:PaymentTerms", PREFIJOS)
    formas = []
    for indice, bloque in enumerate(bloques, 1):
        ruta = f"cac:PaymentTerms[{indice}]/cbc:PaymentMeansID"
        medios = bloque.findall("cbc:PaymentMeansID", PREFIJOS)
        if len(medios) > 1:
            raise ValueError(f"SUNAT 3461 | {ruta}: hay más de un medio dentro del mismo bloque.")
        if bloque.findtext("cbc:ID", namespaces=PREFIJOS) == "FormaPago":
            formas.append((ruta, medios))

    if not formas:
        raise ValueError("SUNAT 3244 | cac:PaymentTerms/cbc:ID: falta un bloque con indicador FormaPago.")

    valores = []
    for ruta, medios in formas:
        if not medios:
            raise ValueError(f"SUNAT 3245 | {ruta}: falta el medio de pago del bloque FormaPago.")
        valor = medios[0].text or ""
        if valor not in ("Contado", "Credito") and not re.fullmatch(r"Cuota[0-9]{3}", valor):
            raise ValueError(f"SUNAT 3246 | {ruta}: {valor!r} debe ser Contado, Credito o Cuota seguida de tres dígitos.")
        valores.append(valor)

    if "Contado" in valores and "Credito" in valores:
        raise ValueError(
            "SUNAT 3247 | cac:PaymentTerms/cbc:PaymentMeansID: "
            "Contado y Credito aparecen en bloques FormaPago del mismo comprobante."
        )
    vistos = set()
    for (ruta, _), valor in zip(formas, valores, strict=True):
        if valor in vistos:
            raise ValueError(f"SUNAT 3248 | {ruta}: el valor {valor!r} se repite en otro bloque FormaPago.")
        vistos.add(valor)
    if "Credito" not in vistos:
        for (ruta, _), valor in zip(formas, valores, strict=True):
            if valor.startswith("Cuota"):
                raise ValueError(f"SUNAT 3252 | {ruta}: la cuota {valor} requiere un bloque FormaPago con Credito.")

    if valores != ["Contado"] or len(bloques) != 1:
        raise FueraDelPerfil(
            "cac:PaymentTerms: fuera del perfil académico. "
            "Solo se admite un bloque FormaPago al Contado."
        )


def verificar_perfil(raiz) -> None:
    """Comprueba códigos y conciliación del perfil local. Informa el primer error."""
    _iguales(raiz.tag, f"{{{NS[None]}}}Invoice", "Raíz XML")
    for ruta, valor in (("cbc:UBLVersionID", "2.1"), ("cbc:CustomizationID", "2.0")):
        _iguales(_texto(_campo(raiz, ruta)), valor, ruta)
    tipo = _campo(raiz, "cbc:InvoiceTypeCode")
    moneda = _texto(_campo(raiz, "cbc:DocumentCurrencyCode"))
    for valor, esperado, campo in (
        (_texto(tipo), "01", "InvoiceTypeCode (catálogo 01)"),
        (tipo.get("listID"), "0101", "InvoiceTypeCode/@listID (catálogo 51)"),
        (moneda, MONEDA, "DocumentCurrencyCode (catálogo 02)"),
    ):
        if valor != esperado:
            raise FueraDelPerfil(f"{campo}: fuera del perfil académico. Se requiere {esperado}; se encontró {valor!r}.")

    for nombre in ("AccountingSupplierParty", "AccountingCustomerParty"):
        parte = _campo(raiz, f"cac:{nombre}/cac:Party")
        ruta_ruc = "cac:PartyIdentification/cbc:ID"
        try:
            ruc = _campo(parte, ruta_ruc)
        except ValueError as error:
            raise ValueError(f"{nombre}/Party/{error}") from error
        numero_ruc = _texto(ruc)
        if not numero_ruc:
            raise ValueError(f"{nombre}/Party/{ruta_ruc}: el RUC está vacío.")
        _iguales(ruc.get("schemeID"), "6", f"{nombre}/PartyIdentification/@schemeID (catálogo 06)")
        try:
            validar_ruc(numero_ruc)
        except ValueError as error:
            raise ValueError(f"{nombre}/PartyIdentification/ID (control local): {error}") from error
        entidad = _campo(parte, "cac:PartyLegalEntity")
        razon = _texto(_campo(entidad, "cbc:RegistrationName"))
        if not 1 <= len(razon) <= 1500:
            raise ValueError(f"{nombre}/RegistrationName: se requieren de 1 a 1500 caracteres.")
        if nombre == "AccountingSupplierParty":
            codigo = _campo(entidad, "cac:RegistrationAddress/cbc:AddressTypeCode")
            if not re.fullmatch(r"[0-9]{4}", _texto(codigo)):
                raise ValueError("AddressTypeCode: se requieren cuatro dígitos.")

    _verificar_forma_pago(raiz)
    totales = _campo(raiz, "cac:LegalMonetaryTotal")
    for ruta in (
        ".//cac:AllowanceCharge", "cac:PrepaidPayment", "cbc:TaxCurrencyCode",
        "cac:WithholdingTaxTotal", "cac:InvoiceLine/cac:WithholdingTaxTotal",
        "cac:LegalMonetaryTotal/cbc:PrepaidAmount",
        "cac:LegalMonetaryTotal/cbc:PayableRoundingAmount",
        "cac:LegalMonetaryTotal/cbc:ChargeTotalAmount",
        "cac:LegalMonetaryTotal/cbc:AllowanceTotalAmount",
    ):
        if raiz.find(ruta, PREFIJOS) is not None:
            raise FueraDelPerfil(f"{ruta}: fuera del perfil académico de esta verificación.")

    lineas = raiz.findall("cac:InvoiceLine", PREFIJOS)
    if not lineas:
        raise ValueError("InvoiceLine: se requiere al menos una línea.")
    _verificar_campos_item(lineas)
    # Comprobar todas las ramas tributarias antes de emitir códigos aritméticos.
    try:
        total_global, subtotal_global = _tributo_del_perfil(raiz)
        tributos_linea = [_tributo_del_perfil(linea, linea=True) for linea in lineas]
    except ValueError as error:
        raise FueraDelPerfil(f"Tributos fuera del perfil académico: {error}") from error

    # Cada factor puede tener 12 enteros y 10 decimales.
    with localcontext(Context(prec=50)):
        base_acumulada = Decimal("0")
        venta_acumulada = Decimal("0")
        for numero, (linea, (total, subtotal)) in enumerate(zip(lineas, tributos_linea, strict=True), 1):
            try:
                base, venta = _comprobar_linea(linea, total, subtotal)
            except ValueError as error:
                raise ValueError(f"cac:InvoiceLine[{numero}] | {error}") from error
            base_acumulada += base
            venta_acumulada += venta

        igv_referencia = base_acumulada * IGV / 100
        igv_declarado = _importe(subtotal_global, "cbc:TaxAmount")
        venta_global = _importe(totales, "cbc:LineExtensionAmount")
        precio_global = _importe(totales, "cbc:TaxInclusiveAmount")
        # Factura2_0, filas 351 y 420. Ambas usan las bases declaradas.
        _comparar_sunat(
            "3291", "cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount",
            igv_declarado, igv_referencia, tolerancia=TOLERANCIA_MONETARIA,
        )
        _comparar_sunat(
            "3279", "cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount",
            precio_global, venta_global + igv_referencia, tolerancia=TOLERANCIA_MONETARIA,
        )

        _iguales(_importe(subtotal_global, "cbc:TaxableAmount"), base_acumulada, "TaxableAmount global (control local)")
        _iguales(_importe(total_global, "cbc:TaxAmount"), igv_declarado, "TaxTotal/TaxAmount global (control local)")
        _iguales(venta_global, venta_acumulada, "LegalMonetaryTotal/cbc:LineExtensionAmount (control local)")
        _iguales(_importe(totales, "cbc:PayableAmount"), precio_global, "LegalMonetaryTotal/cbc:PayableAmount (control local)")
