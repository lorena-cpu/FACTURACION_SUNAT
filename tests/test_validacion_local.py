from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lxml import etree

from facturacion_sunat.ejemplo import factura_ejemplo
from facturacion_sunat.serializador import generar_xml
from facturacion_sunat.validacion_local import XSD_OFICIAL, validar_factura
from facturacion_sunat.verificacion_xml import PREFIJOS


class PruebasValidacionLocal(unittest.TestCase):
    def _validar(self, contenido, xsd=XSD_OFICIAL):
        with TemporaryDirectory() as carpeta:
            xml = Path(carpeta) / "factura.xml"
            xml.write_bytes(contenido)
            antes = xml.stat().st_mtime_ns
            resultado = validar_factura(xml, xsd)
            self.assertEqual(xml.read_bytes(), contenido)
            self.assertEqual(xml.stat().st_mtime_ns, antes)
            return resultado

    def _mutar(self, ruta, valor):
        raiz = etree.fromstring(generar_xml(factura_ejemplo()))
        raiz.find(ruta, PREFIJOS).text = valor
        return etree.tostring(raiz)

    def test_original_aprobado(self):
        resultado = self._validar(generar_xml(factura_ejemplo()))
        self.assertEqual((resultado.xsd, resultado.perfil), ("Aprobado", "Aprobado"))
        self.assertEqual(resultado.categoria, "Validación local aprobada")

    def test_error_xsd_y_xml_mal_formado(self):
        for xml in (b"<Invoice/>", b"<Invoice>"):
            with self.subTest(xml=xml):
                resultado = self._validar(xml)
                self.assertEqual((resultado.xsd, resultado.perfil), ("Rechazado", "Sin evaluar"))
                self.assertEqual(resultado.categoria, "Error XSD o XML")
                self.assertIn("línea", resultado.elemento)

    def test_regla_sunat_con_ruta_indexada(self):
        resultado = self._validar(self._mutar(
            "cac:InvoiceLine/cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceAmount", "1"
        ))
        self.assertEqual((resultado.xsd, resultado.perfil), ("Aprobado", "Rechazado"))
        self.assertEqual(resultado.categoria, "Regla SUNAT")
        self.assertEqual(resultado.codigo, "3270")
        self.assertTrue(resultado.elemento.startswith("cac:InvoiceLine[1]/"))
        self.assertIn("precio unitario", resultado.descripcion)

    def test_documento_fuera_del_perfil(self):
        for ruta, valor in (
            ("cac:PaymentTerms/cbc:PaymentMeansID", "Credito"),
            ("cbc:DocumentCurrencyCode", "USD"),
        ):
            with self.subTest(ruta=ruta):
                resultado = self._validar(self._mutar(ruta, valor))
                self.assertEqual((resultado.xsd, resultado.perfil), ("Aprobado", "Fuera del perfil"))
                self.assertEqual(resultado.codigo, "")

    def test_xsd_ausente(self):
        resultado = self._validar(generar_xml(factura_ejemplo()), XSD_OFICIAL.with_name("ausente.xsd"))
        self.assertEqual((resultado.xsd, resultado.perfil), ("No disponible", "Sin evaluar"))
