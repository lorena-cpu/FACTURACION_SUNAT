from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from facturacion_sunat.formulario_factura import crear_factura, leer_producto
from facturacion_sunat.serializador import generar_xml
from facturacion_sunat.validacion_local import validar_factura


DATOS = dict(
    ruc_emisor="20999999001", razon_emisor="Emisor de prueba", establecimiento="0000",
    ruc_adquirente="20999999019", razon_adquirente="Adquirente de prueba",
    serie="F001", correlativo="1", fecha="2026-11-12",
    leyenda="DOSCIENTOS TREINTA Y SEIS CON 00/100 SOLES",
)


class PruebasFormulario(unittest.TestCase):
    def test_generacion_desde_formulario_pasa_xsd_y_perfil(self):
        factura = crear_factura(**DATOS, productos=(
            leer_producto("Cuaderno & separadores", "2", "55,00"),
            leer_producto("Archivador", "3", "30.00"),
        ))
        self.assertEqual(str(factura.totales.valor_venta), "200.00")
        self.assertEqual(str(factura.totales.igv), "36.00")
        self.assertEqual(str(factura.totales.importe_a_pagar), "236.00")
        with TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "20999999001-01-F001-1.xml"
            xml = generar_xml(factura)
            ruta.write_bytes(xml)
            resultado = validar_factura(ruta)
            self.assertEqual((resultado.xsd, resultado.perfil), ("Aprobado", "Aprobado"))
            self.assertEqual(ruta.read_bytes(), xml)

    def test_errores_de_producto(self):
        for descripcion, cantidad, precio, mensaje in (
            ("", "1", "10", "Descripción"),
            ("A", "0", "10", "Cantidad"),
            ("A", "1,234.56", "10", "Cantidad"),
            ("A", "1", "NaN", "Valor unitario"),
            ("A", "1", "1.12345678901", "Valor unitario"),
        ):
            with self.subTest(cantidad=cantidad, precio=precio):
                with self.assertRaisesRegex(ValueError, mensaje):
                    leer_producto(descripcion, cantidad, precio)

    def test_errores_de_cabecera_y_detalle(self):
        producto = leer_producto("Producto", "1", "10")
        for cambios, mensaje in (
            ({"ruc_emisor": "123"}, "RUC del emisor"),
            ({"ruc_adquirente": "123"}, "RUC del adquirente"),
            ({"fecha": "2026-02-30"}, "Fecha de emisión"),
            ({"fecha": "20261112"}, "Fecha de emisión"),
            ({"correlativo": "1.5"}, "Correlativo"),
            ({"establecimiento": "00"}, "establecimiento"),
            ({"serie": "B001"}, "serie"),
            ({"leyenda": ""}, "Leyenda"),
        ):
            with self.subTest(cambios=cambios), self.assertRaisesRegex(ValueError, mensaje):
                crear_factura(**(DATOS | cambios), productos=(producto,))
        with self.assertRaisesRegex(ValueError, "al menos una línea"):
            crear_factura(**DATOS, productos=())
        with self.assertRaisesRegex(ValueError, "999"):
            crear_factura(**DATOS, productos=(producto,) * 1000)
