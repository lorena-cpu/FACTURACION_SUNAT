from dataclasses import replace
from decimal import Decimal
import unittest

from lxml import etree

from facturacion_sunat.ejemplo import factura_ejemplo
from facturacion_sunat.modelos import Detalle
from facturacion_sunat.serializador import generar_xml
from facturacion_sunat.verificacion_xml import PREFIJOS, verificar_perfil


LINEA = "cac:InvoiceLine/"
PRECIO = LINEA + "cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceAmount"
SUBTOTAL = "cac:TaxTotal/cac:TaxSubtotal/"
TOTAL = "cac:LegalMonetaryTotal/"


def _poner(raiz, ruta, valor):
    raiz.find(ruta, PREFIJOS).text = str(valor)


def _factura_pequena(numero, valor):
    detalle = Detalle("Producto de prueba", Decimal("1"), Decimal(valor))
    return etree.fromstring(generar_xml(replace(factura_ejemplo(), detalles=(detalle,) * numero)))


class PruebasAritmeticaSUNAT(unittest.TestCase):
    def test_tolerancias_simetricas_de_3270_3271_3291_y_3279(self):
        for codigo, referencia in (
            ("3270", "64.90"), ("3271", "110.00"),
            ("3291", "36.00"), ("3279", "236.00"),
        ):
            for delta in ("-1.01", "-1.00", "-0.99", "0", "0.99", "1.00", "1.01"):
                with self.subTest(codigo=codigo, delta=delta):
                    raiz = etree.fromstring(generar_xml(factura_ejemplo()))
                    valor = Decimal(referencia) + Decimal(delta)
                    if codigo == "3270":
                        _poner(raiz, PRECIO, valor)
                    elif codigo == "3271":
                        _poner(raiz, LINEA + "cbc:LineExtensionAmount", valor)
                        _poner(raiz, LINEA + SUBTOTAL + "cbc:TaxableAmount", valor)
                        igv = (valor * Decimal(".18")).quantize(Decimal(".01"))
                        _poner(raiz, LINEA + SUBTOTAL + "cbc:TaxAmount", igv)
                        _poner(raiz, LINEA + "cac:TaxTotal/cbc:TaxAmount", igv)
                        _poner(raiz, SUBTOTAL + "cbc:TaxableAmount", valor + 90)
                        _poner(raiz, TOTAL + "cbc:LineExtensionAmount", valor + 90)
                        subtotal = ((valor + 90) * Decimal("1.18")).quantize(Decimal(".01"))
                        _poner(raiz, TOTAL + "cbc:TaxInclusiveAmount", subtotal)
                        _poner(raiz, TOTAL + "cbc:PayableAmount", subtotal)
                    elif codigo == "3291":
                        _poner(raiz, SUBTOTAL + "cbc:TaxAmount", valor)
                        _poner(raiz, "cac:TaxTotal/cbc:TaxAmount", valor)
                    else:
                        _poner(raiz, TOTAL + "cbc:TaxInclusiveAmount", valor)
                        _poner(raiz, TOTAL + "cbc:PayableAmount", valor)
                    if abs(Decimal(delta)) > 1:
                        with self.assertRaisesRegex(ValueError, f"SUNAT {codigo}"):
                            verificar_perfil(raiz)
                    else:
                        verificar_perfil(raiz)

    def test_3272_compara_base_con_valor_declarado_sin_tolerancia(self):
        for valor in ("109.99", "110.01"):
            with self.subTest(valor=valor):
                raiz = etree.fromstring(generar_xml(factura_ejemplo()))
                verificar_perfil(raiz)
                _poner(raiz, LINEA + SUBTOTAL + "cbc:TaxableAmount", valor)
                with self.assertRaisesRegex(ValueError, "SUNAT 3272"):
                    verificar_perfil(raiz)

    def test_dos_lineas_con_diferencia_de_redondeo_dentro_del_margen(self):
        for base, igv_declarado, referencia in (("0.08", "0.02", "0.0288"), ("0.09", "0.04", "0.0324")):
            with self.subTest(base=base):
                raiz = _factura_pequena(2, base)
                _poner(raiz, SUBTOTAL + "cbc:TaxAmount", igv_declarado)
                _poner(raiz, "cac:TaxTotal/cbc:TaxAmount", igv_declarado)
                total_anterior = 2 * Decimal(base) + Decimal(igv_declarado)
                _poner(raiz, TOTAL + "cbc:TaxInclusiveAmount", total_anterior)
                _poner(raiz, TOTAL + "cbc:PayableAmount", total_anterior)
                self.assertEqual(raiz.findtext(SUBTOTAL + "cbc:TaxAmount", namespaces=PREFIJOS), igv_declarado)
                self.assertEqual(2 * Decimal(base) * Decimal(".18"), Decimal(referencia))
                verificar_perfil(raiz)

    def test_300_lineas_aislan_3291_y_3279(self):
        raiz = _factura_pequena(300, "0.08")
        _poner(raiz, SUBTOTAL + "cbc:TaxAmount", "3.00")
        _poner(raiz, "cac:TaxTotal/cbc:TaxAmount", "3.00")
        _poner(raiz, TOTAL + "cbc:TaxInclusiveAmount", "27.00")
        _poner(raiz, TOTAL + "cbc:PayableAmount", "27.00")
        self.assertEqual(raiz.findtext(SUBTOTAL + "cbc:TaxAmount", namespaces=PREFIJOS), "3.00")
        with self.assertRaisesRegex(ValueError, "SUNAT 3291"):
            verificar_perfil(raiz)
        _poner(raiz, SUBTOTAL + "cbc:TaxAmount", "4.32")
        _poner(raiz, "cac:TaxTotal/cbc:TaxAmount", "4.32")
        with self.assertRaisesRegex(ValueError, "SUNAT 3279"):
            verificar_perfil(raiz)
        _poner(raiz, TOTAL + "cbc:TaxInclusiveAmount", "28.32")
        _poner(raiz, TOTAL + "cbc:PayableAmount", "28.32")
        verificar_perfil(raiz)

    def test_generador_serializa_igv_global_sobre_bases_acumuladas(self):
        casos = (
            (2, "0.08", "0.01", "0.16", "0.03", "0.19"),
            (2, "0.09", "0.02", "0.18", "0.03", "0.21"),
            (300, "0.08", "0.01", "24.00", "4.32", "28.32"),
        )
        for cantidad, base, igv_linea, base_global, igv_global, total in casos:
            with self.subTest(cantidad=cantidad, base=base):
                raiz = _factura_pequena(cantidad, base)
                lineas = raiz.findall("cac:InvoiceLine", PREFIJOS)
                self.assertEqual(len(lineas), cantidad)
                for linea in lineas:
                    self.assertEqual(linea.findtext(SUBTOTAL + "cbc:TaxableAmount", namespaces=PREFIJOS), base)
                    for ruta in (SUBTOTAL + "cbc:TaxAmount", "cac:TaxTotal/cbc:TaxAmount"):
                        self.assertEqual(linea.findtext(ruta, namespaces=PREFIJOS), igv_linea)
                for ruta, esperado in (
                    (SUBTOTAL + "cbc:TaxableAmount", base_global),
                    (SUBTOTAL + "cbc:TaxAmount", igv_global),
                    ("cac:TaxTotal/cbc:TaxAmount", igv_global),
                    (TOTAL + "cbc:LineExtensionAmount", base_global),
                    (TOTAL + "cbc:TaxInclusiveAmount", total),
                    (TOTAL + "cbc:PayableAmount", total),
                ):
                    self.assertEqual(raiz.findtext(ruta, namespaces=PREFIJOS), esperado, ruta)
                verificar_perfil(raiz)

    def test_3291_no_redondea_la_referencia_antes_de_comparar(self):
        raiz = _factura_pequena(2, "0.08")
        for importe in ("1.02", "1.03"):
            _poner(raiz, SUBTOTAL + "cbc:TaxAmount", importe)
            _poner(raiz, "cac:TaxTotal/cbc:TaxAmount", importe)
            if importe == "1.02":
                verificar_perfil(raiz)
            else:
                # 1,03 está fuera respecto de 0,0288 y en el límite respecto de 0,03.
                with self.assertRaisesRegex(ValueError, "SUNAT 3291"):
                    verificar_perfil(raiz)

    def test_excluye_tributos_y_ajustes_antes_de_calcular(self):
        ruta = LINEA + SUBTOTAL + "cac:TaxCategory/cac:TaxScheme/cbc:ID"
        for codigo in ("9996", "2000", "1016"):
            with self.subTest(codigo=codigo):
                raiz = etree.fromstring(generar_xml(factura_ejemplo()))
                _poner(raiz, PRECIO, "1")
                _poner(raiz, ruta, codigo)
                with self.assertRaisesRegex(ValueError, "fuera del perfil académico") as error:
                    verificar_perfil(raiz)
                self.assertNotIn("SUNAT 3270", str(error.exception))
        for nombre in ("AllowanceCharge", "PrepaidPayment"):
            with self.subTest(nombre=nombre):
                raiz = etree.fromstring(generar_xml(factura_ejemplo()))
                _poner(raiz, PRECIO, "1")
                etree.SubElement(raiz, etree.QName(PREFIJOS["cac"], nombre))
                with self.assertRaisesRegex(ValueError, f"{nombre}.*fuera del perfil"):
                    verificar_perfil(raiz)
