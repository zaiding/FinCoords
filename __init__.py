"""
Point d'entrée du plugin. QGIS appelle classFactory() au chargement
"""


def classFactory(iface):
    from .fin_coord_wgs84 import FinCoordsWGS84
    return FinCoordsWGS84(iface)
