"""
9ellet maydar code:)
-------------------
Selects a point on a vector point layer and instantly displays its coordinates in EPSG:4326 (latitude/longitude) in a small window, with buttons to copy each value to the clipboard. Developped to be used in GEMS to add manholes.
"""

import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsWkbTypes,
)


class CoordPickerDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent, Qt.Tool)
        self.iface = iface
        self.setWindowTitle("Fin Coordinates (EPSG:4326)")
        self.setMinimumWidth(320)

        self.lat_edit = QLineEdit()
        self.lon_edit = QLineEdit()
        for e in (self.lat_edit, self.lon_edit):
            e.setReadOnly(True)

        self.status_label = QLabel("Select a point on the active layer.")
        self.status_label.setWordWrap(True)

        lat_row = QHBoxLayout()
        lat_row.addWidget(QLabel("Latitude :"))
        lat_row.addWidget(self.lat_edit)
        btn_lat = QPushButton("Copy")
        btn_lat.clicked.connect(lambda: self.copy_text(self.lat_edit.text()))
        lat_row.addWidget(btn_lat)

        lon_row = QHBoxLayout()
        lon_row.addWidget(QLabel("Longitude :"))
        lon_row.addWidget(self.lon_edit)
        btn_lon = QPushButton("Copy")
        btn_lon.clicked.connect(lambda: self.copy_text(self.lon_edit.text()))
        lon_row.addWidget(btn_lon)

        btn_both = QPushButton("Copy Latitude, Longitude")
        btn_both.clicked.connect(self.copy_both)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addLayout(lat_row)
        layout.addLayout(lon_row)
        layout.addWidget(btn_both)
        self.setLayout(layout)

        self._connected_layer = None
        self.iface.currentLayerChanged.connect(self.on_layer_changed)
        self.on_layer_changed(self.iface.activeLayer())

    def copy_text(self, text):
        QApplication.clipboard().setText(text)

    def copy_both(self):
        self.copy_text(f"{self.lat_edit.text()}, {self.lon_edit.text()}")

    def on_layer_changed(self, layer):
        if self._connected_layer is not None:
            try:
                self._connected_layer.selectionChanged.disconnect(self.update_coords)
            except (TypeError, RuntimeError):
                pass
            self._connected_layer = None

        if (
            layer is not None
            and layer.type() == layer.VectorLayer
            and layer.geometryType() == QgsWkbTypes.PointGeometry
        ):
            layer.selectionChanged.connect(self.update_coords)
            self._connected_layer = layer
            self.update_coords()
        else:
            self.status_label.setText("The active layer is not a vector point layer")
            self.lat_edit.clear()
            self.lon_edit.clear()

    def update_coords(self, *args):
        layer = self._connected_layer
        if layer is None:
            return

        selected = layer.selectedFeatures()
        if not selected:
            self.status_label.setText("No feature is selected")
            self.lat_edit.clear()
            self.lon_edit.clear()
            return

        source_crs = layer.crs()
        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())

        geom = selected[0].geometry()
        if geom is None or geom.isEmpty():
            self.status_label.setText("Empty geometry.")
            return

        if QgsWkbTypes.isMultiType(geom.wkbType()):
            pt = geom.asMultiPoint()[0]
        else:
            pt = geom.asPoint()

        pt_4326 = transform.transform(pt)
        lon, lat = pt_4326.x(), pt_4326.y()

        self.lat_edit.setText(f"{lat:.8f}")
        self.lon_edit.setText(f"{lon:.8f}")

        extra = ""
        if len(selected) > 1:
            extra = f" ({len(selected)} selected features, la 1ère est affichée)"
        self.status_label.setText(f"Point sélectionné{extra}.")

    def closeEvent(self, event):
        # Se déconnecte proprement à la fermeture pour éviter les erreurs
        if self._connected_layer is not None:
            try:
                self._connected_layer.selectionChanged.disconnect(self.update_coords)
            except (TypeError, RuntimeError):
                pass
        try:
            self.iface.currentLayerChanged.disconnect(self.on_layer_changed)
        except (TypeError, RuntimeError):
            pass
        event.accept()


class FinCoordsWGS84:
    """Classe principale du plugin, gère l'intégration dans l'interface QGIS."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.dialog = None

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        self.action = QAction(QIcon(icon_path), "FinCoords WGS84", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.action.setCheckable(False)

        # Ajoute un bouton dans la barre d'outils et une entrée dans le menu Extensions
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&FinCoords WGS84", self.action)

    def unload(self):
        self.iface.removePluginMenu("&FinCoords WGS84", self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.dialog is not None:
            self.dialog.close()
            self.dialog = None

    def run(self):
        # Réutilise la fenêtre si elle existe déjà plutôt que d'en ouvrir plusieurs
        if self.dialog is None:
            self.dialog = CoordPickerDialog(self.iface, self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
